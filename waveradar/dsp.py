"""
WaveRadar — signal processing core.

Turns a stream of Wi-Fi channel measurements (RSSI or per-subcarrier CSI
amplitudes) into motion information:

  * motion score   — adaptive, baseline-normalised band energy
  * Doppler        — FFT of the detrended channel over a sliding window,
                     restricted to the human-motion band (0.15 – 4 Hz)
  * radar points   — per-sector motion energy projected onto a polar view

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
License: MIT
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

# ----------------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------------

WINDOW = 64          # samples per analysis window (sliding)
SECTORS = 12         # angular sectors on the radar display
BAND_LO = 0.15       # Hz — below this is drift / breathing tail
BAND_HI = 4.0        # Hz — above this is noise for body-scale motion
BASELINE_TC = 30.0   # s  — time constant of the quiet-baseline tracker
SCORE_ATTACK = 0.55  # EWMA factor when score rises (fast attack)
SCORE_DECAY = 0.25   # EWMA factor when score falls (release)


@dataclass
class Frame:
    """One measurement from a source."""
    t: float                                  # unix timestamp
    rssi: float                               # dBm
    amps: Optional[List[float]] = None        # per-subcarrier amplitude (CSI)
    phases: Optional[List[float]] = None      # per-subcarrier phase (CSI)


@dataclass
class RadarPoint:
    angle: float      # degrees, 0 = north, clockwise
    r: float          # 0..1 normalised range
    intensity: float  # 0..1


@dataclass
class MotionState:
    t: float = 0.0
    score: float = 0.0            # 0..1 motion score
    level: str = "idle"           # idle | low | motion | strong
    rssi: float = -100.0
    fps: float = 0.0
    doppler_hz: float = 0.0       # dominant motion frequency
    spectrum: List[float] = field(default_factory=list)   # 0..1 bins, lo..hi
    points: List[RadarPoint] = field(default_factory=list)
    csi: bool = False             # true when per-subcarrier data is present
    samples: int = 0

    def to_dict(self) -> dict:
        return {
            "t": self.t,
            "score": round(self.score, 4),
            "level": self.level,
            "rssi": round(self.rssi, 1),
            "fps": round(self.fps, 2),
            "doppler_hz": round(self.doppler_hz, 3),
            "spectrum": [round(v, 4) for v in self.spectrum],
            "points": [
                {"a": round(p.angle, 1), "r": round(p.r, 3),
                 "i": round(p.intensity, 3)}
                for p in self.points
            ],
            "csi": self.csi,
            "samples": self.samples,
        }


class MotionEngine:
    """Sliding-window motion analysis over RSSI or CSI frames."""

    def __init__(self, window: int = WINDOW, sectors: int = SECTORS):
        self.window = window
        self.sectors = sectors
        self.frames: deque[Frame] = deque(maxlen=window)
        self.baseline: Optional[float] = None      # quiet band-energy level
        self.score = 0.0
        self.samples = 0
        self._last_t: Optional[float] = None
        self._fps = 0.0
        self._sector_smooth = np.zeros(sectors)
        self._warmed = False

    # -- public ---------------------------------------------------------

    def push(self, frame: Frame) -> None:
        if self._last_t is not None:
            dt = frame.t - self._last_t
            if dt > 0:
                inst = 1.0 / dt
                self._fps = 0.9 * self._fps + 0.1 * inst if self._fps else inst
        self._last_t = frame.t
        self.frames.append(frame)
        self.samples += 1

    def state(self) -> MotionState:
        st = MotionState()
        if not self.frames:
            return st
        last = self.frames[-1]
        st.t = last.t
        st.rssi = last.rssi
        st.fps = self._fps
        st.samples = self.samples
        st.csi = last.amps is not None

        if len(self.frames) < max(16, self.window // 4) or self._fps <= 0:
            return st

        # Build the channel matrix: (n_samples, n_channels).
        # CSI: one channel per subcarrier.  RSSI-only: a single channel.
        if st.csi:
            n_sc = min(len(f.amps) for f in self.frames if f.amps)
            mat = np.array([f.amps[:n_sc] for f in self.frames
                            if f.amps], dtype=float)
        else:
            mat = np.array([[f.rssi] for f in self.frames], dtype=float)

        fs = self._fps
        n = mat.shape[0]

        # Detrend each channel (remove the static path / slow drift).
        mat = mat - mat.mean(axis=0, keepdims=True)
        taper = np.hanning(n)[:, None]
        spec = np.abs(np.fft.rfft(mat * taper, axis=0))
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)

        band = (freqs >= BAND_LO) & (freqs <= BAND_HI)
        if not band.any():
            return st

        band_spec = spec[band]                       # (n_bins, n_channels)
        band_freqs = freqs[band]

        # Aggregate Doppler spectrum across channels.
        agg = band_spec.mean(axis=1)
        peak = float(agg.max()) or 1.0
        st.doppler_hz = float(band_freqs[int(np.argmax(agg))])

        # Band energy per channel → total motion energy.
        energy = float((band_spec ** 2).mean())

        # Warm-up: while the window is still filling, the spectral estimate
        # is not comparable between calls (bin spacing changes) — report calm
        # and start the baseline fresh on the first full window.
        if len(self.frames) < self.window:
            st.level = "calibrating"
            st.spectrum = [0.0] * int(band.sum())
            return st
        if not self._warmed:
            self.baseline = energy
            self._warmed = True

        # Adaptive quiet baseline (only tracks *down* fast, up slowly, so a
        # person moving does not become the new "quiet").
        if self.baseline is None:
            self.baseline = energy
        else:
            alpha = min(1.0, (1.0 / fs) / BASELINE_TC)
            if energy < self.baseline:
                self.baseline += (energy - self.baseline) * min(1.0, alpha * 20)
            else:
                self.baseline += (energy - self.baseline) * alpha
        base = max(self.baseline, 1e-9)

        # Score: how far above the quiet floor we are (log ratio, squashed).
        ratio = energy / base
        raw = 1.0 - math.exp(-max(0.0, math.log10(max(ratio, 1e-6))) / 0.55)
        raw = float(np.clip(raw, 0.0, 1.0))
        k = SCORE_ATTACK if raw > self.score else SCORE_DECAY
        self.score += (raw - self.score) * k
        st.score = self.score
        st.level = ("strong" if st.score > 0.72 else
                    "motion" if st.score > 0.38 else
                    "low" if st.score > 0.15 else "idle")

        # Spectrum for display: peak-normalised shape, scaled by the motion
        # score so a quiet room shows a quiet spectrum.
        scale = 0.06 + 0.94 * self.score
        st.spectrum = list(np.clip(agg / peak * scale, 0, 1))

        # ---- radar points ------------------------------------------------
        # With CSI, subcarrier groups react differently depending on which
        # multipath components the moving body perturbs; we project that
        # structure onto angular sectors (a stable pseudo-bearing — see the
        # README for what this does and does not mean physically).
        n_ch = mat.shape[1]
        ch_energy = (band_spec ** 2).mean(axis=0)    # per-channel band energy
        sec = np.zeros(self.sectors)
        if n_ch >= self.sectors:
            groups = np.array_split(ch_energy, self.sectors)
            sec = np.array([g.mean() for g in groups])
        else:
            # RSSI-only: spread the single channel across sectors with a
            # deterministic rotation so the display still conveys activity.
            phase = (st.t * 0.35) % 1.0
            idx = int(phase * self.sectors)
            sec[idx] = ch_energy.mean()
            sec[(idx + 1) % self.sectors] = ch_energy.mean() * 0.5

        sec_norm = sec / (sec.max() + 1e-12)
        self._sector_smooth = 0.6 * self._sector_smooth + 0.4 * sec_norm

        # Range ring: faster dominant Doppler ⇒ larger radial velocity ⇒
        # rendered closer to the centre (stronger interaction with the link).
        rng = float(np.clip(1.0 - (st.doppler_hz - BAND_LO) /
                            (BAND_HI - BAND_LO), 0.15, 0.95))

        pts: List[RadarPoint] = []
        if st.score > 0.12:
            for i, e in enumerate(self._sector_smooth):
                inten = float(e * st.score)
                if inten < 0.10:
                    continue
                ang = (i + 0.5) * (360.0 / self.sectors)
                jitter = (hash((i, int(st.t * 2))) % 100) / 100.0 - 0.5
                pts.append(RadarPoint(
                    angle=(ang + jitter * 10.0) % 360.0,
                    r=float(np.clip(rng + jitter * 0.08, 0.1, 0.97)),
                    intensity=min(1.0, inten * 1.4),
                ))
        st.points = pts
        return st
