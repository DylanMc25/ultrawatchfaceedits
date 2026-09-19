#!/usr/bin/env python3
"""Illustrative WFF layout proof from generated XML + explicit fixture data.
This is NOT a Wear OS renderer or emulator screenshot. Requires Pillow and Node.
Use --font /path/to/Roboto-Regular.ttf for Android-like text metrics.
"""
import argparse
import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
XML=ROOT/'app/src/main/res/raw/watchface.xml'
RES=ROOT/'app/src/main/res/drawable-nodpi'
SCALE=3


def render(font_path, ambient=False, size=450, hour=14, minute=26):
    root=ET.parse(XML).getroot()
    from generate_watchface import PALETTE
    colors=PALETTE
    palette={f'CONFIGURATION.theme_color.{i}':c for i,c in enumerate(colors)}
    global_data={'HOUR_0_23':hour,'MINUTE':minute,'SECOND':38,'IS_24_HOUR_MODE':False,
                 'MONTH_F':'September','DAY_OF_WEEK_S':'Sat','DAY':19,
                 'WEATHER.IS_AVAILABLE':True,'WEATHER.CONDITION':14,'WEATHER.IS_DAY':True,'WEATHER.TEMPERATURE':90}
    for i in (2,4,6,8):
        for key,val in dict(IS_AVAILABLE=True,IS_DAY=(hour+i)%24<19,CONDITION={2:14,4:2,6:8,8:1}[i],TEMPERATURE={2:90,4:88,6:86,8:82}[i]).items():
            global_data[f'WEATHER.HOURS.{i}.{key}']=val
    fixtures={
        '1':dict(TEXT='71',TITLE='',MONOCHROMATIC_IMAGE='fixture_heart'),
        '2':dict(TEXT='8,420',TITLE='',MONOCHROMATIC_IMAGE='fixture_steps'),
        '3':dict(TEXT='6:48',TITLE='SUNSET',MONOCHROMATIC_IMAGE='fixture_sunset'),
        '4':dict(TEXT='62%',TITLE='',MONOCHROMATIC_IMAGE='fixture_battery',RANGED_VALUE_MIN=0,RANGED_VALUE_MAX=100,RANGED_VALUE_VALUE=62),
        '5':{},'6':{}}
    expressions=set()
    for n in root.iter():
        if n.tag=='Expression':expressions.add(n.text)
        if n.tag=='Parameter':expressions.add(n.get('expression'))
        if n.tag=='Transform':expressions.add(n.get('value'))
    data=[global_data]+[global_data|{f'COMPLICATION.{k}':v for k,v in fixtures[str(i)].items()} for i in range(1,7)]
    # Evaluate this repository's WFF arithmetic using matching JavaScript operators.
    # No file/network access is provided to the expression function.
    js=r'''
let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{
const {expressions,data}=JSON.parse(s); const result=data.map(values=>Object.fromEntries(expressions.map(e=>{
const code=e.replace(/\[([^\]]+)\]/g,(_,k)=>JSON.stringify(values[k]??''));
try {return [e,Function('clamp','numberFormat','textLength','return ('+code+')')((n,a,b)=>Math.max(a,Math.min(n,b)),(_,n)=>Number(n).toLocaleString('en-US'),s=>String(s).length)];}catch{return [e,null];}
})));process.stdout.write(JSON.stringify(result));});'''
    results=json.loads(subprocess.run(['node','-e',js],input=json.dumps({'expressions':list(expressions),'data':data}),text=True,capture_output=True,check=True).stdout)
    def evaluate(expr,ctx):return results[ctx].get(expr)
    im=Image.new('RGBA',(450*SCALE,450*SCALE),'black');draw=ImageDraw.Draw(im)
    def color(value):
        value=palette.get(value.strip('[]'),value)
        if value.startswith('#') and len(value)==9:return '#'+value[3:]
        return value
    def font(sz,weight='NORMAL',condensed=False):
        f=ImageFont.truetype(str(font_path),round(float(sz)*SCALE))
        try:
            axes=f.get_variation_axes();v=[a['default'] for a in axes]
            for i,a in enumerate(axes):
                if a['name']==b'Weight':v[i]={'THIN':100,'LIGHT':300,'NORMAL':400,'MEDIUM':500,'BOLD':700}.get(weight,400)
                if a['name']==b'Width' and condensed:v[i]=a['minimum']
            f.set_variation_by_axes(v)
        except (OSError,AttributeError):pass
        return f
    def textvalue(f,ctx):
        t=f.find('Template')
        if t is None:return f.text or ''
        vals=tuple(evaluate(p.get('expression'),ctx) for p in t.findall('Parameter'))
        try:return (t.text or '')%vals
        except (ValueError,TypeError):return '—'
    def drawtext(x,y,w,h,value,f,align='CENTER'):
        bounds=draw.textbbox((0,0),value,font=f);tw=bounds[2]-bounds[0];th=bounds[3]-bounds[1]
        # WFF ellipsis trims to the fixed box; keep the layout proof bounded too.
        while tw>w*SCALE and len(value)>1:
            value=value[:-2]+'…';bounds=draw.textbbox((0,0),value,font=f);tw=bounds[2]-bounds[0]
        px=x*SCALE+(0 if align=='START' else (w*SCALE-tw)/2 if align=='CENTER' else w*SCALE-tw)
        py=y*SCALE+(h*SCALE-th)/2-bounds[1]
        return px,py,value
    def paint(node,ox=0,oy=0,ctx=0):
        nonlocal draw
        attrs=node.attrib
        alpha=attrs.get('alpha','255')
        if ambient:
            v=node.find("Variant[@mode='AMBIENT'][@target='alpha']")
            if v is not None:alpha=v.get('value')
        if float(alpha)==0:return
        tag=node.tag
        if tag in ['Metadata','BitmapFonts','UserConfigurations','Variant','ScreenReader','DefaultProviderPolicy'] or tag.startswith('Bounding'):return
        x=ox+float(attrs.get('x',0));y=oy+float(attrs.get('y',0));w=float(attrs.get('width',0));h=float(attrs.get('height',0))
        if tag=='Condition':
            for compare in node.findall('Compare'):
                expression=node.find(f"./Expressions/Expression[@name='{compare.get('expression')}']").text
                if evaluate(expression,ctx):
                    for child in compare:paint(child,ox,oy,ctx)
                    return
            default=node.find('Default')
            if default is not None:
                for child in default:paint(child,ox,oy,ctx)
            return
        if tag=='ComplicationSlot':
            sid=node.get('slotId');kind='EMPTY' if sid in ['5','6'] else 'RANGED_VALUE' if sid=='4' else 'SHORT_TEXT'
            for child in node.find(f"Complication[@type='{kind}']"):paint(child,x,y,int(sid))
            return
        if tag=='Rectangle' or tag=='Ellipse':
            fill=node.find('Fill')
            if fill.get('color','').startswith('#00'):return
            c=color(fill.get('color'));gradient=fill.find('LinearGradient')
            if gradient is not None:
                cs=[color(v) for v in gradient.get('colors').split()]
                rgb=[tuple(int(v[j:j+2],16) for j in (1,3,5)) for v in cs]
                for row in range(round(h*SCALE)):
                    t=row/max(h*SCALE-1,1);c=tuple(round(a*(1-t)+b*t) for a,b in zip(*rgb))
                    draw.line([(x*SCALE,y*SCALE+row),((x+w)*SCALE,y*SCALE+row)],fill=c)
            else:
                bounds=(x*SCALE,y*SCALE,(x+w)*SCALE,(y+h)*SCALE)
                (draw.ellipse if tag=='Ellipse' else draw.rectangle)(bounds,fill=c)
            return
        if tag=='Line':
            stroke=node.find('Stroke');c=color(stroke.get('color'));thick=float(stroke.get('thickness'))
            points=[((ox+float(attrs[k+'X']))*SCALE,(oy+float(attrs[k+'Y']))*SCALE) for k in ['start','end']]
            draw.line(points,fill=c,width=round(thick*SCALE))
            for px,py in points:
                rr=thick*SCALE/2;draw.ellipse((px-rr,py-rr,px+rr,py+rr),fill=c)
            return
        if tag=='Arc':
            cx=ox+float(attrs['centerX']);cy=oy+float(attrs['centerY']);start=float(attrs['startAngle']);end=float(attrs['endAngle'])
            t=node.find('Transform')
            if t is not None:end=evaluate(t.get('value'),ctx) or start
            stroke=node.find('Stroke')
            if stroke is None:return
            thick=float(stroke.get('thickness'));c=color(stroke.get('color'));r=w/2
            if end>start:
                outer=r+thick/2
                draw.arc(((cx-outer)*SCALE,(cy-outer)*SCALE,(cx+outer)*SCALE,(cy+outer)*SCALE),
                         start-90,end-90,fill=c,width=round(thick*SCALE))
            if end>start:
                for angle in (start,end):
                    a=math.radians(angle);xx=cx+r*math.sin(a);yy=cy-r*math.cos(a);rr=thick/2
                    draw.ellipse(((xx-rr)*SCALE,(yy-rr)*SCALE,(xx+rr)*SCALE,(yy+rr)*SCALE),fill=c)
            return
        if tag=='TimeText':
            fmt=node.get('format');v=f'{hour%12 or 12:02}' if fmt=='hh' else f'{minute:02}' if fmt=='mm' else '38'
            f=node.find('Font');ft=font(f.get('size'),f.get('weight','NORMAL'),True)
            xx,yy,v=drawtext(x,y,w,h,v,ft);draw.text((xx,yy),v,font=ft,fill=color(f.get('color')));return
        if tag=='PartText':
            t=node.find('Text')
            if t is None:
                t=node.find('TextCircular');f=t.find('Font');value=textvalue(f,ctx);ft=font(f.get('size'),f.get('weight','NORMAL'))
                # Position a rotated label centered on the same circular baseline.
                angle=(float(t.get('startAngle'))+float(t.get('endAngle')))/2;r=float(t.get('width'))/2-5
                b=ft.getbbox(value);tile=Image.new('RGBA',(b[2]-b[0]+12*SCALE,b[3]-b[1]+12*SCALE));td=ImageDraw.Draw(tile)
                td.text((6*SCALE-b[0],6*SCALE-b[1]),value,font=ft,fill=color(f.get('color')))
                tile=tile.rotate(-angle,resample=Image.Resampling.BICUBIC,expand=True)
                a=math.radians(angle);cx=(x+float(t.get('centerX'))+r*math.sin(a))*SCALE;cy=(y+float(t.get('centerY'))-r*math.cos(a))*SCALE
                im.alpha_composite(tile,(round(cx-tile.width/2),round(cy-tile.height/2)));return
            f=t.find('Font')
            if f is None:
                f=t.find('BitmapFont');code=textvalue(f,ctx);family=f.get('family')
                glyph=Image.open(RES/f'{family}_{code}.png').convert('RGBA').resize((round(w*SCALE),round(h*SCALE)),Image.Resampling.LANCZOS)
                tint=Image.new('RGBA',glyph.size,color(f.get('color')));tint.putalpha(glyph.getchannel('A'));im.alpha_composite(tint,(round(x*SCALE),round(y*SCALE)));return
            ft=font(f.get('size'),f.get('weight','NORMAL'));value=textvalue(f,ctx)
            if float(node.get('angle','0')):
                tile=Image.new('RGBA',(round(w*SCALE),round(h*SCALE)))
                xx,yy,value=drawtext(0,0,w,h,value,ft,t.get('align','CENTER'))
                ImageDraw.Draw(tile).text((xx,yy),value,font=ft,fill=color(f.get('color')))
                tile=tile.rotate(-float(node.get('angle')),resample=Image.Resampling.BICUBIC,expand=True)
                im.alpha_composite(tile,(round((x+w/2)*SCALE-tile.width/2),round((y+h/2)*SCALE-tile.height/2)))
            else:
                xx,yy,value=drawtext(x,y,w,h,value,ft,t.get('align','CENTER'));draw.text((xx,yy),value,font=ft,fill=color(f.get('color')))
            return
        if tag=='PartImage':
            resource=node.find('Image').get('resource');value=fixtures.get(str(ctx),{}).get(resource.strip('[]').split('.')[-1],'')
            c=color(node.get('tintColor',colors[2]));cx=(x+w/2)*SCALE;cy=(y+h/2)*SCALE
            if value=='fixture_heart':
                points=[]
                for i in range(100):
                    a=i*math.tau/100;points.append((cx+(16*math.sin(a)**3)*w*SCALE/36,cy-(13*math.cos(a)-5*math.cos(2*a)-2*math.cos(3*a)-math.cos(4*a))*h*SCALE/36))
                draw.polygon(points,fill=c)
            elif value=='fixture_battery':
                draw.rounded_rectangle((cx-7*SCALE,cy-9*SCALE,cx+7*SCALE,cy+10*SCALE),radius=2*SCALE,fill=c)
                draw.rectangle((cx-3*SCALE,cy-12*SCALE,cx+3*SCALE,cy-8*SCALE),fill=c)
            elif value=='fixture_steps':
                draw.ellipse((cx-7*SCALE,cy-9*SCALE,cx-1*SCALE,cy+3*SCALE),fill=c);draw.ellipse((cx+2*SCALE,cy-2*SCALE,cx+8*SCALE,cy+10*SCALE),fill=c)
            elif value=='fixture_sunset':
                draw.arc((cx-8*SCALE,cy-5*SCALE,cx+8*SCALE,cy+11*SCALE),180,360,fill=c,width=2*SCALE);draw.line([(cx-12*SCALE,cy+3*SCALE),(cx+12*SCALE,cy+3*SCALE)],fill=c,width=2*SCALE)
            return
        for child in node:paint(child,x,y,ctx)
    paint(root.find('Scene'))
    mask=Image.new('L',im.size);ImageDraw.Draw(mask).ellipse((0,0,im.width-1,im.height-1),fill=255);im.putalpha(mask)
    return im.resize((size,size),Image.Resampling.LANCZOS)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--font',type=Path,required=True);args=parser.parse_args()
    out=ROOT/'docs/previews';out.mkdir(exist_ok=True)
    for mode in ['active','ambient']:
        im=render(args.font,mode=='ambient');im.save(out/f'{mode}-illustrative.png')
        if mode=='active':im.save(RES/'preview.png')
    print('Wrote illustrative previews. These are not emulator evidence.')
