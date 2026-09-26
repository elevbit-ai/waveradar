"""
Render the WaveRadar video tutorial (MP4, 1280x720, narrated in pt-BR).

Ten sections: opening, physics, install (Windows/Linux), the radar live
(driven by the real DSP pipeline), sensing modes, internals, ESP32,
honest limitations, closing.  Narration is synthesised with the Windows
pt-BR voice; each section's length follows its narration.

Usage:  python scripts/make_tutorial.py

Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import sys
import tempfile
import wave as wavemod
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from waveradar.dsp import MotionEngine  # noqa: E402
from waveradar.sources.simulator import SimulatorSource  # noqa: E402

W, H = 1280, 720
FPS = 24
OUT_MP4 = ROOT / "docs" / "assets" / "tutorial.mp4"
WORK = Path(tempfile.gettempdir()) / "waveradar_tutorial"
FRAMES = WORK / "frames"
AUDIO = WORK / "audio"

BG = (5, 13, 10)
PANEL = (8, 23, 17)
LINE = (15, 43, 30)
GREEN = (43, 255, 136)
GREEN_DIM = (15, 145, 80)
AMBER = (255, 199, 77)
RED = (255, 93, 93)
TEXT = (201, 244, 221)
MUTED = (94, 143, 118)
DARKLBL = (51, 96, 74)

LEVEL_COLOR = {"calibrating": DARKLBL, "idle": MUTED, "low": GREEN,
               "motion": AMBER, "strong": RED}
LEVEL_TEXT = {"calibrating": "CALIBRANDO", "idle": "PARADO", "low": "LEVE",
              "motion": "MOVIMENTO", "strong": "FORTE"}


# ---------------------------------------------------------------- fonts ----

def _font(file: str, size: int):
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{file}", size)
    except OSError:
        return ImageFont.load_default()


def seg(s): return _font("segoeui.ttf", s)
def segb(s): return _font("segoeuib.ttf", s)
def mono(s): return _font("consola.ttf", s)


def ease(p: float) -> float:
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def wrap(d: ImageDraw.ImageDraw, text: str, font, maxw: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def base_frame(kicker: str = "", title: str = "") -> tuple:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((50, 26), "WAVERADAR", font=segb(22), fill=GREEN)
    d.text((190, 32), "tutorial", font=seg(16), fill=MUTED)
    d.text((W - 50, 32), "elevbit-ai.github.io/waveradar", font=mono(15),
           fill=DARKLBL, anchor="ra")
    if kicker:
        d.text((50, 84), kicker.upper(), font=segb(15), fill=GREEN_DIM)
    if title:
        d.text((50, 106), title, font=segb(36), fill=TEXT)
    d.text((W // 2, H - 22), "© 2026 Joaquim Pedro de Morais Filho",
           font=seg(14), fill=DARKLBL, anchor="mm")
    return img, d


def bullet_list(d, items, x, y, maxw, t, per=1.0, font=None, gap=14,
                color=TEXT):
    """Draw bullets that fade in one after another (t in seconds)."""
    font = font or seg(22)
    lh = font.size + 8
    for i, it in enumerate(items):
        a = ease((t - i * per) / 0.5)
        if a <= 0:
            continue
        c = tuple(int(BG[j] + (color[j] - BG[j]) * a) for j in range(3))
        g = tuple(int(BG[j] + (GREEN[j] - BG[j]) * a) for j in range(3))
        d.ellipse([x, y + 9, x + 8, y + 17], fill=g)
        for line in wrap(d, it, font, maxw):
            d.text((x + 22, y), line, font=font, fill=c)
            y += lh
        y += gap


# ------------------------------------------------------------- sections ----

def sec_open(t, dur, k):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    # background mini radar, right side
    cx, cy, R = 990, 380, 240
    for i in range(1, 5):
        d.ellipse([cx - R * i / 4, cy - R * i / 4,
                   cx + R * i / 4, cy + R * i / 4], outline=LINE, width=1)
    for a in range(0, 360, 30):
        r_ = math.radians(a)
        d.line([cx, cy, cx + R * math.cos(r_), cy + R * math.sin(r_)],
               fill=LINE, width=1)
    sw = (t * 110) % 360
    for i in range(30):
        a = math.radians(sw - i * 2 - 90)
        alpha = int(70 * (1 - i / 30))
        d.line([cx, cy, cx + R * math.cos(a), cy + R * math.sin(a)],
               fill=(43, 255, 136, alpha), width=3)
    for ba, br in ((40, .55), (130, .7), (260, .4)):
        pa = ease((t - 1.2) / .8)
        a = math.radians(ba - 90)
        x, y = cx + R * br * math.cos(a), cy + R * br * math.sin(a)
        pulse = .6 + .4 * math.sin(t * 3 + ba)
        d.ellipse([x - 7, y - 7, x + 7, y + 7],
                  fill=(43, 255, 136, int(220 * pa * pulse)))
    # title
    a = ease(t / 1.0)
    c = tuple(int(BG[i] + (GREEN[i] - BG[i]) * a) for i in range(3))
    d.text((70, 250), "WAVERADAR", font=segb(74), fill=c)
    a2 = ease((t - .7) / 1.0)
    c2 = tuple(int(BG[i] + (TEXT[i] - BG[i]) * a2) for i in range(3))
    for i, ln in enumerate(["Radar de movimento pelo", "Wi-Fi do seu roteador"]):
        d.text((74, 350 + i * 40), ln, font=seg(30), fill=c2)
    a3 = ease((t - 1.6) / 1.0)
    c3 = tuple(int(BG[i] + (MUTED[i] - BG[i]) * a3) for i in range(3))
    d.text((74, 470), "CSI · Doppler · amplitude e fase", font=mono(20),
           fill=c3)
    d.text((74, 560), "Joaquim Pedro de Morais Filho", font=segb(24),
           fill=tuple(int(BG[i] + (TEXT[i] - BG[i]) * a3) for i in range(3)))
    d.text((74, 594), "j360074@hotmail.com · MIT License", font=seg(17),
           fill=c3)
    return img


def sec_physics(t, dur, k):
    img, d = base_frame("a física", "Como o Wi-Fi sente movimento")
    gy = 400
    # router
    rx = 180
    d.rounded_rectangle([rx - 45, gy - 22, rx + 45, gy + 22], 8,
                        fill=PANEL, outline=GREEN_DIM, width=2)
    d.text((rx, gy), "roteador", font=seg(15), fill=TEXT, anchor="mm")
    for ax in (-25, 0, 25):
        d.line([rx + ax, gy - 22, rx + ax, gy - 44], fill=GREEN_DIM, width=3)
    # receiver
    lx = 1100
    d.rounded_rectangle([lx - 50, gy - 22, lx + 50, gy + 22], 8,
                        fill=PANEL, outline=GREEN_DIM, width=2)
    d.text((lx, gy), "receptor", font=seg(15), fill=TEXT, anchor="mm")
    # person (walking bob)
    px = 620 + 30 * math.sin(t * .9)
    py = gy - 10 + 4 * math.sin(t * 5)
    d.ellipse([px - 12, py - 78, px + 12, py - 54], outline=AMBER, width=3)
    d.line([px, py - 54, px, py - 10], fill=AMBER, width=3)
    d.line([px - 22, py - 40, px + 22, py - 44], fill=AMBER, width=3)
    s_ = math.sin(t * 5)
    d.line([px, py - 10, px - 14 * s_ - 6, py + 26], fill=AMBER, width=3)
    d.line([px, py - 10, px + 14 * s_ + 6, py + 26], fill=AMBER, width=3)
    # expanding arcs from the router
    for i in range(5):
        r = ((t * 130 + i * 78) % 390) + 30
        alpha = int(150 * max(0, 1 - r / 420))
        d.arc([rx - r, gy - r, rx + r, gy + r], -55, 55,
              fill=(43, 255, 136, alpha), width=3)
    # perturbed arcs from body to receiver (wiggly)
    for i in range(3):
        r = ((t * 130 + i * 110) % 330) + 40
        alpha = int(130 * max(0, 1 - r / 360))
        wob = 6 * math.sin(t * 6 + i)
        d.arc([px - r + wob, py - 40 - r, px + r + wob, py - 40 + r],
              -45, 45, fill=(255, 199, 77, alpha), width=3)
    d.text((640, gy + 90), "o corpo em movimento perturba o multipercurso",
           font=seg(18), fill=MUTED, anchor="mm")
    # chips timed to narration thirds
    chips = ["Amplitude e fase mudam a cada passo",
             "Doppler: f\u2094 \u2248 2v/\u03bb  (movimento humano: 0,15\u20134 Hz)",
             "CSI: o canal medido em ~52 subportadoras"]
    per = dur / (len(chips) + 1.4)
    y = 540
    for i, c in enumerate(chips):
        a = ease((t - (i + 1) * per + 1.2) / .6)
        if a <= 0:
            continue
        wdt = d.textlength(c, font=seg(20)) + 40
        x0 = 80 + i * 20
        d.rounded_rectangle([x0, y, x0 + wdt, y + 42], 10,
                            fill=(8, 23, 17, int(255 * a)),
                            outline=(15, 145, 80, int(255 * a)), width=2)
        d.text((x0 + 20, y + 9), c, font=seg(20),
               fill=tuple(int(BG[j] + (TEXT[j] - BG[j]) * a)
                          for j in range(3)))
        y += 54
    return img


def _terminal(d, title, x, y, w_, h_):
    d.rounded_rectangle([x, y, x + w_, y + h_], 12, fill=(3, 17, 10),
                        outline=LINE, width=2)
    d.rectangle([x + 2, y + 2, x + w_ - 2, y + 34], fill=PANEL)
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([x + 16 + i * 24, y + 11, x + 30 + i * 24, y + 25], fill=c)
    d.text((x + w_ / 2, y + 18), title, font=seg(15), fill=MUTED, anchor="mm")


def _type_out(d, x, y, prompt, cmd, out_lines, t, t_type0, cps, out_start,
              out_per, cursor=True):
    f = mono(19)
    lh = 30
    d.text((x, y), prompt, font=f, fill=GREEN_DIM)
    px = x + d.textlength(prompt + " ", font=f)
    n = max(0, int((t - t_type0) * cps))
    shown = cmd[:n]
    d.text((px, y), shown, font=f, fill=TEXT)
    if cursor and (t < t_type0 + len(cmd) / cps + .4) and int(t * 2.4) % 2:
        cx = px + d.textlength(shown, font=f)
        d.rectangle([cx + 2, y + 2, cx + 12, y + 24], fill=GREEN)
    yy = y + lh + 8
    for i, (ln, col) in enumerate(out_lines):
        if t >= out_start + i * out_per:
            d.text((x, yy), ln, font=mono(17), fill=col)
            yy += 26
    return yy


def sec_install_win(t, dur, k):
    img, d = base_frame("instalação · windows", "Uma linha no PowerShell")
    _terminal(d, "Windows PowerShell", 80, 180, 1120, 420)
    cmd = "irm https://elevbit-ai.github.io/waveradar/install.ps1 | iex"
    out = [
        ("", MUTED),
        ("  WaveRadar — Wi-Fi sensing motion radar", GREEN),
        ("  (c) 2026 Joaquim Pedro de Morais Filho", GREEN_DIM),
        ("", MUTED),
        ("[1/2] Installing waveradar from GitHub...", (120, 200, 255)),
        ("[2/2] Starting the radar (your router's Wi-Fi signal)...",
         (120, 200, 255)),
        ("", MUTED),
        ("  Run it again anytime with:  waveradar", GREEN),
        ("  No hardware demo:           waveradar --source sim", GREEN),
        ("", MUTED),
        ("[waveradar] radar UI: http://127.0.0.1:8347", AMBER),
    ]
    tt = 1.2
    _type_out(d, 116, 240, "PS C:\\>", cmd, out, t,
              t_type0=tt, cps=26, out_start=tt + len(cmd) / 26 + .8,
              out_per=.55)
    a = ease((t - dur + 4.5) / .8)
    if a > 0:
        d.text((W // 2, 648),
               "o navegador abre sozinho — pronto para usar",
               font=seg(21),
               fill=tuple(int(BG[i] + (AMBER[i] - BG[i]) * a)
                          for i in range(3)), anchor="mm")
    return img


def sec_install_linux(t, dur, k):
    img, d = base_frame("instalação · linux / macos", "Uma linha no terminal")
    _terminal(d, "bash", 80, 180, 1120, 330)
    cmd = ("curl -fsSL https://elevbit-ai.github.io/waveradar/install.sh "
           "| bash")
    out = [
        ("", MUTED),
        ("  WaveRadar — Wi-Fi sensing motion radar", GREEN),
        ("[1/2] Installing waveradar from GitHub...", (120, 200, 255)),
        ("[2/2] Starting the radar...", (120, 200, 255)),
        ("[waveradar] radar UI: http://127.0.0.1:8347", AMBER),
    ]
    _type_out(d, 116, 240, "$", cmd, out, t, t_type0=.9, cps=30,
              out_start=.9 + len(cmd) / 30 + .7, out_per=.5)
    d.text((80, 560), "Depois da primeira vez, basta digitar:",
           font=seg(20), fill=MUTED)
    a = ease((t - 4.5) / .6)
    if a > 0:
        d.rounded_rectangle([80, 596, 330, 646], 10, fill=(3, 17, 10),
                            outline=GREEN_DIM, width=2)
        d.text((100, 608), "$ waveradar", font=mono(22),
               fill=tuple(int(BG[i] + (GREEN[i] - BG[i]) * a)
                          for i in range(3)))
    return img


class RadarSim:
    """Feeds the real engine with the simulator and draws the radar."""

    def __init__(self):
        self.sim = iter(SimulatorSource(realtime=False))
        self.engine = MotionEngine()
        self.sim_t = 0.0
        self.blips = []
        self.sweep = 0.0
        self.state = None

    def step(self, dt):
        self.sim_t += dt
        while self.engine.samples < self.sim_t * 20.0:
            self.engine.push(next(self.sim))
        self.state = self.engine.state().to_dict()
        for b in self.blips:
            b["age"] += dt
        self.blips = [b for b in self.blips if b["age"] < 2.6]
        for p in self.state["points"]:
            self.blips.append({"a": p["a"], "r": p["r"], "i": p["i"],
                               "age": 0.0})
        self.sweep = (self.sweep + 110 * dt) % 360

    def draw(self, d, cx, cy, R):
        for i in range(1, 5):
            r = R * i / 4
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LINE,
                      width=1)
        for a in range(0, 360, 30):
            rd = math.radians(a - 90)
            d.line([cx, cy, cx + R * math.cos(rd), cy + R * math.sin(rd)],
                   fill=LINE, width=1)
            d.text((cx + (R + 16) * math.cos(rd),
                    cy + (R + 16) * math.sin(rd)), f"{a}°",
                   font=mono(13), fill=DARKLBL, anchor="mm")
        for i in range(28):
            a = math.radians(self.sweep - i * 1.8 - 90)
            alpha = int(85 * (1 - i / 28))
            d.line([cx, cy, cx + R * math.cos(a), cy + R * math.sin(a)],
                   fill=(43, 255, 136, alpha), width=3)
        a = math.radians(self.sweep - 90)
        d.line([cx, cy, cx + R * math.cos(a), cy + R * math.sin(a)],
               fill=(140, 255, 190, 230), width=2)
        for b in self.blips:
            age = b["age"] / 2.6
            alpha = (1 - age) * (0.35 + 0.65 * b["i"])
            rd = math.radians(b["a"] - 90)
            x = cx + R * b["r"] * math.cos(rd)
            y = cy + R * b["r"] * math.sin(rd)
            size = 3 + 7 * b["i"]
            core = RED if b["i"] > .7 else GREEN
            for mult, aa in ((3.0, .18), (1.8, .35), (.8, 1.0)):
                d.ellipse([x - size * mult, y - size * mult,
                           x + size * mult, y + size * mult],
                          fill=core + (int(255 * alpha * aa),))
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=GREEN)


_radar_holder = {}


def sec_radar(t, dur, k):
    rs = _radar_holder.setdefault("rs", RadarSim())
    rs.step(1.0 / FPS)
    st = rs.state
    img, d = base_frame("na prática", "O radar em funcionamento")
    rs.draw(d, 330, 420, 230)
    # side panel
    x0 = 660
    d.rounded_rectangle([x0, 175, 1230, 400], 14, fill=PANEL,
                        outline=LINE, width=2)
    lvl = st["level"]
    d.text((x0 + 26, 195), "NÍVEL DE MOVIMENTO", font=segb(14),
           fill=DARKLBL)
    d.text((x0 + 26, 218), LEVEL_TEXT.get(lvl, lvl.upper()),
           font=segb(40), fill=LEVEL_COLOR.get(lvl, MUTED))
    # meter
    mw = 520
    d.rectangle([x0 + 26, 286, x0 + 26 + mw, 302], outline=LINE, width=1)
    fw = int((mw - 2) * st["score"])
    if fw:
        c = RED if st["score"] > .72 else AMBER if st["score"] > .38 \
            else GREEN
        d.rectangle([x0 + 27, 287, x0 + 27 + fw, 301], fill=c)
    d.text((x0 + 26, 316),
           f"score {st['score']:.2f}    doppler {st['doppler_hz']:.2f} Hz"
           f"    rssi {st['rssi']:.0f} dBm",
           font=mono(18), fill=TEXT)
    d.text((x0 + 26, 350), "CSI · 52 subportadoras · fonte: simulador",
           font=seg(16), fill=MUTED)
    # spectrum
    d.rounded_rectangle([x0, 420, 1230, 560], 14, fill=PANEL,
                        outline=LINE, width=2)
    d.text((x0 + 26, 434), "ESPECTRO DOPPLER · 0,15–4 Hz", font=segb(14),
           fill=DARKLBL)
    specv = st.get("spectrum") or []
    if specv:
        sx, sy, sw_, sh = x0 + 26, 462, 520, 80
        bw = sw_ / len(specv)
        for i, v in enumerate(specv):
            c = RED if v > .75 else AMBER if v > .45 else GREEN
            bh = int(sh * v)
            if bh:
                d.rectangle([sx + i * bw + 1, sy + sh - bh,
                             sx + (i + 1) * bw - 1, sy + sh], fill=c)
        d.line([sx, sy + sh, sx + sw_, sy + sh], fill=LINE, width=1)
        d.text((sx, sy + sh + 4), "lento", font=seg(13), fill=DARKLBL)
        d.text((sx + sw_, sy + sh + 4), "rápido", font=seg(13),
               fill=DARKLBL, anchor="ra")
    # timed captions
    caps = [(0, "Ao abrir, o sistema calibra alguns segundos (sala parada)."),
            (dur * .30, "Alguém entra: pontos no radar e o nível sobe."),
            (dur * .58, "O espectro mostra a frequência dominante do movimento."),
            (dur * .80, "Andar rápido → frequências altas; gestos lentos → baixas.")]
    cap = ""
    for tt, c in caps:
        if t >= tt:
            cap = c
    d.rounded_rectangle([80, 596, 1200, 648], 10, fill=(3, 17, 10),
                        outline=LINE, width=1)
    d.text((100, 608), cap, font=seg(21), fill=TEXT)
    return img


def sec_modes(t, dur, k):
    img, d = base_frame("três modos", "Escolha o seu hardware (ou nenhum)")
    cards = [
        ("RSSI", "--source auto", "Qualquer roteador + o Wi-Fi do seu PC.",
         "Hardware: nenhum"),
        ("CSI · ESP32", "--source esp32",
         "52 subportadoras, amplitude + fase, 50–100 Hz via USB.",
         "Hardware: 1 placa ESP32 (~R$ 25)"),
        ("Simulador", "--source sim",
         "Pipeline completo com alvo sintético — usado neste vídeo.",
         "Hardware: nenhum"),
    ]
    per = dur / 3.2
    cw, ch = 360, 340
    for i, (title, flag, desc, hw) in enumerate(cards):
        x = 70 + i * (cw + 30)
        hot = per * i <= t < per * (i + 1) or (i == 2 and t >= per * 3)
        outline = GREEN if hot else LINE
        d.rounded_rectangle([x, 200, x + cw, 200 + ch], 16, fill=PANEL,
                            outline=outline, width=3 if hot else 2)
        d.text((x + 26, 226), flag, font=mono(17), fill=AMBER)
        d.text((x + 26, 258), title, font=segb(30),
               fill=GREEN if hot else TEXT)
        y = 316
        for ln in wrap(d, desc, seg(19), cw - 52):
            d.text((x + 26, y), ln, font=seg(19), fill=TEXT)
            y += 28
        d.text((x + 26, 200 + ch - 46), hw, font=seg(16), fill=MUTED)
    d.text((W // 2, 600), "python -m waveradar --source <modo>",
           font=mono(22), fill=GREEN_DIM, anchor="mm")
    return img


def sec_pipeline(t, dur, k):
    img, d = base_frame("por dentro", "O caminho do sinal até o radar")
    steps = [
        ("Janela deslizante", "64 amostras do canal (RSSI ou CSI)"),
        ("Detrend", "remove caminhos estáticos e deriva lenta"),
        ("FFT com Hann", "espectro de variação de cada canal"),
        ("Banda 0,15–4 Hz", "só o que se move como um corpo humano"),
        ("Baseline adaptativo", "energia vs. sala quieta → score 0–1"),
        ("12 setores", "energia por subportadora → pontos no radar"),
    ]
    per = dur / (len(steps) + 0.8)
    y = 180
    for i, (name, desc) in enumerate(steps):
        a = ease((t - i * per + .6) / .5)
        if a <= 0:
            continue
        hot = per * i <= t < per * (i + 1)
        box_o = GREEN if hot else tuple(
            int(BG[j] + (LINE[j] - BG[j]) * a) for j in range(3))
        d.rounded_rectangle([90, y, 620, y + 62], 10, fill=PANEL,
                            outline=box_o, width=3 if hot else 2)
        d.text((114, y + 8), f"{i+1}.  {name}", font=segb(22),
               fill=GREEN if hot else tuple(
                   int(BG[j] + (TEXT[j] - BG[j]) * a) for j in range(3)))
        d.text((114, y + 36), desc, font=seg(16), fill=tuple(
            int(BG[j] + (MUTED[j] - BG[j]) * a) for j in range(3)))
        if i < len(steps) - 1:
            d.line([355, y + 62, 355, y + 74], fill=GREEN_DIM, width=3)
        y += 74
    # right: little signal → spectrum drawing
    rx, ry = 700, 210
    d.rounded_rectangle([rx, ry, rx + 500, ry + 190], 14, fill=PANEL,
                        outline=LINE, width=2)
    d.text((rx + 20, ry + 12), "canal no tempo", font=seg(15), fill=DARKLBL)
    pts = []
    for i in range(120):
        xx = rx + 20 + i * (460 / 119)
        yy = (ry + 110 + 34 * math.sin(i * .32 + t * 2)
              * (0.4 + .6 * math.sin(i * .05 + t)))
        pts.append((xx, yy))
    d.line(pts, fill=GREEN, width=2)
    ry2 = ry + 220
    d.rounded_rectangle([rx, ry2, rx + 500, ry2 + 190], 14, fill=PANEL,
                        outline=LINE, width=2)
    d.text((rx + 20, ry2 + 12), "espectro (FFT) · banda de movimento",
           font=seg(15), fill=DARKLBL)
    for i in range(24):
        v = max(0.04, math.exp(-((i - 6 - 2 * math.sin(t)) ** 2) / 14)
                * (.6 + .4 * math.sin(t * 3 + i)))
        bh = int(120 * v)
        c = AMBER if 3 <= i <= 11 else GREEN_DIM
        d.rectangle([rx + 24 + i * 19, ry2 + 165 - bh,
                     rx + 38 + i * 19, ry2 + 165], fill=c)
    d.rectangle([rx + 24 + 3 * 19, ry2 + 40, rx + 38 + 11 * 19, ry2 + 165],
                outline=AMBER, width=2)
    d.text((rx + 250, ry2 + 172), "0,15–4 Hz", font=mono(14), fill=AMBER,
           anchor="ma")
    return img


def sec_esp32(t, dur, k):
    img, d = base_frame("modo csi", "ESP32: o canal em 52 subportadoras")
    # board drawing
    bx, by = 120, 230
    d.rounded_rectangle([bx, by, bx + 300, by + 210], 12,
                        fill=(6, 20, 26), outline=(40, 90, 110), width=3)
    d.rectangle([bx + 100, by - 16, bx + 200, by + 40], fill=(20, 40, 50),
                outline=(70, 120, 140), width=2)
    d.text((bx + 150, by + 12), "ESP32", font=segb(20), fill=TEXT,
           anchor="mm")
    for i in range(15):
        d.rectangle([bx - 8, by + 14 + i * 13, bx, by + 22 + i * 13],
                    fill=(180, 160, 60))
        d.rectangle([bx + 300, by + 14 + i * 13, bx + 308, by + 22 + i * 13],
                    fill=(180, 160, 60))
    d.rectangle([bx + 120, by + 190, bx + 180, by + 214],
                fill=(30, 30, 34), outline=(90, 90, 96), width=2)
    d.text((bx + 150, by + 236), "USB → PC", font=seg(15), fill=MUTED,
           anchor="mm")
    if int(t * 2) % 2:
        d.ellipse([bx + 262, by + 22, bx + 274, by + 34], fill=GREEN)
    steps = [
        "Abra firmware/esp32/waveradar_csi.ino no Arduino IDE",
        "Instale a placa ESP32 e a biblioteca ESP32Ping",
        "Configure o SSID e a senha da sua rede no sketch",
        "Grave na placa (Upload) e conecte o USB",
        "Rode:  python -m waveradar --source esp32",
    ]
    bullet_list(d, steps, 520, 220, 660, t, per=dur / (len(steps) + 1.5),
                font=seg(21), gap=10)
    d.text((520, 560), "A porta serial é detectada automaticamente "
           "(--serial COM5 se preferir).", font=seg(17), fill=MUTED)
    return img


def sec_limits(t, dur, k):
    img, d = base_frame("honestidade técnica", "O que ele faz — e o que não faz")
    per = dur / 4.6
    bullet_list(d, [
        "Detecta QUE algo se move, QUANTO se move e a assinatura Doppler.",
        "Não dá posição exata: o ângulo é uma projeção estável das "
        "subportadoras perturbadas, não direção de chegada calibrada.",
        "Localização real exige múltiplas antenas ou múltiplos enlaces.",
    ], 90, 190, 1080, t, per=per, font=seg(23))
    a = ease((t - per * 3) / .6)
    if a > 0:
        d.rounded_rectangle([90, 470, 1190, 590], 12,
                            fill=(18, 15, 5, int(255 * a)),
                            outline=(255, 199, 77, int(255 * a)), width=2)
        d.text((116, 486), "Uso responsável", font=segb(21),
               fill=tuple(int(BG[i] + (AMBER[i] - BG[i]) * a)
                          for i in range(3)))
        msg = ("Use apenas na sua própria rede e nos seus próprios espaços, "
               "com o conhecimento das pessoas presentes. Sensoriar espaços "
               "de terceiros pode ser ilegal.")
        y = 520
        for ln in wrap(d, msg, seg(19), 1040):
            d.text((116, y), ln, font=seg(19), fill=tuple(
                int(BG[i] + (TEXT[i] - BG[i]) * a) for i in range(3)))
            y += 28
    return img


def sec_close(t, dur, k):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy, R = W // 2, 240, 130
    for i in range(1, 4):
        d.ellipse([cx - R * i / 3, cy - R * i / 3,
                   cx + R * i / 3, cy + R * i / 3], outline=LINE, width=1)
    sw = (t * 120) % 360
    for i in range(24):
        a = math.radians(sw - i * 2.2 - 90)
        alpha = int(80 * (1 - i / 24))
        d.line([cx, cy, cx + R * math.cos(a), cy + R * math.sin(a)],
               fill=(43, 255, 136, alpha), width=2)
    d.text((cx, 420), "WAVERADAR", font=segb(52), fill=GREEN, anchor="mm")
    d.text((cx, 478), "Código aberto · Licença MIT", font=seg(22),
           fill=TEXT, anchor="mm")
    d.text((cx, 530), "github.com/elevbit-ai/waveradar", font=mono(26),
           fill=AMBER, anchor="mm")
    d.text((cx, 572), "elevbit-ai.github.io/waveradar", font=mono(20),
           fill=GREEN_DIM, anchor="mm")
    d.text((cx, 640), "Joaquim Pedro de Morais Filho · j360074@hotmail.com",
           font=segb(21), fill=TEXT, anchor="mm")
    return img


# ------------------------------------------------------------ narration ----

SECTIONS = [
    ("open", sec_open,
     "WaveRadar. Um radar de movimento que enxerga através do sinal Wi-Fi "
     "do seu próprio roteador. Neste vídeo você vai ver como instalar e "
     "como tudo funciona por dentro. Criado por Joaquim Pedro de Morais "
     "Filho."),
    ("physics", sec_physics,
     "A física é simples e real. Cada pacote Wi-Fi que atravessa a sala "
     "reflete em paredes, móveis e pessoas. Quando alguém se move, os "
     "caminhos que o sinal percorre mudam de comprimento, e isso modula a "
     "amplitude e a fase da onda recebida. O movimento também desloca a "
     "energia refletida em frequência: é o efeito Doppler. O movimento "
     "humano concentra-se entre zero vírgula quinze e quatro hertz de "
     "variação do canal. É exatamente essa banda que o WaveRadar isola e "
     "analisa."),
    ("install_win", sec_install_win,
     "Instalar é uma linha. No Windows, abra o PowerShell e cole o comando "
     "de instalação, disponível no site do projeto. Ele baixa o pacote "
     "Python, instala as dependências e abre o radar no navegador "
     "automaticamente, no endereço local, porta oito, três, quatro, sete."),
    ("install_linux", sec_install_linux,
     "No Linux ou no Mac, o processo é o mesmo, com uma linha de curl no "
     "terminal. Depois da primeira instalação, basta digitar waveradar "
     "para abrir o radar a qualquer momento."),
    ("radar", sec_radar,
     "Este é o radar em funcionamento, alimentado pelo processamento real "
     "do sistema. Ao abrir, ele calibra por alguns segundos, aprendendo "
     "como é o canal com a sala parada. Quando alguém entra, os pontos "
     "aparecem no radar e o nível sobe: verde para movimento leve, âmbar "
     "para movimento claro, vermelho para movimento forte. À direita, o "
     "espectro Doppler mostra a frequência dominante do movimento. Andar "
     "rápido desloca o espectro para frequências mais altas. Gestos lentos "
     "ficam nas frequências baixas."),
    ("modes", sec_modes,
     "São três modos de uso. O modo RSSI funciona com qualquer roteador e "
     "o Wi-Fi que já está no seu computador, sem nenhum hardware extra. O "
     "modo CSI usa uma placa ESP32, de poucos reais, para capturar as "
     "cinquenta e duas subportadoras do sinal, com amplitude e fase. Muito "
     "mais detalhe. E o modo simulador roda o sistema completo sem "
     "hardware nenhum, ideal para conhecer a interface."),
    ("pipeline", sec_pipeline,
     "Por dentro, o processamento é clássico de sensoriamento por rádio "
     "frequência. As amostras entram numa janela deslizante de sessenta e "
     "quatro pontos. Cada canal é destendenciado, removendo os caminhos "
     "estáticos. Uma transformada rápida de Fourier, com janela de Hann, "
     "extrai o espectro de variação, que é limitado à banda de movimento "
     "humano. A energia dessa banda é comparada com um baseline adaptativo "
     "de sala quieta, gerando o score de movimento. Por fim, a energia de "
     "cada subportadora é projetada em doze setores, que se tornam os "
     "pontos do radar."),
    ("esp32", sec_esp32,
     "Para o modo CSI, o firmware do ESP32 está incluído no repositório. "
     "Abra o sketch no Arduino IDE, configure o nome e a senha da sua "
     "rede, e grave na placa. Depois, conecte o USB e rode waveradar com a "
     "opção source esp32. A porta serial é detectada automaticamente."),
    ("limits", sec_limits,
     "Uma nota de honestidade. Com um único enlace de rádio, o sistema "
     "detecta que algo se move, quanto se move, e sua assinatura Doppler. "
     "Não a posição exata. O ângulo dos pontos é uma projeção estável das "
     "subportadoras perturbadas. E use com responsabilidade: apenas na sua "
     "própria rede e nos seus próprios espaços, com o conhecimento das "
     "pessoas presentes."),
    ("close", sec_close,
     "O projeto é código aberto, sob licença MIT. O código, o site e este "
     "vídeo estão em github ponto com, barra, elevbit traço ai, barra, "
     "waveradar. WaveRadar, por Joaquim Pedro de Morais Filho."),
]

LEAD, TAIL = 0.35, 0.9   # silence around each narration, seconds


def synthesize() -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    for name, _, text in SECTIONS:
        wav = AUDIO / f"{name}.wav"
        if wav.exists():
            continue
        txt_file = AUDIO / f"{name}.txt"
        txt_file.write_text(text, encoding="utf-8")
        ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
foreach ($v in @('Microsoft Daniel','Microsoft Maria Desktop')) {{
  try {{ $s.SelectVoice($v); break }} catch {{ }}
}}
$s.Rate = 0
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050,
  [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
  [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile('{wav}', $fmt)
$s.Speak([IO.File]::ReadAllText('{txt_file}', [Text.Encoding]::UTF8))
$s.Dispose()
"""
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=True, capture_output=True)
        print(f"  voice: {name}.wav")


def wav_seconds(path: Path) -> float:
    with wavemod.open(str(path)) as f:
        return f.getnframes() / f.getframerate()


def build() -> None:
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True, exist_ok=True)

    print("[1/4] narration (Windows pt-BR voice)")
    synthesize()

    print("[2/4] rendering frames")
    plan = []
    for name, fn, _ in SECTIONS:
        dur = LEAD + wav_seconds(AUDIO / f"{name}.wav") + TAIL
        n = int(round(dur * FPS))
        plan.append((name, fn, n))
        print(f"  {name:14s} {n/FPS:6.1f}s")
    total = sum(n for _, _, n in plan)
    print(f"  total          {total/FPS:6.1f}s  ({total} frames)")

    idx = 0
    for name, fn, n in plan:
        for k in range(n):
            img = fn(k / FPS, n / FPS, k)
            img.save(FRAMES / f"f{idx:06d}.png")
            idx += 1
        print(f"  rendered {name}")

    print("[3/4] audio track")
    combined = WORK / "narration.wav"
    with wavemod.open(str(combined), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(22050)
        for name, _, n in plan:
            sec_len = n / FPS
            with wavemod.open(str(AUDIO / f"{name}.wav")) as f:
                data = f.readframes(f.getnframes())
            lead = b"\x00\x00" * int(LEAD * 22050)
            need = int(sec_len * 22050) - len(lead) // 2 - len(data) // 2
            tail = b"\x00\x00" * max(0, need)
            out.writeframes(lead + data + tail)

    print("[4/4] encoding mp4")
    OUT_MP4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS), "-i", str(FRAMES / "f%06d.png"),
        "-i", str(combined),
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", "-shortest",
        str(OUT_MP4),
    ], check=True, capture_output=True)
    print(f"wrote {OUT_MP4}  ({OUT_MP4.stat().st_size/1e6:.1f} MB, "
          f"{total/FPS:.0f}s)")


if __name__ == "__main__":
    build()
