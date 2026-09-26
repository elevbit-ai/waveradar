"""
Windows RSSI source — polls the wireless adapter through
`netsh wlan show interfaces`.

Works with any router and any Windows laptop/desktop with Wi-Fi; nothing to
install or flash.  Sampling rate is limited by netsh (~6–9 Hz), which is
enough for body-scale motion (the useful band is 0.15–4 Hz).

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import re
import subprocess
import time

from ..dsp import Frame

_SIGNAL = re.compile(r"^\s*(Signal|Sinal)\s*:\s*(\d+)\s*%", re.M | re.I)
_SSID = re.compile(r"^\s*SSID\s*:\s*(.+?)\s*$", re.M)


def _percent_to_dbm(pct: int) -> float:
    # Standard WlanSignalQuality mapping: quality = 2 * (dBm + 100)
    return pct / 2.0 - 100.0


class WindowsRssiSource:
    name = "windows-rssi"

    def __init__(self, interval: float = 0.12):
        self.interval = interval
        self.ssid: str | None = None

    def __iter__(self):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        while True:
            t0 = time.time()
            try:
                out = subprocess.run(
                    ["netsh", "wlan", "show", "interfaces"],
                    capture_output=True, text=True, timeout=3,
                    creationflags=flags,
                ).stdout
            except (subprocess.TimeoutExpired, OSError):
                time.sleep(0.5)
                continue

            m = _SIGNAL.search(out)
            if m:
                if self.ssid is None:
                    s = _SSID.search(out)
                    self.ssid = s.group(1) if s else "?"
                yield Frame(t=time.time(),
                            rssi=_percent_to_dbm(int(m.group(2))))
            else:
                # Not associated to any network — wait and retry.
                time.sleep(1.0)
                continue

            elapsed = time.time() - t0
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
