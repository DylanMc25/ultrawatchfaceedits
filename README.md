# Ultra Info Board

A Galaxy Watch face with a blue gradient, large stacked time and seven editable complication areas. The new **Wear OS 6 Samsung forecast preview** bundles the resource-only face, permission setup and an interchangeable hourly weather provider in one APK.

**Start with the [Samsung forecast installation and comparison guide](docs/SAMSUNG_FORECAST_TESTING.md).** Download `weatherbridge-debug.apk` from the `samsung-forecast-preview` artifact in [this workflow](https://github.com/DylanMc25/ultrawatchfaceedits/actions/workflows/samsung-weather.yml), checking the source version before installation. The user confirmed the forecast appears in the face and tapping opens Samsung Weather; the narrowed picker still needs a physical Samsung check. The bundled face is **Ultra Forecast**. This is a development preview, not a store release.

The current layout is standalone `:app` version **0.1.7 / 8** and Samsung forecast preview **0.2.0-preview.4 / 11**. The original standalone face remains available on Wear OS 5+ as `com.example.ultrainfoboard`; the bundled preview requires Wear OS 6. Version 11 keeps the familiar staggered layout, reduces the date/time slightly and enlarges complication readings and the forecast. The current layout passed native checks on small/large API 36 and standalone API 34/35; physical readability and upgrade retention still need review. Final branding, package identity and release signing remain release prerequisites.

![Illustrative provider layout](docs/previews/active-illustrative.png)

*Illustrative layout with explicit sample data, not an emulator capture. Native captures and their tested versions are recorded in [validation evidence](docs/VALIDATION.md).*

## Layout

- Month and day/date remain on two lines above stacked hours/minutes. Month/date type is 24/21 units and time is 134 units; seconds retain a separate column.
- Three staggered circles on the right: heart rate, steps and sunrise/sunset. Diameters are 96/94/96 units, with main readings up to 46 units and smaller sizes for longer values.
- Segmented left battery gauge, thick right-edge arc, provider icons and angled edge labels. Right edge and bottom shortcut start unassigned.
- One transparent **Bottom rectangle**, 262 × 94 units, for compatible installed apps' `LONG_TEXT` and `SMALL_IMAGE` complications, or Empty. Wear OS determines which installed sources support those types; there is no app whitelist.
- Black always-on display with thin time and date; all complications are hidden.

Long-press the face and choose **Customize → Complications → Bottom rectangle** (or tap the rectangle in the editor). Choose an installed provider, such as Weather, calendar or a compatible image/chart provider. The provider owns the data, units and whole-area tap action. Time follows the device's 12/24-hour preference. A `+` marks an empty slot; missing text is a dash.

In the standalone face, Samsung's **public Weather complication** is the preferred default when installed and eligible; otherwise the rectangle starts empty. It supplies current conditions, **not Info Brick's hourly forecast**. In the Wear OS 6 preview, **Weather** under **Ultra Info Board Weather** is our Samsung-source hourly provider and is the default. An eligible image provider can supply its own chart; the face does not manufacture forecasts or history.

All seven slot IDs stay stable in this update. The narrower rectangle type list removes short-text, progress and icon-only choices from its menu. A previously assigned source that only supports a removed type may need to be selected again or replaced; migration and saved-assignment retention have not been verified. The other six slots retain normal complication selection.

**Historical update from 0.1.5 to 0.1.6:** the fixed Bottom panel menu became standard editable slot 7, preserving IDs 1–6 and their geometry at that time. The old menu choice does not map to a provider assignment. Version 0.1.7 changes the layout described above. The standalone face uses normal providers; the Wear OS 6 preview additionally uses Samsung's observed permission-protected cache interface.

The historical 0.1.5 test reported `Weather —` while its tap correctly opened Samsung Weather with location and forecast data. The standalone face switched to provider data in 0.1.6; its integration remains separate from the physically confirmed Wear OS 6 preview. See [research and compatibility](docs/SAMSUNG_WEATHER.md).

**Samsung forecast preview:** the Wear OS 6 app bundles the face and an hourly forecast complication that reads Samsung Weather's cache with the user's permission. It follows Samsung's saved location, units and hourly selection, and opens Samsung Weather when tapped. [Install and test the preview](docs/SAMSUNG_FORECAST_TESTING.md). Physical forecast display/tap succeeded on an earlier build; the version 11 Samsung picker, detailed data comparison and physical readability remain unverified. The original `:app` build remains available alongside `:weatherbridge` / `:pushface`.

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

CI runners generate temporary debug signing keys. If an update from a different runner fails with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, uninstall the earlier development build before installing the new one; this resets that build's watch-face settings. Stable release signing is a later milestone.

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
