#!/usr/bin/env python3
"""Generate the resource-only WFF definition. Run from any directory; no dependencies."""
from pathlib import Path
import xml.etree.ElementTree as ET
import math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'app/src/main/res/raw/watchface.xml'
# Five WFF 2 palette entries: gradient top/bottom, primary, secondary, surface.
PALETTE = ['#FF234A77', '#FF4A96ED', '#FFDAF1FF', '#FFB4DAF6', '#FF509EFA']
# A single fixed palette needs no editor setting. Keep these values centralized
# for future multi-option themes. This avoids the color-setting parse failure
# observed with this single-option configuration on the API 34/35 emulators.
C = list(PALETTE)
C += [C[0], C[3]]  # Tracks and highlights reuse the five WFF 2 palette entries.


def el(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(int(v) if isinstance(v, float) and v.is_integer() else v) for k, v in attrs.items()})


def box(parent, tag, x, y, w, h, **attrs):
    return el(parent, tag, x=x, y=y, width=w, height=h, **attrs)


def group(parent, name, x=0, y=0, w=450, h=450, **attrs):
    return box(parent, 'Group', x, y, w, h, name=name, **attrs)


def ambient_hide(parent):
    el(parent, 'Variant', mode='AMBIENT', target='alpha', value=0)


def text(parent, x, y, w, h, size, value, *params, color=None, weight='NORMAL', align='CENTER', **attrs):
    p = box(parent, 'PartText', x, y, w, h, **attrs)
    t = el(p, 'Text', align=align, ellipsis='TRUE', maxLines=1)
    f = el(t, 'Font', family='sans-serif', size=size, color=color or C[2], weight=weight)
    if params:
        template = el(f, 'Template'); template.text = value
        for param in params: el(template, 'Parameter', expression=param)
    else: f.text = value
    return p


def image(parent, x, y, w, h, resource, tint=None):
    p = box(parent, 'PartImage', x, y, w, h, **({'tintColor': tint} if tint else {}))
    el(p, 'Image', resource=resource)
    return p


def ellipse(parent, x, y, w, h, color):
    p = box(parent, 'PartDraw', x, y, w, h)
    e = box(p, 'Ellipse', 0, 0, w, h); el(e, 'Fill', color=color)
    return p


def condition(parent, name, expression):
    c = el(parent, 'Condition'); ex = el(c, 'Expressions')
    el(ex, 'Expression', name=name).text = expression
    return c, el(c, 'Compare', expression=name)


def arc(parent, cx, cy, diameter, start, end, color, thickness, expression=None, weighted=False, viewport=(450, 450)):
    p = box(parent, 'PartDraw', 0, 0, *viewport)
    a = el(p, 'Arc', centerX=cx, centerY=cy, width=diameter, height=diameter, startAngle=start, endAngle=end)
    if weighted:
        el(a, 'WeightedStroke', colors='[COMPLICATION.WEIGHTED_ELEMENTS_COLORS]',
           weights='[COMPLICATION.WEIGHTED_ELEMENTS_WEIGHTS]', thickness=thickness, cap='ROUND', discreteGap=3)
    else: el(a, 'Stroke', color=color, thickness=thickness, cap='ROUND')
    if expression: el(a, 'Transform', target='endAngle', value=expression)
    return p


def clock(parent, ambient=False):
    g = group(parent, 'ambient_time' if ambient else 'interactive_time', alpha=0 if ambient else 255)
    el(g, 'Variant', mode='AMBIENT', target='alpha', value=255 if ambient else 0)
    color = '#FF8FA9BC' if ambient else C[2]
    # Move minutes left to reserve a separate, larger seconds column.
    d = box(g, 'DigitalClock', 18, 67, 194, 269)
    for fmt, x, y, width in [('hh', 23, 0, 168), ('mm', 0, 130, 153)]:
        t = box(d, 'TimeText', x, y, width, 139, format=fmt, hourFormat='SYNC_TO_DEVICE', align='CENTER')
        el(t, 'Font', family='sans-serif-condensed', size=126 if ambient else 142,
           color=color, weight='THIN' if ambient else 'MEDIUM')
    text(g, 82, 17, 286, 40, 32, '%s', '[MONTH_F]', color=color, weight='LIGHT' if ambient else 'BOLD')
    text(g, 230, 55, 142, 34, 28, '%s %s', '[DAY_OF_WEEK_S]', '[DAY]', color=color)
    if not ambient:
        seconds = box(g, 'DigitalClock', 173, 292, 36, 44)
        t = box(seconds, 'TimeText', 0, 0, 36, 44, format='ss', align='CENTER')
        el(t, 'Font', family='sans-serif-condensed', size=36, color=C[3], weight='MEDIUM')


PANEL_OPTIONS = ('weather', 'detailed_weather', 'temperature', 'rain', 'steps', 'heart_rate', 'none')
PANEL_BOUNDS = (94, 339, 262, 60)


def forecast_time(index):
    # Format an actual instant so midnight, DST, locale and half-hour zones work.
    stamp = f'([UTC_TIMESTAMP] + {index * 3600000})'
    return f'[IS_24_HOUR_MODE] ? icuText("HH", {stamp}) : icuText("h a", {stamp})'


def line(parent, x1, y1, x2, y2, color=None, thickness=1.5):
    n = el(parent, 'Line', startX=x1, startY=y1, endX=x2, endY=y2)
    el(n, 'Stroke', color=color or C[3], thickness=thickness, cap='ROUND')
    return n


def weather_icon(parent, x, y, size, source, name):
    """Original vector symbols covering all WFF condition values and unknowns."""
    g = group(parent, name, x, y, size, size)
    c = el(g, 'Condition'); expressions = el(c, 'Expressions')
    for codes, symbol in [((1, 8), 'clear'), ((2,), 'cloud'), ((3, 13), 'fog'),
                          ((4, 6, 12), 'rain'), ((5, 7, 11), 'snow'),
                          ((9,), 'storm'), ((10,), 'sleet'), ((14,), 'partly'), ((15,), 'wind')]:
        key = name + '_' + symbol
        el(expressions, 'Expression', name=key).text = ' || '.join(f'[{source}.CONDITION] == {i}' for i in codes)
        branch = el(c, 'Compare', expression=key)
        draw = box(branch, 'PartDraw', 0, 0, size, size)
        def ln(a, b, cc, d): return line(draw, a*size, b*size, cc*size, d*size, thickness=max(1, size*.065))
        def oval(a, b, w, h):
            el(box(draw, 'Ellipse', a*size, b*size, w*size, h*size), 'Fill', color=C[3])
        if symbol in ('clear', 'partly'):
            day, sun = condition(branch, key+'_day', f'[{source}.IS_DAY]')
            sun_draw = box(sun, 'PartDraw', 0, 0, size, size)
            el(box(sun_draw, 'Ellipse', size*.3, size*.3, size*.4, size*.4), 'Fill', color=C[3])
            for angle in range(0, 360, 45):
                a = math.radians(angle)
                line(sun_draw, size*(.5+.32*math.cos(a)), size*(.5+.32*math.sin(a)),
                     size*(.5+.44*math.cos(a)), size*(.5+.44*math.sin(a)), thickness=max(1,size*.06))
            moon = box(el(day,'Default'), 'PartDraw', 0, 0, size, size)
            a = el(moon, 'Arc', centerX=size*.5, centerY=size*.42, width=size*.63,
                   height=size*.63, startAngle=90, endAngle=280)
            el(a, 'Stroke', color=C[3], thickness=size*.18, cap='ROUND')
        if symbol in ('cloud','rain','snow','storm','sleet','partly'):
            # Put cloud above the partly-cloudy sun/moon layers.
            if symbol == 'partly': draw = box(branch,'PartDraw',0,0,size,size)
            oval(.1,.42,.8,.3); oval(.23,.27,.45,.45); oval(.53,.36,.32,.34)
        if symbol in ('rain','sleet'):
            for xx in (.25,.5,.75): ln(xx,.79,xx-.07,.94)
        if symbol in ('snow','sleet'):
            for xx in (.3,.7):
                ln(xx-.07,.87,xx+.07,.87); ln(xx,.8,xx,.94)
        if symbol == 'storm': ln(.55,.68,.4,.82); ln(.4,.82,.6,.82); ln(.6,.82,.44,.97)
        if symbol in ('fog','wind'):
            for yy, xx in ((.3,.15),(.5,.25),(.7,.1)): ln(xx,yy,.85,yy)
    for branch in c.findall('Compare'):
        for part in branch.findall('PartDraw'):
            if len(part) == 0: branch.remove(part)
    text(el(c,'Default'),0,0,size,size,size*.8,'—',color=C[3])


def weather_header(parent, name, title='Now'):
    weather_icon(parent,0,0,20,'WEATHER',name+'_icon')
    text(parent,25,0,205,21,19,title+' %s°%s','[WEATHER.TEMPERATURE]',
         '[WEATHER.TEMPERATURE_UNIT] == 1 ? "C" : "F"',align='START',weight='MEDIUM')


def progress_bar(parent, name, ratio):
    draw = box(parent,'PartDraw',4,50,254,6)
    line(draw,2,3,252,3,C[0],4)
    _, visible = condition(parent,name+'_positive',f'{ratio} > 0')
    draw = box(visible,'PartDraw',4,50,254,6)
    n = line(draw,2,3,252,3,C[3],4)
    el(n,'Transform',target='endX',value=f'2 + 250 * {ratio}')


def bottom_panel(parent):
    container = group(parent,'bottom_panel',*PANEL_BOUNDS); ambient_hide(container)
    choices = el(container,'ListConfiguration',id='bottom_panel')
    for option in PANEL_OPTIONS:
        g = group(el(choices,'ListOption',id=option),'panel_'+option,0,0,262,60)
        if option == 'none': continue
        target = 'HEALTH_HEART_RATE' if option=='heart_rate' else 'com.samsung.android.wear.shealth' if option=='steps' else 'com.samsung.android.watch.weather'
        el(g,'Launch',target=target)
        if option in ('steps','heart_rate'):
            if option=='steps':
                # WFF exposes no separate step-permission/availability flag.
                # Empty/sentinel data stays unavailable; a supplied zero is a valid count.
                c, data = condition(g,'panel_steps_available','[STEP_COUNT] != "" && [STEP_COUNT] >= 0')
                text(data,0,0,262,27,24,'%s steps','numberFormat("#,###", [STEP_COUNT])',weight='MEDIUM')
                goal, valid = condition(data,'panel_steps_goal','[STEP_GOAL] > 0')
                text(valid,0,28,262,19,16,'Goal %s','numberFormat("#,###", [STEP_GOAL])',color=C[3])
                progress_bar(valid,'panel_steps','clamp([STEP_COUNT] / [STEP_GOAL], 0, 1)')
                text(el(goal,'Default'),0,29,262,20,16,'Goal unavailable',color=C[3])
            else:
                c, data = condition(g,'panel_heart_available','[HEART_RATE] != "" && [HEART_RATE] > 0 && [HEART_RATE] <= 240')
                text(data,0,2,262,32,29,'%s bpm','numberFormat("#", [HEART_RATE])',weight='MEDIUM')
                text(data,0,36,262,21,17,'Heart rate',color=C[3])
            text(el(c,'Default'),0,15,262,30,21,'Steps —' if option=='steps' else 'Heart rate —',color=C[3])
            continue
        c, data = condition(g,'panel_'+option+'_available','[WEATHER.IS_AVAILABLE]')
        text(el(c,'Default'),0,5,262,28,23,'Weather —',color=C[3])
        text(c.find('Default'),0,35,262,20,16,'Tap to open Weather',color=C[3])
        _, error = condition(data,'panel_'+option+'_error','[WEATHER.IS_ERROR]')
        text(error,238,0,24,21,18,'!',weight='BOLD')
        if option in ('weather','temperature'):
            weather_header(data,'panel_'+option)
            for i in range(4):
                x = i*66
                hour, available = condition(data,f'{option}_hour_{i}',f'[WEATHER.HOURS.{i}.IS_AVAILABLE]')
                if option=='weather':
                    weather_icon(available,x,22,20,f'WEATHER.HOURS.{i}',f'forecast_{i}_icon')
                    text(available,x+20,22,44,21,18,'%s°',f'[WEATHER.HOURS.{i}.TEMPERATURE]')
                else:
                    text(available,x,20,64,21,18,'%s°',f'[WEATHER.HOURS.{i}.TEMPERATURE]')
                text(el(hour,'Default'),x,22,64,21,18,'—',color=C[3])
                text(data,x,44,64,16,14,'%s',forecast_time(i),color=C[3])
            if option=='temperature':
                # Scale against available points only; never bridge a missing hour.
                temps=[f'[WEATHER.HOURS.{i}.TEMPERATURE]' for i in range(4)]
                valid=[f'[WEATHER.HOURS.{i}.IS_AVAILABLE]' for i in range(4)]
                def extrema(fn, fallback):
                    values=[f'({v} ? {t} : {fallback})' for v,t in zip(valid,temps)]
                    return f'{fn}({fn}({values[0]}, {values[1]}), {fn}({values[2]}, {values[3]}))'
                lo,hi=extrema('min',10000),extrema('max',-10000)
                def ypos(i): return f'({hi} > {lo} ? 42 - 5 * ({temps[i]} - {lo}) / ({hi} - {lo}) : 39.5)'
                for i in range(3):
                    _, segment = condition(data,f'temperature_segment_{i}',f'{valid[i]} && {valid[i+1]}')
                    draw=box(segment,'PartDraw',0,0,262,60)
                    n=line(draw,32+66*i,40,32+66*(i+1),40,thickness=1.5)
                    el(n,'Transform',target='startY',value=ypos(i));el(n,'Transform',target='endY',value=ypos(i+1))
        elif option=='detailed_weather':
            weather_header(data,'panel_detail')
            text(data,0,22,262,18,16,'%s','[WEATHER.CONDITION_NAME]',align='START',color=C[3])
            text(data,0,42,262,18,16,'H %s°  L %s°  Rain %s%%','[WEATHER.DAY_TEMPERATURE_HIGH]',
                 '[WEATHER.DAY_TEMPERATURE_LOW]','[WEATHER.CHANCE_OF_PRECIPITATION]',align='START',color=C[3])
        elif option=='rain':
            text(data,0,0,232,27,24,'%s%%','[WEATHER.CHANCE_OF_PRECIPITATION]',weight='MEDIUM')
            text(data,0,28,262,20,17,'Chance of rain now',color=C[3])
            progress_bar(data,'panel_rain','clamp([WEATHER.CHANCE_OF_PRECIPITATION] / 100, 0, 1)')



RANGE = '([COMPLICATION.RANGED_VALUE_MAX] > [COMPLICATION.RANGED_VALUE_MIN] ? clamp(([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / ([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN]), 0, 1) : 0)'
GOAL = '([COMPLICATION.GOAL_PROGRESS_TARGET_VALUE] > 0 ? clamp([COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE], 0, 1) : 0)'


def complication_label(parent, w, h, kind, label_id):
    # Providers may send an icon, a title, both, or neither. Reserve both bands;
    # absent optional fields render empty, leaving the primary reading centered.
    image(parent, (w-28)/2, 6, 28, 28, '[COMPLICATION.MONOCHROMATIC_IMAGE]', C[2])
    expr = '[COMPLICATION.TEXT]'
    if kind == 'RANGED_VALUE': expr = '[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.RANGED_VALUE_VALUE]) : [COMPLICATION.TEXT]'
    if kind == 'GOAL_PROGRESS': expr = '[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.GOAL_PROGRESS_VALUE]) : [COMPLICATION.TEXT]'
    c, compact = condition(parent, label_id + '_compact', f'textLength({expr}) > 5')
    text(compact, 6, 32, w-12, 37, 22, '%s', expr, weight='BOLD')
    dc, five = condition(el(c,'Default'), label_id + '_five', f'textLength({expr}) > 4')
    text(five, 6, 32, w-12, 37, 30, '%s', expr, weight='BOLD')
    fc, four = condition(el(dc,'Default'), label_id + '_four', f'textLength({expr}) > 3')
    text(four, 6, 32, w-12, 37, 30, '%s', expr, weight='BOLD')
    text(el(fc,'Default'), 6, 32, w-12, 37, 38, '%s', expr, weight='BOLD')
    text(parent, 9, 68, w-18, 20, 16, '%s', '[COMPLICATION.TITLE]', color=C[3])


def circle_slot(parent, sid, name, x, y, size, provider):
    kinds = ['SHORT_TEXT', 'RANGED_VALUE', 'GOAL_PROGRESS', 'WEIGHTED_ELEMENTS', 'MONOCHROMATIC_IMAGE', 'SMALL_IMAGE', 'EMPTY']
    s = box(parent, 'ComplicationSlot', x, y, size, size, slotId=sid, name=name,
            displayName='slot_'+name, supportedTypes=' '.join(kinds), isCustomizable='TRUE')
    box(s, 'BoundingOval', 0, 0, size, size)
    el(s, 'DefaultProviderPolicy', defaultSystemProvider=provider, defaultSystemProviderType='SHORT_TEXT')
    ambient_hide(s)
    for kind in kinds:
        p = el(s, 'Complication', type=kind)
        ellipse(p, 0, 0, size, size, C[4])
        if kind == 'EMPTY':
            text(p, 0, (size-28)/2, size, 28, 24, '+', color=C[3]); continue
        if kind in ['MONOCHROMATIC_IMAGE', 'SMALL_IMAGE']:
            image(p, 16, 16, size-32, size-32, f'[COMPLICATION.{kind}]', C[2] if kind=='MONOCHROMATIC_IMAGE' else None)
            continue
        if kind in ['RANGED_VALUE', 'GOAL_PROGRESS', 'WEIGHTED_ELEMENTS']:
            arc(p, size/2, size/2, size-6, 0, 360, C[5], 3, viewport=(size,size))
            ratio = RANGE if kind=='RANGED_VALUE' else GOAL
            arc(p, size/2, size/2, size-6, 0, 360, C[6], 3,
                None if kind=='WEIGHTED_ELEMENTS' else f'360 * {ratio}', weighted=kind=='WEIGHTED_ELEMENTS', viewport=(size,size))
        complication_label(p, size, size, kind, f'slot_{sid}_{kind.lower()}')


def edge_tick(parent, center, angle, color, viewport):
    p=box(parent,'PartDraw',0,0,*viewport)
    a=math.radians(angle)
    line=el(p,'Line',startX=round(center[0]+202*math.sin(a),3),
            startY=round(center[1]-202*math.cos(a),3),
            endX=round(center[0]+214*math.sin(a),3),
            endY=round(center[1]-214*math.cos(a),3))
    el(line,'Stroke',color=color,thickness=6,cap='ROUND')


def edge_slot(parent, sid, name, left=False):
    kinds = ['SHORT_TEXT', 'RANGED_VALUE', 'GOAL_PROGRESS', 'EMPTY']
    x,y,w,h = (0,105,90,260) if left else (392,105,58,244)
    center = (225-x,225-y)
    s = box(parent, 'ComplicationSlot', x,y,w,h, slotId=sid, name=name,
            displayName='slot_'+name, supportedTypes=' '.join(kinds), isCustomizable='TRUE')
    # Preserve the stable rectangular clipping/tap model used on both OS versions.
    box(s, 'BoundingRoundBox', 0,0,w,h,cornerRadius=12)
    el(s, 'DefaultProviderPolicy', defaultSystemProvider='WATCH_BATTERY' if left else 'EMPTY',
       defaultSystemProviderType='RANGED_VALUE' if left else 'EMPTY')
    ambient_hide(s)
    for kind in kinds:
        p = el(s, 'Complication', type=kind)
        ratio = RANGE if kind=='RANGED_VALUE' else GOAL if kind=='GOAL_PROGRESS' else None
        if left:
            # Twelve separate rounded ticks, filled from the bottom upward.
            for i in range(12):
                a=260+i*2.8
                edge_tick(p,center,a,C[5],(w,h))
                if ratio:
                    _, lit=condition(p,f'slot_{sid}_{kind.lower()}_tick_{i}',f'{ratio} >= {(i+1)/12:.8f}')
                    edge_tick(lit,center,a,C[6],(w,h))
        else:
            arc(p,*center,416,68,98,C[5],20,viewport=(w,h))
            if ratio:
                # Hide the foreground at zero, avoiding a misleading round-cap dot.
                _, positive=condition(p,f'slot_{sid}_{kind.lower()}_positive',f'{ratio} > 0')
                arc(positive,*center,416,68,98,C[6],20,f'68 + 30 * {ratio}',viewport=(w,h))
            elif kind=='SHORT_TEXT':
                # Decorative accent for a text-only provider, not a progress value.
                arc(p,*center,416,68,98,C[6],20,viewport=(w,h))
        ix,iy=(34,8) if left else (0,8)
        if kind=='EMPTY':
            ellipse(p,ix+3,iy+3,20,20,C[3])
        else:
            image(p,ix,iy,28,28,'[COMPLICATION.MONOCHROMATIC_IMAGE]',C[6])
        # The short rotated captions follow the reference without arc clip masks.
        tx,ty=(27,218) if left else (3,178)
        angle=50 if left else -65
        expr='[COMPLICATION.TEXT]'
        if kind=='RANGED_VALUE':
            expr='[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.RANGED_VALUE_VALUE]) : [COMPLICATION.TEXT]'
        if kind=='GOAL_PROGRESS':
            expr='[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.GOAL_PROGRESS_VALUE]) : [COMPLICATION.TEXT]'
        if kind=='EMPTY':
            text(p,tx,ty,50,26,24,'+',color=C[3],angle=angle)
        else:
            c, compact=condition(p,f'slot_{sid}_{kind.lower()}_edge_compact',f'textLength({expr}) > 3')
            text(compact,tx,ty,50,26,20,'%s',expr,weight='MEDIUM',angle=angle)
            text(el(c,'Default'),tx,ty,50,26,24,'%s',expr,weight='MEDIUM',angle=angle)


def shortcut(parent):
    s = box(parent, 'ComplicationSlot', 155, 410, 140, 30, slotId=6, name='shortcut',
            displayName='slot_shortcut', supportedTypes='SHORT_TEXT MONOCHROMATIC_IMAGE SMALL_IMAGE EMPTY', isCustomizable='TRUE')
    box(s, 'BoundingRoundBox', 0, 0, 140, 30, cornerRadius=15)
    el(s, 'DefaultProviderPolicy', defaultSystemProvider='EMPTY', defaultSystemProviderType='EMPTY')
    ambient_hide(s)
    p = el(s, 'Complication', type='SHORT_TEXT')
    image(p, 3, 3, 24, 24, '[COMPLICATION.MONOCHROMATIC_IMAGE]', C[2])
    text(p, 31, 1, 106, 28, 22, '%s', '[COMPLICATION.TEXT]', color=C[2], align='START')
    for kind in ['MONOCHROMATIC_IMAGE','SMALL_IMAGE']:
        p = el(s, 'Complication', type=kind)
        image(p, 55, 0, 30, 30, f'[COMPLICATION.{kind}]', C[2] if kind=='MONOCHROMATIC_IMAGE' else None)
    p = el(s, 'Complication', type='EMPTY')
    text(p, 0, 1, 140, 28, 22, '+  Shortcut', color=C[3])


def build():
    root = ET.Element('WatchFace', width='450', height='450', clipShape='CIRCLE')
    el(root, 'Metadata', key='CLOCK_TYPE', value='DIGITAL')
    configs = el(root, 'UserConfigurations')
    menu = el(configs, 'ListConfiguration', id='bottom_panel', displayName='bottom_panel', defaultValue='weather')
    for option in PANEL_OPTIONS:
        el(menu, 'ListOption', id=option, displayName='panel_'+option)
    scene = el(root, 'Scene', backgroundColor='#FF000000')
    bg = box(scene, 'PartDraw', 0, 0, 450, 450, name='blue_background'); ambient_hide(bg)
    r = box(bg, 'Rectangle', 0, 0, 450, 450); fill = el(r, 'Fill', color=C[0])
    el(fill, 'LinearGradient', startX=0, startY=0, endX=0, endY=450, colors=C[0]+' '+C[1], positions='0 1')
    clock(scene); clock(scene, ambient=True)
    # Keep complication rendering last to reduce ambient memory use.
    circle_slot(scene,1,'upper_circle',210,91,90,'HEART_RATE')
    circle_slot(scene,2,'middle_circle',301,166,90,'STEP_COUNT')
    circle_slot(scene,3,'lower_circle',210,245,90,'SUNRISE_SUNSET')
    edge_slot(scene,4,'left_edge',True); edge_slot(scene,5,'right_edge')
    shortcut(scene)
    bottom_panel(scene)
    ET.indent(root, space='    ')
    return '<?xml version="1.0" encoding="utf-8"?>\n<!-- Generated by tools/generate_watchface.py. Edit the generator, then regenerate. -->\n'+ET.tostring(root,encoding='unicode')+'\n'


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    result=build()
    if args.check:
        if not OUT.exists() or OUT.read_text()!=result: raise SystemExit('Regenerate watchface.xml with tools/generate_watchface.py')
        print('Generated WFF is current.')
    else: OUT.write_text(result)
