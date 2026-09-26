"""
Linux RSSI source — reads /proc/net/wireless (fast, no subprocess) and
falls back to `iw dev <iface> link`.

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import re
import subprocess
import time

from ..dsp import Frame

_IW_SIGNAL = re.compile(r"signal:\s*(-?\d+)\s*dBm")


def _read_proc() -> float | None:
    try:
        with open("/proc/net/wireless") as f:
            lines = f.readlines()
    except OSError:
        return None
    for line in lines[2:]:
        parts = line.split()
        if len(parts) >= 4:
            try:
                return float(parts[3].rstrip("."))
            except ValueError:
                continue
    return None


def _default_iface() -> str | None:
    try:
        out = subprocess.run(["iw", "dev"], capture_output=True,
                             text=True, timeout=3).stdout
    except OSError:
        return None
    m = re.search(r"Interface\s+(\S+)", out)
    return m.group(1) if m else None


class LinuxRssiSource:
    name = "linux-rssi"

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self._iface = None

    def _read_iw(self) -> float | None:
        if self._iface is None:
            self._iface = _default_iface()
            if self._iface is None:
                return None
        try:
            out = subprocess.run(["iw", "dev", self._iface, "link"],
                                 capture_output=True, text=True,
                                 timeout=3).stdout
        except OSError:
            return None
        m = _IW_SIGNAL.search(out)
        return float(m.group(1)) if m else None

    def __iter__(self):
        while True:
            t0 = time.time()
            rssi = _read_proc()
            if rssi is None:
                rssi = self._read_iw()
            if rssi is not None:
                yield Frame(t=time.time(), rssi=rssi)
            else:
                time.sleep(1.0)
                continue
            elapsed = time.time() - t0
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
