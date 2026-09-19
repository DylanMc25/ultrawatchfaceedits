#!/usr/bin/env python3
"""Original monochrome weather icons, drawn at 4x and reduced for clean edges.
Requires Pillow; output is committed so ordinary Android builds need no Python packages.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import math

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'app/src/main/res/drawable-nodpi'
S=4

def icon(code, night):
    im=Image.new('RGBA',(96*S,96*S)); d=ImageDraw.Draw(im)
    def line(points,width=4):d.line([(int(x*S),int(y*S)) for x,y in points],fill='white',width=width*S,joint='curve')
    def ellipse(b,width=4,fill=None):d.ellipse(tuple(int(v*S) for v in b),outline='white',width=width*S,fill=fill)
    def arc(b,a,z,width=4):d.arc(tuple(int(v*S) for v in b),a,z,fill='white',width=width*S)
    def sun(cx=48,cy=45,r=16):
        ellipse((cx-r,cy-r,cx+r,cy+r))
        for a in range(0,360,45):
            t=math.radians(a);line([(cx+(r+6)*math.cos(t),cy+(r+6)*math.sin(t)),(cx+(r+13)*math.cos(t),cy+(r+13)*math.sin(t))],3)
    def moon():
        # Crescent as a closed contour, without erasing unrelated artwork.
        pts=[]
        for a in range(50,311,5):
            t=math.radians(a);pts.append((49+25*math.cos(t),46+25*math.sin(t)))
        for a in range(285,74,-5):
            t=math.radians(a);pts.append((62+24*math.cos(t),37+24*math.sin(t)))
        line(pts+[pts[0]])
    def cloud():
        # Smooth outline assembled from cubic Bezier segments sampled densely.
        curves=[((23,66),(7,66),(8,44),(23,43)),((23,43),(21,17),(61,16),(65,40)),((65,40),(86,35),(93,66),(73,66))]
        pts=[]
        for p0,p1,p2,p3 in curves:
            for j in range(31):
                t=j/30;u=1-t;pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
        pts.append((23,66));line(pts)
    if code==0:
        ellipse((20,18,76,74),3);line([(38,35),(43,30),(54,30),(59,35),(59,42),(48,51),(48,55)],4);ellipse((46,63,50,67),1,'white')
    elif code in [1,8]:
        moon() if night else sun()
    elif code==14:
        if night: arc((15,9,53,47),60,290,3)
        else: sun(30,28,12)
        # Cloud drawn on its own mask so overlapping sun lines are cleanly covered.
        mask=Image.new('RGBA',im.size);old=d;d=ImageDraw.Draw(mask);cloud();d=old
        # Clear the interior beneath the cloud with an opaque mask in temporary image.
        fill=Image.new('L',im.size);fd=ImageDraw.Draw(fill);fd.ellipse((24*S,26*S,65*S,64*S),fill=255);fd.rectangle((20*S,43*S,78*S,66*S),fill=255)
        im.paste((0,0,0,0),(0,0),fill);im.alpha_composite(mask)
    elif code==15:
        line([(12,32),(61,32)]);arc((53,17,73,33),180,360);line([(20,47),(77,47)]);arc((69,47,87,65),270,450);line([(12,63),(50,63)])
    else:
        cloud()
        if code in [3,13]:
            line([(18,76),(78,76)],3);line([(28,85),(69,85)],3)
        elif code in [4,6,12,10]:
            for x in [30,48,66]:line([(x,74),(x-5,85)],4)
            if code==4:line([(78,73),(73,84)],4)
            if code==10:line([(44,87),(51,87)],3)
        elif code in [5,7,11]:
            for x in [28,49,70]:
                line([(x-5,78),(x+5,86)],2);line([(x-5,86),(x+5,78)],2);line([(x,75),(x,89)],2)
        elif code==9:
            line([(53,70),(42,81),(54,81),(45,93)],4)
    return im.resize((96,96),Image.Resampling.LANCZOS)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for mode in ['day','night']:
        for code in range(16):icon(code,mode=='night').save(OUT/f'weather_{mode}_{code}.png',optimize=True)
    print('Generated 32 weather glyphs.')
