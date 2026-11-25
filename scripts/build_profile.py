#!/usr/bin/env python3
"""
build_profile.py  //  generates every SVG used by the profile README.

    assets/hero.svg        name in ASCII block type + spinning ASCII globe (or your face)
    assets/city.svg        your last year of contributions as an ASCII isometric city
    assets/systems.svg     the production ecosystem panel
    assets/h-01..05.svg    section header bars
    assets/footer.svg      sign-off bar

Run it from anywhere:
    python scripts/build_profile.py           -> real data from GitHub
    python scripts/build_profile.py --demo    -> also writes assets/city-demo.svg (fake full year)

Standard library only. Pillow is optional: it is only needed if you drop a photo
at assets/portrait.png (or .jpg) to replace the globe with your face in ASCII.
The GitHub Action in .github/workflows/profile.yml runs this every day.
"""

import datetime as dt
import html
import json
import math
import os
import random
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# ════════════════════════════════════════════════════════════════════════════
#  CONFIG  //  edit these, push, and the Action rebuilds the images
# ════════════════════════════════════════════════════════════════════════════
USER = os.environ.get("GH_USER", "mhrshadfm")

FIRST_NAME = "MEHRSHAD"            # drawn in big ASCII block letters
REST_NAME = "FARHOUD MOGHADAM"     # drawn underneath
ROLE = "SYSTEMS ARCHITECT // FULL-STACK CREATIVE TECHNOLOGIST"
TAGLINE = [
    "Architecting sovereign local-first AI systems,",
    "multimodal AV engines & existential literary software.",
]
PROMPT_LINE = ("$ boot --mode", "sovereign_local_first", "  [ RTX INFERENCE · NLE AUTOMATION · NARRATIVE ENGINES ]")

# bottom row of the hero card. "{since}" becomes the year your GitHub account was made.
STATS = [
    ("SYSTEMS", "05"),
    ("CORE STACK", "30+"),
    ("LANGUAGES", "04"),
    ("BUILDING SINCE", "{since}"),
]

SYSTEMS = [
    ("Viral Studio", "AV / NLE",
     "Next.js 15 · React 19 · FastAPI · SQLite · Premiere XML",
     "macOS glassmorphic pre-production engine: Premiere Pro magnetic timeline, "
     "AE V1–V12 layer inspector, RTL/LTR script editor and cadence WPS engine."),
    ("FuY.Land", "COGNITIVE AI",
     "Python · Ollama (RTX local LLMs) · Qdrant vector DB",
     "Autonomous cognitive synthesis engine. Decodes live signals across AI, "
     "cognitive psychology and platform dynamics with anti-PR quality gates."),
    ("OSINT-Sentinel", "INTELLIGENCE",
     "Python · FastAPI · FFmpeg · NetworkX · interactive graph",
     "Multi-platform intelligence tracker: live HLS broadcast recording daemon, "
     "network centrality metrics and anti-detection jitter engines."),
    ("Spaces", "DESKTOP",
     "Electron · Node.js · Windows 11 / macOS UI",
     "Multi-account isolated application runner with sandboxed cookie/session "
     "storage and clean desktop virtualization."),
    ("Silk Road Core", "INFRA",
     "FastAPI · SQLite · Cloudflare Tunnels · Telegram WebApp",
     "Multi-tier affiliate referral architecture with geometric commission "
     "decay and privacy-preserving downline indexing."),
]

SECTIONS = [
    ("01", "ARCHITECTURAL MANIFESTO"),
    ("02", "PRODUCTION ECOSYSTEM"),
    ("03", "TECHNICAL SPECIFICATION MATRIX"),
    ("04", "THE CITY I'M BUILDING"),
    ("05", "BEYOND CODE"),
]

# ════════════════════════════════════════════════════════════════════════════
#  PALETTE  //  black, white, blue, red
# ════════════════════════════════════════════════════════════════════════════
BG = "#04050a"
BG2 = "#070b18"
LINE = "#18213d"
DIM = "#2b3863"
MUTED = "#7482ad"
WHITE = "#f4f6ff"
ICE = "#bcd0ff"
BLUE = "#2f6bff"
BLUE_L = "#7fb0ff"
BLUE_D = "#1a3a9c"
NAVY = "#0d1838"
RED = "#ff2a44"
RED_D = "#9e1028"

FONT = "ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,'Liberation Mono','Courier New',monospace"

TODAY = dt.date.today()


def esc(s):
    return html.escape(str(s), quote=True)


def f1(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


# ════════════════════════════════════════════════════════════════════════════
#  DATA
# ════════════════════════════════════════════════════════════════════════════
def _get(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "profile-readme-builder", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def fetch_graphql(user, token):
    q = """query($login:String!){user(login:$login){createdAt
      contributionsCollection{contributionCalendar{totalContributions
      weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": q, "variables": {"login": user}}).encode()
    raw = _get("https://api.github.com/graphql", {"Authorization": f"bearer {token}",
                                                   "Content-Type": "application/json"}, body)
    u = json.loads(raw)["data"]["user"]
    days = {}
    for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            days[dt.date.fromisoformat(d["date"])] = d["contributionCount"]
    return days, int(u["createdAt"][:4])


def fetch_html(user):
    page = _get(f"https://github.com/users/{user}/contributions")
    cells = {}
    for tag in re.findall(r"<td\b[^>]*>", page):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        if "data-date" in a and "id" in a:
            cells[a["id"]] = dt.date.fromisoformat(a["data-date"])
    days = {d: 0 for d in cells.values()}
    for for_id, text in re.findall(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        m = re.match(r"\s*([\d,]+) contribution", text)
        if for_id in cells and m:
            days[cells[for_id]] = int(m.group(1).replace(",", ""))
    if not days:
        raise RuntimeError("could not parse contribution calendar")
    since = 2022
    try:
        since = int(json.loads(_get(f"https://api.github.com/users/{user}"))["created_at"][:4])
    except Exception as e:  # rate limits etc. are fine, keep the default
        print("  (profile lookup skipped:", e, ")")
    return days, since


def fetch(user):
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        try:
            return fetch_graphql(user, token)
        except Exception as e:
            print("  graphql failed, falling back to public page:", e)
    return fetch_html(user)


def demo_days():
    rng = random.Random(23)
    end = TODAY
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    days, d, k = {}, start, 0
    while d <= end:
        season = 0.55 + 0.35 * math.sin(k / 40.0) + (0.25 if (k // 7) % 9 in (3, 4) else 0)
        weekend = d.weekday() >= 5
        p = season * (0.55 if weekend else 1.0)
        c = 0
        if rng.random() < p:
            c = max(1, int(rng.lognormvariate(1.4 + season * 0.6, 0.75)))
        days[d] = c
        d += dt.timedelta(days=1)
        k += 1
    return days


def analyse(days):
    ds = sorted(days)
    first = ds[0]
    sunday = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    cells = []
    for d in ds:
        cells.append(((d - sunday).days // 7, (d.weekday() + 1) % 7, days[d], d))
    total = sum(days.values())
    active = sum(1 for c in days.values() if c > 0)
    busiest = max(ds, key=lambda d: (days[d], d))
    longest = run = 0
    for d in ds:
        run = run + 1 if days[d] > 0 else 0
        longest = max(longest, run)
    current = 0
    for d in reversed(ds):
        if days[d] > 0:
            current += 1
        elif d < ds[-1]:  # today being empty doesn't break the streak yet
            break
    return {
        "cells": cells, "weeks": max(c[0] for c in cells) + 1, "total": total, "active": active,
        "busiest": busiest, "busiest_n": days[busiest], "longest": longest, "current": current,
        "start": ds[0], "end": ds[-1],
    }


# ════════════════════════════════════════════════════════════════════════════
#  ASCII CANVAS  //  a character grid rendered as SVG text rows
# ════════════════════════════════════════════════════════════════════════════
class Canvas:
    def __init__(self, cols, rows, cw, ch):
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.c = [[" "] * cols for _ in range(rows)]
        self.k = [[None] * cols for _ in range(rows)]

    def put(self, i, j, char, cls):
        if 0 <= i < self.cols and 0 <= j < self.rows:
            self.c[j][i], self.k[j][i] = char, cls

    def empty(self, i, j):
        return 0 <= i < self.cols and 0 <= j < self.rows and self.c[j][i] == " "

    def fill(self, poly, fn):
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        i0, i1 = max(0, int(min(xs) / self.cw) - 1), min(self.cols - 1, int(max(xs) / self.cw) + 1)
        j0, j1 = max(0, int(min(ys) / self.ch) - 1), min(self.rows - 1, int(max(ys) / self.ch) + 1)
        for j in range(j0, j1 + 1):
            py = (j + 0.5) * self.ch
            for i in range(i0, i1 + 1):
                px = (i + 0.5) * self.cw
                if inside(poly, px, py):
                    r = fn(i, j, px, py)
                    if r:
                        self.put(i, j, r[0], r[1])

    def svg(self, x0=0.0, y0=0.0, cls="a"):
        """One <text> per row; textLength pins every column to the grid in any monospace font."""
        out = []
        for j in range(self.rows):
            row, ks = self.c[j], self.k[j]
            last = max((i for i in range(self.cols) if row[i] != " "), default=-1)
            if last < 0:
                continue
            first = next(i for i in range(self.cols) if row[i] != " ")
            parts, i = [], first
            while i <= last:
                k = ks[i] if row[i] != " " else None
                s = i
                while i <= last and ((ks[i] if row[i] != " " else None) == k):
                    i += 1
                chunk = esc("".join(row[s:i]))
                parts.append(f'<tspan class="{k}">{chunk}</tspan>' if k else chunk)
            n = last - first + 1
            x = x0 + first * self.cw
            y = y0 + (j + 0.78) * self.ch
            out.append(f'<text class="{cls}" x="{f1(x)}" y="{f1(y)}" textLength="{f1(n * self.cw)}" '
                       f'lengthAdjust="spacing" xml:space="preserve">{"".join(parts)}</text>')
        return "\n".join(out)


def inside(poly, px, py):
    sign = 0
    n = len(poly)
    for k in range(n):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % n]
        cr = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if cr:
            s = 1 if cr > 0 else -1
            if not sign:
                sign = s
            elif s != sign:
                return False
    return True


def h32(*a):
    x = 2166136261
    for v in a:
        for ch in str(v):
            x = ((x ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return x


def svg_open(w, h, title, extra_css=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<style>
text{{font-family:{FONT}}}
.mono{{font-family:{FONT}}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
@keyframes twinkle{{0%,100%{{opacity:1}}40%{{opacity:.15}}60%{{opacity:.9}}}}
@keyframes scan{{0%{{transform:translateY(-120px)}}100%{{transform:translateY({h + 40}px)}}}}
.blink{{animation:blink 1.1s steps(1,end) infinite}}
.pulse{{animation:pulse 2.4s ease-in-out infinite}}
.scan{{animation:scan 7s linear infinite}}
{extra_css}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>"""


def frame(w, h, r=14):
    """Card background, faint scanlines, HUD corner brackets."""
    b = 18
    corners = (f"M{b} {b + 22}V{b}H{b + 22} M{w - b - 22} {b}H{w - b}V{b + 22} "
               f"M{w - b} {h - b - 22}V{h - b}H{w - b - 22} M{b + 22} {h - b}H{b}V{h - b - 22}")
    return f"""<defs>
<linearGradient id="bgG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>
<pattern id="scanP" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#ffffff" opacity=".025"/></pattern>
<linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BLUE}" stop-opacity="0"/><stop offset=".85" stop-color="{BLUE}" stop-opacity=".07"/><stop offset="1" stop-color="{BLUE_L}" stop-opacity=".22"/></linearGradient>
<clipPath id="cardClip"><rect width="{w}" height="{h}" rx="{r}"/></clipPath>
</defs>
<rect width="{w}" height="{h}" rx="{r}" fill="url(#bgG)"/>
<g clip-path="url(#cardClip)"><rect width="{w}" height="{h}" fill="url(#scanP)"/>
<rect class="scan" y="0" width="{w}" height="90" fill="url(#scanG)"/></g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r}" fill="none" stroke="{LINE}"/>
<path d="{corners}" fill="none" stroke="{RED}" stroke-width="1.6" opacity=".9"/>"""


# ════════════════════════════════════════════════════════════════════════════
#  HERO  //  ANSI-shadow name + ASCII globe
# ════════════════════════════════════════════════════════════════════════════
ANSI_SHADOW = {
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "B": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "F": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "██║     ", "╚═╝     "],
    "G": [" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "H": ["██╗  ██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "K": ["██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "╚═╝  ╚═╝"],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "M": ["███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
    "U": ["██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    " ": ["   "] * 6,
}


def ansi_rows(word):
    rows = [""] * 6
    for ch in word.upper():
        g = ANSI_SHADOW.get(ch)
        if g is None:
            raise SystemExit(f"letter {ch!r} is missing from ANSI_SHADOW; add it to build_profile.py")
        rows = [r + gr for r, gr in zip(rows, g)]
    return rows


def box_segments(c, x, y, w, h):
    cx, cy, d = x + w / 2, y + h / 2, w * 0.2
    L, R, T, B = x, x + w, y, y + h
    return {
        "═": [[(L, cy - d), (R, cy - d)], [(L, cy + d), (R, cy + d)]],
        "║": [[(cx - d, T), (cx - d, B)], [(cx + d, T), (cx + d, B)]],
        "╗": [[(L, cy - d), (cx + d, cy - d), (cx + d, B)], [(L, cy + d), (cx - d, cy + d), (cx - d, B)]],
        "╔": [[(R, cy - d), (cx - d, cy - d), (cx - d, B)], [(R, cy + d), (cx + d, cy + d), (cx + d, B)]],
        "╝": [[(L, cy + d), (cx + d, cy + d), (cx + d, T)], [(L, cy - d), (cx - d, cy - d), (cx - d, T)]],
        "╚": [[(R, cy + d), (cx - d, cy + d), (cx - d, T)], [(R, cy - d), (cx + d, cy - d), (cx + d, T)]],
    }.get(c, [])


def name_block(word, x0, y0, cw, ch):
    rows = ansi_rows(word)
    rects, path = [], []
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            if row[i] == "█":
                s = i
                while i < len(row) and row[i] == "█":
                    i += 1
                rects.append(f'<rect x="{f1(x0 + s * cw)}" y="{f1(y0 + j * ch)}" width="{f1((i - s) * cw)}" height="{f1(ch - 2.2)}"/>')
                continue
            for seg in box_segments(row[i], x0 + i * cw, y0 + j * ch, cw, ch):
                path.append("M" + "L".join(f"{f1(a)} {f1(b)}" for a, b in seg))
            i += 1
    return "".join(rects), " ".join(path), len(rows[0]) * cw, 6 * ch


GLOBE_CSS = """
.gl{font-size:10.6px}
.g0{fill:#16275e}.g1{fill:#1f45b8}.g2{fill:#2f6bff}.g3{fill:#7fb0ff}.g4{fill:#e9efff}
.gr{fill:#ff2a44}.gR{fill:#9e1028}
.fr{opacity:0;animation:fr var(--T) steps(1,end) infinite}
"""


def globe_canvas(cols, rows, cw, ch, phase):
    cv = Canvas(cols, rows, cw, ch)
    lx, ly, lz = -0.55, -0.5, 0.67
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / n, ly / n, lz / n
    ramp = " .,:;*"
    for j in range(rows):
        for i in range(cols):
            nx = (i + 0.5 - cols / 2) / (cols / 2)
            ny = (j + 0.5 - rows / 2) / (rows / 2)
            r2 = nx * nx + ny * ny
            if r2 > 1:
                continue
            nz = math.sqrt(1 - r2)
            lum = max(0.0, nx * lx + ny * ly + nz * lz)
            lat = math.degrees(math.asin(-ny))
            lon = math.degrees(math.atan2(nx, nz)) + phase
            # line thickness in degrees ~ one character cell
            dlat_w = math.degrees((2 / rows) / max(0.25, math.sqrt(1 - ny * ny))) * 0.55
            dlon_w = math.degrees((2 / cols) / max(0.2, nz)) * 0.55 / max(0.3, math.cos(math.radians(lat)))
            on_lat = abs(((lat + 15) % 30) - 15) < dlat_w
            on_lon = abs(((lon + 15) % 30) - 15) < dlon_w and abs(lat) < 66
            rim = nz < 0.42 and nx > 0.05 and ny > -0.75
            if on_lat or on_lon:
                lon_char = "(" if nx < -0.5 else ")" if nx > 0.5 else "|"
                char = "+" if (on_lat and on_lon) else ("-" if on_lat else lon_char)
                if abs(lat) < dlat_w:  # equator
                    cls = "gr" if lum > 0.08 else "gR"
                else:
                    cls = "g4" if lum > 0.62 else "g3" if lum > 0.3 else "g2" if lum > 0.1 else "g1"
            else:
                idx = min(len(ramp) - 1, int(lum * (len(ramp) - 0.01)))
                char = ramp[idx] if idx else "."
                cls = "g3" if lum > 0.8 else "g2" if lum > 0.5 else "g1" if lum > 0.2 else "g0"
            if rim and not (on_lat or on_lon):
                char, cls = (":" if nz > 0.2 else "."), ("gr" if nz < 0.25 else "gR")
            cv.put(i, j, char, cls)
    return cv


def portrait_canvas(path, cols, rows, cw, ch):
    from PIL import Image, ImageOps  # optional dependency
    im = ImageOps.grayscale(Image.open(path))
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    im = ImageOps.autocontrast(im.resize((cols, rows)), cutoff=2)
    ramp = " .:-=+*#%@"
    cv = Canvas(cols, rows, cw, ch)
    for j in range(rows):
        for i in range(cols):
            nx = (i + 0.5 - cols / 2) / (cols / 2)
            ny = (j + 0.5 - rows / 2) / (rows / 2)
            if nx * nx + ny * ny > 1:
                continue
            v = im.getpixel((i, j)) / 255
            idx = int(v * (len(ramp) - 0.01))
            if idx == 0:
                continue
            cls = "g4" if v > 0.78 else "g3" if v > 0.55 else "g2" if v > 0.32 else "g1"
            cv.put(i, j, ramp[idx], cls)
    return cv


def build_hero(stats_since):
    W, H = 1000, 520
    gx, gy, R = 790, 228, 150
    cw, ch = 6.36, 11.4
    cols, rows = 47, 26
    ox, oy = gx - cols * cw / 2, gy - rows * ch / 2

    portrait = next((p for p in (ASSETS / "portrait.png", ASSETS / "portrait.jpg") if p.exists()), None)
    frames_svg, n_frames, T = "", 12, 3.6
    css = GLOBE_CSS.replace("var(--T)", f"{T}s")
    if portrait:
        try:
            frames_svg = portrait_canvas(portrait, cols, rows, cw, ch).svg(ox, oy, "gl")
            n_frames = 0
        except Exception as e:
            print("  portrait skipped (pip install pillow?):", e)
            portrait = None
    if not portrait:
        step = 100 / n_frames
        css += f"@keyframes fr{{0%{{opacity:1}}{step:.3f}%{{opacity:0}}100%{{opacity:0}}}}\n"
        css += "".join(f".f{k}{{animation-delay:{k * T / n_frames:.3f}s}}" for k in range(n_frames))
        css += ".f0{opacity:1}"
        frames_svg = "\n".join(
            f'<g class="fr f{k}">{globe_canvas(cols, rows, cw, ch, 30 * k / n_frames).svg(ox, oy, "gl")}</g>'
            for k in range(n_frames))
    css += """
@keyframes glitchA{0%,86%,100%{transform:translate(0,0);opacity:0}87%{transform:translate(-5px,1px);opacity:.85}89%{transform:translate(4px,-1px);opacity:.7}91%{transform:translate(-2px,0);opacity:.0}95%{transform:translate(3px,0);opacity:.6}96%{opacity:0}}
@keyframes glitchB{0%,86%,100%{transform:translate(0,0);opacity:0}87%{transform:translate(5px,-1px);opacity:.85}89%{transform:translate(-4px,1px);opacity:.7}91%{opacity:0}95%{transform:translate(-3px,0);opacity:.6}96%{opacity:0}}
.gA{animation:glitchA 6s steps(1,end) infinite}.gB{animation:glitchB 6s steps(1,end) infinite}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes spinR{to{transform:rotate(-360deg)}}
.ring{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}
.ringR{transform-box:fill-box;transform-origin:center;animation:spinR 9s linear infinite}
"""

    nx0, ny0, ncw, nch = 48, 116, 8.0, 16.2
    rects, path, nw, nh = name_block(FIRST_NAME, nx0, ny0, ncw, nch)

    s = [svg_open(W, H, f"{FIRST_NAME} {REST_NAME} — {ROLE}", css), frame(W, H)]
    s.append(f"""<defs>
<linearGradient id="nameG" gradientUnits="userSpaceOnUse" x1="0" y1="{ny0}" x2="0" y2="{ny0 + nh}"><stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="{WHITE}"/><stop offset="1" stop-color="{BLUE_L}"/></linearGradient>
<radialGradient id="glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{BLUE}" stop-opacity=".18"/><stop offset=".7" stop-color="{BLUE}" stop-opacity=".04"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
<g id="nm">{rects}</g>
</defs>""")
    # top bar
    s.append(f"""<text x="48" y="44" font-size="10" letter-spacing="3" fill="{MUTED}">{esc(USER.upper())} <tspan fill="{DIM}">/</tspan> LIVING IDENTITY</text>
<text x="952" y="44" font-size="10" letter-spacing="3" fill="{MUTED}" text-anchor="end"><tspan class="pulse" fill="{RED}">●</tspan> ONLINE <tspan fill="{DIM}">·</tspan> SYS_ID 0x23</text>
<line x1="48" y1="60" x2="952" y2="60" stroke="{LINE}"/>
<line x1="48" y1="60" x2="148" y2="60" stroke="{RED}" stroke-width="2"/>""")
    # name
    s.append(f"""<text x="{nx0}" y="100" font-size="11" letter-spacing="3" fill="{BLUE_L}"><tspan fill="{RED}">&gt;</tspan> HELLO, WORLD. I'M</text>
<use href="#nm" fill="{RED}" class="gA"/><use href="#nm" fill="{BLUE}" class="gB"/>
<use href="#nm" fill="url(#nameG)"/>
<path d="{path}" fill="none" stroke="{RED}" stroke-width="1.25" stroke-linecap="square"/>
<text x="{nx0}" y="{ny0 + nh + 38}" font-size="21" font-weight="700" letter-spacing="8.4" fill="{WHITE}">{esc(REST_NAME)}<tspan class="blink" fill="{RED}"> █</tspan></text>
<text x="{nx0}" y="{ny0 + nh + 72}" font-size="11.5" letter-spacing="1.6" fill="{BLUE_L}">{esc(ROLE)}</text>""")
    ty = ny0 + nh + 102
    for k, line in enumerate(TAGLINE):
        s.append(f'<text x="{nx0}" y="{ty + k * 19}" font-size="12" fill="{MUTED}">{esc(line)}</text>')
    py = ty + len(TAGLINE) * 19 + 20
    p0, p1, p2 = PROMPT_LINE
    s.append(f'<text x="{nx0}" y="{py}" font-size="10.5" fill="{MUTED}"><tspan fill="{RED}">{esc(p0)}</tspan> '
             f'<tspan fill="{WHITE}">{esc(p1)}</tspan><tspan fill="{DIM}">{esc(p2)}</tspan></text>')
    # globe + radar rings
    s.append(f"""<circle cx="{gx}" cy="{gy}" r="{R + 40}" fill="url(#glow)"/>
<circle class="ring" cx="{gx}" cy="{gy}" r="{R + 16}" fill="none" stroke="{BLUE_D}" stroke-dasharray="2 7"/>
<circle class="ringR" cx="{gx}" cy="{gy}" r="{R + 28}" fill="none" stroke="{RED}" stroke-width="1.4" stroke-dasharray="46 1060" opacity=".85"/>
<circle cx="{gx}" cy="{gy}" r="{R + 28}" fill="none" stroke="{LINE}"/>
<path d="M{gx} {gy - R - 36}v10 M{gx} {gy + R + 26}v10 M{gx - R - 36} {gy}h10 M{gx + R + 26} {gy}h10" stroke="{BLUE_L}" stroke-width="1.4"/>
{frames_svg}
<text x="{gx + R + 40}" y="{gy - 8}" font-size="8" letter-spacing="2" fill="{DIM}" text-anchor="end" transform="rotate(90 {gx + R + 40} {gy - 8})">{'IDENTITY SCAN' if portrait else 'SOVEREIGN NODE'} // 0x23</text>""")
    # stats row
    sy = 430
    s.append(f'<line x1="48" y1="{sy - 20}" x2="952" y2="{sy - 20}" stroke="{LINE}"/>')
    colw = 904 / len(STATS)
    for k, (label, value) in enumerate(STATS):
        x = 48 + k * colw
        v = value.replace("{since}", str(stats_since))
        s.append(f"""<text x="{f1(x)}" y="{sy + 4}" font-size="9" letter-spacing="3" fill="{MUTED}">{esc(label)}</text>
<rect x="{f1(x + colw - 30)}" y="{sy - 3}" width="6" height="6" fill="{RED if k % 2 else BLUE}"/>
<text x="{f1(x)}" y="{sy + 40}" font-size="30" font-weight="700" fill="{WHITE}">{esc(v)}</text>""")
    s.append(f"""<text x="48" y="{H - 22}" font-size="9" letter-spacing="2" fill="{DIM}">github.com/{esc(USER)}</text>
<text x="952" y="{H - 22}" font-size="9" letter-spacing="2" fill="{DIM}" text-anchor="end">ASCII RENDER · {TODAY.isoformat()}</text>
</svg>""")
    return "\n".join(s)


# ════════════════════════════════════════════════════════════════════════════
#  CONTRIBUTION CITY  //  isometric scene rasterised into characters
# ════════════════════════════════════════════════════════════════════════════
TIERS = {
    #       lit window, dark window, wall,     right lit,  right dark, top,      edge
    1: ("#3f6fe0", "#1a3480", "#1d3784", "#2a4fb8", "#12245c", "#5b86f0", "#6f95f5"),
    2: ("#5d93ff", "#1f45b0", "#2550c4", "#3567e6", "#16307e", "#9cc0ff", "#a9c7ff"),
    3: ("#b8d0ff", "#2f63e0", "#3b6ff0", "#6f9cff", "#1d3d9e", "#f2f6ff", "#ffffff"),
    4: ("#ff6b7d", "#a5142d", "#c81a36", "#ff2a44", "#6e0b1d", "#ffd5da", "#ffe6e9"),
}
GROUND = "#2d4796"
CITY_CSS = """
.c{font-size:7px}
.gd{fill:#2d4796}.av{fill:#ff2a44;opacity:.55}.pl{fill:#1a2b63}.pr{fill:#101c44}.pe{fill:#3d63c9}
.st{fill:#5a6fa8}.bc{fill:#ff2a44}
.tw{animation:twinkle 3.4s ease-in-out infinite}
.tw1{animation-delay:-.7s}.tw2{animation-delay:-1.5s}.tw3{animation-delay:-2.3s}.tw4{animation-delay:-2.9s}
.bcn{animation:blink 1.2s steps(1,end) infinite}
"""


def build_city(a, title_note=""):
    """The year is split into two districts (older half behind, recent half in front)
    so every building is wide enough to read as a 3D block in ASCII."""
    W = 1000
    cw, ch = 4.2, 7.2
    weeks = a["weeks"]
    half = (weeks + 1) // 2
    AVE = 1.3                                   # avenue between the districts

    def lay(w, d):                              # calendar cell -> ground coords
        k = w // half
        return w - k * half, d + k * (7 + AVE)

    X0, Y0, X1, Y1 = -0.4, -0.4, half + 0.4, 14 + AVE + 0.4
    left, right, top_y = 196, W - 22, 150
    span = (X1 - X0) + (Y1 - Y0)
    U = (right - left) / span
    V = U / 2
    plate = 10.0
    OX = left - (X0 - Y1) * U
    OY = top_y - (X0 + Y0) * V
    H = int(top_y + span * V + plate + 46)
    cols, rows = int(W / cw) + 1, int(H / ch) + 1
    cv = Canvas(cols, rows, cw, ch)

    def P(x, y, z=0.0):
        return OX + (x - y) * U, OY + (x + y) * V - z

    def to_ground(px, py):
        u_, b_ = (px - OX) / U, (py - OY) / V
        return (u_ + b_) / 2, (b_ - u_) / 2

    nz = [c for c in a["cells"] if c[2] > 0]
    mx = max([c[2] for c in nz], default=1)
    counts = sorted(c[2] for c in nz)

    def tier(n):
        rank = sum(1 for v in counts if v <= n) / max(1, len(counts))
        return 1 if rank <= 0.3 else 2 if rank <= 0.6 else 3 if rank <= 0.88 else 4

    HMAX, HMIN = 128.0, 8.0
    heights = {}
    for w, d, n, _ in nz:
        x, y = lay(w, d)
        hgt = HMIN + (n / mx) ** 0.6 * (HMAX - HMIN)
        room = OY + (x + y) * V - 14            # keep the tallest towers inside the card
        heights[(w, d)] = min(hgt, room)

    css_tiers = "".join(
        f".l{t}{{fill:{lw}}}.d{t}{{fill:{dw}}}.w{t}{{fill:{wall}}}.r{t}{{fill:{rl}}}"
        f".q{t}{{fill:{rd}}}.t{t}{{fill:{tp}}}.e{t}{{fill:{edge}}}"
        for t, (lw, dw, wall, rl, rd, tp, edge) in TIERS.items())

    # ── ground plate: dotted lots, an avenue with a dashed centre line, lit edges
    mid = 7 + AVE / 2

    def ground(i, j, px, py):
        x, y = to_ground(px, py)
        fx = x - math.floor(x)
        if 7 <= y < 7 + AVE:
            if abs(y - mid) < 0.16 and (x * 1.6) % 1 < 0.55:
                return "-", "av"
            return None
        fy = (y - (7 + AVE) if y >= 7 + AVE else y) % 1
        if 0 <= x < half and 0.18 < fx < 0.82 and 0.18 < fy < 0.82:
            return ".", "gd"
        return None

    cv.fill([P(X0, Y0), P(X1, Y0), P(X1, Y1), P(X0, Y1)], ground)
    edge_l = P(X0, Y1)

    def plate_left(i, j, px, py):
        top_at = edge_l[1] + (px - edge_l[0]) * V / U
        return ("_", "pe") if py < top_at + ch * 0.8 else ("=", "pl")

    def plate_right(i, j, px, py):
        top_at = P(X1, Y1)[1] - (px - P(X1, Y1)[0]) * V / U
        return ("_", "pe") if py < top_at + ch * 0.8 else (":", "pr")

    cv.fill([P(X0, Y1), P(X1, Y1), P(X1, Y1, -plate), P(X0, Y1, -plate)], plate_left)
    cv.fill([P(X1, Y0), P(X1, Y1), P(X1, Y1, -plate), P(X1, Y0, -plate)], plate_right)

    # ── buildings, back to front
    FH = ch * 2                                 # one floor = two character rows
    beacon = None
    order = sorted(nz, key=lambda c: (sum(lay(c[0], c[1])), lay(c[0], c[1])[0]))
    for w, d, n, date in order:
        x, y = lay(w, d)
        t = tier(n)
        hot = date == a["busiest"]
        if hot:
            t = 4
        hgt = heights[(w, d)]
        g = 0.09
        bx0, by0, bx1, by1 = x + g, y + g, x + 1 - g, y + 1 - g
        bid = f"{w}-{d}"

        def left_face(i, j, px, py, bx0=bx0, bx1=bx1, by1=by1, t=t, bid=bid):
            wx = (px - OX) / U + by1
            z = OY + (wx + by1) * V - py
            if (z % FH) / FH > 0.5:
                return "=", f"w{t}"
            col = int((wx - bx0) / (bx1 - bx0) * 3)
            lit = h32(bid, int(z // FH), col, "L") % 100 < 68
            return ("#", f"l{t}") if lit else ("#", f"d{t}")

        def right_face(i, j, px, py, by0=by0, by1=by1, bx1=bx1, t=t, bid=bid):
            wy = bx1 - (px - OX) / U
            z = OY + (bx1 + wy) * V - py
            if (z % FH) / FH > 0.5:
                return "-", f"q{t}"
            col = int((wy - by0) / (by1 - by0) * 3)
            lit = h32(bid, int(z // FH), col, "R") % 100 < 40
            return (":", f"r{t}") if lit else (".", f"q{t}")

        cv.fill([P(bx0, by1), P(bx1, by1), P(bx1, by1, hgt), P(bx0, by1, hgt)], left_face)
        cv.fill([P(bx1, by0), P(bx1, by1), P(bx1, by1, hgt), P(bx1, by0, hgt)], right_face)
        cv.fill([P(bx0, by0, hgt), P(bx1, by0, hgt), P(bx1, by1, hgt), P(bx0, by1, hgt)],
                lambda i, j, px, py, t=t: ("@", f"t{t}"))
        if hot:
            beacon = P(x + 0.5, y + 0.5, hgt)

    rng = random.Random(a["total"] * 7 + a["active"])
    lit_cells = [(i, j) for j in range(rows) for i in range(cols)
                 if cv.c[j][i] in "#:" and (cv.k[j][i] or "")[:1] in "lr"]
    for i, j in rng.sample(lit_cells, min(len(lit_cells), 46)):
        cv.k[j][i] += f" tw tw{rng.randint(1, 4)}"

    if beacon:                                  # antenna + blinking light on the busiest day
        bi, bj = int(beacon[0] / cw), int(beacon[1] / ch)
        for k in (1, 2, 3):
            cv.put(bi, bj - k, "|", "e4")
        cv.put(bi, bj - 4, "*", "bc bcn")

    for _ in range(170):                        # night sky
        i, j = rng.randrange(int(270 / cw), cols - 3), rng.randrange(2, int(top_y * 1.5 / ch))
        if i * cw > W - 260 and j * ch < 82:
            continue
        if all(cv.empty(i + di, j + dj) for di in range(-3, 4) for dj in range(-1, 6)):
            k = "st" + (f" tw tw{rng.randint(1, 4)}" if rng.random() < 0.35 else "")
            cv.put(i, j, rng.choice("......+*"), k)

    # ── svg
    css = CITY_CSS + css_tiers
    s = [svg_open(W, H, f"Contribution city of {USER}: {a['total']} contributions in the last year", css), frame(W, H)]
    s.append(f"""<defs><radialGradient id="cityGlow" cx=".6" cy=".62" r=".6"><stop offset="0" stop-color="{BLUE}" stop-opacity=".16"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient></defs>
<rect width="{W}" height="{H}" rx="14" fill="url(#cityGlow)"/>""")
    s.append(cv.svg(0, 0, "c"))

    # street signs: month names along each district's front edge
    ang = math.degrees(math.atan2(V, U))
    seen = set()
    for w, d, n, date in a["cells"]:
        key = (date.year, date.month)
        if d == 0 and date.day <= 7 and key not in seen:
            seen.add(key)
            x, _ = lay(w, 0)
            k = w // half
            if x < 0.5 or x > half - 1.5:
                continue
            yy = 7 + AVE * 0.72 if k == 0 else Y1 + 0.5
            zz = 0 if k == 0 else -plate
            mx_, my_ = P(x + 0.5, yy, zz)
            s.append(f'<text x="{f1(mx_)}" y="{f1(my_ + 3)}" font-size="7.5" letter-spacing="1.5" fill="{DIM if k else "#26386e"}" '
                     f'transform="rotate({ang:.2f} {f1(mx_)} {f1(my_ + 3)})">{date.strftime("%b").upper()}</text>')

    def kv(y, k, v, color=WHITE):
        return (f'<text x="40" y="{y}" font-size="10" letter-spacing="2" fill="{MUTED}">{esc(k)}</text>'
                f'<text x="236" y="{y}" font-size="11" font-weight="700" fill="{color}" text-anchor="end">{esc(v)}</text>')

    b = a["busiest"]
    busiest_txt = f"{a['busiest_n']} · {b.strftime('%b %d').upper()}" if a["busiest_n"] else "—"
    s.append(f"""<text x="40" y="50" font-size="10" letter-spacing="3" fill="{BLUE_L}">CONTRIBUTION CITY<tspan fill="{RED}" class="blink"> _</tspan></text>
<text x="38" y="104" font-size="46" font-weight="700" fill="{WHITE}">{a['total']:,}</text>
<text x="40" y="124" font-size="11" fill="{MUTED}">contributions in the last year</text>
<line x1="40" y1="142" x2="236" y2="142" stroke="{LINE}"/>
{kv(164, "ACTIVE DAYS", a["active"])}
{kv(184, "BUSIEST DAY", busiest_txt, RED)}
{kv(204, "LONGEST STREAK", f"{a['longest']}d")}
{kv(224, "CURRENT STREAK", f"{a['current']}d", BLUE_L)}""")
    sw = [GROUND, TIERS[1][5], TIERS[2][5], TIERS[3][5], TIERS[4][3]]
    lx = W - 40 - 30 - len(sw) * 13
    s.append(f'<text x="{lx - 8}" y="50" font-size="9" letter-spacing="2" fill="{MUTED}" text-anchor="end">LESS</text>')
    for k, col in enumerate(sw):
        s.append(f'<rect x="{lx + k * 13}" y="42" width="9" height="9" rx="1.5" fill="{col}"/>')
    s.append(f"""<text x="{W - 40}" y="50" font-size="9" letter-spacing="2" fill="{MUTED}" text-anchor="end">MORE</text>
<text x="{W - 40}" y="68" font-size="8.5" letter-spacing="1.5" fill="{DIM}" text-anchor="end">{a['start'].strftime('%b %d %Y').upper()} → {a['end'].strftime('%b %d %Y').upper()}{esc(title_note)}</text>
<text x="40" y="{H - 44}" font-size="11" fill="{BLUE_L}">@{esc(USER)}</text>
<text x="40" y="{H - 28}" font-size="8.5" letter-spacing="1.5" fill="{DIM}">ASCII RENDER · 1 BUILDING = 1 DAY · TALLER = MORE COMMITS</text>
</svg>""")
    return "\n".join(s)


# ════════════════════════════════════════════════════════════════════════════
#  SYSTEMS PANEL, SECTION HEADERS, FOOTER
# ════════════════════════════════════════════════════════════════════════════
def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if len(cur) + len(word) + (1 if cur else 0) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    return lines + ([cur] if cur else [])


def build_systems():
    W, rowh, top = 1000, 92, 58
    H = top + rowh * len(SYSTEMS) + 22
    s = [svg_open(W, H, "Production ecosystem: " + ", ".join(x[0] for x in SYSTEMS)), frame(W, H)]
    s.append(f"""<text x="40" y="38" font-size="9" letter-spacing="3" fill="{MUTED}">SYSTEM <tspan fill="{DIM}">/ CLASS</tspan></text>
<text x="330" y="38" font-size="9" letter-spacing="3" fill="{MUTED}">STACK <tspan fill="{DIM}">/ SPECIFICATION</tspan></text>
<text x="960" y="38" font-size="9" letter-spacing="3" fill="{MUTED}" text-anchor="end"><tspan class="pulse" fill="{RED}">■</tspan> {len(SYSTEMS):02d} NODES</text>""")
    for k, (name, cls, stack, desc) in enumerate(SYSTEMS):
        y = top + k * rowh
        accent = RED if k % 2 == 0 else BLUE
        s.append(f"""<line x1="40" y1="{y}" x2="960" y2="{y}" stroke="{LINE}" stroke-dasharray="{'0' if k == 0 else '3 4'}"/>
<rect x="24" y="{y + 16}" width="3" height="{rowh - 32}" fill="{accent}"/>
<text x="40" y="{y + 28}" font-size="10" letter-spacing="2" fill="{accent}">[0x{k + 1:02X}]</text>
<text x="40" y="{y + 52}" font-size="18" font-weight="700" fill="{WHITE}">{esc(name)}</text>
<text x="40" y="{y + 72}" font-size="9" letter-spacing="2.5" fill="{BLUE_L}">// {esc(cls)}</text>
<text x="330" y="{y + 28}" font-size="11" fill="{BLUE_L}">{esc(stack)}</text>""")
        for n, line in enumerate(wrap(desc, 88)[:3]):
            s.append(f'<text x="330" y="{y + 49 + n * 17}" font-size="11.5" fill="{MUTED}">{esc(line)}</text>')
    s.append("</svg>")
    return "\n".join(s)


def build_header(num, title):
    W, H = 1000, 56
    tw = len(title) * (15 * 0.6 + 3.2)
    x_title = 128
    x_line = x_title + tw + 18
    ticks = " ".join(f"M{x} 33v{6 if (x // 12) % 4 == 0 else 3}" for x in range(int(x_line) + 8, 880, 12))
    s = [svg_open(W, H, f"{num} // {title}")]
    s.append(f"""<defs><linearGradient id="hl" x1="0" x2="1"><stop offset="0" stop-color="{RED}"/><stop offset="1" stop-color="{BLUE}"/></linearGradient></defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{LINE}"/>
<text x="22" y="34" font-size="15" fill="{RED}" letter-spacing="-1">░▒▓</text>
<text x="66" y="34" font-size="15" font-weight="700" fill="{RED}">{esc(num)}</text>
<text x="94" y="34" font-size="15" fill="{BLUE}">//</text>
<text x="{x_title}" y="34" font-size="15" font-weight="700" letter-spacing="3.2" fill="{WHITE}">{esc(title)}</text>
<line x1="{f1(x_line)}" y1="29" x2="880" y2="29" stroke="url(#hl)" opacity=".7"/>
<path d="{ticks}" stroke="{DIM}"/>
<text x="976" y="33" font-size="9" letter-spacing="2" fill="{MUTED}" text-anchor="end">SEC.{esc(num)}<tspan class="blink" fill="{RED}"> ▮</tspan></text>
</svg>""")
    return "\n".join(s)


def build_footer():
    W, H = 1000, 120
    s = [svg_open(W, H, "End of transmission"), frame(W, H)]
    s.append(f"""<defs><linearGradient id="fl" x1="0" x2="1"><stop offset="0" stop-color="{RED}" stop-opacity="0"/><stop offset=".25" stop-color="{RED}"/><stop offset=".75" stop-color="{BLUE}"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></linearGradient></defs>
<text x="500" y="52" font-size="16" font-weight="700" letter-spacing="6" fill="{WHITE}" text-anchor="middle"><tspan fill="{RED}">▓▒░ </tspan>END_OF_TRANSMISSION<tspan fill="{BLUE}"> ░▒▓</tspan><tspan class="blink" fill="{RED}"> █</tspan></text>
<rect x="120" y="70" width="760" height="1.5" fill="url(#fl)"/>
<text x="500" y="94" font-size="9" letter-spacing="3" fill="{MUTED}" text-anchor="middle">{esc(USER.upper())} <tspan fill="{DIM}">//</tspan> SYS_ID 0x23 <tspan fill="{DIM}">//</tspan> SIGNAL CLOSED · {TODAY.isoformat()}</text>
</svg>""")
    return "\n".join(s)


# ════════════════════════════════════════════════════════════════════════════
def write(name, content):
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}  ({len(content.encode()) / 1024:.0f} KB)")


def main():
    ASSETS.mkdir(exist_ok=True)
    print(f"building profile assets for @{USER}")
    since = 2022
    try:
        days, since = fetch(USER)
        a = analyse(days)
        print(f"  {a['total']} contributions, {a['active']} active days")
        write("city.svg", build_city(a))
    except Exception as e:
        print("  !! could not fetch contributions, keeping the old city.svg:", e)
    write("hero.svg", build_hero(since))
    write("systems.svg", build_systems())
    for num, title in SECTIONS:
        write(f"h-{num}.svg", build_header(num, title))
    write("footer.svg", build_footer())
    if "--demo" in sys.argv:
        write("city-demo.svg", build_city(analyse(demo_days()), "  · DEMO DATA"))


if __name__ == "__main__":
    main()
