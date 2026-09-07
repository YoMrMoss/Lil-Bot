from PIL import Image, ImageDraw, ImageFont, ImageFilter

CYAN="#19F7FF"; PINK="#FF2DAA"; PURPLE="#8B3DFF"; INK="#02040D"; NAVY="#070A1A"; TEXT="#E9FDFF"

def font(size,bold=False):
    path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:return ImageFont.truetype(path,size)
    except:return ImageFont.load_default()

def glow_shape(im, box, radius, color, blur=22):
    g=Image.new("RGBA",im.size,(0,0,0,0));d=ImageDraw.Draw(g)
    d.rounded_rectangle(box,radius=radius,fill=color)
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))

def face(variant):
    im=Image.new("RGBA",(640,340),NAVY);d=ImageDraw.Draw(im)
    specs={
      "balanced":([(92,76,254,245),(386,76,548,245)],58,.45,"round"),
      "giant":([(95,80,251,241),(389,80,545,241)],61,.61,"round"),
      "tall":([(110,52,248,258),(392,52,530,258)],56,.48,"tall"),
      "organic":([(83,75,260,249),(380,75,557,249)],70,.52,"crescent"),
      "relaxed":([(73,107,270,224),(370,107,567,224)],48,.50,"wide"),
      "asymmetric":([(86,70,260,250),(392,88,548,238)],62,.54,"offset"),
    }
    boxes,rad,ratio,pupil=specs[variant]
    for i,b in enumerate(boxes):
        glow_shape(im,b,rad,CYAN);d.rounded_rectangle(b,radius=rad,fill=CYAN)
        x1,y1,x2,y2=b;cx=(x1+x2)//2;cy=(y1+y2)//2;w=x2-x1;h=y2-y1
        # Every pupil is a near-black unlit area, with no reflective highlight.
        inward=15 if i==0 else -15
        if pupil=="round":
            pr=min(w,h)*ratio/2;d.ellipse((cx+inward-pr,cy-pr,cx+inward+pr,cy+pr),fill=INK)
        elif pupil=="tall":
            pw=w*.40;ph=h*.60;d.rounded_rectangle((cx+inward-pw/2,cy-ph/2,cx+inward+pw/2,cy+ph/2),radius=24,fill=INK)
        elif pupil=="crescent":
            pr=min(w,h)*ratio/1.65;px=cx+inward;d.ellipse((px-pr,cy-pr,px+pr,cy+pr),fill=INK)
            bite=-46 if i==0 else 46;d.ellipse((px+bite-pr*.55,cy-pr*.55,px+bite+pr*.55,cy+pr*.55),fill=CYAN)
        elif pupil=="wide":
            pw=w*.52;ph=h*.55;d.rounded_rectangle((cx+inward-pw/2,cy-ph/2,cx+inward+pw/2,cy+ph/2),radius=ph/2,fill=INK)
        else:
            pw=w*.52;ph=h*.57;shift=(23 if i==0 else -7);d.rounded_rectangle((cx+shift-pw/2,cy-ph/2,cx+shift+pw/2,cy+ph/2),radius=ph*.42,fill=INK)
    mouths={"balanced":(291,245,349,287,PINK),"giant":(294,249,346,283,CYAN),"tall":(294,259,346,293,PINK),"organic":(290,247,350,292,PURPLE),"relaxed":(302,252,338,266,PINK),"asymmetric":(287,249,353,291,CYAN)}
    x1,y1,x2,y2,col=mouths[variant]
    if variant=="relaxed":d.line((x1,(y1+y2)//2,x2,(y1+y2)//2),fill=col,width=8)
    elif variant=="organic":d.arc((x1,y1,x2,y2),180,355,fill=col,width=8)
    else:d.arc((x1,y1,x2,y2),5,175,fill=col,width=8)
    return im

items=[
 ("balanced","A  Balanced squircles","Strong all-purpose baseline"),
 ("giant","B  Extra-large pupils","Cutest and most direct eye contact"),
 ("tall","C  Tall cartoon eyes","More emotional vertical movement"),
 ("organic","D  Organic crescent pupils","Playful and slightly unusual"),
 ("relaxed","E  Relaxed wide eyes","Calm, deadpan desktop companion"),
 ("asymmetric","F  Asymmetrical curiosity","A little imperfect and more alive"),
]

sheet=Image.new("RGB",(1460,1515),"#070914");sd=ImageDraw.Draw(sheet)
sd.text((30,22),"LIL BOT • NORMAL FACE WORKSHOP",font=font(34,True),fill=TEXT)
sd.text((31,67),"Six wide-set foundations. Cyan glows; near-black pupils are portions of the eye switched off.",font=font(17),fill="#9EACCB")
for n,(key,title,sub) in enumerate(items):
    card=Image.new("RGBA",(700,450),"#10162B");d=ImageDraw.Draw(card)
    d.text((22,16),title,font=font(24,True),fill=TEXT);d.text((22,49),sub,font=font(14),fill="#9EACCB")
    d.rounded_rectangle((28,91,672,421),radius=58,fill="#1A1F2D",outline="#3A435B",width=9)
    art=face(key).resize((600,319),Image.Resampling.LANCZOS);mask=Image.new("L",art.size,0);ImageDraw.Draw(mask).rounded_rectangle((0,0,599,318),radius=48,fill=255)
    card.paste(art,(50,98),mask)
    x=30+(n%2)*720;y=108+(n//2)*465;sheet.paste(card,(x,y),card)
sheet.save("LilBot_TestLab/LilBot_Normal_Face_Workshop.png",quality=95)
