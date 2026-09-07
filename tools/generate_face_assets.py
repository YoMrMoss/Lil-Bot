#!/usr/bin/env python3
"""Generate original 1-bit Lil Bot Face (.lbf) assets and a C++ header.

The format borrows the compact local-frame idea used by other desk companions,
but is original to Lil Bot and sized for its 320x170 ST7789 display.
"""

from __future__ import annotations

import struct
from pathlib import Path

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


def face(name: str) -> Canvas:
    import math
    c = Canvas()
    if name == "cat":
        c.line(37,73,55,48); c.line(55,48,73,70); c.line(247,70,265,48); c.line(265,48,283,73)
        c.circle(92,82,12,5); c.circle(228,82,12,5); c.line(148,96,160,106); c.line(160,106,172,96)
        c.arc(140,112,20,0,math.pi/2,4); c.arc(180,112,20,math.pi/2,math.pi,4)
    elif name == "helper":
        c.arc(90,88,25,math.pi,math.tau,6); c.arc(230,88,25,math.pi,math.tau,6)
        c.arc(160,105,24,0,math.pi,5); c.line(33,108,58,122,5); c.line(58,122,45,135,5); c.line(287,108,262,122,5); c.line(262,122,275,135,5)
    elif name == "showoff":
        c.line(35,75,72,75,6); c.line(248,75,285,75,6); c.line(98,116,72,132,5); c.line(222,116,248,132,5)
        c.line(137,106,160,116,4); c.line(160,116,183,106,4)
    elif name == "crying":
        c.line(62,75,112,75,7); c.line(208,75,258,75,7); c.line(112,75,124,92,6); c.line(208,75,196,92,6)
        c.arc(160,124,22,math.pi,math.tau,5); c.line(84,98,77,128,4); c.line(236,98,243,128,4)
    elif name == "nervous":
        c.circle(92,82,22,5); c.circle(228,82,22,5); c.dot(92,82,7); c.dot(228,82,7)
        pts=[(135,124),(145,117),(155,128),(165,117),(175,128),(185,120)]
        for a,b in zip(pts,pts[1:]): c.line(*a,*b,4)
    elif name == "rage":
        c.line(48,66,105,88,7); c.line(272,66,215,88,7); c.circle(95,91,9,4); c.circle(225,91,9,4)
        c.line(137,119,146,111,4); c.line(146,111,155,122,4); c.line(155,122,165,111,4); c.line(165,111,175,122,4); c.line(175,122,184,114,4)
        c.line(18,139,135,139,5); c.line(185,139,302,139,5); c.line(34,139,45,153,4); c.line(286,139,275,153,4)
        c.line(12,46,38,62,5); c.line(38,62,22,78,5); c.line(282,62,308,46,5); c.line(282,62,298,78,5)
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
