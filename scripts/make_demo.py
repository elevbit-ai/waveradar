"""
Render the WaveRadar demo animation (GIF + optional MP4).

Feeds the *real* DSP pipeline (waveradar.dsp.MotionEngine) with the
simulator source and draws the radar exactly like the web UI does, frame
by frame, with PIL.  Output: docs/assets/demo.gif (+ demo.mp4 if ffmpeg
is available) and docs/assets/screenshot.png.

Usage:  python scripts/make_demo.py

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from waveradar.dsp import MotionEngine  # noqa: E402
from waveradar.sources.simulator import SimulatorSource  # noqa: E402

OUT = ROOT / "docs" / "assets"
W, H = 560, 668
RADAR_H = 520
CX, CY, R = W // 2, RADAR_H // 2 + 10, 230

BG = (5, 13, 10)
LINE = (15, 43, 30)
GREEN = (43, 255, 136)
GREEN_DIM = (15, 145, 80)
AMBER = (255, 199, 77)
RED = (255, 93, 93)
TEXT = (201, 244, 221)
MUTED = (94, 143, 118)

FPS_OUT = 10          # display frames per second
DURATION = 30         # seconds
SIM_FS = 20.0

LEVEL_COLOR = {"calibrating": (51, 96, 74), "idle": MUTED, "low": GREEN,
               "motion": AMBER, "strong": RED}


def font(size: int):
    for name in ("consola.ttf", "cour.ttf"):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            continue
    return ImageFont.load_default()


F_SM, F_MD, F_LG = font(13), font(16), font(26)


def draw_frame(state: dict, sweep: float, blips: list) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")

    # title
    d.text((18, 12), "WAVERADAR", font=F_LG, fill=GREEN)
    d.text((190, 22), "Wi-Fi sensing motion radar", font=F_SM, fill=MUTED)

    # rings + spokes
    for k in range(1, 5):
        r = R * k / 4
        d.ellipse([CX - r, CY - r, CX + r, CY + r], outline=LINE, width=1)
    for a in range(0, 360, 30):
        rad = math.radians(a - 90)
        d.line([CX, CY, CX + R * math.cos(rad), CY + R * math.sin(rad)],
               fill=LINE, width=1)
        lx = CX + (R + 16) * math.cos(rad)
        ly = CY + (R + 16) * math.sin(rad)
        d.text((lx, ly), f"{a}°", font=F_SM, fill=(51, 96, 74), anchor="mm")

    # sweep wedge (trailing fade)
    for i in range(28):
        a = sweep - i * 1.8
        rad = math.radians(a - 90)
        alpha = int(80 * (1 - i / 28))
        d.line([CX, CY, CX + R * math.cos(rad), CY + R * math.sin(rad)],
               fill=(43, 255, 136, alpha), width=3)
    rad = math.radians(sweep - 90)
    d.line([CX, CY, CX + R * math.cos(rad), CY + R * math.sin(rad)],
           fill=(140, 255, 190, 230), width=2)

    # blips
    for b in blips:
        age = b["age"] / 26.0
        if age >= 1:
            continue
        alpha = (1 - age) * (0.35 + 0.65 * b["i"])
        brad = math.radians(b["a"] - 90)
        x = CX + R * b["r"] * math.cos(brad)
        y = CY + R * b["r"] * math.sin(brad)
        size = 3 + 7 * b["i"]
        hot = b["i"] > 0.7
        core = RED if hot else GREEN
        for mult, aa in ((3.0, 0.18), (1.8, 0.35), (0.8, 1.0)):
            d.ellipse([x - size * mult, y - size * mult,
                       x + size * mult, y + size * mult],
                      fill=core + (int(255 * alpha * aa),))
    d.ellipse([CX - 3, CY - 3, CX + 3, CY + 3], fill=GREEN)

    # ---- bottom panel -------------------------------------------------
    top = RADAR_H + 14
    d.line([14, top - 6, W - 14, top - 6], fill=LINE, width=1)
    lvl = state["level"]
    d.text((18, top + 4), lvl.upper(), font=F_LG,
           fill=LEVEL_COLOR.get(lvl, MUTED))
    d.text((18, top + 40), f"score {state['score']:.2f}   "
           f"doppler {state['doppler_hz']:.2f} Hz   "
           f"rssi {state['rssi']:.0f} dBm",
           font=F_SM, fill=TEXT)
    d.text((18, top + 60), "CSI · 52 subcarriers · sim source",
           font=F_SM, fill=MUTED)

    # score meter
    mw = 220
    d.rectangle([W - mw - 18, top + 8, W - 18, top + 20],
                outline=LINE, width=1)
    fill_w = int((mw - 2) * state["score"])
    if fill_w > 0:
        c = RED if state["score"] > 0.72 else \
            AMBER if state["score"] > 0.38 else GREEN
        d.rectangle([W - mw - 17, top + 9,
                     W - mw - 17 + fill_w, top + 19], fill=c)

    # doppler spectrum
    spec = state.get("spectrum") or []
    if spec:
        sw, sh = mw, 42
        x0, y0 = W - mw - 18, top + 30
        d.rectangle([x0, y0, x0 + sw, y0 + sh], outline=LINE, width=1)
        bw = sw / len(spec)
        for i, v in enumerate(spec):
            c = RED if v > 0.75 else AMBER if v > 0.45 else GREEN
            bh = int((sh - 2) * v)
            if bh > 0:
                d.rectangle([x0 + 1 + i * bw, y0 + sh - 1 - bh,
                             x0 + max(1, bw - 1) + i * bw, y0 + sh - 1],
                            fill=c)
        d.text((x0, y0 + sh + 4), "doppler spectrum 0.15–4 Hz",
               font=F_SM, fill=MUTED)

    d.text((W // 2, H - 16),
           "WaveRadar · © 2026 Joaquim Pedro de Morais Filho",
           font=F_SM, fill=MUTED, anchor="mm")
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sim = SimulatorSource(realtime=False)
    engine = MotionEngine()
    it = iter(sim)

    sim_per_frame = int(SIM_FS / FPS_OUT)
    n_frames = DURATION * FPS_OUT
    frames, blips = [], []
    sweep = 0.0
    screenshot = None

    for k in range(n_frames):
        for _ in range(sim_per_frame):
            engine.push(next(it))
        st = engine.state().to_dict()
        for b in blips:
            b["age"] += 1
        blips = [b for b in blips if b["age"] < 26]
        for p in st["points"]:
            blips.append({"a": p["a"], "r": p["r"], "i": p["i"], "age": 0})
        sweep = (sweep + 4.6) % 360
        img = draw_frame(st, sweep, blips)
        frames.append(img.quantize(colors=128, dither=Image.Dither.NONE))
        if screenshot is None and st["level"] in ("motion", "strong"):
            screenshot = img
        if k % 50 == 0:
            print(f"  frame {k}/{n_frames}  level={st['level']} "
                  f"score={st['score']:.2f}")

    gif = OUT / "demo.gif"
    frames[0].save(gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / FPS_OUT), loop=0, optimize=True)
    print(f"wrote {gif}  ({gif.stat().st_size/1e6:.1f} MB)")

    if screenshot is not None:
        shot = OUT / "screenshot.png"
        screenshot.save(shot)
        print(f"wrote {shot}")

    if shutil.which("ffmpeg"):
        mp4 = OUT / "demo.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(gif), "-movflags", "faststart",
             "-pix_fmt", "yuv420p",
             "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
             str(mp4)],
            check=True, capture_output=True)
        print(f"wrote {mp4}  ({mp4.stat().st_size/1e6:.1f} MB)")
    else:
        print("ffmpeg not found — GIF only (that's fine).")


if __name__ == "__main__":
    main()
