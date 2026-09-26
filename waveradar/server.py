"""
WaveRadar — local web server.

Stdlib-only HTTP server: serves the radar UI (waveradar/web/index.html) and
a JSON state endpoint (/api/state) that the UI polls at ~12 Hz.  A reader
thread pumps frames from the selected source into the MotionEngine.

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
License: MIT
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .dsp import MotionEngine

WEB_DIR = Path(__file__).parent / "web"


class _Hub:
    """Pumps frames into the engine and refreshes the analysed state at a
    fixed ~10 Hz, independent of how often (or whether) the UI polls —
    the baseline/score dynamics must not depend on HTTP traffic."""

    STATE_DT = 0.1

    def __init__(self, source, source_name: str):
        self.engine = MotionEngine()
        self.lock = threading.Lock()
        self.source = source
        self.source_name = source_name
        self.latest = {
            "t": 0, "score": 0.0, "level": "calibrating", "rssi": -100,
            "fps": 0.0, "doppler_hz": 0.0, "spectrum": [], "points": [],
            "csi": False, "samples": 0, "source": source_name,
        }
        self._last_state_t = 0.0

    def run_reader(self):
        for frame in self.source:
            with self.lock:
                self.engine.push(frame)
                if frame.t - self._last_state_t >= self.STATE_DT:
                    self._last_state_t = frame.t
                    st = self.engine.state().to_dict()
                    st["source"] = self.source_name
                    self.latest = st

    def state(self) -> dict:
        with self.lock:
            return self.latest


def _make_handler(hub: _Hub):
    index_html = (WEB_DIR / "index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep the console clean
            pass

        def _send(self, code: int, ctype: str, body: bytes):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", index_html)
            elif self.path.startswith("/api/state"):
                body = json.dumps(hub.state()).encode()
                self._send(200, "application/json", body)
            else:
                self._send(404, "text/plain", b"not found")

    return Handler


def serve(source, source_name: str, host: str = "127.0.0.1",
          port: int = 8347, open_browser: bool = True) -> None:
    hub = _Hub(source, source_name)
    threading.Thread(target=hub.run_reader, daemon=True).start()

    httpd = ThreadingHTTPServer((host, port), _make_handler(hub))
    url = f"http://{host}:{port}"
    print(f"[waveradar] source: {source_name}")
    print(f"[waveradar] radar UI: {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[waveradar] stopped.")
