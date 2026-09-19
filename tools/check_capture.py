#!/usr/bin/env python3
"""Reject startup/default-face captures using three known background positions.
This narrow rendering smoke check does not replace visual review or a full UI test.
"""
import sys
from PIL import Image
im=Image.open(sys.argv[1]).convert('RGB')
points=[(.5,.48),(.47,.64),(.5,.87)]
top=(35,74,119);bottom=(74,150,237)
hits=0
for x,y in points:
    pixel=im.getpixel((int(im.width*x),int(im.height*y)))
    expected=tuple(round(a*(1-y)+b*y) for a,b in zip(top,bottom))
    hits+=max(abs(a-b) for a,b in zip(pixel,expected))<30
if hits<2:raise SystemExit(f'Expected Glacier Blue background at >=2 sample points, got {hits}.')
print('Expected blue watch-face background rendered.')
