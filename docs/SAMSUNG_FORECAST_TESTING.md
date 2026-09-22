# Samsung forecast integration preview

This preview reads Samsung Weather's saved forecast through its existing user-granted weather permission. It does not contact a replacement weather service, copy Samsung artwork, or modify Samsung's apps. On 2026-09-21 (user's local date), the user installed the CI preview on the API 36 Galaxy Watch and reported that its forecast appeared correct. They then confirmed the forecast appears correctly in the face's rectangle and tapping it opens Samsung Weather. They subsequently reported that it still was not selectable like a normal complication. Data/display/tap checks succeeded; the customization requirement remains unresolved on Samsung hardware. Physical testing is paused at the user's request for the night; no additional watch access is needed for the unattended work below.

## Install one APK on Wear OS 6

Download `weatherbridge-debug.apk` from the **samsung-forecast-preview** artifact in the **Samsung forecast preview** GitHub workflow. The APK contains the weather setup app, a normal selectable forecast complication, and a separately signed/validated WFF face. Do not install the `androidTest` APK or the AAB on your watch.

With the watch already connected in PowerShell:

```powershell
& $adb -s $watchAddress install -r "$env:USERPROFILE\Downloads\weatherbridge-debug.apk"
& $adb -s $watchAddress shell am start -n com.example.ultrainfoboard.bridge/.SetupActivity
```

The earlier `com.example.ultrainfoboard` face stays installed. The preview host is `com.example.ultrainfoboard.bridge`; its bundled face is `com.example.ultrainfoboard.bridge.watchfacepush.board`. These are separate installed packages behind the one downloaded APK. Old face settings are not automatically migrated to the new package.

On the watch:

1. In **Ultra Info Board Weather**, tap **Allow weather access** and respond to Samsung's system permission prompt.
2. Tap **Read saved forecast**. The app shows the selected city, current reading, four hourly entries and saved time. Everything stays on the watch; no coordinates or raw provider records are logged or uploaded.
3. Tap **Open Samsung Weather**. Compare the same location, units, current temperature, forecast hours and temperatures. Refresh Samsung Weather, then return and read again.
4. Select the newly bundled **Ultra Forecast** in the watch-face picker (preview version 10 onward). This distinct name separates it from the older **Ultra Info Board** face. If it is missing, return to the app and tap **Install or update watch face**. The bottom rectangle defaults to **Samsung hourly forecast**.
5. Tap the left, middle and right of the rectangle: each should open Samsung Weather after access is granted. When access is missing, the forecast provider opens its permission setup instead.
6. In Customize → Complications → Bottom rectangle, replace the rectangle with another installed compatible provider. Its own content and tap should take over. Restore **Samsung hourly forecast**, listed under **Ultra Info Board Weather** if the picker groups sources by app. Samsung's ordinary **Weather** source is a different provider and supplies current conditions, not this hourly image.

If the preview's signature conflicts with a previous build, uninstall **only the preview host and bundled face** before installing; doing so resets their settings. Do not uninstall Samsung Weather. GitHub builds cache preview signing keys to reduce these conflicts, but cache loss or switching between locally signed and CI builds can still change debug signatures. Production signing is a separate release requirement.

## Report these outcomes

| Check | Required evidence | Current status |
| --- | --- | --- |
| Permission | A normal system prompt grants weather access to the independently signed app | Physical app displays real data; exact prompt behavior was not separately reported |
| Data | Same Samsung selected city, unit, current value, four times and temperatures | User reports forecast appears correct; detailed field-by-field comparison pending |
| Native behavior | Hour rollover, midnight/noon, day/night conditions, favorite city/unit changes | Adapter fixture tests pass; physical comparison pending |
| Refresh | Samsung app refresh reaches the provider; measure delay with the face active | Pending; content notifications are not assumed reliable |
| Permission denied/revoked | Honest unavailable state, setup tap, no manufactured forecast | Missing-provider emulator test added; physical denial/revocation pending |
| Replaceability/taps | Another provider replaces the entire rectangle and its tap | Physical forecast display and Samsung Weather tap confirmed; user reports normal selection still does not work. API 36 small/large native-picker round trips pass in run 35677046105; Samsung customization unresolved |
| Install/update | One host install adds face; host update updates same face and keeps choices | Physical install and face selection work; exact automatic-vs-setup install path and upgrades not separately verified |
| Active/ambient | Forecast uses full rectangle; ambient retains black time/date only | API 36 active/ambient captures reviewed; approximately 4.8–4.9% lit in tested ambient captures. Physical readability pending |

Do not describe fixture images or stock-emulator results as Samsung integration. The `render-fixtures` PNGs intentionally identify their weather as test data. Stock Wear OS emulators do not contain the Samsung provider.

## Customization investigation

The bundled face declares slot 7 as customizable and supports `SMALL_IMAGE` along with text/progress/image alternatives. The forecast service declares the standard complication action, binding permission and `SMALL_IMAGE` type. Its data source is not hidden or restricted to our own face. The [public registration and selection rules](https://developer.android.com/training/wearables/complications/exposing-data) permit this combination; a source being assigned by default does not establish that it is discoverable in every OEM editor.

A targeted recheck of the supplied Samsung manifests found no additional public rectangle-selection flag to copy: ComplicationHelper does not declare ordinary complication-source services, while Ultra Info Board declares its own wallpaper/editor and only queries the ordinary complication action. Its source-configuration activities concern World Clock/Altimeter, not the hourly weather panel. These findings explain why Samsung's private editor configuration is not a registration recipe for our normal provider; they do not diagnose the user's exact picker failure.

Version 10 adds a service-specific white icon, distinct face name and exact picker guidance. These are identification improvements, not a proven remedy for the reported Samsung selection problem. Its package identity and all seven slot IDs remain unchanged. Reopening setup skips installation when the installed face is current, and refreshing weather does not assign a provider. Google's [Push update contract](https://developer.android.com/reference/androidx/wear/watchfacepush/WatchFacePushManager) preserves configuration for updates using the same face package; actual upgrade retention still needs testing.

The first naming attempt in version 9, **Ultra Info Board Forecast**, was visibly truncated to **Ultra Info Boa…** in the round picker, hiding its distinguishing suffix. Version 10 shortens the label to **Ultra Forecast**. This changes the display name, not the package or existing assignments.

`tools/test_forecast_editor.py` exercises the actual native editor on disposable API 36 emulators. It verifies the active pushed package, opens the rectangle's normal provider picker, selects Alarm, reopens the editor to check persistence, checks taps across the rectangle, opens setup and verifies Alarm remains selected, then finds and restores **Samsung hourly forecast** through the picker. With Samsung absent, the restored provider should open setup. Screenshots, UI trees, provider registration and activity evidence are retained, including on failure. This does not establish behavior in Samsung's watch or phone editors.

[Run 35677046105](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/35677046105), source `b864c30` / version 9, passes that entire sequence on both 384 px and 454 px emulators. Reviewed captures show **Samsung hourly forecast** under **Ultra Info Board Weather** in the ordinary provider list, Alarm occupying the rectangle after replacement, and the forecast restored. All three taps open the chosen provider's destination. Samsung's physical picker issue remains unresolved despite this stock-platform success.

The first API 36 CI attempts stalled with an unauthorized ADB connection before reaching installation. The test setup now provisions one consistent emulator/server key and fails with bounded diagnostics instead of hanging. Those earlier runs are not visual or editor validation.

## Build and verification

Use Java 17, Android SDK 36 and the repository Gradle wrapper:

```bash
python3 tools/prepare_push_bundle.py
./gradlew :weatherbridge:assembleDebug :weatherbridge:assembleDebugAndroidTest :weatherbridge:testDebugUnitTest :weatherbridge:lintDebug
```

Preparation must precede the host build: it creates the signed resource-only face, runs Google's official Push validator, and generates the exact asset/token pair. A failed preparation clears old generated bundle inputs. The original standalone face can still be built with `bash tools/validate.sh`.

The preview AAB produced by CI is an **unsigned host test bundle containing a debug-signed embedded face**. It is not ready for Play release. Production requires separate persistent host/face release keys, rebuilding and validating the release-signed face with `prepare_push_bundle.py --variant release`, and appropriate host signing. No signing key is committed or included in download artifacts.

## Behavior and remaining limits

The adapter follows the observed Samsung favorite-location key, Celsius storage and rounding, raw condition mapping, location timezone and four-hour selection. It retains Samsung's last-four-cached-entries fallback and adds a visible saved-data indication when expired. It honors the requested device 12/24-hour format. Icons are original drawings representing the same conditions, not extracted Samsung artwork.

The provider reads cached data on a 15-minute requested schedule; actual scheduling is controlled by Wear OS. It observes Samsung changes where delivered, and provides bounded future timeline images for hour/expiry changes without another query. After the timeline ends without a successful refresh, it shows unavailable instead of silently restoring an old fresh forecast. It does not force Samsung to fetch data. Instant notification delivery, watch battery cost, exact rendering and the OEM permission's behavior remain physical-test questions.

The permission-based interface was observed in the supplied WeatherWatch APK, not a published stable Samsung SDK. Commercial support and behavior after Samsung updates remain unresolved release questions. [Contract evidence](SAMSUNG_WEATHER_CONTRACT.md), [packaging evidence](WATCH_FACE_PUSH_PLAN.md), and [full investigation](SAMSUNG_APK_FINDINGS.md) distinguish verified code observations from runtime assumptions.
