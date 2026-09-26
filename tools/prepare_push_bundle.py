#!/usr/bin/env python3
"""Build, sign and officially validate the WFF APK embedded in the Wear OS app.

Run before building weatherbridge. All generated assets stay under build/;
Samsung APKs, signing keys and validation-tool binaries are never bundled.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
HOST_PACKAGE = "com.example.ultrainfoboard.bridge"
FACE_PACKAGE = HOST_PACKAGE + ".watchfacepush.board"
FACE_LABEL = "Ultra Forecast"
FORECAST_PROVIDER = HOST_PACKAGE + "/" + HOST_PACKAGE + ".SamsungForecastService"
VALIDATOR_VERSION = "1.1.0-alpha01"
VALIDATOR_SHA256 = "04dc20a0994df3eaebf025e107f7589c147b2ce8a2c628745e01a5c0a63fe4dd"
VALIDATOR_URL = (
    "https://dl.google.com/dl/android/maven2/com/google/android/wearable/watchface/validator/"
    f"validator-push-cli/{VALIDATOR_VERSION}/validator-push-cli-{VALIDATOR_VERSION}.jar"
)


def java_tool(name):
    suffix = ".exe" if os.name == "nt" else ""
    java_home = os.environ.get("JAVA_HOME")
    return str(Path(java_home) / "bin" / (name + suffix)) if java_home else name + suffix


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, text=True, **kwargs)


def prepare_resources():
    destination = ROOT / "pushface/build/generated/watchface/res"
    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(ROOT / "app/src/main/res", destination)
    watchface = destination / "raw/watchface.xml"
    original = watchface.read_text()
    document = ET.fromstring(original)
    slots = document.findall(".//ComplicationSlot")
    rectangle = [slot for slot in slots if slot.attrib.get("slotId") == "7"]
    if len(rectangle) != 1 or rectangle[0].attrib.get("isCustomizable") != "TRUE":
        raise RuntimeError("Expected exactly one customizable bottom rectangle, slot 7")
    if "SMALL_IMAGE" not in rectangle[0].attrib.get("supportedTypes", "").split():
        raise RuntimeError("Bottom rectangle must support the forecast image")
    slot_width = int(rectangle[0].get("width"))
    slot_height = int(rectangle[0].get("height"))
    pattern = re.compile(r'(<ComplicationSlot\b[^>]*\bslotId="7"[^>]*>.*?)(<DefaultProviderPolicy\b[^>]*/>)', re.S)
    policy = (
        f'<DefaultProviderPolicy primaryProvider="{FORECAST_PROVIDER}" '
        'primaryProviderType="SMALL_IMAGE" defaultSystemProvider="EMPTY" '
        'defaultSystemProviderType="EMPTY" />'
    )
    replaced, count = pattern.subn(lambda match: match.group(1) + policy, original)
    if count != 1:
        raise RuntimeError("Could not replace the bottom rectangle's default provider exactly once")
    rectangle_pattern = re.compile(r'(<ComplicationSlot\b[^>]*\bslotId="7"[^>]*>)(.*?)(</ComplicationSlot>)', re.S)

    def fill_rectangle(match):
        content, image_count = re.subn(
            r'(<Complication type="SMALL_IMAGE">\s*)<PartImage\b[^>]*>',
            lambda image: image.group(1) + f'<PartImage x="0" y="0" width="{slot_width}" height="{slot_height}">', match.group(2),
        )
        if image_count != 1:
            raise RuntimeError("Expected one SMALL_IMAGE renderer in the bottom rectangle")
        # The Wear OS 6 panel accepts complete image panels, not generic text.
        opening = re.sub(r'supportedTypes="[^"]*"', 'supportedTypes="SMALL_IMAGE EMPTY"', match.group(1))
        content = re.sub(r'\s*<Complication type="LONG_TEXT">.*?</Complication>', '', content, flags=re.S)
        return opening + content + match.group(3)

    replaced, count = rectangle_pattern.subn(fill_rectangle, replaced)
    if count != 1:
        raise RuntimeError("Could not size the bottom rectangle image exactly once")
    watchface.write_text(replaced)
    # Keep the pushed face distinguishable from the older development face when both are installed.
    strings_file = destination / "values/strings.xml"
    strings = strings_file.read_text()
    named_strings = ET.fromstring(strings).findall("string[@name='app_name']")
    if len(named_strings) != 1:
        raise RuntimeError("Expected one default watch-face app_name resource")
    renamed, count = re.subn(
        r'(<string\b[^>]*\bname="app_name"[^>]*>).*?(</string>)',
        lambda match: match.group(1) + FACE_LABEL + match.group(2), strings, flags=re.S,
    )
    if count != 1:
        raise RuntimeError("Could not distinguish the pushed watch-face label")
    strings_file.write_text(renamed)
    return destination


def prepare_signing(variant):
    if variant == "release":
        required = ("PUSHFACE_KEYSTORE", "PUSHFACE_STORE_PASSWORD", "PUSHFACE_KEY_ALIAS", "PUSHFACE_KEY_PASSWORD")
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise RuntimeError("Release face signing requires: " + ", ".join(missing))
        if not Path(os.environ["PUSHFACE_KEYSTORE"]).is_file():
            raise RuntimeError("PUSHFACE_KEYSTORE does not name an existing signing key")
        return
    key = ROOT / ".cache/pushface-debug.jks"
    if not key.exists():
        key.parent.mkdir(parents=True, exist_ok=True)
        run([
            java_tool("keytool"), "-genkeypair", "-keystore", str(key), "-storepass", "android",
            "-alias", "pushface-debug", "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000", "-dname", "CN=Ultra Info Board Push Debug", "-noprompt",
        ])


def get_validator(override):
    if override:
        validator = Path(override).resolve()
        if not validator.is_file():
            raise RuntimeError(f"Validator JAR not found: {validator}")
    else:
        validator = ROOT / ".cache" / f"validator-push-cli-{VALIDATOR_VERSION}.jar"
    if not validator.exists():
        validator.parent.mkdir(parents=True, exist_ok=True)
        temporary = validator.with_suffix(".download")
        try:
            urllib.request.urlretrieve(VALIDATOR_URL, temporary)
            with zipfile.ZipFile(temporary) as archive:
                if "META-INF/MANIFEST.MF" not in archive.namelist():
                    raise RuntimeError("Downloaded validator is not an executable JAR")
            temporary.replace(validator)
        finally:
            temporary.unlink(missing_ok=True)
    if hashlib.sha256(validator.read_bytes()).hexdigest() != VALIDATOR_SHA256:
        raise RuntimeError(f"Validator does not match the pinned official {VALIDATOR_VERSION} SHA-256")
    return validator


def assert_resource_only(apk):
    with zipfile.ZipFile(apk) as archive:
        invalid = [name for name in archive.namelist() if not (
            name in ("AndroidManifest.xml", "resources.arsc")
            or name.startswith("res/") or name.startswith("META-INF/")
        )]
    if invalid:
        raise RuntimeError("Unexpected files in pushed WFF APK: " + ", ".join(invalid))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("debug", "release"), default="debug")
    parser.add_argument("--validator", help="Existing official validator-push-cli JAR")
    parser.add_argument("--version-code", type=int, default=12)
    parser.add_argument("--version-name", default="0.2.0-preview.5")
    args = parser.parse_args()
    if args.version_code < 1:
        parser.error("--version-code must be positive")

    generated = ROOT / "weatherbridge/build/generated/watchface"
    # Prevent an unsuccessful preparation from silently shipping an older bundle.
    shutil.rmtree(generated, ignore_errors=True)
    prepare_resources()
    prepare_signing(args.variant)
    wrapper = str(ROOT / ("gradlew.bat" if os.name == "nt" else "gradlew"))
    run([
        wrapper, f":pushface:assemble{args.variant.title()}", "--no-daemon",
        f"-PpushVersionCode={args.version_code}", f"-PpushVersionName={args.version_name}",
    ])
    apk = ROOT / f"pushface/build/outputs/apk/{args.variant}/pushface-{args.variant}.apk"
    assert_resource_only(apk)
    validator = get_validator(args.validator)
    try:
        result = run([
            java_tool("java"), "-jar", str(validator), f"--apk_path={apk}", f"--package_name={HOST_PACKAGE}",
        ], capture_output=True)
    except subprocess.CalledProcessError as error:
        print(error.stdout or "", end="")
        print(error.stderr or "", end="")
        raise
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    match = re.search(r"generated token:\s*(\S+)", result.stdout)
    if not match or "Failed check" in result.stdout:
        raise RuntimeError("Official validation did not return a successful token")
    token = match.group(1)
    (generated / "assets").mkdir(parents=True)
    shutil.copyfile(apk, generated / "assets/default_watchface.apk")
    values = generated / "res/values"
    values.mkdir(parents=True)
    resources = ET.Element("resources")
    ET.SubElement(resources, "string", name="default_wf_token", translatable="false").text = token
    ET.SubElement(resources, "string", name="bundled_watchface_package", translatable="false").text = FACE_PACKAGE
    ET.SubElement(resources, "integer", name="bundled_watchface_version").text = str(args.version_code)
    ET.indent(resources)
    ET.ElementTree(resources).write(values / "default_watchface.xml", encoding="utf-8", xml_declaration=True)
    evidence = {
        "host_package": HOST_PACKAGE, "watchface_package": FACE_PACKAGE,
        "watchface_version_code": args.version_code, "watchface_version_name": args.version_name,
        "variant": args.variant, "forecast_provider": FORECAST_PROVIDER,
        "watchface_apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "validator_filename": validator.name,
        "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest(),
        "validation_token": token,
        "physical_installation_verified": False,
    }
    (generated / "validation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (generated / "validator.log").write_text(result.stdout + result.stderr)
    print(f"Prepared validated {args.variant} watch face for weatherbridge: {generated}")


if __name__ == "__main__":
    main()
