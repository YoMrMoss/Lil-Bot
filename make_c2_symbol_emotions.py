from PIL import Image, ImageDraw, ImageFont

CYAN="#19F7FF"; PINK="#FF2DAA"; PURPLE="#8B3DFF"; INK="#02040D"; NAVY="#070A1A"; TEXT="#E9FDFF"

def font(size,bold=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:return ImageFont.truetype(p,size)
    except OSError:return ImageFont.load_default()

def open_eye(d,cx,cy=73,look=0,wide=False):
    w,h=(48,67) if wide else (42,61)
    d.rounded_rectangle((cx-w//2,cy-h//2,cx+w//2,cy+h//2),radius=18,outline=CYAN,width=5)
    # Black negative-space pupil: the only filled part of an open eye.
    d.rounded_rectangle((cx-9+look,cy-20,cx+9+look,cy+20),radius=8,fill=INK)

def heart(d,cx,cy,color=CYAN):
    pts=[(cx-18,cy-5),(cx-18,cy-12),(cx-10,cy-18),(cx,cy-9),(cx+10,cy-18),(cx+18,cy-12),(cx+18,cy-5),(cx,cy+18),(cx-18,cy-5)]
    d.line(pts,fill=color,width=5,joint="curve")

def face(state):
    # Draw at the physical 320x170 screen resolution for an authentic pixel edge.
    im=Image.new("RGB",(320,170),NAVY);d=ImageDraw.Draw(im)
    lx,rx=89,231

    if state=="neutral":
        open_eye(d,lx,look=5,wide=True);open_eye(d,rx,look=-5,wide=True)
        d.arc((148,105,172,124),5,175,fill=PINK,width=4)
    elif state=="happy":
        d.line((67,72,111,72),fill=CYAN,width=5);d.line((209,72,253,72),fill=CYAN,width=5)
        d.arc((146,98,174,124),5,175,fill=PINK,width=4)
    elif state=="love":
        heart(d,lx,70);heart(d,rx,70)
        d.arc((145,99,175,126),5,175,fill=PINK,width=4)
    elif state=="curious":
        d.ellipse((lx-20,52,lx+20,92),outline=CYAN,width=5);d.ellipse((rx-20,52,rx+20,92),outline=CYAN,width=5)
        d.arc((151,101,169,128),270,90,fill=PURPLE,width=4)
        # Question mark is an activity icon, not an eyebrow.
        d.arc((148,18,172,43),200,80,fill=PINK,width=5);d.rectangle((158,39,163,49),fill=PINK);d.rectangle((158,54,163,59),fill=PINK)
    elif state=="alert":
        d.ellipse((lx-21,51,lx+21,93),outline=CYAN,width=5);d.ellipse((rx-21,51,rx+21,93),outline=CYAN,width=5)
        d.rectangle((157,108,163,124),fill=PINK);d.arc((151,101,169,116),180,360,fill=PINK,width=4)
        d.rectangle((157,17,163,40),fill=PURPLE);d.rectangle((157,46,163,52),fill=PURPLE)
    elif state=="laugh":
        d.line((67,59,101,73,67,87),fill=CYAN,width=5,joint="curve");d.line((253,59,219,73,253,87),fill=CYAN,width=5,joint="curve")
        d.arc((143,96,177,130),0,180,fill=PINK,width=5);d.line((143,113,177,113),fill=PINK,width=5)
    elif state=="sleep":
        d.line((67,72,111,72),fill=CYAN,width=5);d.line((209,72,253,72),fill=CYAN,width=5)
        d.arc((151,104,169,123),270,90,fill=PINK,width=4)
        d.text((259,38),"z",font=font(22,True),fill=CYAN);d.text((278,20),"z",font=font(16,True),fill=PINK)
    elif state=="sad":
        d.ellipse((lx-20,52,lx+20,92),outline=CYAN,width=5);d.ellipse((rx-20,52,rx+20,92),outline=CYAN,width=5)
        d.arc((145,105,175,132),188,352,fill=PINK,width=4)
        d.line((253,98,248,110,253,118,258,110,253,98),fill=PURPLE,width=4,joint="curve")
    elif state=="error":
        d.line((73,57,105,89),fill=CYAN,width=5);d.line((105,57,73,89),fill=CYAN,width=5)
        d.line((215,57,247,89),fill=CYAN,width=5);d.line((247,57,215,89),fill=CYAN,width=5)
        d.line((146,115,174,115),fill=PINK,width=4)
    elif state=="angry":
        d.line((66,55,112,72,101,91,76,82,66,55),fill=CYAN,width=5,joint="curve")
        d.line((254,55,208,72,219,91,244,82,254,55),fill=CYAN,width=5,joint="curve")
        d.arc((145,106,175,133),188,352,fill=PINK,width=4)
    return im.resize((640,340),Image.Resampling.NEAREST)

items=[
 ("neutral","C2-N  NEUTRAL","Primary open-eye face"),("happy","C2-H  HAPPY","Closed-eye smile"),
 ("love","C2-L  LOVE","Heart-eye reaction"),("curious","C2-C  CURIOUS","Question or browsing"),
 ("alert","C2-AL  ALERT","Notification or surprise"),("laugh","C2-LF  LAUGH","Win or funny moment"),
 ("sleep","C2-Z  SLEEP","Idle and sleep mode"),("sad","C2-S  SAD","Loss or disconnect"),
 ("error","C2-X  ERROR","Crash or offline"),("angry","C2-A  ANGRY","Defeat or playful rage"),
]

sheet=Image.new("RGB",(1460,2435),"#070914");sd=ImageDraw.Draw(sheet)
sd.text((30,22),"LIL BOT • C2 SYMBOL-FACE WORKSHOP",font=font(34,True),fill=TEXT)
sd.text((31,68),"No eyebrows. Expressions come from eye symbols, tiny mouths, and native 320×170 pixel geometry.",font=font(17),fill="#9EACCB")
for n,(state,title,sub) in enumerate(items):
    card=Image.new("RGB",(700,450),"#10162B");cd=ImageDraw.Draw(card)
    cd.text((22,16),title,font=font(23,True),fill=TEXT);cd.text((22,49),sub,font=font(14),fill="#9EACCB")
    cd.rounded_rectangle((28,91,672,421),radius=58,fill="#1A1F2D",outline="#3A435B",width=9)
    art=face(state);mask=Image.new("L",art.size,0);ImageDraw.Draw(mask).rounded_rectangle((0,0,639,339),radius=48,fill=255)
    card.paste(art,(30,88),mask)
    sheet.paste(card,(30+(n%2)*720,108+(n//2)*465))
sheet.save("LilBot_C2_Symbol_Emotion_Workshop.png",quality=95)
