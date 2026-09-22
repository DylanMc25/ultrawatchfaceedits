# Samsung Weather investigation

Current findings: see [Samsung APK comparison and one-product packaging](SAMSUNG_APK_FINDINGS.md). The 2026-09-21 helper inspection confirms the caller restriction, and Ultra Info Board confirms the custom picker/renderer path. Follow-up inspection found a separate runtime-permission-based WeatherWatch hourly provider; this lead is untested and supersedes any generalization that all Samsung hourly access is signature-restricted. The user requires matching Samsung forecasts and permits multiple APKs packaged as one Play product. Watch Face Push is the documented architecture under consideration; no application changes were made during this investigation.

The sections below preserve the investigation history. Statements that helper access was uninspected describe the earlier checkpoint and are superseded by the current report.

## Verified on the physical watch

The user ran the read-only package-manager service query for Samsung Weather. It returned five exported complication services under `com.samsung.android.watch.weather.complication`:

- `WeatherComplicationService`
- `PrecipitationComplicationService`
- `FeelsLikeTempComplicationService`
- `SunriseSunsetComplicationService`
- `UvIndexComplicationService`

All belong to `com.samsung.android.watch.weather` and require `com.google.android.wearable.permission.BIND_COMPLICATION_PROVIDER`. The installed application has version code `113060000`, targets API 36, and lives at `/system/priv-app/WeatherWatch/WeatherWatch.apk`.

The first service query did not show supported-type metadata. A subsequent successful APK manifest inspection on the user's PC established:

| Provider | Declared types |
| --- | --- |
| Weather | `LONG_TEXT, SHORT_TEXT` |
| Chance of rain | `RANGED_VALUE` |
| Feels like temperature | `SHORT_TEXT` |
| Sunrise/sunset | `SHORT_TEXT, ICON` |
| UV index | `RANGED_VALUE` |

## APK inspection findings

The user supplied the installed 28,848,169-byte WeatherWatch APK. SHA-256: `578106ddfc6a88d86b7e2fce050e4721a8c1d70b824bf1146d96f15cd8694077`. Its manifest matches the earlier device output. Inspection used official JADX 1.5.6 locally, outside the repository; no Samsung binaries, assets or decompiled source are redistributed here.

`WeatherComplicationService` constructs these live responses:

| Requested type | Actual payload |
| --- | --- |
| `SHORT_TEXT` | Current temperature as text; monochromatic current-condition icon; Samsung Weather tap action |
| `LONG_TEXT` | City name as text; current temperature as title; a small image of the current-condition icon; Samsung Weather tap action |

The long-text small image is a resource icon, not an hourly chart. Neither response includes hourly temperatures, times, a forecast array or a forecast image. The service's base request handler delegates the loaded current weather to this builder. Changing the slot's type preference cannot produce Info Brick's hourly forecast from these responses.

A separate `WeatherContentProvider` extends `SignatureCheckContentProvider`. On production (`user`) builds its query path checks the calling UID against allowed signatures and rejects unapproved callers. The resource-only WFF face has no supported path to call this interface. This inspection establishes the public complication's limits; the exact internal data path used by Info Brick itself has not been inspected.

The current slot accepts both text types but lists SHORT_TEXT first. Its long-text renderer currently handles the monochromatic icon, title and text, not the optional small image; that omission is a separate rendering improvement, not the cause of missing hourly data.

## Public interface and current implementation

In the [WFF complication model](https://developer.android.com/training/wearables/wff/complications), a provider supplies data and the face renders it. Selecting the same provider name on two faces therefore does not guarantee identical content or appearance.

The [documented fields](https://developer.android.com/reference/wear-os/wff/complication/complication?version=2) include text, titles, images and progress values. They do not define an hourly forecast array. WFF also has [separate native weather sources](https://developer.android.com/training/wearables/wff/weather), but drawing these directly would not establish the user's requested interchangeable Samsung provider presentation.

Slot 7 currently accepts short/long text, images and progress and passes taps to the selected provider. It is a 262 × 60 rectangle. The stock-emulator Alarm assignment verifies replacement and tap dispatch only. The current basic Weather card does **not** yet fulfill the requested Info Brick forecast. No fake hourly values or fixed forecast buttons have been introduced.

## Info Brick follow-up

The user requested Info Brick behavior as closely as possible rather than choosing a separate Forecast/Complication editor switch. Do not silently substitute that alternative.

After activating Info Brick, the user's wallpaper diagnostic identified:

- Package: `com.samsung.android.watch.watchface.healthmodular`
- Service: `com.samsung.android.watch.watchface.healthmodular.HealthModularWatchFaceService`

The supplied Info Brick APK is version `1.0.01.4110` (`100104110`), SHA-256 `8723b7ce49f7bf60fb3cc44be06ef8be9904328845def521fa2850a46adecfa6`. It is a code-based wallpaper/watch-face service, not a resource-only WFF face.

Inspection traced the rectangular `box_weather` option to Info Brick's internal WEATHER renderer (`W1.b` selecting `Z1.O` and its view). Its own weather model (`com.samsung.android.watch.watchface.data.j1`) queries a `/weatherinfo_hour` content URI and reads hourly timestamps, temperatures, condition icons, day/night state and rain probability. The model selects between `com.samsung.android.watch.watchface.complication.weather` and `com.samsung.android.watch.weather.provider` authorities. The WeatherWatch authority's production signature check is described above; the helper authority's own access rules have not been inspected.

The editor associates this internal option with the familiar Samsung Weather service name, but the hourly rendering/data path is implemented in the face. Detailed weather and Temperature are separate internal options. This confirms the user's correction that the screenshot is Weather, not Detailed weather.

Resource-only WFF 2 cannot execute this custom renderer or query arbitrary Android content providers. Copying a provider component name or preferring LONG_TEXT will not port this behavior. Exact Samsung editor/data access parity is not established for a third-party WFF face. A built-in native forecast plus a separate editor switch is a possible approximation; achieving a true selectable forecast complication would require an appropriate external provider. Neither alternative has been approved as a replacement for the requested behavior.

The current basic Weather card remains incomplete relative to the requested forecast. No Samsung code, images or binaries have been added to this repository, and no fabricated readings or independent forecast buttons have been introduced.

## Curated bottom panel implementation (0.1.5)

The subsequent Info Brick inspection resolves the rectangle-picker question. Its medium rectangle uses `complication_type_box`, whose ordinary public supported-type list contains only EMPTY; Samsung injects its own curated panel entries. The medium rectangle's weather entries are **Weather, Detailed weather, Temperature and Chance of rain**. The circle and edge lists are different. Merely accepting more ordinary WFF complication types does not reproduce this picker or its forecast.

Info Brick's health model also makes `ContentResolver.call` requests through `com.samsung.android.watch.watchface.complication.health` or `com.samsung.android.wear.shealth.healthdataprovider`. This establishes Samsung's own data path, not access for an independently signed face. No Samsung Health/helper APK access audit established a public historical-chart contract. A resource-only WFF face cannot execute these arbitrary provider queries regardless of whether an authority is exported.

The approved implementation therefore replaces slot 7 with the **Bottom panel** WFF `ListConfiguration`, defaulting to Weather. Weather, Detailed weather, Temperature and Chance of rain use documented native WFF sources. Steps and Heart rate use native current readings, not history. None is empty and noninteractive. Each nonempty option has one whole-panel Launch target; the other six complication slots retain their provider-owned selection/data/taps.

WFF 2 cannot conditionally enable/disable a complication slot using the newer `complicationSlotIds` configuration attribute. Removing the old rectangle slot avoids invisible, overlapping provider touch targets. Bottom panel appears as a separate editor setting; it does not pretend to be Samsung's private provider-picker extension. Existing slot 7 selections are retired on upgrade, while IDs 1–6 remain stable.

Weather uses hourly indices 0–3 (the current hour and three following hours). Each hour checks its own availability. Labels format future instants using device locale/time zone and time-format preference, including midnight and daylight-saving transitions. Temperature trends only connect adjacent available points. WFF 2 has no hourly precipitation field; Chance of rain displays the current probability. The runtime's temperature-unit preference governs all weather values.

Missing weather shows `Weather —` and a single tap to open Samsung Weather. Available weather accompanied by `WEATHER.IS_ERROR` remains visible with `!`. Missing hours remain dashes. Empty or nonpositive/out-of-range heart rate is unavailable; a zero step count is valid. Native WFF has no separate step permission/availability flag, so the face cannot distinguish a runtime-supplied zero caused by unavailable access from a genuine zero. Physical-watch permission behavior remains a required test.

These sources are provided by the Wear OS runtime, not the Samsung public complication service inspected above. Their availability and freshness on this particular Galaxy Watch must be verified on that watch. Weather launch targets the installed Samsung Weather package; stock emulators lacking that package cannot prove the launch destination. No Samsung artwork, code, APK or private authority is included in the app.

References: [native weather](https://developer.android.com/training/wearables/wff/weather), [available fields](https://developer.android.com/reference/wear-os/wff/common/attributes/source-type), [date/time expression formatting](https://developer.android.com/reference/wear-os/wff/common/attributes/arithmetic-expression).

## Physical result and app-selectable rectangle (0.1.6, 2026-09-21)

The user tested 0.1.5 on their Galaxy Watch: `Weather —` on the face, successful launch of Samsung Weather, and a real location/hourly forecast inside that app. The exact cause of the native WFF weather source being unavailable is not established. Samsung Weather having data does not prove that the separate WFF source receives it.

The user then explicitly clarified that the rectangle must accept **other apps' rectangular complications**. Version 0.1.6 replaces the curated menu with standard editable slot 7; IDs 1–6 and the geometry stay unchanged. All supported public text/image/progress formats have renderers. Samsung Weather's verified public component is the preferred LONG_TEXT default with EMPTY fallback; no signature-restricted service is called. Each provider owns the displayed data and tap action.

This enables provider choice but does **not** reproduce Info Brick's hourly forecast. A suitable installed image/chart provider may supply richer content. No claim is made that Samsung's public Weather provider now exposes an hourly chart, or that its data delivery on this new build has been physically verified.

## Investigation checkpoint: trace the helper before further implementation

On 2026-09-21 the user requested evidence-led investigation rather than more trial implementations, and offered the Ultra Info Board APK. Further application changes are paused. Commit `c44ac53` is a standard-provider implementation checkpoint, not a verified solution to Info Brick parity and not a new physical-test requirement.

Reinspection confirms these details from the supplied Info Brick APK:

- `data/j1.java` constructs the provider selector with the helper authority first, then Samsung Weather's own authority. `p067u1/c.java` chooses the first authority resolvable by PackageManager; this is presence selection, not proof that an independently signed caller is permitted to query it.
- `data/j1.java:T` conditionally binds `com.samsung.android.watch.watchface.complicationhelper.ComplicationLaunchTransitionHelper` on API >34 when the helper version is below 100104045. Newer helper versions omit this binding. This establishes a helper-version dependency in Samsung's implementation, not a requirement we can assume for WFF.
- `data/f1.java:f` forms the hourly URI using the selected authority and `/weatherinfo_hour`.
- The rectangle's public supported-type array remains EMPTY-only (`p079x2/a.java:d`, selected in `p082y2/e.java`). The custom picker adds a list of Samsung panels in `J0/c.java`, separately from the standard complication payloads.
- Samsung Weather's own signature check is confirmed, but it must not be generalized to the uninspected helper. A helper APK inspection is required to determine its provider declarations, access checks, data forwarding and any public extension path. No query or signature bypass is proposed.

Requested comparison inputs: `com.samsung.android.watch.watchface.ultrainfoboard` and `com.samsung.android.watch.watchface.complicationhelper`. Trace their manifest, selection menu, weather rendering/data source and access conditions before choosing an implementation. No Samsung code/assets will be redistributed. The reason native WFF weather is unavailable on the test watch also remains unproven.
