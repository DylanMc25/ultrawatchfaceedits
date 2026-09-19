#!/usr/bin/env python3
"""Generate the resource-only WFF definition. Run from any directory; no dependencies."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'app/src/main/res/raw/watchface.xml'
# Five WFF 2 palette entries: gradient top/bottom, primary, secondary, surface.
PALETTE = ['#FF234A77', '#FF4A96ED', '#FFDAF1FF', '#FFB4DAF6', '#FF509EFA']
# A single fixed palette needs no editor setting. Keep these values centralized
# for future multi-option themes; WFF runtimes reject a one-option color setting.
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


def arc(parent, cx, cy, diameter, start, end, color, thickness, expression=None, weighted=False):
    p = box(parent, 'PartDraw', 0, 0, 450, 450)
    a = el(p, 'Arc', centerX=cx, centerY=cy, width=diameter, height=diameter, startAngle=start, endAngle=end)
    if weighted:
        el(a, 'WeightedStroke', colors='[COMPLICATION.WEIGHTED_ELEMENTS_COLORS]',
           weights='[COMPLICATION.WEIGHTED_ELEMENTS_WEIGHTS]', thickness=thickness, cap='ROUND', discreteGap=3)
    else: el(a, 'Stroke', color=color, thickness=thickness, cap='ROUND')
    if expression: el(a, 'Transform', target='endAngle', value=expression)
    return p


def circular_text(parent, start, end, value, *params, size=18):
    p = box(parent, 'PartText', 0, 0, 450, 450)
    t = el(p, 'TextCircular', centerX=225, centerY=225, width=416, height=416,
           startAngle=start, endAngle=end, direction='CLOCKWISE', align='CENTER', ellipsis='TRUE')
    f = el(t, 'Font', family='sans-serif', size=size, color=C[2], weight='MEDIUM')
    if params:
        temp = el(f, 'Template'); temp.text = value
        for v in params: el(temp, 'Parameter', expression=v)
    else: f.text = value


def clock(parent, ambient=False):
    g = group(parent, 'ambient_time' if ambient else 'interactive_time', alpha=0 if ambient else 255)
    el(g, 'Variant', mode='AMBIENT', target='alpha', value=255 if ambient else 0)
    color = '#FF8FA9BC' if ambient else C[2]
    # Same alignment in both modes; thinner and slightly smaller ambient numerals.
    d = box(g, 'DigitalClock', 56, 61, 180, 222)
    for fmt, y in [('hh', 0), ('mm', 107)]:
        t = box(d, 'TimeText', 0, y, 156, 119, format=fmt, hourFormat='SYNC_TO_DEVICE', align='CENTER')
        el(t, 'Font', family='sans-serif-condensed', size=112 if ambient else 120,
           color=color, weight='THIN' if ambient else 'MEDIUM')
    text(g, 94, 23, 262, 35, 27, '%s', '[MONTH_F]', color=color, weight='LIGHT' if ambient else 'BOLD')
    text(g, 235, 60, 132, 31, 24, '%s %s', '[DAY_OF_WEEK_S]', '[DAY]', color=color)
    if not ambient:
        seconds = box(g, 'DigitalClock', 206, 245, 33, 30)
        t = box(seconds, 'TimeText', 0, 0, 33, 30, format='ss', align='CENTER')
        el(t, 'Font', family='sans-serif-condensed', size=25, color=C[3], weight='MEDIUM')


def weather_icon(parent, prefix, x, y, size, name):
    c, day = condition(parent, name+'_day', f'[{prefix}.IS_DAY]')
    for mode, target in [('day', day), ('night', el(c, 'Default'))]:
        p = box(target, 'PartText', x, y, size, size)
        t = el(p, 'Text', align='CENTER')
        f = el(t, 'BitmapFont', family='weather_'+mode, size=size, color=C[2])
        temp = el(f, 'Template'); temp.text = '%s'
        el(temp, 'Parameter', expression=f'[{prefix}.CONDITION] >= 0 &amp;&amp; [{prefix}.CONDITION] <= 15 ? [{prefix}.CONDITION] : 0'.replace('&amp;', '&'))


def weather(parent):
    g = group(parent, 'weather'); ambient_hide(g)
    c, available = condition(g, 'weather_available', '[WEATHER.IS_AVAILABLE]')
    weather_icon(available, 'WEATHER', 70, 291, 31, 'current')
    text(available, 105, 290, 128, 32, 22, 'Now %s°', '[WEATHER.TEMPERATURE]', align='START', weight='MEDIUM')
    text(el(c, 'Default'), 70, 292, 158, 28, 18, 'Weather —', color=C[3], align='START')
    # Forecast hours have their own availability; never substitute today's reading.
    for i, offset in enumerate((2, 4, 6, 8)):
        x = 80 + i*73
        col = group(g, f'forecast_{offset}', x, 328, 70, 64)
        c, yes = condition(col, f'forecast_{offset}_available', f'[WEATHER.IS_AVAILABLE] &amp;&amp; [WEATHER.HOURS.{offset}.IS_AVAILABLE]'.replace('&amp;', '&'))
        weather_icon(yes, f'WEATHER.HOURS.{offset}', 18, 0, 32, f'forecast_{offset}')
        text(yes, 0, 30, 68, 22, 18, '%s°', f'[WEATHER.HOURS.{offset}.TEMPERATURE]', weight='MEDIUM')
        text(el(c, 'Default'), 0, 18, 68, 30, 21, '—', color=C[3])
        c, h24 = condition(col, f'forecast_{offset}_24h', '[IS_24_HOUR_MODE]')
        hour = f'([HOUR_0_23] + {offset}) % 24'
        text(h24, 0, 53, 68, 20, 14, '%02d:00', hour, color=C[3], weight='MEDIUM')
        text(el(c, 'Default'), 0, 53, 68, 20, 14, '%d %s', f'(({hour}) + 11) % 12 + 1',
             f'({hour}) < 12 ? "AM" : "PM"', color=C[3], weight='MEDIUM')
        if i < 3:
            p = box(g, 'PartDraw', x+71, 337, 1, 45)
            r = box(p, 'Rectangle', 0, 0, 1, 45); el(r, 'Fill', color=C[5])


RANGE = '([COMPLICATION.RANGED_VALUE_MAX] > [COMPLICATION.RANGED_VALUE_MIN] ? clamp(([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / ([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN]), 0, 1) : 0)'
GOAL = '([COMPLICATION.GOAL_PROGRESS_TARGET_VALUE] > 0 ? clamp([COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE], 0, 1) : 0)'


def complication_label(parent, w, h, kind, label_id):
    # Providers may send an icon, a title, both, or neither. Reserve both bands;
    # absent optional fields render empty, leaving the primary reading centered.
    image(parent, (w-22)/2, 10, 22, 22, '[COMPLICATION.MONOCHROMATIC_IMAGE]', C[2])
    expr = '[COMPLICATION.TEXT]'
    if kind == 'RANGED_VALUE': expr = '[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.RANGED_VALUE_VALUE]) : [COMPLICATION.TEXT]'
    if kind == 'GOAL_PROGRESS': expr = '[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.GOAL_PROGRESS_VALUE]) : [COMPLICATION.TEXT]'
    c, compact = condition(parent, label_id + '_compact', f'textLength({expr}) > 5')
    text(compact, 7, 33, w-14, 29, 16, '%s', expr, weight='BOLD')
    text(el(c, 'Default'), 7, 33, w-14, 29, 23 if w>80 else 21, '%s', expr, weight='BOLD')
    text(parent, 9, 62, w-18, 16, 11, '%s', '[COMPLICATION.TITLE]', color=C[3])


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
            arc(p, size/2, size/2, size-6, 0, 360, C[5], 3)
            ratio = RANGE if kind=='RANGED_VALUE' else GOAL
            arc(p, size/2, size/2, size-6, 0, 360, C[6], 3,
                None if kind=='WEIGHTED_ELEMENTS' else f'360 * {ratio}', weighted=kind=='WEIGHTED_ELEMENTS')
        complication_label(p, size, size, kind, f'slot_{sid}_{kind.lower()}')


def edge_slot(parent, sid, name, left=False):
    kinds = ['SHORT_TEXT', 'RANGED_VALUE', 'GOAL_PROGRESS', 'EMPTY']
    s = box(parent, 'ComplicationSlot', 0, 0, 450, 450, slotId=sid, name=name,
            displayName='slot_'+name, supportedTypes=' '.join(kinds), isCustomizable='TRUE')
    start,end = (232,298) if left else (62,136)
    el(s, 'BoundingArc', centerX=225, centerY=225, width=420, height=420,
       thickness=28, startAngle=start, endAngle=end)
    el(s, 'DefaultProviderPolicy', defaultSystemProvider='WATCH_BATTERY' if left else 'EMPTY',
       defaultSystemProviderType='RANGED_VALUE' if left else 'EMPTY')
    ambient_hide(s)
    for kind in kinds:
        p = el(s, 'Complication', type=kind)
        a,b = (252,292) if left else (68,110)
        arc(p, 225, 225, 420, a,b, C[5], 7)
        if kind in ['RANGED_VALUE','GOAL_PROGRESS']:
            ratio = RANGE if kind=='RANGED_VALUE' else GOAL
            arc(p,225,225,420,a,b,C[6],7,f'{a} + {b-a} * {ratio}')
        if kind=='EMPTY':
            circular_text(p, 234 if left else 114, 252 if left else 135, '+', size=20)
        else:
            circular_text(p, 232 if left else 112, 252 if left else 136, '%s', '[COMPLICATION.TEXT]', size=16)


def shortcut(parent):
    s = box(parent, 'ComplicationSlot', 165, 403, 120, 30, slotId=6, name='shortcut',
            displayName='slot_shortcut', supportedTypes='SHORT_TEXT MONOCHROMATIC_IMAGE SMALL_IMAGE EMPTY', isCustomizable='TRUE')
    box(s, 'BoundingRoundBox', 0, 0, 120, 30, cornerRadius=15)
    el(s, 'DefaultProviderPolicy', defaultSystemProvider='EMPTY', defaultSystemProviderType='EMPTY')
    ambient_hide(s)
    p = el(s, 'Complication', type='SHORT_TEXT')
    image(p, 3, 4, 22, 22, '[COMPLICATION.MONOCHROMATIC_IMAGE]', C[2])
    text(p, 29, 2, 88, 26, 16, '%s', '[COMPLICATION.TEXT]', color=C[2], align='START')
    for kind in ['MONOCHROMATIC_IMAGE','SMALL_IMAGE']:
        p = el(s, 'Complication', type=kind)
        image(p, 46, 1, 28, 28, f'[COMPLICATION.{kind}]', C[2] if kind=='MONOCHROMATIC_IMAGE' else None)
    p = el(s, 'Complication', type='EMPTY')
    text(p, 0, 2, 120, 26, 15, '+  Shortcut', color=C[3])


def build():
    root = ET.Element('WatchFace', width='450', height='450')
    el(root, 'Metadata', key='CLOCK_TYPE', value='DIGITAL')
    fonts = el(root, 'BitmapFonts')
    for mode in ['day','night']:
        font = el(fonts, 'BitmapFont', name='weather_'+mode)
        for i in range(16):
            el(font, 'Character' if i<10 else 'Word', name=i, resource=f'weather_{mode}_{i}', width=96, height=96)
    scene = el(root, 'Scene', backgroundColor='#FF000000')
    bg = box(scene, 'PartDraw', 0, 0, 450, 450, name='blue_background'); ambient_hide(bg)
    r = box(bg, 'Rectangle', 0, 0, 450, 450); fill = el(r, 'Fill', color=C[0])
    el(fill, 'LinearGradient', startX=0, startY=0, endX=0, endY=450, colors=C[0]+' '+C[1], positions='0 1')
    clock(scene); clock(scene, ambient=True)
    weather(scene)
    # Keep complication rendering last to reduce ambient memory use.
    circle_slot(scene,1,'upper_circle',240,99,88,'HEART_RATE')
    circle_slot(scene,2,'middle_circle',322,172,80,'STEP_COUNT')
    circle_slot(scene,3,'lower_circle',240,228,88,'SUNRISE_SUNSET')
    edge_slot(scene,4,'left_edge',True); edge_slot(scene,5,'right_edge')
    shortcut(scene)
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
