// WaveRadar — motion and presence from one Wi-Fi RSSI stream.
// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT
//
// Android reports the associated access point's RSSI, often only a few times
// per second and sometimes slower. That is enough to notice a body perturbing
// the phone↔router link (variance against a quiet baseline, then a presence
// hold). It is not enough for a 0.15–4 Hz Doppler estimate unless the phone
// is actually delivering samples at 8 Hz or faster. This engine refuses to
// invent that frequency.

package ai.elevbit.waveradar.dsp

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.hypot
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

enum class Level { CALIBRATING, IDLE, LOW, MOTION, STRONG }

enum class Presence { CALIBRATING, CLEAR, PRESENT, MOVING }

data class Frame(val t: Double, val rssi: Double)

data class MotionState(
    val t: Double = 0.0,
    val score: Double = 0.0,
    val level: Level = Level.CALIBRATING,
    val presence: Presence = Presence.CALIBRATING,
    val rssi: Double = -100.0,
    val fps: Double = 0.0,
    val effectiveHz: Double = 0.0,
    val dopplerHz: Double? = null,
    val spectrum: List<Double> = emptyList(),
    val stdDb: Double = 0.0,
    val samples: Int = 0,
    val calibrationProgress: Double = 0.0,
    val trace: List<Double> = emptyList(),
)

class MotionEngine(
    private val calibrationSeconds: Double = 8.0,
    initialHoldSeconds: Double = 30.0,
) {
    var presenceHoldSec: Double = initialHoldSeconds
        set(value) {
            field = value.coerceIn(10.0, 180.0)
        }

    private val frames = ArrayDeque<Frame>()
    private var startT: Double? = null
    private var lastT: Double? = null
    private var fps = 0.0
    private var samples = 0
    private var analysed = -1
    private var calibrated = false
    private var baseline = 0.20
    private var score = 0.0
    private var lastMotionT = Double.NEGATIVE_INFINITY

    fun reset() {
        frames.clear()
        startT = null
        lastT = null
        fps = 0.0
        samples = 0
        analysed = -1
        calibrated = false
        baseline = 0.20
        score = 0.0
        lastMotionT = Double.NEGATIVE_INFINITY
    }

    fun push(frame: Frame) {
        if (startT == null) startT = frame.t
        val prev = lastT
        if (prev != null) {
            val dt = frame.t - prev
            if (dt > 0.0) {
                val inst = 1.0 / dt
                fps = if (fps == 0.0) inst else fps * 0.9 + inst * 0.1
            }
        }
        lastT = frame.t
        frames.addLast(frame)
        while (frames.size > CAPACITY) frames.removeFirst()
        samples++
    }

    fun state(): MotionState {
        val last = frames.lastOrNull()
        val elapsed = if (startT != null && last != null) last.t - startT!! else 0.0
        val progress = (elapsed / calibrationSeconds).coerceIn(0.0, 1.0)
        if (!calibrated && elapsed >= calibrationSeconds && frames.size >= 24) {
            calibrated = true
            baseline = max(stddev(recent(4.0)), 0.20)
        }

        val fresh = samples != analysed
        analysed = samples

        val std = if (frames.size >= 4) stddev(recent(4.0)) else 0.0
        if (fresh && calibrated && fps > 0.0) {
            val dt = 1.0 / fps
            val alpha = min(1.0, dt / BASELINE_TC)
            if (std < baseline) {
                baseline += (std - baseline) * min(1.0, alpha * 20.0)
            } else {
                baseline += (std - baseline) * alpha
            }
            baseline = max(baseline, 0.15)
            val ratio = std / baseline
            val raw = 1.0 - exp(-max(0.0, log10(max(ratio, 1e-6))) / 0.45)
            val k = if (raw > score) SCORE_ATTACK else SCORE_DECAY
            score += (raw.coerceIn(0.0, 1.0) - score) * k
            if (score > 0.38) lastMotionT = last?.t ?: lastMotionT
        }

        val level = when {
            !calibrated -> Level.CALIBRATING
            score > 0.72 -> Level.STRONG
            score > 0.38 -> Level.MOTION
            score > 0.18 -> Level.LOW
            else -> Level.IDLE
        }
        val moving = calibrated && score > 0.38
        val held = calibrated && last != null && (last.t - lastMotionT) <= presenceHoldSec
        val presence = when {
            !calibrated -> Presence.CALIBRATING
            moving -> Presence.MOVING
            held -> Presence.PRESENT
            else -> Presence.CLEAR
        }

        val eff = effectiveHz()
        val xs = recent(6.0)
        val doppler = if (calibrated && score > 0.25 && fps >= 8.0 && eff >= 4.0 && xs.size >= 48) {
            dominantDoppler(xs, fps)
        } else {
            null
        }
        val spectrum = if (doppler != null && xs.size >= 48) bandShape(xs, fps) else emptyList()

        return MotionState(
            t = last?.t ?: 0.0,
            score = if (calibrated) score else 0.0,
            level = level,
            presence = presence,
            rssi = last?.rssi ?: -100.0,
            fps = fps,
            effectiveHz = eff,
            dopplerHz = doppler,
            spectrum = spectrum,
            stdDb = std,
            samples = samples,
            calibrationProgress = if (calibrated) 1.0 else progress,
            trace = frames.takeLast(48).map { it.rssi },
        )
    }

    private fun recent(seconds: Double): DoubleArray {
        if (frames.isEmpty()) return DoubleArray(0)
        val cut = frames.last().t - seconds
        val out = ArrayList<Double>()
        for (f in frames) if (f.t >= cut) out.add(f.rssi)
        return out.toDoubleArray()
    }

    /** How often the reported RSSI actually changes, not how often we poll. */
    private fun effectiveHz(): Double {
        if (frames.size < 2) return 0.0
        val end = frames.last().t
        val cut = end - 12.0
        var changes = 0
        var firstT = 0.0
        var prev: Frame? = null
        var seen = 0
        for (f in frames) {
            if (f.t < cut) continue
            if (seen == 0) firstT = f.t
            val p = prev
            if (p != null && abs(f.rssi - p.rssi) >= 0.6) changes++
            prev = f
            seen++
        }
        val span = end - firstT
        if (seen < 2 || span <= 0.2) return 0.0
        return changes / span
    }

    companion object {
        private const val CAPACITY = 512
        private const val BASELINE_TC = 30.0
        private const val SCORE_ATTACK = 0.55
        private const val SCORE_DECAY = 0.25

        fun stddev(xs: DoubleArray): Double {
            if (xs.size < 2) return 0.0
            var m = 0.0
            for (x in xs) m += x
            m /= xs.size
            var a = 0.0
            for (x in xs) {
                val d = x - m
                a += d * d
            }
            return sqrt(a / (xs.size - 1))
        }

        fun dominantDoppler(xs: DoubleArray, fs: Double): Double? {
            val built = spectrum(xs, fs) ?: return null
            var bestK = -1
            var best = 0.0
            for (k in built.mag.indices) {
                val f = k * built.df
                if (f < 0.15 || f > built.hi) continue
                if (built.mag[k] > best) {
                    best = built.mag[k]
                    bestK = k
                }
            }
            if (bestK < 0 || best <= 0.0) return null
            return bestK * built.df
        }

        fun bandShape(xs: DoubleArray, fs: Double): List<Double> {
            val built = spectrum(xs, fs) ?: return emptyList()
            var peak = 1e-9
            val picked = ArrayList<Double>()
            for (k in built.mag.indices) {
                val f = k * built.df
                if (f < 0.15 || f > built.hi) continue
                peak = max(peak, built.mag[k])
                picked.add(built.mag[k])
            }
            if (picked.isEmpty()) return emptyList()
            return picked.map { (it / peak).coerceIn(0.0, 1.0) }
        }

        private data class Spec(val mag: DoubleArray, val df: Double, val hi: Double)

        private fun spectrum(xs: DoubleArray, fs: Double): Spec? {
            if (xs.size < 48 || fs < 8.0) return null
            val n = min(64, xs.size)
            val slice = xs.copyOfRange(xs.size - n, xs.size)
            var mean = 0.0
            for (v in slice) mean += v
            mean /= n
            for (i in slice.indices) {
                val w = 0.5 - 0.5 * cos(2.0 * PI * i / (n - 1))
                slice[i] = (slice[i] - mean) * w
            }
            return Spec(
                mag = rfftMagnitude(slice),
                df = fs / n,
                hi = min(4.0, fs * 0.45),
            )
        }

        fun rfftMagnitude(x: DoubleArray): DoubleArray {
            val n = x.size
            val bins = n / 2 + 1
            val mag = DoubleArray(bins)
            for (k in 0 until bins) {
                var re = 0.0
                var im = 0.0
                val w = -2.0 * PI * k / n
                for (i in x.indices) {
                    val a = w * i
                    re += x[i] * cos(a)
                    im += x[i] * sin(a)
                }
                mag[k] = hypot(re, im)
            }
            return mag
        }
    }
}
