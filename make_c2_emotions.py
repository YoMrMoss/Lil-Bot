from PIL import Image, ImageDraw, ImageFont, ImageFilter

CYAN = "#19F7FF"
PINK = "#FF2DAA"
PURPLE = "#8B3DFF"
INK = "#02040D"
NAVY = "#070A1A"
TEXT = "#E9FDFF"


def font(size, bold=False):
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def glow_shape(im, draw_fn, color=CYAN, blur=20):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), color)
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def pixel_brow(d, x, y, direction, color):
    """A three-step brow built on a 12 px grid; direction points toward its high end."""
    steps = [(x, y + 16, x + 34, y + 28), (x + 32, y + 8, x + 68, y + 20), (x + 66, y, x + 102, y + 12)]
    if direction < 0:
        steps = [(x, y, x + 36, y + 12), (x + 34, y + 8, x + 70, y + 20), (x + 68, y + 16, x + 102, y + 28)]
    for step in steps:
        d.rectangle(step, fill=color)


def face(state):
    """Render at 2x the T-Display-S3's physical 320x170 resolution."""
    im = Image.new("RGBA", (640, 340), NAVY)
    d = ImageDraw.Draw(im)

    # Locked C2 anchors: same eye size, 188 px internal gap, fixed mouth center.
    boxes = [(94, 52, 226, 256), (414, 52, 546, 256)]

    for box in boxes:
        glow_shape(im, lambda gd, c, b=box: gd.rounded_rectangle(b, 54, fill=c))
        d.rounded_rectangle(box, radius=54, fill=CYAN)

    # Expressions are made from unlit screen masks. Pupils never emit light.
    pupil_specs = {
        "happy": [(124, 92, 206, 217), (434, 92, 516, 217)],
        "excited": [(116, 75, 210, 220), (430, 75, 524, 220)],
        "surprised": [(130, 84, 202, 224), (438, 84, 510, 224)],
        "focused": [(132, 91, 204, 229), (436, 91, 508, 229)],
        "annoyed": [(112, 116, 196, 231), (444, 116, 528, 231)],
        "worried": [(128, 103, 200, 231), (440, 103, 512, 231)],
        "sad": [(124, 116, 200, 238), (440, 116, 516, 238)],
        "sleepy": [(110, 151, 205, 231), (435, 151, 530, 231)],
    }
    for p in pupil_specs[state]:
        d.rounded_rectangle(p, radius=min((p[2]-p[0])//2, 34), fill=INK)

    # Eyelids and brows alter the silhouette while preserving C2's anchors.
    if state == "happy":
        d.pieslice((98, 47, 226, 185), 180, 360, fill=INK)
        d.pieslice((414, 47, 542, 185), 180, 360, fill=INK)
        d.arc((284, 242, 356, 301), 8, 172, fill=PINK, width=10)
    elif state == "excited":
        pixel_brow(d, 104, 30, 1, PINK)
        pixel_brow(d, 434, 30, -1, PINK)
        d.rounded_rectangle((287, 248, 353, 307), radius=29, fill=PINK)
        d.rounded_rectangle((299, 256, 341, 292), radius=18, fill=INK)
    elif state == "surprised":
        d.rectangle((108, 30, 212, 42), fill=PURPLE)
        d.rectangle((120, 18, 200, 30), fill=PURPLE)
        d.rectangle((428, 30, 532, 42), fill=PURPLE)
        d.rectangle((440, 18, 520, 30), fill=PURPLE)
        d.ellipse((299, 253, 341, 304), fill=PINK)
        d.ellipse((309, 263, 331, 294), fill=INK)
    elif state == "focused":
        d.polygon([(94, 52), (226, 52), (226, 88), (94, 118)], fill=INK)
        d.polygon([(414, 52), (546, 52), (546, 118), (414, 88)], fill=INK)
        pixel_brow(d, 112, 38, -1, PINK)
        pixel_brow(d, 426, 38, 1, PINK)
        d.line((294, 276, 346, 276), fill=PINK, width=9)
    elif state == "annoyed":
        d.rounded_rectangle((94, 52, 226, 126), radius=50, fill=INK)
        d.rounded_rectangle((414, 52, 546, 126), radius=50, fill=INK)
        pixel_brow(d, 112, 52, -1, PINK)
        pixel_brow(d, 426, 52, 1, PINK)
        d.line((295, 278, 345, 278), fill=PURPLE, width=9)
    elif state == "worried":
        pixel_brow(d, 112, 34, 1, PINK)
        pixel_brow(d, 426, 34, -1, PINK)
        d.arc((293, 263, 347, 302), 188, 352, fill=PURPLE, width=9)
    elif state == "sad":
        d.polygon([(94, 52), (226, 52), (226, 99), (94, 75)], fill=INK)
        d.polygon([(414, 52), (546, 52), (546, 75), (414, 99)], fill=INK)
        pixel_brow(d, 112, 39, 1, PURPLE)
        pixel_brow(d, 426, 39, -1, PURPLE)
        d.arc((289, 265, 351, 307), 188, 352, fill=PINK, width=9)
        d.ellipse((551, 220, 569, 249), fill=CYAN)
    elif state == "sleepy":
        d.rounded_rectangle((94, 52, 226, 169), radius=50, fill=INK)
        d.rounded_rectangle((414, 52, 546, 169), radius=50, fill=INK)
        d.rectangle((106, 146, 216, 158), fill=PURPLE)
        d.rectangle((424, 146, 534, 158), fill=PURPLE)
        d.arc((295, 267, 345, 293), 5, 175, fill=PINK, width=8)
        d.text((549, 74), "z", font=font(34, True), fill=CYAN)
        d.text((579, 39), "z", font=font(25, True), fill=PINK)

    return im


items = [
    ("happy", "C2-H1  HAPPY", "Warm default response"),
    ("excited", "C2-E1  EXCITED", "Music beat or achievement"),
    ("surprised", "C2-S1  SURPRISED", "Alert or sudden event"),
    ("focused", "C2-F1  FOCUSED", "Gaming and active work"),
    ("annoyed", "C2-A1  ANNOYED", "Funny error reaction"),
    ("worried", "C2-W1  WORRIED", "Low battery or warning"),
    ("sad", "C2-SD1  SAD", "Loss, disconnect, or quiet beat"),
    ("sleepy", "C2-Z1  SLEEPY", "Idle and sleep mode"),
]

sheet = Image.new("RGB", (1460, 1970), "#070914")
sd = ImageDraw.Draw(sheet)
sd.text((30, 22), "LIL BOT • C2 EMOTION WORKSHOP", font=font(34, True), fill=TEXT)
sd.text(
    (31, 68),
    "C2 is now the primary face rig: wide-set tall eyes, fully unlit pupils, centered mouth, no nose.",
    font=font(17),
    fill="#9EACCB",
)

for n, (state, title, sub) in enumerate(items):
    card = Image.new("RGBA", (700, 450), "#10162B")
    cd = ImageDraw.Draw(card)
    cd.text((22, 16), title, font=font(23, True), fill=TEXT)
    cd.text((22, 49), sub, font=font(14), fill="#9EACCB")
    cd.rounded_rectangle((28, 91, 672, 421), radius=58, fill="#1A1F2D", outline="#3A435B", width=9)
    art = face(state).resize((600, 319), Image.Resampling.LANCZOS)
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 599, 318), radius=48, fill=255)
    card.paste(art, (50, 98), mask)
    x = 30 + (n % 2) * 720
    y = 108 + (n // 2) * 465
    sheet.paste(card, (x, y), card)

sheet.save("LilBot_C2_Emotion_Workshop.png", quality=95)
