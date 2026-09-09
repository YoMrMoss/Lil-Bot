#!/usr/bin/env python3
"""Generate original 1-bit Lil Bot Face (.lbf) assets and a C++ header.

The format borrows the compact local-frame idea used by other desk companions,
but is original to Lil Bot and sized for its 320x170 ST7789 display.
"""

from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "firmware" / "data" / "faces"
HEADER = ROOT / "firmware" / "include" / "face_assets.h"
WIDTH, HEIGHT = 320, 170


class Canvas:
    def __init__(self):
        self.pixels = bytearray(WIDTH * HEIGHT)

    def dot(self, x: int, y: int, radius: int = 3):
        for py in range(max(0, y-radius), min(HEIGHT, y+radius+1)):
            for px in range(max(0, x-radius), min(WIDTH, x+radius+1)):
                if (px-x)**2 + (py-y)**2 <= radius**2:
                    self.pixels[py*WIDTH+px] = 1

    def line(self, x0: int, y0: int, x1: int, y1: int, width: int = 4):
        dx, sx, dy, sy = abs(x1-x0), 1 if x0<x1 else -1, -abs(y1-y0), 1 if y0<y1 else -1
        err = dx + dy
        while True:
            self.dot(x0, y0, max(1, width//2))
            if x0 == x1 and y0 == y1:
                return
            twice = 2*err
            if twice >= dy: err, x0 = err+dy, x0+sx
            if twice <= dx: err, y0 = err+dx, y0+sy

    def circle(self, cx: int, cy: int, radius: int, width: int = 4):
        import math
        points = [(round(cx+math.cos(a/80*math.tau)*radius), round(cy+math.sin(a/80*math.tau)*radius)) for a in range(81)]
        for a, b in zip(points, points[1:]): self.line(*a, *b, width)

    def arc(self, cx: int, cy: int, radius: int, start: float, end: float, width: int = 4):
        import math
        points = [(round(cx+math.cos(start+(end-start)*i/40)*radius), round(cy+math.sin(start+(end-start)*i/40)*radius)) for i in range(41)]
        for a, b in zip(points, points[1:]): self.line(*a, *b, width)

    def packed(self) -> bytes:
        out = bytearray((WIDTH*HEIGHT+7)//8)
        for index, value in enumerate(self.pixels):
            if value: out[index//8] |= 0x80 >> (index%8)
        return bytes(out)

    def emoticon(self, text: str, max_width: int = 294, max_height: int = 104):
        """Rasterize the same emoticon text used by the browser simulator."""
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        size = 72
        while size > 10:
            font = ImageFont.truetype(font_path, size)
            left, top, right, bottom = font.getbbox(text, stroke_width=1)
            if right - left <= max_width and bottom - top <= max_height:
                break
            size -= 1
        image = Image.new("1", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(image)
        left, top, right, bottom = font.getbbox(text, stroke_width=1)
        x = (WIDTH - (right - left)) // 2 - left
        y = (HEIGHT - (bottom - top)) // 2 - top
        draw.text((x, y), text, font=font, fill=1, stroke_width=1, stroke_fill=1)
        self.pixels[:] = bytes(image.getdata())


def face(name: str) -> Canvas:
    import math
    c = Canvas()
    symbols = {
        "cat": "≽^•⩊•^≼",
        "helper": "(ദ്ദി˙ᗜ˙)",
        "showoff": "(つ▀¯▀ )つ",
        "crying": "(T⌓T)",
        "nervous": "⊙˛̼⊙",
        "rage": "(┛◉Д◉)┛彡┻━┻",
    }
    if name in symbols and name not in {"helper", "showoff", "rage"}:
        c.emoticon(symbols[name])
    elif name == "cat":
        c.line(37,73,55,48); c.line(55,48,73,70); c.line(247,70,265,48); c.line(265,48,283,73)
        c.circle(92,82,12,5); c.circle(228,82,12,5); c.line(148,96,160,106); c.line(160,106,172,96)
        c.arc(140,112,20,0,math.pi/2,4); c.arc(180,112,20,math.pi/2,math.pi,4)
    elif name == "helper":
        # Eager helper: familiar face plus a clear little thumbs-up.
        c.dot(112,78,11); c.dot(208,78,11); c.arc(160,100,27,0,math.pi,8)
        c.line(42,112,61,126,8); c.line(61,126,72,112,8); c.line(61,126,48,142,8)
        c.line(278,112,259,126,8); c.line(259,126,248,112,8); c.line(259,126,272,142,8)
    elif name == "showoff":
        # Confident "check this out" pose with block shades and open arms.
        c.line(82,76,122,76,12); c.line(198,76,238,76,12); c.line(143,111,177,111,7)
        c.line(25,105,55,121,7); c.line(55,121,39,139,7); c.line(295,105,265,121,7); c.line(265,121,281,139,7)
    elif name == "crying":
        c.line(62,75,112,75,7); c.line(208,75,258,75,7); c.line(112,75,124,92,6); c.line(208,75,196,92,6)
        c.arc(160,124,22,math.pi,math.tau,5); c.line(84,98,77,128,4); c.line(236,98,243,128,4)
    elif name == "nervous":
        c.circle(92,82,22,5); c.circle(228,82,22,5); c.dot(92,82,7); c.dot(228,82,7)
        pts=[(135,124),(145,117),(155,128),(165,117),(175,128),(185,120)]
        for a,b in zip(pts,pts[1:]): c.line(*a,*b,4)
    elif name == "rage":
        c.line(48,55,108,82,8); c.line(272,55,212,82,8); c.circle(98,87,11,5); c.circle(222,87,11,5)
        c.circle(160,111,15,7)
        c.line(31,139,289,139,9); c.line(48,139,60,158,7); c.line(272,139,260,158,7)
        c.line(14,96,43,112,7); c.line(306,74,280,91,7); c.line(300,55,276,69,6)
    elif name == "gaming":
        c.line(36,48,36,124,6); c.line(36,48,58,48,6); c.line(36,124,58,124,6)
        c.line(284,48,284,124,6); c.line(262,48,284,48,6); c.line(262,124,284,124,6)
        c.line(79,86,111,86,7); c.line(95,70,95,102,7); c.dot(150,86,5); c.dot(174,86,5); c.dot(223,80,8); c.dot(246,92,8)
    else:
        raise ValueError(name)
    return c


def main():
    ASSET_DIR.mkdir(parents=True, exist_ok=True); HEADER.parent.mkdir(parents=True, exist_ok=True)
    names = ["cat", "helper", "showoff", "crying", "nervous", "rage", "gaming"]
    arrays=[]; manifest=[]
    for name in names:
        packed=face(name).packed(); blob=b"LBF1"+struct.pack("<BHHBH",1,WIDTH,HEIGHT,1,1000)+packed
        (ASSET_DIR/f"{name}.lbf").write_bytes(blob)
        values=",".join(f"0x{x:02x}" for x in packed)
        symbol=f"FACE_{name.upper()}"
        arrays.append(f"const uint8_t {symbol}[] PROGMEM = {{{values}}};")
        manifest.append(f'  {{"{name}", {symbol}, sizeof({symbol})}},')
    rows = [line[:-2] + f", {WIDTH}, {HEIGHT}}}," for line in manifest]
    HEADER.write_text("#pragma once\n#include <Arduino.h>\n\n"+"\n".join(arrays)+"\n\nstruct FaceAsset { const char* name; const uint8_t* data; size_t size; uint16_t width; uint16_t height; };\nconst FaceAsset FACE_ASSETS[] = {\n"+"\n".join(rows)+"\n};\nconst size_t FACE_ASSET_COUNT = sizeof(FACE_ASSETS)/sizeof(FACE_ASSETS[0]);\n",encoding="utf-8")
    print(f"Generated {len(names)} faces in {ASSET_DIR}")


if __name__ == "__main__": main()
