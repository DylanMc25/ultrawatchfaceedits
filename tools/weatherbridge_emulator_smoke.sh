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
forecast_adb="$(command -v adb)"
export ANDROID_SERIAL="${ANDROID_SERIAL:-emulator-5554}"
adb() { timeout 60s "$forecast_adb" "$@"; }
stage() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$1" | tee -a "$report/progress.txt"; }
collect_report() {
    local forecast_status=$?
    printf '%s\n' "$forecast_status" > "$report/smoke-exit-code.txt"
    timeout 5s "$forecast_adb" devices -l > "$report/adb-devices-last.txt" 2>&1 || true
    timeout 5s "$forecast_adb" get-state > "$report/adb-state-last.txt" 2>&1 || true
    if grep -qx device "$report/adb-state-last.txt"; then
        timeout 15s "$forecast_adb" logcat -d > "$report/logcat.txt" 2>/dev/null || true
    fi
}
trap collect_report EXIT
stage 'Waiting for Wear OS boot'
booted=false
boot_deadline=$((SECONDS + 600))
forecast_auth_deadline=$((SECONDS + 180))
forecast_next_report=0
while ((SECONDS < boot_deadline)); do
    if [[ -n "${EMULATOR_PID:-}" ]] && ! kill -0 "$EMULATOR_PID" 2>/dev/null; then exit 1; fi
    timeout 5s "$forecast_adb" get-state > "$report/adb-state-last.txt" 2>&1 || true
    if ((SECONDS >= forecast_next_report)); then
        timeout 5s "$forecast_adb" devices -l > "$report/adb-devices-last.txt" 2>&1 || true
        cat "$report/adb-devices-last.txt"
        forecast_next_report=$((SECONDS + 30))
    fi
    if ((SECONDS >= forecast_auth_deadline)) && grep -qw unauthorized "$report/adb-state-last.txt"; then
        stage 'ADB authorization failed after 180 seconds; installation tests were not reached'
        exit 1
    fi
    if grep -qx device "$report/adb-state-last.txt" && [[ "$(timeout 5s "$forecast_adb" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then
        booted=true
        break
    fi
    sleep 5
done
if [[ "$booted" != true ]]; then
    stage 'Wear OS did not finish booting within 600 seconds; installation tests were not reached'
    exit 1
fi
stage 'Wear OS booted'
adb shell getprop > "$report/device-properties.txt"
sleep 30
adb logcat -c
adb shell settings put global device_provisioned 1
adb shell settings put secure user_setup_complete 1
adb shell settings put system screen_off_timeout 1800000
adb shell svc power stayon true
adb shell input keyevent KEYCODE_WAKEUP
stage 'Installing host APK'
timeout 180s "$forecast_adb" install -r "$apk" | tee "$report/install.txt"
stage 'Host APK installed'
sleep 15
adb shell pm path "$face" > "$report/default-face-before-launch.txt" || true
timeout 180s "$forecast_adb" install -r -t "$tests"
stage 'Running Android rendering tests'
timeout 180s "$forecast_adb" shell am instrument -w "$pkg.test/androidx.test.runner.AndroidJUnitRunner" | tee "$report/instrumentation.txt"
grep -q 'OK (' "$report/instrumentation.txt"
! grep -qE 'FAILURES|INSTRUMENTATION_FAILED|Process crashed' "$report/instrumentation.txt"
adb exec-out run-as "$pkg" tar -cf - files/render-fixtures > "$report/fixtures.tar"
tar -xf "$report/fixtures.tar" -C "$report"
adb shell am start -n "$pkg/.SetupActivity" > "$report/setup-launch.txt"
stage 'Setup app started'
sleep 10
adb exec-out screencap -p > "$report/setup-samsung-unavailable.png"
installed=false
for attempt in $(seq 1 12); do
    if adb shell pm path "$face" | grep -q 'package:'; then installed=true; break; fi
    sleep 5
done
[[ "$installed" == true ]]
stage 'Bundled watch face found'
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
stage 'Testing native rectangle selection, replacement and restoration'
timeout 600s python3 tools/test_forecast_editor.py
stage 'Native rectangle replacement and restoration passed'
adb shell settings put global always_on_display_constants 'enabled=true'
adb shell settings put secure doze_enabled 1
adb shell svc power stayon false
adb shell dumpsys battery unplug
adb shell settings put system screen_off_timeout 5000
sleep 25
adb shell dumpsys display > "$report/display-after-idle.txt"
adb exec-out screencap -p > "$report/after-idle.png"
python3 tools/check_ambient_capture.py "$report/after-idle.png" "$report/display-after-idle.txt" > "$report/ambient-pixels.json"
printf '%s\n' 'Stock emulator: installed bundled face; rendering, unavailable data, native provider replacement/restoration and ambient checks passed. This run does not verify Samsung data or its OEM editor.' > "$report/result.txt"
