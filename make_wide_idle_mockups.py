from PIL import Image, ImageDraw, ImageFont, ImageFilter

CYAN="#19F7FF"; PINK="#FF2DAA"; PURPLE="#8B3DFF"; INK="#02040D"; NAVY="#070A1A"; TEXT="#E9FDFF"

def font(size,bold=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:return ImageFont.truetype(p,size)
    except:return ImageFont.load_default()

def glow(im, draw_fn, color, blur=22):
    g=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(g); draw_fn(d,color); im.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))

def heart(draw,cx,cy,s,fill):
    pts=[(cx,cy+s),(cx-s,cy),(cx-s,cy-s//2),(cx-s//2,cy-s),(cx,cy-s//2),(cx+s//2,cy-s),(cx+s,cy-s//2),(cx+s,cy)]
    draw.polygon(pts,fill=fill)

def star(draw,cx,cy,r,fill):
    pts=[(cx,cy-r),(cx+r//4,cy-r//4),(cx+r,cy),(cx+r//4,cy+r//4),(cx,cy+r),(cx-r//4,cy+r//4),(cx-r,cy),(cx-r//4,cy-r//4)]
    draw.polygon(pts,fill=fill)

def screen(kind):
    im=Image.new("RGBA",(640,340),NAVY); d=ImageDraw.Draw(im)
    # Centers at 174 and 466 leave a much larger central gap than the earlier studies.
    centers=(174,466)
    if kind=="normal":
        for i,cx in enumerate(centers):
            box=(cx-74,78,cx+74,246); glow(im,lambda q,c,b=box:q.rounded_rectangle(b,radius=60,fill=c),CYAN);d.rounded_rectangle(box,radius=60,fill=CYAN)
            px=cx+(20 if i==0 else -20);d.ellipse((px-34,126,px+34,208),fill=INK)
        d.arc((286,239,354,289),5,175,fill=PINK,width=9)
    elif kind=="anime":
        for cx,col in zip(centers,(CYAN,PINK)):
            glow(im,lambda q,c,x=cx:star(q,x,154,61,c),col,28);star(d,cx,154,61,col)
        d.ellipse((160,245,188,258),fill=PINK);d.ellipse((452,245,480,258),fill=PINK);d.arc((283,221,357,287),5,175,fill=CYAN,width=9)
    elif kind=="reading":
        for i,cx in enumerate(centers):
            d.rounded_rectangle((cx-88,75,cx+88,239),radius=53,outline=CYAN,width=13)
            px=cx+(15 if i==0 else -15);d.ellipse((px-31,120,px+31,196),fill=CYAN);d.ellipse((px-17,137,px+17,180),fill=INK)
        d.line((262,133,378,133),fill=PINK,width=12);d.line((83,120,28,97),fill=PINK,width=9);d.line((557,120,612,97),fill=PINK,width=9)
        d.arc((288,246,352,287),5,175,fill=PURPLE,width=8);d.text((291,36),"www",font=font(22,True),fill=PINK)
    elif kind=="racing":
        visor=[(52,102),(151,70),(320,91),(489,70),(588,102),(548,222),(365,203),(320,174),(275,203),(92,222)]
        glow(im,lambda q,c:q.polygon(visor,fill=c),PINK,25);d.polygon(visor,fill=PINK)
        inner=[(67,112),(158,86),(309,102),(288,174),(267,187),(104,204),(67,112),(331,102),(482,86),(573,112),(536,204),(373,187),(352,174)]
        d.polygon(inner,fill=INK);d.line((83,126,270,110),fill=CYAN,width=7);d.line((370,110,557,126),fill=CYAN,width=7)
        d.arc((286,235,354,286),5,175,fill=CYAN,width=9);d.text((281,286),"GO!",font=font(21,True),fill=PINK)
    elif kind=="hearts":
        for cx,col in zip(centers,(PINK,CYAN)):
            glow(im,lambda q,c,x=cx:heart(q,x,156,68,c),col,25);heart(d,cx,156,68,col)
        d.ellipse((150,245,198,262),fill=PINK);d.ellipse((442,245,490,262),fill=PINK);d.arc((282,220,358,290),5,175,fill=PINK,width=10)
    elif kind=="buffering":
        for cx,col in zip(centers,(CYAN,PINK)):
            for n in range(3):d.arc((cx-63+n*12,91+n*12,cx+63-n*12,217-n*12),210,510,fill=col,width=10)
        d.line((302,260,338,260),fill=PURPLE,width=9);d.text((255,28),"LOADING",font=font(18,True),fill=CYAN)
    return im

items=[("normal","A  Wide-set normal","More breathing room; no headphones"),("anime","B  Anime sparkle idle","Occasional over-the-top happy face"),("reading","C  Web-browsing glasses","Tiny reading glasses and www indicator"),("racing","D  Racing visor","Sporty wraparound shades for fast activity"),("hearts","E  Heart-eye idle","Rare affectionate or achievement reaction"),("buffering","F  Buffering spirals","Funny loading or waiting expression")]
sheet=Image.new("RGB",(1460,1515),"#070914");sd=ImageDraw.Draw(sheet)
sd.text((30,22),"LIL BOT • WIDE-GAP FACE & IDLE STUDY",font=font(34,True),fill=TEXT)
sd.text((31,67),"Headphones removed from the face area. Each preview uses the actual 320 × 170 screen ratio.",font=font(17),fill="#9EACCB")
for n,(kind,title,sub) in enumerate(items):
    card=Image.new("RGBA",(700,450),"#10162B");d=ImageDraw.Draw(card)
    d.text((22,16),title,font=font(24,True),fill=TEXT);d.text((22,49),sub,font=font(14),fill="#9EACCB")
    d.rounded_rectangle((28,91,672,421),radius=58,fill="#1A1F2D",outline="#3A435B",width=9)
    face=screen(kind).resize((600,319),Image.Resampling.LANCZOS);mask=Image.new("L",face.size,0);ImageDraw.Draw(mask).rounded_rectangle((0,0,599,318),radius=48,fill=255)
    card.paste(face,(50,98),mask)
    x=30+(n%2)*720;y=108+(n//2)*465;sheet.paste(card,(x,y),card)
sheet.save("LilBot_TestLab/LilBot_WideGap_Idle_Mockups.png",quality=95)
