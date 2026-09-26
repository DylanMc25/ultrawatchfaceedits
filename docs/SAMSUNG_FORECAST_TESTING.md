# Samsung forecast integration preview

This preview reads Samsung Weather's saved forecast through its existing user-granted weather permission. It does not contact a replacement weather service, copy Samsung artwork, or modify Samsung's apps. On 2026-09-21 (user's local date), the user installed the CI preview on the API 36 Galaxy Watch and reported that its forecast appeared correct. They confirmed it appears in the face's rectangle and tapping opens Samsung Weather, then reported it still was not selectable like a normal complication. Data/display/tap checks succeeded on that earlier build; Samsung customization and the version 11 layout remain unverified.

## Install one APK on Wear OS 6

Download `weatherbridge-debug.apk` from the **samsung-forecast-preview** artifact in the **Samsung forecast preview** GitHub workflow. The APK contains the weather setup app, a normal selectable forecast complication, and a separately signed/validated WFF face. Do not install the `androidTest` APK or the AAB on your watch.

The current source is **0.2.0-preview.6 / version 13**. It keeps the familiar layout, gives the three 96-unit circles equal spacing, centers the two date lines together with a tighter line gap, and makes the active date bold. The time and circles sit eight units higher, retaining equal gaps. The 262 × 94 forecast panel is unchanged. Its standard picker now accepts only small-image panels or Empty, excluding generic long-text choices. The left edge has 18 ticks and the right arc spans 40 degrees. The bottom shortcut accepts small-image icons or Empty; its former text/monochrome-only assignments may need replacing. Circle and edge formats stay unchanged. Validation of this revision is recorded in [the validation log](VALIDATION.md); older runs are not evidence for this update.

For historical comparison, the reviewed version 10 build is [run 35677889561](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/35677889561), source `e9fe68d`. Its build/validation and both stock Wear OS 6 editor tests pass. Those results do not validate the new layout or narrowed provider menu.

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
4. Select **Ultra Forecast** in the watch-face picker. This distinct name separates it from the older **Ultra Info Board** face. If it is missing, return to the app and tap **Install or update watch face**. The bottom rectangle defaults to **Weather** from **Ultra Info Board Weather** in version 13; older previews call this source **Samsung hourly forecast**.
5. Tap the left, middle and right of the rectangle: each should open Samsung Weather after access is granted. When access is missing, the forecast provider opens its permission setup instead.
6. In Customize → Complications → Bottom rectangle, replace the rectangle with another installed small-image provider, such as a compatible chart source. Its content and tap should take over. Restore **Weather** under **Ultra Info Board Weather**. Samsung's own **Weather** entry is a different provider and supplies current conditions, not this hourly image. Wear OS determines which installed apps are eligible; the face does not whitelist providers.

The seven slot IDs and package identities are unchanged. Because version 13 also removes long-text types from the rectangle, an existing assignment that supports only a removed type may need replacing. Upgrade migration and retention of these assignments have not been tested; do not assume a consistently signed update preserves an incompatible source.

### Keeping weather permission across updates

The user reported that granting **Allow weather access** restored the forecast. Reinstalling the host resets its permission; use `install -r` for normal updates. Do not clear the app's data or uninstall as a routine update step. Android/Samsung controls permission grants and can revoke them; the app cannot silently bypass the prompt.

The actual version 10 and 11 CI APKs had different host certificates, explaining the reported signature conflict. The old cache retained the face key but did not preserve the host signing identity used by those builds. Version 13 explicitly selects the cached host keystore, migrates to a new cache, verifies both APK certificates, and records their public fingerprints. Once pinned, CI refuses a changed or missing key rather than silently shipping another incompatible update. Cache storage is not a durable production key backup; release signing still needs secure persistent storage.

The earlier ephemeral host key cannot be recovered from its APK. Moving from version 11 to the stable preview key will require a one-time reinstall and permission grant; keep the working version if you do not want to reset it now. Never uninstall Samsung Weather. Subsequent same-key preview updates should retain access; physical update retention still needs verification. Local builds use a separate local key and should not be mixed with CI downloads.

## Report these outcomes

| Check | Required evidence | Current status |
| --- | --- | --- |
| Permission | A normal system prompt grants weather access to the independently signed app | Physical app displays real data; exact prompt behavior was not separately reported |
| Data | Same Samsung selected city, unit, current value, four times and temperatures | User reports forecast appears correct; detailed field-by-field comparison pending |
| Native behavior | Hour rollover, midnight/noon, day/night conditions, favorite city/unit changes | Adapter fixture tests pass; physical comparison pending |
| Refresh | Samsung app refresh reaches the provider; measure delay with the face active | Pending; content notifications are not assumed reliable |
| Permission denied/revoked | Honest unavailable state, setup tap, no manufactured forecast | Missing-provider emulator test added; physical denial/revocation pending |
| Replaceability/taps | Another eligible provider replaces the entire rectangle and its tap; restore Weather under Ultra Info Board Weather | Version 11 narrowed-menu round trip, persistence and all three tap positions pass on both stock API 36 sizes. Physical Samsung editor check remains pending |
| Install/update | One host install adds face; host update updates same face and keeps choices | Physical install and face selection work; exact automatic-vs-setup install path and upgrades not separately verified |
| Active/ambient | Enlarged forecast and circular readings are readable; ambient retains black time/date only | Version 11 captures and delivered-size forecast fixtures reviewed; DOZE 4.2378% small / 4.1484% large lit. Physical readability pending; active system overlay covers part of shortcut |

Do not describe fixture images or stock-emulator results as Samsung integration. The `render-fixtures` PNGs intentionally identify their weather as test data. Stock Wear OS emulators do not contain the Samsung provider.

## Customization investigation

Version 13 declares slot 7 customizable with exactly `SMALL_IMAGE EMPTY`. This narrows the menu by data type, not by app identity, and therefore does not reproduce a fixed Samsung-only list. The forecast service declares the standard complication action, binding permission and `SMALL_IMAGE` type. It is not hidden or restricted to our own face. The [public registration and selection rules](https://developer.android.com/training/wearables/complications/exposing-data) permit this combination; a source being assigned by default does not establish discoverability in every OEM editor.

A targeted recheck of the supplied Samsung manifests found no additional public rectangle-selection flag to copy: ComplicationHelper does not declare ordinary complication-source services, while Ultra Info Board declares its own wallpaper/editor and only queries the ordinary complication action. Its source-configuration activities concern World Clock/Altimeter, not the hourly weather panel. These findings explain why Samsung's private editor configuration is not a registration recipe for our normal provider; they do not diagnose the user's exact picker failure.

Version 10 adds a service-specific white icon, distinct face name and exact picker guidance. These are identification improvements, not a proven remedy for the reported Samsung selection problem. Its package identity and all seven slot IDs remain unchanged. Reopening setup skips installation when the installed face is current, and refreshing weather does not assign a provider. Google's [Push update contract](https://developer.android.com/reference/androidx/wear/watchfacepush/WatchFacePushManager) preserves configuration for updates using the same face package; actual upgrade retention still needs testing.

The first naming attempt in version 9, **Ultra Info Board Forecast**, was visibly truncated to **Ultra Info Boa…** in the round picker, hiding its distinguishing suffix. Version 10 shortens the label to **Ultra Forecast**. This changes the display name, not the package or existing assignments.

`tools/test_forecast_editor.py` exercises the actual native editor on disposable API 36 emulators. It verifies the active pushed package, replaces the rectangle with an eligible source, checks persistence and taps, verifies opening setup does not overwrite the assignment, then restores the forecast through the picker. Version 13 uses an isolated test-only image chart app to verify replacement and taps, and restores **Weather**; version 11 used Battery; the historical version 9/10 runs below used Alarm and **Samsung hourly forecast**. With Samsung absent, the restored provider should open setup. Screenshots, UI trees, provider registration and activity evidence are retained, including on failure. This does not establish behavior in Samsung's watch or phone editors.

[Run 35677046105](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/35677046105), source `b864c30` / version 9, passes that entire sequence on both 384 px and 454 px emulators. Reviewed captures show **Samsung hourly forecast** under **Ultra Info Board Weather** in the ordinary provider list, Alarm occupying the rectangle after replacement, and the forecast restored. All three taps open the chosen provider's destination. Samsung's physical picker issue remains unresolved despite this stock-platform success.

Version 10 repeats all those checks successfully in run **35677889561**. Reviewed picker captures show the complete **Ultra Forecast** name on both display sizes. [Saved results and screenshots](VALIDATION.md) retain the exact source versions and separate emulator evidence from the physical report.

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
