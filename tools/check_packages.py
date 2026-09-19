#!/usr/bin/env python3
"""Check resource-only packaging in the actual APK and release bundle."""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
for rel, prefix in [('app/build/outputs/apk/debug/app-debug.apk',''),('app/build/outputs/bundle/release/app-release.aab','base/')]:
    with zipfile.ZipFile(root/rel) as z:
        names=z.namelist()
        assert not any(n.endswith('.dex') for n in names), f'{rel} contains code'
        assert prefix+'res/raw/watchface.xml' in names, f'{rel} missing watch face'
        face=ET.fromstring(z.read(prefix+'res/raw/watchface.xml'))
        # WFF raw XML is not binary-compiled; all static image references must ship.
        for node in face.iter():
            res=node.get('resource','')
            if res and not res.startswith('['):
                assert any(Path(n).stem==res and '/drawable' in n for n in names), f'Missing drawable {res}'
        if prefix:
            assert not any(n.upper().endswith(('.RSA','.DSA','.EC')) for n in names), 'Release bundle should remain unsigned'
    print(f'{rel}: resources present, no DEX, expected signing policy.')
