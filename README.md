# Ultra Info Board

A resource-only Galaxy Watch / Wear OS face with a blue gradient, large stacked time, native weather, and six editable complication areas. Based on the supplied layout references; the artwork and weather glyphs here are original.

**Development milestone, not a store release.** Requires Wear OS 5 (API 34) or later. The working package is `com.example.ultrainfoboard`; choose the permanent publisher/package identity before the first store upload.

## Layout

- Month and day/date above large hours/minutes; seconds in interactive mode.
- Three staggered circles on the right: heart rate, steps, sunrise/sunset by default.
- Left edge defaults to battery; right edge and bottom shortcut start unassigned.
- Current weather and forecasts for +2, +4, +6, +8 hours, with icons, temperatures and local times.
- Black always-on display with thin time and date; all other content is hidden.

Long-press the face and choose **Customize** to assign each slot. Providers available on a particular watch determine which data/apps can be selected. Samsung activity, stress, media and Gemini are not bundled or guaranteed providers. A `+` marks an unassigned area; assign it through the editor. Weather and health readings are never hard-coded; unavailable readings remain empty or show a dash. The face uses the system's weather data and temperature unit and follows 12/24-hour time preferences.

## Build and install

Install JDK 17, Android SDK command-line tools, platform 35 and build-tools 35.0.0. Set `ANDROID_HOME` or create ignored `local.properties` with `sdk.dir=/your/android/sdk`.

```sh
sdkmanager 'platforms;android-35' 'build-tools;35.0.0' 'platform-tools'
./gradlew :app:assembleDebug :app:bundleRelease
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
  --es operation set-watchface --es watchFaceId com.example.ultrainfoboard
```

The debug APK is installable and signed with the development key. The release AAB is **unsigned**, for later release preparation. Both builds remove generated Android resource bytecode so no DEX is packaged. Do not enable resource shrinking: resources referenced in raw WFF XML must remain available.

## Edit and validate

`tools/generate_watchface.py` is the source of truth for the XML, geometry and five-color palette. It uses only Python's standard library. After editing:

```sh
python3 tools/generate_watchface.py
bash tools/validate.sh
```

Validation checks generated-file consistency, geometry/time regressions, Google's WFF 2 schema, Android lint/builds, code-free package contents and memory limits. Official validator downloads are SHA-256 checked; a changed upstream release requires a deliberate hash update. `WFF_TOOLS_DIR` can select an existing tools cache.

Weather icons are committed PNG resources. To redraw them, install Pillow and run `python3 tools/generate_weather_icons.py`. The app requires no Python runtime, API keys, server or companion app.

## CI and emulator checks

GitHub Actions uploads `watchface-build-and-reports` with APK, AAB and validation reports. Separate jobs attempt large round API 34 and small round API 35 (Wear OS 5.1 uses the `android-35-ext15` image) captures. Emulator artifacts contain installation/activation logs, 12/24-hour captures, and an after-idle capture. These require visual review: an after-idle capture is not proof of ambient mode without matching DOZE state.

See [validation evidence](docs/VALIDATION.md) and the [release checklist](docs/RELEASE.md) for completed checks and remaining work.
