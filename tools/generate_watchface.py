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
    # Retain the installed face's stacked time and two-line date. Slightly
    # smaller, inset digits clear the battery gauge and larger forecast below.
    d = box(g, 'DigitalClock', 28, 67, 176, 246)
    for fmt, x, y, width in [('hh', 22, 0, 154), ('mm', 0, 116, 138)]:
        t = box(d, 'TimeText', x, y, width, 130, format=fmt, hourFormat='SYNC_TO_DEVICE', align='CENTER')
        el(t, 'Font', family='sans-serif-condensed', size=116 if ambient else 134,
           color=color, weight='THIN' if ambient else 'MEDIUM')
    text(g, 82, 17, 286, 40, 24, '%s', '[MONTH_F]',
         color=color if ambient else C[3], weight='LIGHT' if ambient else 'NORMAL')
    text(g, 230, 55, 142, 29, 21, '%s %s', '[DAY_OF_WEEK_S]', '[DAY]',
         color=color if ambient else C[3])
    if not ambient:
        seconds = box(g, 'DigitalClock', 168, 270, 36, 40)
        t = box(seconds, 'TimeText', 0, 0, 36, 40, format='ss', align='CENTER')
        el(t, 'Font', family='sans-serif-condensed', size=36, color=C[3], weight='MEDIUM')


def rectangle_slot(parent):
    # Keep the native picker, limited to formats suited to a wide information
    # panel. The system controls app categories; WFF cannot whitelist providers.
    kinds = ['LONG_TEXT', 'SMALL_IMAGE', 'EMPTY']
    s = box(parent, 'ComplicationSlot', 94, 310, 262, 94, slotId=7, name='rectangle',
            displayName='slot_rectangle', supportedTypes=' '.join(kinds), isCustomizable='TRUE')
    box(s, 'BoundingRoundBox', 0, 0, 262, 94, cornerRadius=16)
    el(s, 'DefaultProviderPolicy',
       primaryProvider='com.samsung.android.watch.weather/com.samsung.android.watch.weather.complication.WeatherComplicationService',
       primaryProviderType='LONG_TEXT', defaultSystemProvider='EMPTY', defaultSystemProviderType='EMPTY')
    ambient_hide(s)
    p = el(s, 'Complication', type='EMPTY')
    text(p, 8, 31, 246, 32, 18, '+ Complication', color=C[3])
    p = el(s, 'Complication', type='SMALL_IMAGE')
    image(p, 0, 0, 262, 94, '[COMPLICATION.SMALL_IMAGE]')
    p = el(s, 'Complication', type='LONG_TEXT')
    image(p, 8, 29, 34, 34, '[COMPLICATION.MONOCHROMATIC_IMAGE]', C[2])
    expr='textLength([COMPLICATION.TEXT]) > 0 ? [COMPLICATION.TEXT] : "—"'
    c, titled = condition(p, 'rectangle_long_text_title', 'textLength([COMPLICATION.TITLE]) > 0')
    for target, y, h in [(titled, 8, 52), (el(c, 'Default'), 17, 62)]:
        part = text(target, 49, y, 205, h, 23, '%s', expr, align='START', weight='MEDIUM')
        part.find('Text').set('maxLines', '2')
    text(titled, 49, 63, 205, 22, 16, '%s', '[COMPLICATION.TITLE]', align='START', color=C[3])


RANGE = '([COMPLICATION.RANGED_VALUE_MAX] > [COMPLICATION.RANGED_VALUE_MIN] ? clamp(([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / ([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN]), 0, 1) : 0)'
GOAL = '([COMPLICATION.GOAL_PROGRESS_TARGET_VALUE] > 0 ? clamp([COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE], 0, 1) : 0)'


def complication_label(parent, w, h, kind, label_id):
    # Primary values receive the largest type; optional provider titles stay
    # subordinate in their own small band.
    expr = '[COMPLICATION.TEXT]'
    if kind == 'RANGED_VALUE': expr = '[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.RANGED_VALUE_VALUE]) : [COMPLICATION.TEXT]'
    if kind == 'GOAL_PROGRESS': expr = '[COMPLICATION.TEXT] == "" ? numberFormat("#,###", [COMPLICATION.GOAL_PROGRESS_VALUE]) : [COMPLICATION.TEXT]'
    inset = (h-96)/2
    image(parent, (w-30)/2, 5+inset, 30, 30, '[COMPLICATION.MONOCHROMATIC_IMAGE]', C[2])
    c, compact = condition(parent, label_id + '_compact', f'textLength({expr}) > 5')
    text(compact, 5, 32+inset, w-10, 45, 25, '%s', expr, weight='BOLD')
    dc, five = condition(el(c,'Default'), label_id + '_five', f'textLength({expr}) > 4')
    text(five, 5, 32+inset, w-10, 45, 33, '%s', expr, weight='BOLD')
    fc, four = condition(el(dc,'Default'), label_id + '_four', f'textLength({expr}) > 3')
    text(four, 5, 32+inset, w-10, 45, 37, '%s', expr, weight='BOLD')
    text(el(fc,'Default'), 5, 32+inset, w-10, 45, 46, '%s', expr, weight='BOLD')
    text(parent, 9, 77+inset, w-18, 18, 14, '%s', '[COMPLICATION.TITLE]', color=C[3])


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
    x,y,w,h = (0,105,90,260) if left else (398,105,52,238)
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
        tx,ty=(27,218) if left else (0,178)
        angle=50 if left else -70
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
    text(p, 31, 1, 106, 28, 24, '%s', '[COMPLICATION.TEXT]', color=C[2], align='START')
    for kind in ['MONOCHROMATIC_IMAGE','SMALL_IMAGE']:
        p = el(s, 'Complication', type=kind)
        image(p, 55, 0, 30, 30, f'[COMPLICATION.{kind}]', C[2] if kind=='MONOCHROMATIC_IMAGE' else None)
    p = el(s, 'Complication', type='EMPTY')
    text(p, 0, 4, 140, 22, 16, '+ Shortcut', color=C[3])


def build():
    root = ET.Element('WatchFace', width='450', height='450', clipShape='CIRCLE')
    el(root, 'Metadata', key='CLOCK_TYPE', value='DIGITAL')
    scene = el(root, 'Scene', backgroundColor='#FF000000')
    bg = box(scene, 'PartDraw', 0, 0, 450, 450, name='blue_background'); ambient_hide(bg)
    r = box(bg, 'Rectangle', 0, 0, 450, 450); fill = el(r, 'Fill', color=C[0])
    el(fill, 'LinearGradient', startX=0, startY=0, endX=0, endY=450, colors=C[0]+' '+C[1], positions='0 1')
    clock(scene); clock(scene, ambient=True)
    # Keep complication rendering last to reduce ambient memory use.
    circle_slot(scene,1,'upper_circle',204,86,96,'HEART_RATE')
    circle_slot(scene,2,'middle_circle',302,166,94,'STEP_COUNT')
    circle_slot(scene,3,'lower_circle',204,212,96,'SUNRISE_SUNSET')
    edge_slot(scene,4,'left_edge',True); edge_slot(scene,5,'right_edge')
    shortcut(scene)
    rectangle_slot(scene)
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
