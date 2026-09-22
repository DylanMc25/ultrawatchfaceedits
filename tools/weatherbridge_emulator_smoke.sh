#!/usr/bin/env bash
# Stock Wear OS verifies packaging and fallback behavior, not Samsung's weather permission.
set -euo pipefail
cd "$(dirname "$0")/.."
report=build/forecast-emulator
mkdir -p "$report"
pkg=com.example.ultrainfoboard.bridge
face="$pkg.watchfacepush.board"
apk="${APK:-weatherbridge/build/outputs/apk/debug/weatherbridge-debug.apk}"
tests="${TEST_APK:-weatherbridge/build/outputs/apk/androidTest/debug/weatherbridge-debug-androidTest.apk}"
trap 'adb logcat -d > "$report/logcat.txt" 2>/dev/null || true' EXIT
booted=false
for attempt in $(seq 1 120); do
    if [[ -n "${EMULATOR_PID:-}" ]] && ! kill -0 "$EMULATOR_PID" 2>/dev/null; then exit 1; fi
    if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then
        booted=true
        break
    fi
    sleep 5
done
[[ "$booted" == true ]]
adb shell getprop > "$report/device-properties.txt"
sleep 30
adb logcat -c
adb shell settings put global device_provisioned 1
adb shell settings put secure user_setup_complete 1
adb shell settings put system screen_off_timeout 1800000
adb shell svc power stayon true
adb shell input keyevent KEYCODE_WAKEUP
adb install -r "$apk"
sleep 15
adb shell pm path "$face" > "$report/default-face-before-launch.txt" || true
adb install -r -t "$tests"
adb shell am instrument -w "$pkg.test/androidx.test.runner.AndroidJUnitRunner" | tee "$report/instrumentation.txt"
grep -q 'OK (' "$report/instrumentation.txt"
! grep -qE 'FAILURES|INSTRUMENTATION_FAILED|Process crashed' "$report/instrumentation.txt"
adb exec-out run-as "$pkg" tar -cf - files/render-fixtures > "$report/fixtures.tar"
tar -xf "$report/fixtures.tar" -C "$report"
adb shell am start -n "$pkg/.SetupActivity" > "$report/setup-launch.txt"
sleep 10
adb exec-out screencap -p > "$report/setup-samsung-unavailable.png"
installed=false
for attempt in $(seq 1 12); do
    if adb shell pm path "$face" | grep -q 'package:'; then installed=true; break; fi
    sleep 5
done
[[ "$installed" == true ]]
adb shell pm path "$face" > "$report/installed-face.txt"
adb shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
    --es operation set-watchface --es watchFaceId "$face" > "$report/activation.txt"
sleep 15
adb shell input keyevent KEYCODE_BACK
adb shell input keyevent KEYCODE_BACK
sleep 3
adb exec-out screencap -p > "$report/active.png"
adb shell dumpsys wallpaper > "$report/wallpaper.txt"
python3 tools/check_capture.py "$report/active.png"
adb shell settings put global always_on_display_constants 'enabled=true'
adb shell settings put secure doze_enabled 1
adb shell svc power stayon false
adb shell dumpsys battery unplug
adb shell settings put system screen_off_timeout 5000
sleep 25
adb shell dumpsys display > "$report/display-after-idle.txt"
adb exec-out screencap -p > "$report/after-idle.png"
python3 tools/check_ambient_capture.py "$report/after-idle.png" "$report/display-after-idle.txt" > "$report/ambient-pixels.json"
printf '%s\n' 'Stock emulator: installed bundled face and ran rendering/fallback tests. Samsung data access remains unverified.' > "$report/result.txt"
