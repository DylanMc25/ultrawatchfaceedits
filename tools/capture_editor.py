#!/usr/bin/env python3
"""Capture actual editor/provider screens; retain inconclusive results for review.

No selections are saved. UI labels vary between Wear OS images, so these captures
are supporting evidence rather than an assertion that every provider works.
"""
import json
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from PIL import Image

out = Path('build/emulator')


def adb(*args):
    return subprocess.run(['adb', *args], check=True, capture_output=True, timeout=30).stdout


def capture(name):
    (out / f'{name}.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    adb('shell', 'uiautomator', 'dump', '/sdcard/window.xml')
    raw = adb('shell', 'cat', '/sdcard/window.xml')
    (out / f'{name}.xml').write_bytes(raw)
    (out / f'{name}-activity.txt').write_bytes(adb('shell', 'dumpsys', 'activity', 'activities'))
    return ET.fromstring(raw)


def tap(x, y):
    adb('shell', 'input', 'tap', str(round(x)), str(round(y)))
    time.sleep(3)


results = {'editor_opened': False, 'slot_captures': [], 'tap_captures': [], 'notes': []}
try:
    w, h = Image.open(out / 'active.png').size
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
    adb('shell', 'settings', 'put', 'system', 'screen_off_timeout', '1800000')
    # Observe the installed providers' own tap actions without changing settings.
    for name, x, y in [('heart-rate', 284, 143), ('steps', 362, 212),
                       ('sunrise-sunset', 284, 272), ('battery', 16, 225)]:
        tap(x*w/450, y*h/450)
        capture(f'tap-{name}')
        results['tap_captures'].append(name)
        adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
        adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
        time.sleep(2)
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
        capture('editor-slots')
        results['editor_opened'] = True
        # Coordinates come from the six WFF touch regions, scaled to the display.
        for name, x, y in [('upper', 284, 143), ('middle', 362, 212),
                           ('lower', 284, 272), ('left', 16, 225),
                           ('right', 434, 225), ('bottom', 225, 418)]:
            tap(x*w/450, y*h/450)
            capture(f'editor-slot-{name}')
            results['slot_captures'].append(name)
            adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
            time.sleep(2)
except Exception as exc:
    results['notes'].append(f'Editor automation inconclusive: {exc}')
finally:
    (out / 'editor-results.json').write_text(json.dumps(results, indent=2) + '\n')
    adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
