from PIL import Image, ImageDraw, ImageFont, ImageFilter

CYAN = "#19F7FF"
PINK = "#FF2DAA"
PURPLE = "#8B3DFF"
INK = "#02040D"
NAVY = "#070A1A"
TEXT = "#E9FDFF"

def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()

def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def glow_shape(base, box, radius, color, blur=25):
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle(box, radius=radius, fill=color)
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(blur)))

def face_panel(style, mood="normal", accent=CYAN):
    scale = 2
    panel = Image.new("RGBA", (320 * scale, 170 * scale), NAVY)
    d = ImageDraw.Draw(panel)
    # subtle screen vignette
    for inset in range(28, 0, -2):
        shade = 10 + (28-inset)//3
        d.rounded_rectangle((inset, inset, 640-inset, 340-inset), radius=55, outline=(shade, shade+8, shade+25, 160), width=3)

    eyes = [(142, 104, 282, 232), (358, 104, 498, 232)]
    if mood == "music":
        eyes = [(142, 94, 282, 222), (358, 112, 498, 240)]
    if mood == "gaming":
        eyes = [(132, 112, 292, 214), (348, 112, 508, 214)]
    if mood == "sleep":
        eyes = [(140, 160, 285, 178), (355, 160, 500, 178)]

    for i, box in enumerate(eyes):
        eye_color = PINK if mood == "music" and i == 1 else accent
        glow_shape(panel, box, 42 if mood != "sleep" else 9, eye_color, 22)
        d.rounded_rectangle(box, radius=42 if mood != "sleep" else 9, fill=eye_color)
        if mood != "sleep":
            cx = (box[0]+box[2])//2 + (8 if mood == "gaming" else 0)
            cy = (box[1]+box[3])//2
            if style == "oval":
                d.ellipse((cx-14, cy-22, cx+14, cy+22), fill=INK)
            elif style == "rounded-square":
                d.rounded_rectangle((cx-17, cy-20, cx+17, cy+20), radius=11, fill=INK)
            elif style == "capsule":
                d.rounded_rectangle((cx-11, cy-27, cx+11, cy+27), radius=11, fill=INK)
            elif style == "edge-notch":
                if i == 0:
                    d.rounded_rectangle((box[2]-30, cy-23, box[2]+4, cy+23), radius=16, fill=INK)
                else:
                    d.rounded_rectangle((box[0]-4, cy-23, box[0]+30, cy+23), radius=16, fill=INK)

    # simple mouth, also made from unlit pixels
    if mood == "sleep":
        d.arc((292, 212, 348, 244), 0, 180, fill=PURPLE, width=8)
    elif mood == "music":
        d.arc((288, 212, 352, 266), 5, 175, fill=PINK, width=8)
        d.text((34, 35), "♪", font=font(36, True), fill=CYAN)
        d.text((560, 45), "♫", font=font(36, True), fill=PINK)
    elif mood == "gaming":
        d.line((300, 247, 340, 247), fill=PINK, width=8)
    else:
        d.arc((294, 216, 346, 250), 5, 175, fill=CYAN, width=7)
    return panel

def robot_card(style, title, subtitle, mood):
    card = Image.new("RGBA", (700, 470), "#10162B")
    d = ImageDraw.Draw(card)
    # headphone band and cups
    d.arc((112, 64, 588, 372), 180, 360, fill="#343B54", width=38)
    d.arc((122, 72, 578, 362), 180, 360, fill=PINK, width=8)
    rounded(d, (74, 190, 145, 350), 30, "#171C2C", CYAN, 7)
    rounded(d, (555, 190, 626, 350), 30, "#171C2C", CYAN, 7)
    d.ellipse((90, 235, 129, 304), outline=PINK, width=8)
    d.ellipse((571, 235, 610, 304), outline=PINK, width=8)
    # head and exact-aspect screen
    rounded(d, (104, 128, 596, 382), 58, "#1A1F2D", "#3A435B", 8)
    preview = face_panel(style, mood).resize((448, 238), Image.Resampling.LANCZOS)
    mask = Image.new("L", preview.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 447, 237), radius=42, fill=255)
    card.paste(preview, (126, 142), mask)
    d.text((22, 18), title, font=font(24, True), fill=TEXT)
    d.text((22, 48), subtitle, font=font(14), fill="#9EACCB")
    return card

cards = [
    robot_card("oval", "A  Soft oval cutout", "Normal • familiar and friendly", "normal"),
    robot_card("rounded-square", "B  Rounded-square cutout", "Music • matches the eye-panel language", "music"),
    robot_card("capsule", "C  Vertical capsule cutout", "Gaming • focused and more robotic", "gaming"),
    robot_card("edge-notch", "D  Inward edge notch", "Normal • no floating pupil shape", "normal"),
]

sheet = Image.new("RGB", (1460, 1060), "#070914")
d = ImageDraw.Draw(sheet)
d.text((30, 22), "LIL BOT • UNLIT PUPIL STUDY", font=font(34, True), fill=TEXT)
d.text((31, 65), "All dark pupil areas represent LEDs switched off — no pupil glow or white reflection.", font=font(17), fill="#9EACCB")
positions = [(30, 108), (730, 108), (30, 588), (730, 588)]
for card, pos in zip(cards, positions):
    sheet.paste(card, pos, card)
sheet.save("LilBot_TestLab/LilBot_Unlit_Pupil_Mockups.png", quality=95)

# Also export actual 320 x 170 screen proofs for the recommended option.
for mood in ("normal", "music", "gaming", "sleep"):
    face_panel("oval", mood).resize((320, 170), Image.Resampling.LANCZOS).convert("RGB").save(f"LilBot_TestLab/screen_{mood}.png")

def cartoon_face(mood):
    im = Image.new("RGBA", (640, 340), NAVY)
    d = ImageDraw.Draw(im)
    # Expressive tall eye panels inspired by vintage cartoon construction.
    eye_boxes = [(138, 73, 282, 248), (358, 73, 502, 248)]
    if mood == "surprised": eye_boxes = [(145, 55, 278, 262), (362, 55, 495, 262)]
    if mood == "gaming": eye_boxes = [(128, 102, 292, 231), (348, 102, 512, 231)]
    if mood == "sleepy": eye_boxes = [(136, 116, 286, 221), (354, 116, 504, 221)]
    if mood == "happy": eye_boxes = [(135, 82, 285, 237), (355, 82, 505, 237)]
    for i, box in enumerate(eye_boxes):
        col = PINK if mood == "music" and i == 1 else CYAN
        glow_shape(im, box, 57, col, 24)
        d.rounded_rectangle(box, radius=57, fill=col)
        x1,y1,x2,y2=box; cx=(x1+x2)//2; cy=(y1+y2)//2
        # Each pupil is only a near-black region cut from the lit panel.
        if mood == "normal":
            if i == 0: d.polygon([(cx-28,y1+23),(cx+18,cy),(cx-28,y2-21)], fill=INK)
            else: d.polygon([(cx+28,y1+23),(cx-18,cy),(cx+28,y2-21)], fill=INK)
        elif mood == "happy":
            d.pieslice((cx-44,cy-47,cx+44,cy+41), 0, 180, fill=INK)
        elif mood == "music":
            shift = -8 if i == 0 else 8
            d.rounded_rectangle((cx-19+shift,cy-43,cx+19+shift,cy+43), radius=19, fill=INK)
        elif mood == "gaming":
            pts=[(x1-2,y1-2),(x2+2,y1-2),(x2-17,y1+45),(cx,cy+12),(x1+17,y1+45)]
            d.polygon(pts, fill=INK)
        elif mood == "sleepy":
            d.rectangle((x1, y1, x2, cy+7), fill=INK)
        elif mood == "surprised":
            d.ellipse((cx-17,cy-28,cx+17,cy+28), fill=INK)
    # Brows/lids carry most of the emotion; pupils remain fully unlit.
    brow = PINK if mood in ("gaming","music") else CYAN
    if mood == "gaming":
        d.line((142,72,278,104),fill=brow,width=10);d.line((362,104,498,72),fill=brow,width=10)
    elif mood == "sleepy":
        d.arc((135,79,286,155),180,350,fill=PURPLE,width=9);d.arc((354,79,505,155),190,360,fill=PURPLE,width=9)
    else:
        d.arc((142,35,278,101),185,350,fill=brow,width=8);d.arc((362,35,498,101),190,355,fill=brow,width=8)
    if mood == "surprised": d.ellipse((300,265,340,307),outline=PINK,width=8)
    elif mood == "sleepy": d.arc((296,257,344,285),0,180,fill=PURPLE,width=7)
    elif mood == "gaming": d.line((300,280,340,280),fill=PINK,width=8)
    else: d.arc((292,250,348,292),5,175,fill=PINK if mood=="music" else CYAN,width=8)
    if mood == "music":
        d.text((43,35),"♪",font=font(36,True),fill=CYAN);d.text((555,48),"♫",font=font(38,True),fill=PINK)
    return im

def expression_card(mood, title):
    card=Image.new("RGBA",(660,410),"#10162B");d=ImageDraw.Draw(card)
    d.text((20,16),title,font=font(23,True),fill=TEXT)
    d.text((20,47),"Dark shapes = LEDs off",font=font(14),fill="#9EACCB")
    d.arc((90,65,570,360),180,360,fill="#343B54",width=30)
    d.arc((100,72,560,352),180,360,fill=PINK,width=7)
    rounded(d,(45,170,112,340),28,"#171C2C",CYAN,6);rounded(d,(548,170,615,340),28,"#171C2C",CYAN,6)
    rounded(d,(72,103,588,365),55,"#1A1F2D","#3A435B",8)
    face=cartoon_face(mood).resize((480,255),Image.Resampling.LANCZOS)
    mask=Image.new("L",face.size,0);ImageDraw.Draw(mask).rounded_rectangle((0,0,479,254),radius=45,fill=255)
    card.paste(face,(90,106),mask)
    return card

expressions=[("normal","Normal • inward wedge"),("happy","Happy • lowered dark lids"),("music","Music • offset cutouts"),("gaming","Gaming • sharp upper mask"),("sleepy","Sleepy • lights fading down"),("surprised","Surprised • expanded eye panels")]
sheet2=Image.new("RGB",(1400,1395),"#070914");d=ImageDraw.Draw(sheet2)
d.text((30,22),"LIL BOT • EXPRESSIVE CARTOON EYE STUDY",font=font(33,True),fill=TEXT)
d.text((31,66),"Original neon robot expressions using tall eye panels, elastic brows, and unlit pupil shapes.",font=font(17),fill="#9EACCB")
for n,(mood,title) in enumerate(expressions):
    x=30+(n%2)*690;y=106+(n//2)*425
    card=expression_card(mood,title);sheet2.paste(card,(x,y),card)
sheet2.save("LilBot_TestLab/LilBot_Cartoon_Eye_Mockups.png",quality=95)

def liquid_face(kind):
    im=Image.new("RGBA",(640,340),NAVY);d=ImageDraw.Draw(im)
    boxes=[(130,66,296,250),(344,66,510,250)]
    for i,b in enumerate(boxes):
        col=CYAN if i==0 else (PINK if kind=="split-color" else CYAN)
        glow_shape(im,b,66,col,23);d.rounded_rectangle(b,radius=66,fill=col)
        x1,y1,x2,y2=b;cx=(x1+x2)//2;cy=(y1+y2)//2
        if kind=="bottom-pool":
            d.pieslice((x1-8,cy-20,x2+8,y2+38),0,180,fill=INK)
        elif kind=="inner-glance":
            px=x2-48 if i==0 else x1+48
            d.ellipse((px-40,cy-49,px+40,cy+49),fill=INK)
        elif kind=="soft-crescent":
            px=x2-35 if i==0 else x1+35
            d.ellipse((px-59,cy-72,px+59,cy+72),fill=INK)
            # Lit eye color cuts back into the dark pool to form an organic crescent.
            bite_x=px-24 if i==0 else px+24
            d.ellipse((bite_x-38,cy-38,bite_x+38,cy+38),fill=col)
        elif kind=="split-color":
            d.pieslice((x1-5,cy-24,x2+5,y2+28),180,360,fill=INK)
    if kind=="bottom-pool": d.arc((291,254,349,292),5,175,fill=PINK,width=8)
    elif kind=="inner-glance": d.arc((294,253,346,287),5,175,fill=CYAN,width=7)
    elif kind=="soft-crescent": d.arc((294,259,346,291),180,355,fill=PURPLE,width=7)
    else: d.arc((288,249,352,295),5,175,fill=PINK,width=8)
    return im

liquid=[("bottom-pool","A  Bottom pools","Soft, friendly, highly readable"),("inner-glance","B  Large inner pupils","Classic cartoon eye contact"),("soft-crescent","C  Organic crescents","Most playful and expressive"),("split-color","D  Two-color music eyes","Dark lower mask with Miami energy")]
sheet3=Image.new("RGB",(1400,990),"#070914");d=ImageDraw.Draw(sheet3)
d.text((30,22),"LIL BOT • LIQUID UNLIT EYE STUDY",font=font(33,True),fill=TEXT)
d.text((31,66),"The cyan and pink areas glow. Every near-black pool is a section of the eye switched off.",font=font(17),fill="#9EACCB")
for n,(kind,title,sub) in enumerate(liquid):
    card=Image.new("RGBA",(660,410),"#10162B");cd=ImageDraw.Draw(card)
    cd.text((20,16),title,font=font(23,True),fill=TEXT);cd.text((20,48),sub,font=font(14),fill="#9EACCB")
    cd.arc((90,65,570,360),180,360,fill="#343B54",width=30);cd.arc((100,72,560,352),180,360,fill=PINK,width=7)
    rounded(cd,(45,170,112,340),28,"#171C2C",CYAN,6);rounded(cd,(548,170,615,340),28,"#171C2C",CYAN,6)
    rounded(cd,(72,103,588,365),55,"#1A1F2D","#3A435B",8)
    face=liquid_face(kind).resize((480,255),Image.Resampling.LANCZOS);mask=Image.new("L",face.size,0);ImageDraw.Draw(mask).rounded_rectangle((0,0,479,254),radius=45,fill=255)
    card.paste(face,(90,106),mask)
    x=30+(n%2)*690;y=106+(n//2)*425;sheet3.paste(card,(x,y),card)
sheet3.save("LilBot_TestLab/LilBot_Liquid_Unlit_Eye_Mockups.png",quality=95)
