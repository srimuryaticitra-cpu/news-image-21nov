#!/usr/bin/env python3
"""news-image-20261121 -- "The World Today: Saturday 21 November 2026".

Draws a one-page newspaper front page summing up the world news of
Saturday 21 November 2026, using only the Python standard library.
The image is rendered procedurally into a pixel buffer and encoded as
PNG by hand (zlib + struct only). Fully deterministic: no clock, no
randomness, no network, no file input. The same bytes come out of
every run.

Run:  python3 main.py            (writes $MAKEFUN_OUTPUT_DIR/entry.png,
                                  or /output/entry.png when unset)
"""

import os
import struct
import zlib
from binascii import crc32

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 234)   # warm newsprint
INK = (18, 18, 20)        # near-black text
NAVY = (20, 38, 74)       # masthead / NATO blue
NAVY_LT = (38, 64, 112)
GOLD = (201, 162, 39)
RED = (178, 34, 34)       # lead red
RED_LT = (232, 222, 214)
BLUE_SKY = (214, 230, 240)
LAND = (196, 205, 178)    # pale land green
LAND_EDGE = (90, 100, 80)
SEA = (186, 211, 226)
GREY = (110, 110, 108)
RULE = (150, 140, 125)
WHITE = (255, 255, 255)
PANEL_BG = (255, 255, 255)
DARK_STRIP = (26, 26, 30)

# ------------------------------------------------------- 5x7 pixel font
# Each glyph is 7 rows of 5 bits, written as strings of 0/1.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    'a': ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    'b': ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    'c': ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    'd': ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    'e': ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    'f': ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    'g': ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    'h': ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    'i': ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    'j': ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    'k': ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    'l': ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    'n': ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    'o': ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    'p': ("00000", "00000", "11110", "10001", "11110", "10000", "10000"),
    'q': ("00000", "00000", "01111", "10001", "01111", "00001", "00001"),
    'r': ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    's': ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    't': ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    'u': ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    'v': ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    'w': ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    'x': ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    'y': ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    'z': ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '*': ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '@': ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    '_': ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    '<': ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    '>': ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
}


class Canvas:
    """RGB pixel buffer with simple vector/text drawing."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c):
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.w), min(y + h, self.h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = bytes(c) * (x1 - x0)

    def hline(self, x0, x1, y, c, t=1):
        for t_ in range(t):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.put(x, y + t_, c)

    def vline(self, x, y0, y1, c, t=1):
        for t_ in range(t):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                self.put(x + t_, y, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for a in range(t):
                for b in range(t):
                    self.put(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            if fill:
                self.hline(cx - dx, cx + dx, cy + dy, c)
            else:
                self.put(cx - dx, cy + dy, c)
                self.put(cx + dx, cy + dy, c)

    def ring(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            for dy in range(-rr, rr + 1):
                dx = int((rr * rr - dy * dy) ** 0.5)
                self.put(cx - dx, cy + dy, c)
                self.put(cx + dx, cy + dy, c)

    def poly(self, pts, c, outline=None):
        """Scanline fill of a polygon (list of (x, y))."""
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(xs[k]), int(xs[k + 1]), y, c)
        if outline:
            n = len(pts)
            for i in range(n):
                self.line(pts[i][0], pts[i][1],
                          pts[(i + 1) % n][0], pts[(i + 1) % n][1],
                          outline, 2)

    # ---- text ---------------------------------------------------------
    def char(self, x, y, ch, s, c):
        g = FONT.get(ch)
        if g is None:
            g = FONT['?']
        for r, row in enumerate(g):
            for col, bit in enumerate(row):
                if bit == '1':
                    self.rect(x + col * s, y + r * s, s, s, c)

    def text_w(self, s, scale):
        return len(s) * 6 * scale - scale

    def text(self, x, y, s, scale, c, align='l'):
        if align == 'c':
            x -= self.text_w(s, scale) // 2
        elif align == 'r':
            x -= self.text_w(s, scale)
        for ch in s:
            self.char(x, y, ch, scale, c)
            x += 6 * scale
        return x

    def wrap(self, s, scale, max_w):
        """Greedy word wrap; returns list of lines."""
        lines, cur = [], ''
        for word in s.split(' '):
            trial = (cur + ' ' + word).strip()
            if self.text_w(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, scale, c, max_w, leading=None):
        lh = leading if leading is not None else 7 * scale + 4
        for line in self.wrap(s, scale, max_w):
            self.text(x, y, line, scale, c)
            y += lh
        return y


# ------------------------------------------------------------- PNG write
def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack('>IIBBBBB', cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 9)) +
            chunk(b'IEND', b''))


# ------------------------------------------------------- NATO star emblem
def nato_star(cv, cx, cy, r, c):
    """Four-pointed NATO compass star: two long and two short spikes."""
    pts = []
    for k in range(8):
        ang = k * 3.141592653589793 / 4.0
        rr = r if k % 2 == 0 else r * 0.22
        # rotate so spikes point N/E/S/W
        import math
        a = ang - math.pi / 2
        pts.append((int(cx + rr * math.cos(a)), int(cy + rr * math.sin(a))))
    cv.poly(pts, c)


def burst(cv, cx, cy, r, c):
    """Explosion starburst marker."""
    import math
    pts = []
    for k in range(16):
        ang = k * math.pi / 8.0
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((int(cx + rr * math.cos(ang)),
                    int(cy + rr * math.sin(ang))))
    cv.poly(pts, c)
    cv.circle(cx, cy, max(2, r // 3), WHITE)


# ------------------------------------------------------------------ page
def build():
    cv = Canvas(W, H, PAPER)

    # ---- masthead -----------------------------------------------------
    cv.rect(0, 0, W, 148, NAVY)
    cv.rect(0, 148, W, 4, GOLD)
    cv.text(W // 2, 22, "THE WORLD TODAY", 8, WHITE, 'c')
    cv.text(W // 2, 100, "SATURDAY 21 NOVEMBER 2026", 5, GOLD, 'c')

    # ---- lead headline ------------------------------------------------
    cv.text(W // 2, 172, "RUSSIAN MISSILES LAND IN POLAND", 5, RED, 'c')
    cv.hline(28, 995, 216, RULE, 2)

    # ---- map panel (left) ---------------------------------------------
    mx0, my0, mw, mh = 28, 230, 460, 330
    cv.rect(mx0, my0, mw, mh, SEA)
    # frame
    cv.hline(mx0, mx0 + mw, my0, INK, 2)
    cv.hline(mx0, mx0 + mw, my0 + mh, INK, 2)
    cv.vline(mx0, my0, my0 + mh, INK, 2)
    cv.vline(mx0 + mw, my0, my0 + mh, INK, 2)
    cv.text(mx0 + 14, my0 + 10, "POLAND UNDER FIRE", 2, RED)
    cv.text(mx0 + mw - 14, my0 + 10, "NATO ALLY HIT", 2, NAVY, 'r')

    # Poland outline, normalised coords -> map box
    bx, by, bw, bh = mx0 + 50, my0 + 44, 340, 250
    outline = [
        (0.03, 0.14), (0.10, 0.18), (0.16, 0.10), (0.30, 0.05),
        (0.42, 0.02), (0.55, 0.07), (0.66, 0.05), (0.78, 0.12),
        (0.90, 0.20), (0.97, 0.34), (0.99, 0.48), (0.93, 0.62),
        (0.86, 0.80), (0.72, 0.92), (0.55, 0.97), (0.38, 0.90),
        (0.22, 0.86), (0.10, 0.70), (0.04, 0.48), (0.01, 0.30),
    ]
    pts = [(bx + int(fx * bw), by + int(fy * bh)) for fx, fy in outline]
    cv.poly(pts, LAND, LAND_EDGE)
    cv.text(bx + int(0.30 * bw), by + int(0.44 * bh), "POLAND", 4, (70, 80, 60), 'c')

    # neighbours (kept clear of the landmass and of the impact labels)
    cv.text(mx0 + 6, by + int(0.55 * bh), "GERMANY", 2, GREY)
    cv.text(mx0 + mw - 8, by + int(0.40 * bh), "BELARUS", 2, GREY, 'r')
    cv.text(mx0 + mw - 8, by + bh - 10, "UKRAINE", 2, GREY, 'r')
    cv.text(bx + int(0.78 * bw), by + 2, "BALTIC SEA", 2, NAVY_LT, 'c')

    # Warsaw star
    wx, wy = bx + int(0.52 * bw), by + int(0.38 * bh)
    cv.circle(wx, wy, 7, NAVY)
    cv.text(wx + 12, wy - 7, "WARSAW", 2, INK)

    # missile impact markers (south-east Poland); labels sit left of
    # the burst for the two northern sites, right for the southern one,
    # so none of them runs past the panel edge or over another label.
    impacts = [
        (0.76, 0.58, "RUDNIK NAD SANEM", 'l'),
        (0.80, 0.66, "NOWY LIPOWIEC", 'l'),
        (0.86, 0.72, "MOLODYCZ", 'r'),
    ]
    for fx, fy, name, side in impacts:
        ix, iy = bx + int(fx * bw), by + int(fy * bh)
        burst(cv, ix, iy, 13, RED)
        if side == 'l':
            cv.text(ix - 14, iy - 6, name, 2, RED, 'r')
        else:
            cv.text(ix + 16, iy - 6, name, 2, RED)

    # NATO emblem, top-right of the map panel
    ex, ey = mx0 + mw - 52, my0 + 74
    cv.circle(ex, ey, 30, NAVY)
    cv.ring(ex, ey, 30, WHITE, 2)
    nato_star(cv, ex, ey, 22, WHITE)
    cv.text(ex, ey + 38, "NATO", 3, NAVY, 'c')

    cv.text(mx0 + mw // 2, my0 + mh - 22,
            "2 Kh-101 cruise missiles + 1 jet drone", 2, INK, 'c')

    # ---- lead body (right column) --------------------------------------
    lx, lw = 512, 484
    y = 230
    cv.text(lx, y, "LEAD STORY", 2, RED)
    y = 256
    y = cv.para(lx, y,
                "Two Kh-101 cruise missiles and a jet drone hit "
                "Poland before dawn on Friday.",
                3, INK, lw, leading=24)
    y += 6
    y = cv.para(lx, y,
                "Tusk: an 'intentional provocation', timed with "
                "Coalition drills. Rutte: a 'grave violation'.",
                3, INK, lw, leading=24)
    y += 6
    y = cv.para(lx, y,
                "NATO jets scrambled. Rutte in Warsaw today. No "
                "deaths, no damage. 8 killed in Kyiv the same night; "
                "embassies hit.",
                3, INK, lw, leading=24)

    # ---- markets strip --------------------------------------------------
    sy0 = 578
    cv.rect(0, sy0, W, 86, DARK_STRIP)
    cv.text(28, sy0 + 10, "WALL STREET IN CORRECTION", 4, GOLD)
    cv.text(28, sy0 + 44,
            "S&P 500 -3.7%   DOW -3.7%   NASDAQ -5.28%",
            3, WHITE)
    cv.text(28, sy0 + 70,
            "NIKKEI -5.06%   NVIDIA -14%   Anthropic IPO +17% day one, then -11% day two.",
            2, (200, 200, 200))

    # ---- story panels ---------------------------------------------------
    panels = [
        ("SUMMIT AFTERMATH",
         "First Trump-Xi-Putin summit ends in a joint declaration, "
         "few concrete results. Trump calls Putin 'my friend'."),
        ("ICJ: GENOCIDE VERDICT",
         "The International Court of Justice rules Myanmar committed "
         "genocide against the Rohingya minority."),
        ("UK AND EU SIGN 3 DEALS",
         "Britain and the EU sign three deals in Brussels: food "
         "trade, a carbon market and youth mobility. PM Andy Burnham."),
        ("BERLIN: READY TO TALK",
         "Ukraine's backers meet in Berlin: Europe is ready to "
         "negotiate with Russia. Kushner: Russia is 'comfortable' "
         "with Article 5-style security guarantees."),
        ("IRAN WAR NEARS MONTH 9",
         "Trump in no rush; a decision may come only in 2027. US "
         "sanctions four oil managers. A tanker burns near Hormuz. "
         "Saudi coalition stops a Houthi missile over Riyadh."),
        ("NVIDIA IN TURMOIL",
         "Trump urges the board to bring back Jensen Huang; the "
         "board refuses. Reuters: the SEC is investigating Nvidia's "
         "accounting."),
    ]
    px, py = 28, 678
    pw, ph, gap = 312, 136, 16
    for i, (title, body) in enumerate(panels):
        x = px + (i % 3) * (pw + gap)
        yy = py + (i // 3) * (ph + gap)
        cv.rect(x, yy, pw, ph, PANEL_BG)
        cv.hline(x, x + pw, yy, INK, 2)
        cv.hline(x, x + pw, yy + ph, INK, 1)
        cv.vline(x, yy, yy + ph, INK, 1)
        cv.vline(x + pw, yy, yy + ph, INK, 1)
        cv.rect(x, yy + 2, pw, 4, RED)
        cv.text(x + 10, yy + 14, title, 2, NAVY)
        cv.para(x + 10, yy + 36, body, 2, INK, pw - 20, leading=14)

    # ---- footer ---------------------------------------------------------
    fy = 978
    cv.hline(28, 995, fy, RULE, 2)
    cv.para(28, fy + 10,
            "ALSO: Gold hits a 14-month low, -9.4% in a week. North "
            "Korea expands its uranium enrichment plant. Palisades "
            "fire: LA jury convicts Jonathan Rinderknecht.",
            2, INK, 968, leading=17)

    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(build())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
