"""
WaveRadar CLI.

    python -m waveradar                     # auto: router RSSI on this OS
    python -m waveradar --source sim        # no hardware, synthetic target
    python -m waveradar --source esp32 --serial COM5   # true CSI
    python -m waveradar --port 9000 --no-browser

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import argparse

from . import __version__
from .server import serve
from .sources import create


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="waveradar",
        description="Wi-Fi sensing motion radar — see movement through the "
                    "radio channel of your own router.",
    )
    ap.add_argument("--source", default="auto",
                    choices=["auto", "sim", "windows", "linux", "esp32"],
                    help="signal source (default: auto)")
    ap.add_argument("--serial", default=None, metavar="PORT",
                    help="serial port of the ESP32 (e.g. COM5, /dev/ttyUSB0)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8347)
    ap.add_argument("--no-browser", action="store_true",
                    help="do not open the browser automatically")
    ap.add_argument("--version", action="version",
                    version=f"waveradar {__version__}")
    args = ap.parse_args()

    src = create(args.source, serial_port=args.serial)
    serve(src, getattr(src, "name", args.source),
          host=args.host, port=args.port,
          open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
