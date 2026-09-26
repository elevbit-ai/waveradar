"""
WaveRadar signal sources.

Every source is an iterator of :class:`waveradar.dsp.Frame` objects.

  windows  — RSSI polled from the Wi-Fi adapter via `netsh` (no extra hardware)
  linux    — RSSI polled from /proc/net/wireless or `iw`
  esp32    — per-subcarrier CSI streamed over USB serial from an ESP32
  sim      — synthetic CSI with a moving target (demo / development)
  auto     — esp32 if a serial port is given, otherwise the OS RSSI source

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import sys


def create(name: str, serial_port: str | None = None):
    name = (name or "auto").lower()
    if name == "auto":
        if serial_port:
            name = "esp32"
        elif sys.platform.startswith("win"):
            name = "windows"
        else:
            name = "linux"

    if name == "sim":
        from .simulator import SimulatorSource
        return SimulatorSource()
    if name == "windows":
        from .windows_rssi import WindowsRssiSource
        return WindowsRssiSource()
    if name == "linux":
        from .linux_rssi import LinuxRssiSource
        return LinuxRssiSource()
    if name == "esp32":
        from .esp32_csi import Esp32CsiSource
        return Esp32CsiSource(serial_port)
    raise ValueError(f"unknown source: {name!r} "
                     "(expected auto|sim|windows|linux|esp32)")
