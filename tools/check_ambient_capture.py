#!/usr/bin/env python3
"""Check one real DOZE capture, including system overlays, against the 15% limit.

This is evidence for the captured date/time, not every possible date/time.
"""
import json
from pathlib import Path
import sys
from PIL import Image

capture, display = map(Path, sys.argv[1:3])
if 'mScreenState=DOZE' not in display.read_text():
    raise SystemExit('No DOZE display state: cannot claim an ambient capture.')
im = Image.open(capture).convert('RGB')
w, h = im.size
pixels = [im.getpixel((x, y)) for y in range(h) for x in range(w)
          if (x + .5 - w / 2)**2 + (y + .5 - h / 2)**2 <= (min(w, h) / 2)**2]
lit = sum(max(pixel) > 0 for pixel in pixels)
percent = 100 * lit / len(pixels)
print(json.dumps({'capture': capture.name, 'dimensions': [w, h],
                  'display_state': 'DOZE', 'round_screen_pixels': len(pixels),
                  'lit_pixels_including_system_overlays': lit,
                  'lit_percent': round(percent, 4), 'limit_percent': 15}, indent=2))
if not 0 < percent <= 15:
    raise SystemExit(f'Ambient capture has {percent:.2f}% lit pixels; expected 0–15%.')
