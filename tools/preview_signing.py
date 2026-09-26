#!/usr/bin/env python3
"""Keep CI preview updates on one signing identity; publish certificates, never keys."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
KEY = Path.home() / '.android/debug.keystore'
PIN = ROOT / 'tools/preview-certificates.json'


def certificate(key, alias):
    der = subprocess.check_output(['keytool', '-exportcert', '-keystore', str(key),
                                   '-storepass', 'android', '-alias', alias])
    return hashlib.sha256(der).hexdigest()


def identities():
    return {'host': certificate(KEY, 'androiddebugkey'),
            'face': certificate(ROOT / '.cache/pushface-debug.jks', 'pushface-debug')}


def check_pins(actual):
    if os.environ.get('CI') == 'true' and PIN.exists():
        for name, expected in json.loads(PIN.read_text()).items():
            if actual[name] != expected:
                raise RuntimeError(f'{name} signing identity changed. Restore the original signing key; '
                                   'do not distribute an incompatible replacement APK.')


def main():
    if sys.argv[1:] == ['prepare']:
        # Once CI identities are pinned, a lost cache must fail instead of silently
        # generating an APK that requires users to uninstall and grant access again.
        if not KEY.exists():
            if os.environ.get('CI') == 'true' and PIN.exists():
                raise RuntimeError('Preview host key cache is missing. Restore the original key.')
            KEY.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['keytool', '-genkeypair', '-keystore', str(KEY), '-storepass', 'android',
                            '-alias', 'androiddebugkey', '-keypass', 'android', '-keyalg', 'RSA',
                            '-keysize', '2048', '-validity', '10000',
                            '-dname', 'CN=Ultra Info Board Preview', '-noprompt'], check=True)
        if PIN.exists():
            check_pins(identities())
    elif sys.argv[1:] == ['verify']:
        actual = identities()
        check_pins(actual)
        sdk = Path(os.environ.get('ANDROID_HOME', os.environ.get('ANDROID_SDK_ROOT', '')))
        signer = sdk / 'build-tools/35.0.0/apksigner'
        for name, apk in [('host', 'weatherbridge/build/outputs/apk/debug/weatherbridge-debug.apk'),
                          ('face', 'pushface/build/outputs/apk/debug/pushface-debug.apk')]:
            output = subprocess.check_output([str(signer), 'verify', '--print-certs', str(ROOT / apk)], text=True)
            if f'Signer #1 certificate SHA-256 digest: {actual[name]}' not in output:
                raise RuntimeError(f'{name} APK was signed with an unexpected key')
        report = ROOT / 'weatherbridge/build/reports/preview-certificates.json'
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(actual, indent=2) + '\n')
        print(report.read_text())
    else:
        raise SystemExit('Usage: preview_signing.py prepare|verify')


if __name__ == '__main__':
    main()
