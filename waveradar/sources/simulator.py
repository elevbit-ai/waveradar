"""
Simulator source — synthetic 52-subcarrier CSI with a target that
alternates between stillness, walking and fast movement.

Used for the demo video, UI development and for trying WaveRadar without
any hardware:  `python -m waveradar --source sim`

The synthesis follows the physics the real system exploits: a moving body
perturbs a subset of multipath components, which modulates the amplitude
of a *correlated group* of subcarriers at the body's Doppler frequency.

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import math
import random
import time

from ..dsp import Frame

N_SC = 52


class SimulatorSource:
    name = "simulator"

    def __init__(self, fs: float = 20.0, realtime: bool = True,
                 seed: int = 7):
        self.fs = fs
        self.realtime = realtime
        self.rng = random.Random(seed)
        self.base = [8.0 + 4.0 * math.sin(i / 6.0) +
                     self.rng.uniform(-0.5, 0.5) for i in range(N_SC)]
        # scenario: (duration s, doppler Hz, strength, centre subcarrier)
        self.script = [
            (6.0, 0.0, 0.00, 0),    # empty room
            (6.0, 0.9, 0.55, 12),   # person walks in
            (5.0, 0.3, 0.30, 20),   # slows down / gestures
            (5.0, 1.8, 0.85, 34),   # fast crossing
            (6.0, 0.0, 0.00, 0),    # still again
            (5.0, 0.6, 0.45, 44),   # moves near the far wall
        ]

    def __iter__(self):
        t = 0.0
        dt = 1.0 / self.fs
        t0 = time.time()
        k = 0
        while True:
            # locate scenario segment (loops)
            total = sum(s[0] for s in self.script)
            tt = t % total
            acc = 0.0
            dop, strength, centre = 0.0, 0.0, 0
            for dur, d, s, c in self.script:
                if tt < acc + dur:
                    dop, strength, centre = d, s, c
                    # soft edges
                    edge = min(tt - acc, acc + dur - tt)
                    strength *= min(1.0, edge / 0.8)
                    break
                acc += dur

            amps = []
            for i in range(N_SC):
                a = self.base[i]
                a += 0.12 * math.sin(2 * math.pi * 0.02 * t + i)  # slow drift
                if strength > 0:
                    # Gaussian footprint over subcarriers around `centre`
                    w = math.exp(-((i - centre) ** 2) / (2 * 6.0 ** 2))
                    a += (strength * 2.2 * w *
                          math.sin(2 * math.pi * dop * t + i * 0.4))
                    a += (strength * 0.7 * w *
                          math.sin(2 * math.pi * dop * 2.1 * t + i))
                a += self.rng.gauss(0, 0.10)
                amps.append(max(0.1, a))

            rssi = -52.0 + 1.5 * math.sin(2 * math.pi * 0.01 * t)
            rssi += strength * 1.8 * math.sin(2 * math.pi * dop * t)
            rssi += self.rng.gauss(0, 0.25)

            yield Frame(t=t0 + t, rssi=rssi, amps=amps)
            t += dt
            k += 1
            if self.realtime:
                target = t0 + t
                now = time.time()
                if target > now:
                    time.sleep(target - now)
