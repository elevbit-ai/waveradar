"""
ESP32 CSI source — true Channel State Information, one amplitude + phase
per OFDM subcarrier, streamed over USB serial.

Pair this with the firmware in `firmware/esp32/waveradar_csi/`, which prints
one line per received Wi-Fi frame:

    CSI_DATA,<rssi>,<n_pairs>,[i0,q0,i1,q1,...]

The same parser also accepts the CSV produced by Espressif's `esp-csi`
examples (any line containing a `[...]` block of integers; the first
negative integer before the block is taken as RSSI).

Requires:  pip install pyserial

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import math
import re
import time

from ..dsp import Frame

_BLOCK = re.compile(r"\[([-0-9,\s]+)\]")
_INTS = re.compile(r"-?\d+")


def parse_csi_line(line: str) -> Frame | None:
    """Parse one serial line into a Frame, or None if it is not CSI."""
    m = _BLOCK.search(line)
    if not m:
        return None
    raw = [int(v) for v in _INTS.findall(m.group(1))]
    if len(raw) < 8:
        return None
    head = line[:m.start()]
    rssi = -60.0
    for tok in _INTS.findall(head):
        v = int(tok)
        if -100 <= v <= -10:
            rssi = float(v)
            break
    amps, phases = [], []
    for i in range(0, len(raw) - 1, 2):
        im, re_ = raw[i], raw[i + 1]
        amps.append(math.hypot(re_, im))
        phases.append(math.atan2(im, re_))
    return Frame(t=time.time(), rssi=rssi, amps=amps, phases=phases)


def _autodetect_port() -> str | None:
    from serial.tools import list_ports
    for p in list_ports.comports():
        desc = (p.description or "").lower()
        if any(k in desc for k in ("cp210", "ch340", "ch910", "usb serial",
                                   "silicon labs", "esp32", "usb-serial")):
            return p.device
    ports = list(list_ports.comports())
    return ports[0].device if ports else None


class Esp32CsiSource:
    name = "esp32-csi"

    def __init__(self, port: str | None = None, baud: int = 921600):
        try:
            import serial  # noqa: F401
        except ImportError as e:
            raise SystemExit(
                "The esp32 source needs pyserial:  pip install pyserial"
            ) from e
        self.port = port
        self.baud = baud

    def __iter__(self):
        import serial
        port = self.port or _autodetect_port()
        if not port:
            raise SystemExit("No serial port found. Plug in the ESP32 or "
                             "pass --serial COMx / /dev/ttyUSB0.")
        print(f"[waveradar] reading CSI from {port} @ {self.baud}")
        with serial.Serial(port, self.baud, timeout=2) as ser:
            while True:
                try:
                    line = ser.readline().decode("utf-8", "ignore")
                except Exception:
                    time.sleep(0.2)
                    continue
                if not line:
                    continue
                frame = parse_csi_line(line)
                if frame is not None:
                    yield frame
