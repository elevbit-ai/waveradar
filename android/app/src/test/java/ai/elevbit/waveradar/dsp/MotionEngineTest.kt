// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT

package ai.elevbit.waveradar.dsp

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin

class MotionEngineTest {

    @Test
    fun quietRoomStaysClearAndDoesNotInventDoppler() {
        val engine = MotionEngine(calibrationSeconds = 8.0, initialHoldSeconds = 30.0)
        var state = MotionState()
        var t = 0.0
        val dt = 1.0 / 16.0
        while (t < 10.0) {
            engine.push(Frame(t, -52.0))
            state = engine.state()
            t += dt
        }
        assertEquals(Presence.CLEAR, state.presence)
        assertTrue("score ${state.score}", state.score < 0.15)
        assertNull(state.dopplerHz)
        assertTrue(state.rssi == -52.0)
    }

    @Test
    fun walkingSineRaisesPresenceAndDoppler() {
        val engine = MotionEngine(calibrationSeconds = 8.0, initialHoldSeconds = 30.0)
        var t = 0.0
        val dt = 1.0 / 16.0
        while (t < 8.2) {
            engine.push(Frame(t, -52.0))
            engine.state()
            t += dt
        }
        var state = MotionState()
        val start = t
        while (t < start + 6.0) {
            val rssi = -52.0 + 4.0 * sin(2.0 * PI * 1.0 * t)
            engine.push(Frame(t, rssi))
            state = engine.state()
            t += dt
        }
        assertEquals(
            "score=${state.score} fps=${state.fps} eff=${state.effectiveHz}",
            Presence.MOVING,
            state.presence,
        )
        assertTrue(state.score > 0.5)
        val doppler = state.dopplerHz
        assertNotNull("fps=${state.fps} eff=${state.effectiveHz} score=${state.score}", doppler)
        assertTrue("doppler=$doppler", abs(doppler!! - 1.0) < 0.3)
        assertTrue(state.spectrum.isNotEmpty())
    }

    @Test
    fun presenceHoldsAfterMotionThenClears() {
        val engine = MotionEngine(calibrationSeconds = 8.0, initialHoldSeconds = 5.0)
        var t = 0.0
        val dt = 1.0 / 16.0
        while (t < 8.2) {
            engine.push(Frame(t, -50.0))
            engine.state()
            t += dt
        }
        val motionStart = t
        while (t < motionStart + 4.0) {
            val rssi = -50.0 + 5.0 * sin(2.0 * PI * 0.8 * t)
            engine.push(Frame(t, rssi))
            engine.state()
            t += dt
        }
        var state = engine.state()
        assertEquals(Presence.MOVING, state.presence)

        val quietStart = t
        while (t < quietStart + 5.0) {
            engine.push(Frame(t, -50.0))
            state = engine.state()
            t += dt
        }
        assertEquals(Presence.PRESENT, state.presence)

        while (t < quietStart + 20.0) {
            engine.push(Frame(t, -50.0))
            state = engine.state()
            t += dt
        }
        assertEquals(Presence.CLEAR, state.presence)
        assertNull(state.dopplerHz)
    }

    @Test
    fun rfftPeaksOnATwoHertzTone() {
        val n = 64
        val fs = 16.0
        val x = DoubleArray(n) { i ->
            val w = 0.5 - 0.5 * kotlin.math.cos(2.0 * PI * i / (n - 1))
            w * sin(2.0 * PI * 2.0 * i / fs)
        }
        val mag = MotionEngine.rfftMagnitude(x)
        val df = fs / n
        var bestK = 0
        for (k in mag.indices) if (mag[k] > mag[bestK]) bestK = k
        assertEquals(2.0, bestK * df, 0.26)
    }
}
