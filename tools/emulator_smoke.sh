#!/usr/bin/env bash
# Run against a freshly booting, disposable Wear OS emulator.
set -euo pipefail
cd "$(dirname "$0")/.."
report=build/emulator
mkdir -p "$report"
apk="${APK:-app/build/outputs/apk/debug/app-debug.apk}"
pkg=com.example.ultrainfoboard
booted=false
for attempt in $(seq 1 120); do
    if [[ -n "${EMULATOR_PID:-}" ]] && ! kill -0 "$EMULATOR_PID" 2>/dev/null; then
        cat "$report/emulator.log" >&2
        exit 1
    fi
    if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then
        booted=true
        break
    fi
    sleep 5
done
if [[ "$booted" != true ]]; then
    adb devices > "$report/devices.txt" || true
    echo 'Wear OS did not finish booting within 10 minutes.' >&2
    exit 1
fi
adb shell getprop > "$report/device-properties.txt"
sleep 30 # Wear services and the initial favorites catalogue initialize after Android boot.
adb logcat -c
adb shell settings put global device_provisioned 1
adb shell settings put secure user_setup_complete 1
adb shell settings put system screen_off_timeout 1800000
adb shell svc power stayon true
adb shell input keyevent KEYCODE_WAKEUP
adb shell dumpsys battery unplug
adb install -r "$apk"
sleep 10
adb shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
    --es operation set-watchface --es watchFaceId "$pkg" > "$report/activation.txt"
sleep 20
adb shell input keyevent KEYCODE_HOME
rendered=false
for attempt in $(seq 1 6); do
    adb shell input keyevent KEYCODE_WAKEUP
    adb exec-out screencap -p > "$report/active.png"
    if python3 tools/check_capture.py "$report/active.png"; then
        rendered=true
        break
    fi
    adb shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
        --es operation set-watchface --es watchFaceId "$pkg" >> "$report/activation.txt"
    sleep 10
done
adb shell dumpsys wallpaper > "$report/wallpaper.txt"
adb shell dumpsys activity activities > "$report/activities.txt"
adb logcat -d > "$report/logcat.txt"
if [[ "$rendered" != true ]]; then
    echo 'The installed face did not render its expected blue background.' >&2
    exit 1
fi
if grep -E 'DWF:.*(failed to parse UserStyleSetting|Cannot parse theme color)' "$report/logcat.txt"; then
    echo 'Watch-face runtime rejected the theme.' >&2
    exit 1
fi
adb shell settings put system time_12_24 24
sleep 3
adb exec-out screencap -p > "$report/24-hour.png"
adb shell settings put system time_12_24 12
sleep 3
adb exec-out screencap -p > "$report/12-hour.png"
adb shell settings put global always_on_display_constants 'enabled=true'
adb shell settings put secure doze_enabled 1
adb shell svc power stayon false
adb shell settings put system screen_off_timeout 5000
sleep 20
adb shell dumpsys display > "$report/display-after-idle.txt"
adb exec-out screencap -p > "$report/after-idle.png"
python3 tools/check_ambient_capture.py "$report/after-idle.png" "$report/display-after-idle.txt" > "$report/ambient-pixels.json"
python3 tools/capture_editor.py
adb logcat -d > "$report/logcat.txt"
# Installation is asserted; activation, visuals and ambient state need review of
# these artifacts. Never report an after-idle image as ambient without DOZE evidence.
adb shell pm path "$pkg" | grep -q 'package:'
echo 'APK installed and blue face rendered; review exported captures and ambient state.'
