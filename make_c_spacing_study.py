from PIL import Image, ImageDraw, ImageFont, ImageFilter

CYAN="#19F7FF"; PINK="#FF2DAA"; INK="#02040D"; NAVY="#070A1A"; TEXT="#E9FDFF"

def font(size,bold=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:return ImageFont.truetype(p,size)
    except:return ImageFont.load_default()

def face(inner_gap):
    im=Image.new("RGBA",(640,340),NAVY);d=ImageDraw.Draw(im)
    eye_w=132;eye_h=204;cy=154
    left_right=320-inner_gap/2;right_left=320+inner_gap/2
    boxes=[(left_right-eye_w,cy-eye_h/2,left_right,cy+eye_h/2),(right_left,cy-eye_h/2,right_left+eye_w,cy+eye_h/2)]
    for i,b in enumerate(boxes):
        g=Image.new("RGBA",im.size,(0,0,0,0));gd=ImageDraw.Draw(g);gd.rounded_rectangle(b,radius=54,fill=CYAN);im.alpha_composite(g.filter(ImageFilter.GaussianBlur(22)))
        d.rounded_rectangle(b,radius=54,fill=CYAN)
        x1,y1,x2,y2=b;cx=(x1+x2)/2;py=(y1+y2)/2;inward=12 if i==0 else -12
        # Large pupil is entirely unlit screen area.
        pw=56;ph=122
        d.rounded_rectangle((cx+inward-pw/2,py-ph/2,cx+inward+pw/2,py+ph/2),radius=25,fill=INK)
    # Fixed mouth center: x=320. There is deliberately no nose element.
    d.arc((294,258,346,292),5,175,fill=PINK,width=8)
    return im

items=[
 (168,"C1  Gentle spread","24 px wider than the original C"),
 (188,"C2  Medium spread","Balanced separation and eye size"),
 (208,"C3  Wide spread","Strong use of the full screen width"),
 (228,"C4  Maximum spread","Most open center; eyes approach the edges"),
]

sheet=Image.new("RGB",(1460,1045),"#070914");sd=ImageDraw.Draw(sheet)
sd.text((30,22),"LIL BOT • TALL-EYE SPACING STUDY",font=font(34,True),fill=TEXT)
sd.text((31,67),"Based on design C. The mouth stays centered at x=160 on the physical display; no nose is used.",font=font(17),fill="#9EACCB")
for n,(gap,title,sub) in enumerate(items):
    card=Image.new("RGBA",(700,450),"#10162B");d=ImageDraw.Draw(card)
    d.text((22,16),title,font=font(24,True),fill=TEXT);d.text((22,49),sub,font=font(14),fill="#9EACCB")
    d.rounded_rectangle((28,91,672,421),radius=58,fill="#1A1F2D",outline="#3A435B",width=9)
    art=face(gap).resize((600,319),Image.Resampling.LANCZOS);mask=Image.new("L",art.size,0);ImageDraw.Draw(mask).rounded_rectangle((0,0,599,318),radius=48,fill=255)
    card.paste(art,(50,98),mask)
    x=30+(n%2)*720;y=108+(n//2)*465;sheet.paste(card,(x,y),card)
sheet.save("LilBot_TestLab/LilBot_TallEye_Spacing_Study.png",quality=95)
