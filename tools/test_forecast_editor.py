#!/usr/bin/env python3
"""Exercise the real Wear OS picker, replacement, persistence and provider taps.

Run only on a disposable stock emulator with the bundled forecast face active.
A synthetic chart provider lives only in a separately installed test-only app.
No synthetic Samsung provider or weather readings are installed. Screenshots and
UI trees are retained on failure so an automation failure is not reported as a
successful selection test.
"""
import json
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from PIL import Image


OUT = Path("build/forecast-emulator/editor")
HOST = "com.example.ultrainfoboard.bridge"
FACE = HOST + ".watchfacepush.board"
CHART_ACTIVITY = "com.example.ultrainfoboard.panelfixture/" + HOST + ".ChartTestActivity"
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


def open_rectangle(name):
    wait_editor()
    tap(RECTANGLE_CENTER[0] * WIDTH / 450, RECTANGLE_CENTER[1] * HEIGHT / 450)
    current = capture(name)
    if "ProviderChooserActivity" not in top_activity():
        raise RuntimeError("Rectangle did not open the normal provider chooser")
    return current


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


def rectangle_label(current):
    x, y = RECTANGLE_CENTER[0] * WIDTH / 450, RECTANGLE_CENTER[1] * HEIGHT / 450
    found = []
    for node in current.iter("node"):
        b = bounds(node)
        if len(b) == 4 and b[0] <= x <= b[2] and b[1] <= y <= b[3] and label(node):
            found.append(((b[2] - b[0]) * (b[3] - b[1]), label(node)))
    return min(found)[1] if found else ""


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
        open_editor("replace")
        tap(225 * WIDTH / 450, 425 * HEIGHT / 450)
        capture("shortcut-chooser")
        if "ProviderChooserActivity" not in top_activity():
            raise RuntimeError("Shortcut did not open the native chooser")
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        wait_editor()
        open_rectangle("replace-chooser")
        # A separate app proves SMALL_IMAGE remains replaceable through the native picker.
        select_provider("Test chart", "chart", "Panel test")
        leave_editor()
        capture("chart-active")
        # Reopening proves it was saved, not only highlighted in the chooser.
        current = open_editor("chart-persisted")
        if rectangle_label(current).casefold() != "test chart":
            raise RuntimeError("Chart assignment did not persist in the rectangle")
        RESULT["checks"].append({"replacement_persisted": rectangle_label(current)})
        leave_editor()
        verify_taps("chart", lambda resumed: CHART_ACTIVITY in resumed)
        adb("shell", "am", "start", "-n", HOST + "/.SetupActivity")
        time.sleep(5)
        current = open_editor("chart-after-setup")
        if rectangle_label(current).casefold() != "test chart":
            raise RuntimeError("Opening setup replaced the saved Chart assignment")
        RESULT["checks"].append({"replacement_survives_setup": True})
        leave_editor()
        open_editor("restore")
        open_rectangle("restore-chooser")
        select_provider("Weather", "forecast", "Ultra Info Board Weather")
        leave_editor()
        capture("forecast-restored-active")
        current = open_editor("forecast-persisted")
        restored_label = rectangle_label(current)
        if restored_label.casefold() != "weather":
            raise RuntimeError("Forecast assignment did not persist in the rectangle: " + restored_label)
        leave_editor()
        # Without Samsung installed, the real provider's unavailable-state tap
        # opens our setup app. This confirms the provider was restored, not Weather integration.
        verify_taps("forecast", lambda resumed: HOST + "/.SetupActivity" in resumed
                    or HOST + "/" + HOST + ".SetupActivity" in resumed)
        RESULT["checks"].append({"restoration_persisted": restored_label})
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
