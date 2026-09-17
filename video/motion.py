"""Frame-by-frame motion design: bold type, live UI animation, and editorial imagery."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

W,H=1920,1080
ASSETS=Path(__file__).with_name("assets")
BLACK="#101013"
WHITE="#F6F5F9"
VIOLET="#8055FF"
LIME="#DCFF64"
GRAY="#AFAEBB"


@lru_cache(maxsize=100)
def font(size,display=False):
    face=ImageFont.truetype(str(ASSETS/("Anton-Regular.ttf" if display else "Manrope[wght].ttf")),int(size))
    if not display:
        face.set_variation_by_axes([550])
    return face


def ease(t):
    return 1-(1-max(0,min(1,t)))**3


@lru_cache(maxsize=8)
def background(mode="dark"):
    if mode=="photo":
        image=ImageOps.fit(Image.open(ASSETS/"salon-editorial.png").convert("RGB"),(W,H))
        pixels=np.array(image,dtype=np.float32)
        shade=np.linspace(.20,.82,W,dtype=np.float32)[None,:,None]
        return Image.fromarray((pixels*shade).astype("uint8"))
    yy,xx=np.mgrid[0:H,0:W]
    glow=np.exp(-((xx-1450)**2+(yy-400)**2)/500000)
    base=np.zeros((H,W,3),dtype=np.uint8)
    for channel,(low,high) in enumerate(zip((16,16,20),(61,37,102) if mode=="dark" else (127,68,248))):
        base[:,:,channel]=low+glow*(high-low)
    return Image.fromarray(base)


def text(draw,xy,value,size=48,color=WHITE,display=False):
    draw.text((round(xy[0]),round(xy[1])),value,font=font(size,display),fill=color,stroke_width=0)


def fit_size(draw,value,size,max_width,display=False):
    while draw.textlength(value,font=font(size,display))>max_width and size>18:
        size-=2
    return size


def lines(draw,xy,value,size=130,color=WHITE,gap=1.12,max_width=1720):
    for i,line in enumerate(value.split("\n")):
        f=fit_size(draw,line,size,max_width,True)
        text(draw,(xy[0],xy[1]+i*size*gap),line,f,color,True)


def pill(draw,box,label,color=VIOLET,ink=WHITE,size=25):
    draw.rounded_rectangle(tuple(round(v) for v in box),radius=24,fill=color)
    text(draw,(box[0]+24,box[1]+13),label,size,ink)


def check(draw,x,y,progress):
    draw.ellipse((x,y,x+44,y+44),fill=LIME)
    if progress>.4:
        draw.line((x+11,y+22,x+19,y+31,x+34,y+13),fill=BLACK,width=5)


def caption(image,cues,t):
    cue=next((c for c in cues if c["start"]<=t<c["end"]),None)
    if cue is None:
        return
    draw=ImageDraw.Draw(image)
    words=cue["text"].upper().split()
    size=49
    while sum(draw.textlength(w,font=font(size,True))+16 for w in words)>1700:
        size-=2
    widths=[draw.textlength(w,font=font(size,True)) for w in words]
    span=max(.001,cue["end"]-cue["start"])
    active=min(len(words)-1,int((t-cue["start"])/span*len(words)))
    total=sum(widths)+16*(len(words)-1)
    x=(W-total)/2
    y=940
    draw.rounded_rectangle((x-26,y-9,x+total+26,y+78),radius=18,fill="#101013")
    for i,(word,width) in enumerate(zip(words,widths)):
        text(draw,(x,y),word,size,LIME if i==active else WHITE,True)
        x+=width+16


def frame(scene,t,length,index,total,cues=(),height=1080):
    kind=scene["kind"]
    photo=kind in ("intro","redeem")
    image=background("photo" if photo else "violet" if kind in ("promise","outro","price") else "dark").copy()
    # Camera move on photographic shots, independent of foreground typography.
    if photo:
        zoom=1.035+.055*t/max(length,.1)
        image=image.resize((round(W*zoom),round(H*zoom)),Image.Resampling.BILINEAR)
        left=round((image.width-W)*.7)
        top=round((image.height-H)*.4)
        image=image.crop((left,top,left+W,top+H))
    d=ImageDraw.Draw(image)
    enter=ease(t/.38)
    shift=round((1-enter)*110)
    # Small permanent branding, not a presentation header/footer.
    d.rounded_rectangle((76,49,119,92),radius=12,fill=LIME)
    text(d,(87,49),"g",30,BLACK,True)
    text(d,(136,58),"GREATCLIPSDEAL",24,WHITE)
    text(d,(1585,61),"COUPON GUIDE",18,GRAY)
    d.rectangle((0,H-5,W*(index+t/max(length,.1))/total,H),fill=LIME)

    if kind=="intro":
        pill(d,(80,182,554,244),"BEFORE YOUR NEXT HAIRCUT",size=23)
        lines(d,(74+shift,290),"CHECK FOR\nA COUPON.",154,max_width=1080)
        d.rectangle((82,686,720,700),fill=LIME)
        text(d,(82,742),"Great Clips coupons, explained fast.",32)
        text(d,(1390,858),"AI-GENERATED SALON VISUAL",17,GRAY)
    elif kind=="promise":
        labels=["FIND IT.","CHECK IT.","USE IT."]
        for i,label in enumerate(labels):
            a=ease((t-i*.33)/.3)
            color=LIME if i==min(2,int(t/.75)) else WHITE
            text(d,(110+(1-a)*180,159+i*211),label,168,color,True)
        text(d,(1120,347),"YOUR LOCATION.",40,LIME,True)
        text(d,(1120,407),"YOUR OFFER.",40,WHITE,True)
        text(d,(1120,491),"No guessing.",29,GRAY)
    elif kind=="search":
        text(d,(85+shift,183),"START LOCAL.",135,WHITE,True)
        d.rounded_rectangle((90,417,1830,550),radius=30,fill=WHITE)
        d.ellipse((134,457,172,495),outline=BLACK,width=5)
        d.line((166,490,185,509),fill=BLACK,width=5)
        value="Your city or location"
        typed=value[:max(0,min(len(value),int((t-.4)*16)))]
        text(d,(224,446),typed+('|' if int(t*3)%2==0 else ''),44,BLACK)
        for i,(label,x) in enumerate([("CITY",90),("STATE",655),("YOUR SALON",1220)]):
            a=ease((t-.85-i*.2)/.3)
            y=608+(1-a)*80
            d.rounded_rectangle((x,y,x+520,y+120),radius=22,fill="#27242F",outline="#534D69",width=2)
            text(d,(x+35,y+28),label,43,LIME if i==min(2,int(t/1.15)) else WHITE,True)
        text(d,(97,792),"greatclipsdeal.com",37,LIME)
        text(d,(1400,817),"ILLUSTRATED SEARCH FLOW",18,GRAY)
    elif kind in ("compare","price"):
        pill(d,(87,169,602,231),"EXAMPLE / NOT A LIVE OFFER",size=23,color="#332A48")
        main="$5 OFF" if kind=="compare" else "$5 HAIRCUT"
        size=fit_size(d,main,257,1710,True)
        text(d,(80+shift,259),main,size,LIME if kind=="compare" else WHITE,True)
        label="DISCOUNT FROM THE REGULAR PRICE" if kind=="compare" else "FIXED PRICE WITH THAT OFFER"
        text(d,(93,641),label,49,WHITE,True)
        text(d,(94,750),"Read the actual coupon. The wording matters.",34,GRAY)
    elif kind=="check":
        lines(d,(86+shift,203),"TWO THINGS\nTO CHECK.",135,max_width=930)
        for i,(title,sub) in enumerate([("YOUR SALON","Is it a participating location?"),("THE DATE","Will the offer still be valid?")]):
            a=ease((t-.5-i*.7)/.4)
            yy=260+i*254+(1-a)*90
            d.rounded_rectangle((1105,yy-20,1835,yy+157),radius=28,fill="#26222F")
            check(d,1140,yy+6,a)
            text(d,(1220,yy-4),title,52,LIME,True)
            text(d,(1140,yy+85),sub,27,WHITE)
        text(d,(93,689),"Unclear? Call the salon before you go.",34,GRAY)
    elif kind=="email":
        lines(d,(86+shift,195),"GET THE\nCOUPON LINK.",118,max_width=1110)
        pill(d,(95,570,684,671),"Get Coupon   >",size=46,color=VIOLET)
        text(d,(98,735),"Enter your email. Open the official offer.",32,GRAY)
        a=ease((t-.35)/.5)
        x=1250+round((1-a)*220)
        y=273+round(math.sin(t*2)*9)
        d.rounded_rectangle((x,y,x+488,y+311),radius=30,fill=WHITE)
        d.line((x+15,y+24,x+244,y+172,x+473,y+24),fill=VIOLET,width=11)
        d.line((x+15,y+291,x+175,y+175),fill="#D2C8EE",width=5)
        d.line((x+473,y+291,x+313,y+175),fill="#D2C8EE",width=5)
        if t>1.3:
            pill(d,(x-75,y+348,x+535,y+418),"OFFICIAL OFFER IN YOUR INBOX",size=25,color=LIME,ink=BLACK)
        text(d,(1420,817),"ILLUSTRATED EMAIL FLOW",18,GRAY)
    elif kind=="redeem":
        lines(d,(80+shift,180),"SHOW IT\nBEFORE\nYOU PAY.",139,max_width=1100)
        text(d,(103,783),"Follow the instructions on the coupon.",31,LIME)
        text(d,(1390,858),"AI-GENERATED SALON VISUAL",17,GRAY)
    elif kind=="offer":
        offer=scene["offer"]
        label=offer["location"].upper()
        text(d,(90,188),label,fit_size(d,label,73,1730,True),LIME,True)
        main=offer["label"].upper()
        text(d,(80+shift,302),main,fit_size(d,main,220,1710,True),WHITE,True)
        pill(d,(94,631,839,719),f"EXPIRES {offer['expiration']}",size=37)
        place=offer.get("address") or "Participating locations only. Check the official terms."
        text(d,(98,779),place,fit_size(d,place,36,1700),GRAY)
    else:
        text(d,(88+shift,184),"CHECK BEFORE YOU GO.",115,WHITE,True)
        d.rounded_rectangle((86,437,1834,599),radius=36,fill=LIME)
        text(d,(133,437),"greatclipsdeal.com",116,BLACK,True)
        text(d,(110,692),"WEBSITE LINK IN THE DESCRIPTION",46,WHITE,True)
        d.line((1640,684,1640,793),fill=LIME,width=11)
        d.line((1606,752,1640,793,1674,752),fill=LIME,width=11)
        text(d,(112,803),"Independent coupon resource. Not affiliated with Great Clips.",23,GRAY)
    caption(image,cues,t)
    if height!=1080:
        image=image.resize((height*16//9,height),Image.Resampling.LANCZOS)
    return image


def render_thumbnail(plan,path):
    if plan.get("offers"):
        render_official_thumbnail(plan,path)
        return
    image=background("photo").copy()
    d=ImageDraw.Draw(image)
    pill(d,(79,90,673,171),"GREAT CLIPS COUPON GUIDE",size=30)
    if plan.get("location"):
        location=plan["location"].upper()
        text(d,(79,230),location,fit_size(d,location,150,1710,True),LIME,True)
        label=plan["offers"][0]["label"].upper()
        text(d,(79,445),label,fit_size(d,label,190,1700,True),WHITE,True)
        text(d,(83,714),"AT LISTED PARTICIPATING LOCATIONS",42,WHITE,True)
    else:
        lines(d,(67,231),"CHECK\nBEFORE\nYOU GO.",165,max_width=1040)
    d.rounded_rectangle((83,862,1023,978),radius=24,fill=LIME)
    text(d,(119,875),"greatclipsdeal.com",72,BLACK,True)
    if plan["offers"]:
        pill(d,(1190,893,1822,975),f"LOCAL DEALS / {plan['date']}",size=27)
    image.resize((1280,720),Image.Resampling.LANCZOS).save(path,quality=95)


def render_official_thumbnail(plan,path):
    """Keep the official offer artwork intact within a labeled 16:9 frame."""
    import io
    import json
    from urllib.parse import urlparse
    import requests
    from bs4 import BeautifulSoup
    offer=plan['offers'][0]
    response=requests.get(offer['url'],timeout=(4,12),allow_redirects=False)
    response.raise_for_status()
    node=BeautifulSoup(response.text,'html.parser').select_one('meta[property="og:image"]')
    if not node or not node.get('content'):
        raise RuntimeError('Official coupon artwork unavailable; review before publishing.')
    url=node['content']
    parsed=urlparse(url)
    host=parsed.hostname or ''
    if parsed.scheme!='https' or parsed.username or parsed.port not in (None,443) or not (
            host=='offers.greatclips.com' or host.endswith('.rackcdn.com')):
        raise RuntimeError('Unexpected official coupon artwork host.')
    response=requests.get(url,timeout=(4,15),allow_redirects=False)
    response.raise_for_status()
    original=Image.open(io.BytesIO(response.content)).convert('RGB')
    image=Image.new('RGB',(1280,720),BLACK)
    art=ImageOps.contain(original,(1280,640),Image.Resampling.LANCZOS)
    image.paste(art,((1280-art.width)//2,80+(640-art.height)//2))
    d=ImageDraw.Draw(image)
    location=plan.get('location') or offer['location']
    label=f"{location.upper()}  |  PARTICIPATING LOCATIONS"
    text(d,(30,16),label,fit_size(d,label,38,1220,True),WHITE,True)
    image.save(path,quality=95)
    Path(path).with_suffix('.source.json').write_text(json.dumps({
        'offer_url':offer['url'],'image_url':url,'checked_at':plan['date'],
        'layout':'Full official artwork, uncropped; location label outside artwork.'},indent=2),encoding='utf-8')
