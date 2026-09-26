#!/usr/bin/env python3
"""Capture actual editor/provider screens; retain inconclusive results for review.

Choosers are cancelled individually, then the right edge is assigned Alarm on the
disposable emulator to check its text clipping. UI labels vary between Wear OS
images, so these captures require review rather than proving every provider works.
"""
import json
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from PIL import Image

out = Path('build/emulator')
BATTERY_ACTIVITY = ('com.google.android.apps.wearable.settings/'
                    'com.google.android.clockwork.settings.MainSettingsActivity')


def adb(*args):
    return subprocess.run(['adb', *args], check=True, capture_output=True, timeout=30).stdout


def launch_log(pattern='Launch::onTap'):
    # Startup emits enough unrelated logs to interrupt unfiltered dumps on
    # small Wear emulators. Read only launch events, retrying read failures.
    for attempt in range(3):
        try:
            return set(adb('logcat', '-d', '-e', pattern).decode().splitlines())
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            time.sleep(1)


def capture(name):
    (out / f'{name}.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    adb('shell', 'uiautomator', 'dump', '/sdcard/window.xml')
    raw = adb('shell', 'cat', '/sdcard/window.xml')
    (out / f'{name}.xml').write_bytes(raw)
    (out / f'{name}-activity.txt').write_bytes(adb('shell', 'dumpsys', 'activity', 'activities'))
    return ET.fromstring(raw)


def resumed_activity(activity):
    # Older chooser activities remain in the task history after dismissal.
    # Only the current foreground activity can prove that a new tap opened it.
    return '\n'.join(line for line in activity.splitlines() if
                     'mResumedActivity' in line or 'topResumedActivity' in line)


def tap(x, y):
    adb('shell', 'input', 'tap', str(round(x)), str(round(y)))
    time.sleep(3)


def ensure_face():
    # BACK/HOME can open the launcher when already on the face. Inspect before
    # navigating so a later coordinate never accidentally targets another app.
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
    for attempt in range(4):
        time.sleep(2)
        path=out / 'interaction-face.png'
        path.write_bytes(adb('exec-out', 'screencap', '-p'))
        if subprocess.run(['python3','tools/check_capture.py',str(path)],capture_output=True).returncode==0:
            return
        adb('shell','input','keyevent','KEYCODE_HOME')
    raise RuntimeError('Cannot confirm watch face before interaction; stopped coordinate taps.')


def return_to_editor():
    # Provider chooser dismissal may leave a transitional blank activity. Wait
    # for the actual editor before the next tap, instead of assuming one BACK
    # always returns there on both Wear OS versions.
    for attempt in range(4):
        adb('shell','uiautomator','dump','/sdcard/window.xml')
        tree=ET.fromstring(adb('shell','cat','/sdcard/window.xml'))
        if any(n.get('resource-id','').endswith(':id/layout_editor') for n in tree.iter('node')):
            return tree
        adb('shell','input','keyevent','KEYCODE_BACK')
        time.sleep(3)
    raise RuntimeError('Editor did not return after provider chooser; stopped coordinate taps.')


def find_battery(chooser, w, h):
    """Locate the stock LONG_TEXT source, including its Wear OS app label."""
    previous = None
    for page in range(8):
        for node in chooser.iter('node'):
            b = tuple(map(int, re.findall(r'\d+', node.get('bounds', ''))))
            if (node.get('text') == 'Battery, Wear OS' and len(b) == 4
                    and b[3] - b[1] >= 18):
                return node
        visible = [(n.get('text'), n.get('bounds')) for n in chooser.iter('node') if n.get('text')]
        if visible == previous:
            break
        previous = visible
        adb('shell', 'input', 'swipe', str(w // 2), str(round(h * .78)),
            str(w // 2), str(round(h * .25)), '500')
        time.sleep(2)
        chooser = capture(f'weather-battery-page-{page:02}')
    return None


results = {'editor_opened': False, 'slot_captures': [], 'tap_captures': [], 'tap_mismatches': [], 'notes': []}
try:
    w, h = Image.open(out / 'active.png').size
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
    adb('shell', 'settings', 'put', 'system', 'screen_off_timeout', '1800000')
    # Observe the installed providers' own tap actions without changing settings.
    for sid, name, x, y in [(1, 'heart-rate', 250, 126), (2, 'steps', 348, 183),
                            (3, 'sunrise-sunset', 250, 239), (4, 'battery', 16, 225),
                            (1, 'upper-boundary', 287, 148), (2, 'middle-upper-boundary', 314, 156),
                            (2, 'middle-lower-boundary', 314, 210), (3, 'lower-boundary', 287, 262)]:
        ensure_face()
        before=launch_log()
        tap(x*w/450, y*h/450)
        capture(f'tap-{name}')
        after=launch_log()-before
        ids=[int(m.group(1)) for line in after if (m:=re.search(r'\[Launch::onTap\] complication: COMPLICATION\.(\d+)',line))]
        results['tap_captures'].append({'name':name,'expected_slot':sid,'observed_launch_slots':ids})
        if any(actual!=sid for actual in ids) or (sid in [2,3,4] and sid not in ids):
            results['tap_mismatches'].append(name)
    ensure_face()
    adb('shell', 'input', 'swipe', str(w//2), str(h//2), str(w//2), str(h//2), '1200')
    time.sleep(3)
    tree = capture('editor-entry')
    edit = next((n for n in tree.iter('node') if re.search(
        r'edit|customi[sz]e', ' '.join(n.get(k, '') for k in
        ['text', 'content-desc', 'resource-id']), re.I)), None)
    if edit is None:
        results['notes'].append('No edit control identified; inspect editor-entry capture.')
    else:
        x1, y1, x2, y2 = map(int, re.findall(r'\d+', edit.get('bounds')))
        tap((x1+x2)/2, (y1+y2)/2)
        slot_tree=capture('editor-slots')
        results['editor_opened'] = True
        # Coordinates come from the seven WFF touch regions, scaled to the display.
        for name, x, y in [('upper', 250, 126), ('middle', 348, 183),
                           ('lower', 250, 239), ('left', 16, 225),
                           ('right', 420, 225), ('bottom', 225, 425), ('weather', 225, 357)]:
            slot_tree=return_to_editor()
            label='Bottom rectangle' if name=='weather' else 'Bottom shortcut' if name=='bottom' else f'{name.title()} '+('edge' if name in ['left','right'] else 'circle')
            node=next((n for n in slot_tree.iter('node') if label.lower() in (n.get('text','')+' '+n.get('content-desc','')).lower()),None)
            if node is not None:
                x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')))
                tap((x1+x2)/2,(y1+y2)/2)
            else:tap(x*w/450,y*h/450)
            chooser=capture(f'editor-slot-{name}')
            activity=(out / f'editor-slot-{name}-activity.txt').read_text()
            visible=any(n.get('text') for n in chooser.iter('node'))
            results['slot_captures'].append({'name':name,'provider_chooser_visible':visible and
                                            'ProviderChooserActivity' in resumed_activity(activity)})
        # Reproduce the reported edge-label clipping with real provider text.
        return_to_editor()
        tap(420*w/450,225*h/450)
        chooser=capture('edge-alarm-chooser')
        alarm=next((n for n in chooser.iter('node') if n.get('text')=='Alarm'),None)
        if alarm is None:
            results['notes'].append('Alarm provider unavailable for edge-label capture.')
        else:
            x1,y1,x2,y2=map(int,re.findall(r'\d+',alarm.get('bounds')))
            tap((x1+x2)/2,(y1+y2)/2)
            return_to_editor()
            capture('editor-edge-alarm')
            adb('shell','input','keyevent','KEYCODE_HOME')
            ensure_face()
            capture('active-edge-alarm')
            results['edge_alarm_capture']=True
        # A stock emulator lacks Samsung Weather. Select its LONG_TEXT Battery
        # provider in the rectangle to verify assignment and provider-owned taps.
        # This does not claim Samsung Weather integration on physical hardware.
        if results.get('edge_alarm_capture'):
            # Reopen the editor, since the preceding check returned to the face.
            adb('shell', 'input', 'swipe', str(w//2), str(h//2), str(w//2), str(h//2), '1200')
            time.sleep(3)
            tree=capture('weather-editor-entry')
            edit=next(n for n in tree.iter('node') if re.search(r'edit|customi[sz]e', ' '.join(n.get(k,'') for k in ['text','content-desc','resource-id']), re.I))
            x1,y1,x2,y2=map(int,re.findall(r'\d+',edit.get('bounds')))
            tap((x1+x2)/2,(y1+y2)/2)
            return_to_editor()
            tap(225*w/450,357*h/450)
            chooser=capture('weather-provider-chooser')
            battery=find_battery(chooser,w,h)
            if battery is None:
                results['notes'].append('Battery test provider unavailable in rectangle slot.')
            else:
                x1,y1,x2,y2=map(int,re.findall(r'\d+',battery.get('bounds')))
                tap((x1+x2)/2,(y1+y2)/2)
                return_to_editor()
                capture('editor-weather-assigned')
                adb('shell','input','keyevent','KEYCODE_HOME')
                ensure_face()
                capture('active-weather-assigned')
                attempts=[]
                for point,x in [('left',100),('center',225),('right',350)]:
                    ensure_face()
                    before=launch_log()
                    tap(x*w/450,357*h/450)
                    capture('tap-rectangle-'+point)
                    evidence=sorted(launch_log()-before)
                    (out/f'tap-rectangle-{point}-launch.txt').write_text('\n'.join(evidence)+'\n')
                    ids=[int(m.group(1)) for line in evidence if (m:=re.search(r'\[Launch::onTap\] complication: COMPLICATION\.(\d+)',line))]
                    activity=(out/f'tap-rectangle-{point}-activity.txt').read_text()
                    resumed=resumed_activity(activity)
                    attempts.append({'point':point,'observed_launch_slots':ids,'resumed_activity':resumed})
                    if ids != [7] or BATTERY_ACTIVITY not in resumed:
                        results['tap_mismatches'].append('rectangle-'+point)
                results['weather_provider_test']={'assigned_provider':'Battery','expected_slot':7,
                    'observed_launch_slots':attempts[1]['observed_launch_slots'],'tap_attempts':attempts,
                    'samsung_weather_verified':False}

except Exception as exc:
    detail = (getattr(exc, 'stderr', None) or b'').decode(errors='replace').strip()
    results['notes'].append(f'Editor automation inconclusive: {exc}; {detail}')
finally:
    (out / 'editor-results.json').write_text(json.dumps(results, indent=2) + '\n')
    adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
if results['tap_mismatches']:
    raise SystemExit('Wrong complication received taps: '+', '.join(results['tap_mismatches']))

if len(results['slot_captures']) != 7 or not all(s['provider_chooser_visible'] for s in results['slot_captures']):
    raise SystemExit('Not all seven native provider choosers were verified; inspect editor-results.json.')
if not results.get('edge_alarm_capture'):
    raise SystemExit('Assigned edge text was not captured; inspect editor-results.json.')

if 7 not in results.get('weather_provider_test',{}).get('observed_launch_slots',[]):
    raise SystemExit('Weather slot provider tap was not verified; inspect weather tap logs.')
