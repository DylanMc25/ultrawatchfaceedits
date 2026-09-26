# Ultra Info Board

A Galaxy Watch face with a blue gradient, large stacked time, six editable complications and a curated bottom chart panel. The new **Wear OS 6 Samsung forecast preview** bundles the resource-only face, permission setup and a Samsung-source weather and chart provider in one APK.

**Start with the [Samsung forecast installation and comparison guide](docs/SAMSUNG_FORECAST_TESTING.md).** Download `weatherbridge-debug.apk` from the `samsung-forecast-preview` artifact in [this workflow](https://github.com/DylanMc25/ultrawatchfaceedits/actions/workflows/samsung-weather.yml), checking the source version before installation. The user confirmed the forecast appears in the face and tapping opens Samsung Weather; the new chart menu still needs a physical Samsung check. The bundled face is **Ultra Forecast**. This is a development preview, not a store release.

The current layout is standalone `:app` version **0.1.9 / 10** and Samsung forecast preview **0.2.0-preview.7 / 14**. The original standalone face remains available on Wear OS 5+ as `com.example.ultrainfoboard`; the bundled preview requires Wear OS 6. Version 14 keeps the version 13 layout and replaces the bottom provider picker with four chart choices in the watch app: Weather, Temperature trend, Chance of rain, and None. Local builds, format/memory validation and tests pass; native emulator checks for this revision are pending. Final branding, package identity and release signing remain release prerequisites.

![Illustrative provider layout](docs/previews/active-illustrative.png)

*Illustrative layout with explicit sample data, not an emulator capture. Native captures and their tested versions are recorded in [validation evidence](docs/VALIDATION.md).*

## Layout

- Month and day/date form a centered two-line header above stacked hours/minutes, with a tighter gap between the date lines. The time and circles sit eight units higher to fill the upper section. Active month/date text is bold, 24/21 units and hours/minutes are 134/130 units; seconds retain a separate column.
- Three staggered circles on the right: heart rate, steps and sunrise/sunset. Diameters are 96/96/96 units, with main readings up to 46 units and smaller sizes for longer values.
- Longer edges: an 18-segment battery gauge on the left and a 40-degree arc on the right, with inset icons and angled labels. The bottom shortcut accepts only `SMALL_IMAGE` or Empty to reduce picker choices. Right edge and shortcut start unassigned.
- One transparent **Bottom panel**, 262 × 94 units. In **Ultra Info Board Weather → Bottom panel**, choose Weather, Temperature trend, Chance of rain, or None. The Wear OS 6 face fixes this area to our provider; it no longer opens the general app picker. The legacy standalone face retains its editable rectangle.
- Black always-on display with thin time and date; all complications are hidden.

Open **Ultra Info Board Weather** on the watch and tap **Bottom panel**. The choice saves automatically and applies to the bundled **Ultra Forecast** face. Weather shows the current conditions and four hourly forecasts. Temperature trend draws their temperatures; Chance of rain draws Samsung's hourly precipitation probabilities on a 0–100% scale. Missing values remain unavailable. All three panels open Samsung Weather, or permission setup when access is missing. None leaves the panel blank with no action. The other six areas remain editable through **Customize → Complications**.

Version 14 retires editable slot 7 and uses fixed slot 8, preventing an old third-party rectangle assignment from carrying over into the curated panel. IDs 1–6 and their geometry remain unchanged. Updates default to Weather until a chart is chosen in the app. The chart choice applies to this app's bundled face instances on the watch. The legacy standalone app and its seven-slot picker remain separate.

The [WFS investigation](docs/WFS_PICKER_FINDINGS.md) explains why this uses our own menu: format filtering cannot restrict the ordinary picker to named chart apps. Version 14 implements the user's subsequent request for a curated chart menu. It does not provide arbitrary third-party providers in the bottom panel.

**Historical update from 0.1.5 to 0.1.6:** the fixed Bottom panel menu became standard editable slot 7, preserving IDs 1–6 and their geometry at that time. The old menu choice does not map to a provider assignment. Version 0.1.7 changes the layout described above. The standalone face uses normal providers; the Wear OS 6 preview additionally uses Samsung's observed permission-protected cache interface.

The historical 0.1.5 test reported `Weather —` while its tap correctly opened Samsung Weather with location and forecast data. The standalone face switched to provider data in 0.1.6; its integration remains separate from the physically confirmed Wear OS 6 preview. See [research and compatibility](docs/SAMSUNG_WEATHER.md).

**Samsung forecast preview:** the Wear OS 6 app bundles the face and an hourly forecast complication that reads Samsung Weather's cache with the user's permission. It follows Samsung's saved location, units and hourly selection, and opens Samsung Weather when tapped. [Install and test the preview](docs/SAMSUNG_FORECAST_TESTING.md). Physical forecast display/tap succeeded on an earlier build; the version 14 chart menu, precipitation values, detailed data comparison and physical readability remain unverified. The original `:app` build remains available alongside `:weatherbridge` / `:pushface`.

## Build and install

Install JDK 17, Python 3 and Node.js 22 (for fixture checks), Android SDK command-line tools, platform 35 and build-tools 35.0.0. Set `ANDROID_HOME` or create ignored `local.properties` with `sdk.dir=/your/android/sdk`.

```sh
sdkmanager 'platforms;android-35' 'build-tools;35.0.0' 'platform-tools'
./gradlew :app:assembleDebug :app:bundleRelease
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
  --es operation set-watchface --es watchFaceId com.example.ultrainfoboard
```

The debug APK is installable and signed with the development key. The release AAB is **unsigned**, for later release preparation. Both builds remove generated Android resource bytecode so no DEX is packaged. Do not enable resource shrinking: resources referenced in raw WFF XML must remain available.

The standalone CI build uses temporary debug keys. The Wear OS 6 preview now explicitly caches and checks its signing identity to avoid repeated reinstalls and permission resets; see [preview update guidance](docs/SAMSUNG_FORECAST_TESTING.md#keeping-weather-permission-across-updates). Production signing remains a release prerequisite.

### Test a downloaded APK in Android Studio on Windows

1. In Android Studio's **Device Manager**, create and start a round Wear OS API 34 or API 35 virtual device.
2. Open the latest successful [GitHub Actions run](https://github.com/DylanMc25/ultrawatchfaceedits/actions/workflows/watchface.yml?query=branch%3Acodex%2Fwatchface-redesign) and download **watchface-build-and-reports** under **Artifacts**. Extract the ZIP and locate `app-debug.apk`.
3. Drag the APK onto the running emulator. This package is a watch face, so it has no normal app launch screen.
4. Long-press the current watch face, add **Ultra Info Board**, and select it. Long-press again and choose **Customize** or **Edit** to assign complications.

If installation reports mismatched signatures, run this in PowerShell while only one emulator is running, then drag the new APK onto it again:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" -e uninstall com.example.ultrainfoboard
```

Expect `Success`. Uninstalling resets this face's saved complication choices. The full path avoids the `adb is not recognized` error; if your SDK is elsewhere, use its location from Android Studio's SDK Manager.

For a physical Galaxy Watch, enable developer options and wireless debugging, then use `adb pair WATCH_IP:PAIRING_PORT` and `adb connect WATCH_IP:DEBUG_PORT` with the addresses shown on the watch. After standalone installation, open the watch-face picker and add **Ultra Info Board**. The debug selection broadcast above is used by the emulator tests; use the picker if the watch does not honor it. For the hourly preview, follow the [Samsung forecast guide](docs/SAMSUNG_FORECAST_TESTING.md) and select **Ultra Forecast**. The current layouts still need physical review.

## Edit and validate

`tools/generate_watchface.py` is the source of truth for the XML, geometry and five-color palette. It uses only Python's standard library. After editing:

```sh
python3 tools/generate_watchface.py
bash tools/validate.sh
```

Validation checks generated-file consistency, geometry/complication regressions, Google's WFF 2 schema, Android lint/builds, code-free package contents and memory limits. Official validator downloads are SHA-256 checked; a changed upstream release requires a deliberate hash update. `WFF_TOOLS_DIR` can select an existing tools cache.

Provider icons come from the selected complications. The app requires no Python runtime, API keys, server or companion app.

## CI and emulator checks

GitHub Actions uploads `watchface-build-and-reports` with APK, AAB and validation reports. Separate jobs install and render on large round API 34 and small round API 35 (Wear OS 5.1 uses the `android-35-ext15` image). Emulator artifacts contain installation/activation logs, 12/24-hour captures, ambient captures with DOZE/illumination checks, and editor/provider interaction diagnostics. These require visual review: a successful install alone is not visual validation, and editor automation records inconclusive results explicitly.

See [validation evidence](docs/VALIDATION.md) and the [release checklist](docs/RELEASE.md) for completed checks and remaining work.
