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
adb logcat -c
adb shell settings put global device_provisioned 1
adb shell settings put secure user_setup_complete 1
adb shell settings put system screen_off_timeout 1800000
adb shell svc power stayon true
adb shell input keyevent KEYCODE_WAKEUP
adb install -r "$apk"
adb shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
    --es operation set-watchface --es watchFaceId "$pkg" > "$report/activation.txt"
sleep 15
adb shell dumpsys wallpaper > "$report/wallpaper.txt"
adb shell dumpsys activity activities > "$report/activities.txt"
adb logcat -d > "$report/logcat.txt"
# Export captures for visual review; the image alone is not a rendering assertion.
adb exec-out screencap -p > "$report/active.png"
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
adb logcat -d > "$report/logcat.txt"
# Installation is asserted; activation, visuals and ambient state need review of
# these artifacts. Never report an after-idle image as ambient without DOZE evidence.
adb shell pm path "$pkg" | grep -q 'package:'
echo 'APK installed; emulator captures and logs exported. Review activation and images.'
