#!/usr/bin/env python3
"""Exercise the curated chart menu, six native slots, persistence and panel taps.

Only for a disposable stock emulator. Samsung readings are not installed;
renderer fixtures and real provider unavailable states are tested separately.
UI trees and screenshots are retained on failure.
"""
import json
from pathlib import Path
import re
import subprocess
import statistics
import time
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops


OUT = Path("build/forecast-emulator/editor")
HOST = "com.example.ultrainfoboard.bridge"
FACE = HOST + ".watchfacepush.board"
RECTANGLE_CENTER = (225, 357)
RESULT = {"passed": False, "checks": [], "samsung_integration_verified": False}
WIDTH = HEIGHT = 0


def adb(*args):
    return subprocess.run(["adb", *args], check=True, capture_output=True, timeout=35).stdout


def tree():
    adb("shell", "uiautomator", "dump", "/sdcard/forecast-editor.xml")
    return ET.fromstring(adb("shell", "cat", "/sdcard/forecast-editor.xml"))


def capture(name):
    (OUT / (name + ".png")).write_bytes(adb("exec-out", "screencap", "-p"))
    current = tree()
    ET.ElementTree(current).write(OUT / (name + ".xml"), encoding="utf-8")
    (OUT / (name + "-activity.txt")).write_bytes(adb("shell", "dumpsys", "activity", "activities"))
    return current


def tap(x, y):
    adb("shell", "input", "tap", str(round(x)), str(round(y)))
    time.sleep(2)


def bounds(node):
    return tuple(map(int, re.findall(r"\d+", node.get("bounds", ""))))


def click(node):
    x1, y1, x2, y2 = bounds(node)
    tap((x1 + x2) / 2, (y1 + y2) / 2)


def label(node):
    return (node.get("text", "") + " " + node.get("content-desc", "")).strip()


def is_editor(current):
    return any(n.get("resource-id", "").endswith(":id/layout_editor") for n in current.iter("node"))


def wait_editor():
    for _ in range(8):
        current = tree()
        if is_editor(current):
            return current
        # Allow the system's explicit permission step, if displayed. This is a
        # disposable emulator; it never grants Samsung access on a user's watch.
        allow = next((n for n in current.iter("node") if n.get("text", "").lower() in
                      ("allow", "allow all the time", "while using the app")), None)
        if allow is not None:
            click(allow)
        time.sleep(2)
    raise RuntimeError("Native editor did not return after selection")


def ensure_face():
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    for _ in range(5):
        time.sleep(2)
        path = OUT / "current-face.png"
        path.write_bytes(adb("exec-out", "screencap", "-p"))
        if subprocess.run(["python3", "tools/check_capture.py", str(path)], capture_output=True).returncode == 0:
            return
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
    raise RuntimeError("Could not confirm face before opening editor")


def open_editor(name):
    ensure_face()
    adb("shell", "input", "swipe", str(WIDTH // 2), str(HEIGHT // 2),
        str(WIDTH // 2), str(HEIGHT // 2), "1200")
    time.sleep(3)
    current = capture(name + "-entry")
    # WFF wallpaper dumps often identify only the delegating system runtime.
    # Confirm the selected face by its distinct, centered picker title instead.
    selected = [n for n in current.iter("node") if label(n) == "Ultra Forecast"
                and len(bounds(n)) == 4 and bounds(n)[0] < WIDTH / 2 < bounds(n)[2]]
    if not selected:
        raise RuntimeError("Centered picker item is not Ultra Forecast")
    edit = next((n for n in current.iter("node") if re.search(
        r"edit|customi[sz]e", label(n) + " " + n.get("resource-id", ""), re.I)), None)
    if edit is None:
        raise RuntimeError("No native Edit control found")
    click(edit)
    wait_editor()
    return capture(name + "-slots")


def provider_match(current, wanted, category, in_category=False):
    """Match a source within its own app, never another app's same-name source."""
    for node in current.iter("node"):
        b = bounds(node)
        if len(b) != 4 or b[3] - b[1] < 18:
            continue
        if not category or in_category:
            if label(node).casefold() == wanted.casefold():
                return node
        elif node.get("clickable") == "true":
            # Flat pickers expose both the combined accessible label and the
            # source/app children. Require the two names on the same row.
            if label(node).casefold() == f"{wanted}, {category}".casefold():
                return node
            descendants = list(node.iter("node"))
            primary = any(n.get("resource-id", "").endswith("wear_chip_primary_text")
                          and label(n).casefold() == wanted.casefold() for n in descendants)
            secondary = any(n.get("resource-id", "").endswith("wear_chip_secondary_text")
                            and label(n).casefold() == category.casefold() for n in descendants)
            if primary and secondary:
                return node
    return None


def select_provider(wanted, prefix, category=None):
    previous = None
    in_category = False
    for page in range(20):
        current = capture(f"{prefix}-page-{page:02}")
        nodes = list(current.iter("node"))
        match = provider_match(current, wanted, category, in_category)
        if match is not None:
            click(match)
            wait_editor()
            capture(prefix + "-selected")
            return
        # Some system versions group sources under their application name.
        group = next((n for n in nodes if category and not in_category
                      and label(n).casefold() == category.casefold()
                      and not n.get("resource-id", "").endswith("wear_chip_secondary_text")), None)
        if group is not None:
            click(group)
            in_category = True
            previous = None
            continue
        visible = [(label(n), n.get("bounds")) for n in nodes if label(n)]
        if visible == previous:
            break
        previous = visible
        adb("shell", "input", "swipe", str(WIDTH // 2), str(round(HEIGHT * .78)),
            str(WIDTH // 2), str(round(HEIGHT * .25)), "500")
        time.sleep(2)
    raise RuntimeError(f"Provider {wanted!r} was not found in the native rectangle picker")


def leave_editor():
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    ensure_face()


def top_activity():
    activity = adb("shell", "dumpsys", "activity", "activities").decode()
    return "\n".join(line for line in activity.splitlines() if
                     "mResumedActivity" in line or "topResumedActivity" in line)


def verify_taps(prefix, expected):
    for point, x in (("left", 100), ("middle", 225), ("right", 350)):
        ensure_face()
        tap(x * WIDTH / 450, RECTANGLE_CENTER[1] * HEIGHT / 450)
        capture(prefix + "-tap-" + point)
        resumed = top_activity()
        if not expected(resumed):
            raise RuntimeError(f"{prefix} {point} tap opened unexpected activity: {resumed}")
        RESULT["checks"].append({"tap": prefix + "-" + point, "resumed_activity": resumed})


def open_panel_menu(prefix):
    # Start at setup deliberately. A normal launcher-style resume may correctly
    # return to the still-open panel menu, especially after untappable None.
    adb("shell", "am", "start", "-f", "0x14000000", "-n", HOST + "/.SetupActivity")
    time.sleep(3)
    current = capture(prefix + "-setup")
    button = next((n for n in current.iter("node") if n.get("text") == "Bottom panel"), None)
    if button is None:
        raise RuntimeError("Setup does not expose the Bottom panel button")
    click(button)
    current = capture(prefix + "-menu")
    if "BottomPanelActivity" not in top_activity():
        raise RuntimeError("Bottom panel button did not open curated menu")
    return current


def find_chart(wanted, prefix, require_checked=False):
    for page in range(6):
        current = capture(f"{prefix}-{page}")
        node = next((n for n in current.iter("node") if n.get("text") == wanted
                     and n.get("class") == "android.widget.RadioButton"), None)
        if node is not None:
            if require_checked and node.get("checked") != "true":
                raise RuntimeError(wanted + " did not remain selected")
            return node
        adb("shell", "input", "swipe", str(WIDTH // 2), str(round(HEIGHT * .78)),
            str(WIDTH // 2), str(round(HEIGHT * .3)), "400")
        time.sleep(1)
    raise RuntimeError("Curated choice not found: " + wanted)


def select_chart(wanted, prefix):
    click(find_chart(wanted, prefix))
    find_chart(wanted, prefix + "-selected", require_checked=True)
    time.sleep(5)


def panel_pixels(prefix, empty=False):
    # Stay within the panel, clear of the rim, clock and charging overlay.
    shot = Image.open(OUT / (prefix + "-active.png")).convert("RGB")
    crop = shot.crop(tuple(round(v * (WIDTH if i % 2 == 0 else HEIGHT) / 450)
                           for i, v in enumerate((99, 316, 351, 397))))
    foreground = 0
    for y in range(crop.height):
        row = [crop.getpixel((x, y)) for x in range(crop.width)]
        background = [statistics.median(p[c] for p in row) for c in range(3)]
        foreground += sum(max(abs(p[c] - background[c]) for c in range(3)) > 8 for p in row)
    if empty and foreground > crop.width * crop.height * .001:
        raise RuntimeError("None still has visible panel content")
    if not empty and foreground < 100:
        raise RuntimeError(prefix + " has no visible panel content")
    RESULT["checks"].append({"panel_pixels": prefix, "foreground_pixels": foreground})
    crop.save(OUT / (prefix + "-panel-crop.png"))
    return crop


def main():
    global WIDTH, HEIGHT
    OUT.mkdir(parents=True, exist_ok=True)
    WIDTH, HEIGHT = Image.open(OUT.parent / "active.png").size
    try:
        wallpaper = adb("shell", "dumpsys", "wallpaper").decode()
        (OUT / "wallpaper-before.txt").write_text(wallpaper)
        (OUT / "installed-face.txt").write_bytes(adb("shell", "pm", "path", FACE))
        adb("shell", "settings", "put", "system", "screen_off_timeout", "1800000")
        providers = adb("shell", "cmd", "package", "query-services", "--query-flags", "128", "-a",
                        "android.support.wearable.complications.ACTION_COMPLICATION_UPDATE_REQUEST", "-p", HOST)
        (OUT / "registered-providers.txt").write_bytes(providers)
        if b"SamsungForecastService" not in providers:
            raise RuntimeError("Forecast source not discoverable through standard complication action")
        current = open_editor("curated")
        slot_nodes = [n for n in current.iter("node") if n.get("clickable") == "true"
                      and n.get("content-desc") and not n.get("resource-id")]
        if len(slot_nodes) != 6:
            raise RuntimeError(f"Expected six editable slots, found {len(slot_nodes)}")
        RESULT["checks"].append({"editable_slots": [label(n) for n in slot_nodes]})
        tap(RECTANGLE_CENTER[0] * WIDTH / 450, RECTANGLE_CENTER[1] * HEIGHT / 450)
        capture("bottom-is-fixed")
        if "ProviderChooserActivity" in top_activity():
            raise RuntimeError("Bottom panel still opens the unrestricted provider picker")
        tap(225 * WIDTH / 450, 425 * HEIGHT / 450)
        shortcut_tree = capture("shortcut-chooser")
        if "ProviderChooserActivity" not in top_activity():
            raise RuntimeError("Shortcut did not open the native chooser")
        if not any("app shortcut" in label(n).casefold() for n in shortcut_tree.iter("node")):
            raise RuntimeError("Shortcut lost the system App shortcut source")
        select_provider("Empty", "shortcut-empty")
        leave_editor()
        rendered_panels = []
        for wanted in ["Temperature trend", "Chance of rain", "None", "Weather"]:
            prefix = wanted.lower().replace(" ", "-")
            open_panel_menu(prefix)
            select_chart(wanted, prefix)
            # Kill/reopen the app to verify durable persistence, not only a selected radio button.
            adb("shell", "am", "force-stop", HOST)
            open_panel_menu(prefix + "-reopened")
            find_chart(wanted, prefix + "-persisted", require_checked=True)
            leave_editor()
            time.sleep(8)
            capture(prefix + "-active")
            crop = panel_pixels(prefix, empty=wanted == "None")
            if wanted != "None":
                if any(ImageChops.difference(crop, previous).getbbox() is None for previous in rendered_panels):
                    raise RuntimeError("Different panel choices produced the same image")
                rendered_panels.append(crop)
            if wanted == "None":
                before = top_activity()
                verify_taps(prefix, lambda resumed: resumed == before)
            else:
                verify_taps(prefix, lambda resumed: HOST + "/.SetupActivity" in resumed
                            or HOST + "/" + HOST + ".SetupActivity" in resumed)
            RESULT["checks"].append({"panel": wanted, "selection_persisted": True,
                                     "tap": "none" if wanted == "None" else "setup_without_samsung"})
        leave_editor()
        RESULT["passed"] = True
    except Exception as error:
        RESULT["error"] = str(error)
        try:
            capture("failure")
        except Exception:
            pass
        raise
    finally:
        (OUT / "results.json").write_text(json.dumps(RESULT, indent=2) + "\n")
        adb("shell", "input", "keyevent", "KEYCODE_HOME")


if __name__ == "__main__":
    main()
