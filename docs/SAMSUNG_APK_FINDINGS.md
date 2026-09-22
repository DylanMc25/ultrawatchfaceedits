# Samsung panel investigation and one-product packaging

Investigation date: 2026-09-21. This is a research result, not a new implementation or a claim of successful physical integration. Application code is unchanged during this investigation.

## Conclusion

Ultra Info Board and Info Brick implement their rich rectangle as a curated Samsung panel with an internal renderer. Their hourly data comes through Samsung's helper/content-provider path, not the ordinary public Weather complication. The newly supplied helper checks the caller before returning data. An ordinary independently signed Play-installed app does not qualify on a production watch.

The user's clarification permits multiple APKs behind one product/listing. Google's **Watch Face Push default-watch-face mechanism** offers a documented way to bundle a code-free WFF face and a Wear OS app containing complication providers. This is a viable architecture to investigate for our own interchangeable forecast complication on **Wear OS 6+**, with an independent authorized weather source. It does not unlock Samsung's private data.

## Inputs and method

| Input | Package | Version / minimum API | SHA-256 |
| --- | --- | --- | --- |
| UltraInfoBoard.apk | `com.samsung.android.watch.watchface.ultrainfoboard` | 1.0.01.4110 / 100104110; min 30, target 36 | `e42fe6e3e56a8b1a997cbbb3db3029c1477126a3888584e1a3f7c9fe8ebd103d` |
| ComplicationHelper.apk | `com.samsung.android.watch.watchface.complicationhelper` | 1.0.01.4104 / 100104104; min/target 36 | `356d4966cc705c58f167429b38b4509bf4229645182d8b9b2fcf94bf01ceb273` |

Inspected manifests with Android SDK apkanalyzer; inspected local code with JADX 1.5.6; cross-checked the helper's caller validator against DEX disassembly using `apkanalyzer dex code --class L.a`; verified Ultra's signing certificate with `apksigner verify --print-certs`. Decompiled class names below identify the supplied versions, not stable public APIs.

JADX reported two errors in helper weather-library conversion/synchronization methods and thirteen errors in the overall Ultra APK. The caller gate and traced picker/model methods inspected here were available; the key access decision was independently checked against bytecode. This is not a claim that every APK method was reconstructed. No APK, Samsung artwork, full certificate, or decompiled implementation is committed.

## Verified selection and forecast path

| Step | Evidence in supplied APKs | Meaning |
| --- | --- | --- |
| Rectangle registration | Ultra `UltraInfoBoardWatchFaceConfigActivity` maps slot 2001 to `complication_type_box`, and the preview configuration uses the BIG box size. | The rectangle has different rules from its circles/edges. |
| Public type filter | Ultra `A2/j.java` selects `p086z2/a.java:d` for the box; that array contains EMPTY. | The rich panel menu is not obtained by advertising LONG_TEXT or an image type. |
| Internal menu | Ultra `A2/b.java` supplies a size-specific list of built-in `box_*` options; `p038m1/m.java:c0` builds Weather. `p038m1/o.java` associates the familiar Weather service component with that entry. | A Weather label/component in Samsung's editor does not establish that its content came from the public complication payload. |
| Renderer | Ultra `X1/b.java` maps `box_weather` to WEATHER, then creates `p006b2/T` and controller `p002a2/O`. The controller observes the weather model and hourly update events. | Samsung draws the rich forecast within its own face. |
| Source | Ultra `data/j1.java` prefers the helper authority, falling back to Samsung Weather's own authority. `data/f1.java` constructs `/weatherinfo_hour`; the model reads hourly time, temperature, condition, day/night and rain fields. | This is a content-provider query, not a WFF weather expression or an ordinary complication response. |
| Helper | `WeatherComplicationContentProvider.query` validates the caller, initializes Samsung Weather API, obtains favorite-location weather, and turns hourly observations into cursor rows. | The helper bridges Samsung's weather data into its watch faces. |

Info Brick's previously inspected medium rectangle follows the same pattern, with a size-specific option list. Neither comparison establishes arbitrary third-party forecast-provider support in Samsung's rectangle.

## The helper's access restriction is now confirmed

The helper manifest exports `WeatherComplicationContentProvider` without a manifest read-permission on that provider. However, the first part of `query` obtains the calling package and invokes `L.a.a(context, callingPackage)`. A rejected caller receives null before weather data is read.

The validator accepts the helper itself, system/updated-system apps, or an app signed with its embedded Samsung certificate. Its application-flags mask is `0x81`: Android's [FLAG_SYSTEM and FLAG_UPDATED_SYSTEM_APP](https://developer.android.com/reference/android/content/pm/ApplicationInfo#FLAG_UPDATED_SYSTEM_APP). An additional engineering-build branch is not applicable to a normal retail installation and is not a product solution.

The embedded allowed certificate's SHA-256 is `4a6fccda080b3057dc3f98641d00f4f7e268f2f2d95cd77d9a034276aa3d192a`. Ultra Info Board's independently verified APK signer has exactly that digest. That establishes why the supplied Samsung face qualifies. Our development/release signing does not provide that identity; changing XML, adding APKs or enabling developer options cannot turn an ordinary app into an eligible production caller.

The helper's Health provider invokes the same validator. Historical Samsung Health panels are therefore not an unrestricted alternative data source either. The previously inspected WeatherWatch provider has its own caller-signature check. No access-control bypass or repackaging of Samsung components is proposed.

## What multiple APKs can legitimately solve

Google explicitly demonstrates shipping a default WFF face APK inside the assets of a Wear OS app, including the case where the host app mainly supplies complication providers. Its system installation hook installs the bundled face alongside the app. See [Google's single-package example](https://android-developers.googleblog.com/2025/08/further-explorations-with-watch-face-push.html).

Proposed project structure, **not implemented**:

```text
One Play product: Ultra Info Board
└── Wear OS host app
    ├── Forecast complication service + cache + setup/details screen
    └── assets/default_watchface.apk
        └── Resource-only WFF face
            └── Editable bottom rectangle, defaulting to our forecast provider
```

The provider can supply an original forecast image (conditions, temperature, four hourly columns) through a standard image complication with a single tap action and accessible description. The rectangle stays customizable, so a user can replace it with another installed compatible provider. The image comes from the provider, not from a hard-coded forecast overlay. Compatibility with image dimensions, editor previews and runtime caching still needs verification.

The host and embedded face remain separate installed package identities. [Watch Face Push](https://developer.android.com/training/wearables/watch-face-push) requires the face name under the host's `.watchfacepush.` prefix, separate face signing, strict APK contents and an official validation token. This would require a migration from the existing development face identity. The original API 34/35 baseline cannot use this Wear OS 6 feature; retaining older watches needs a separate fallback decision, not an unannounced minimum-version change.

The [default-face setup](https://developer.android.com/training/wearables/watch-face-push/wear-os-app) uses `assets/default_watchface.apk` and validation-token metadata. Updating the host does not automatically update an already installed face; Google's example handles app replacement and uses the Push update API. First launch/setup and permission handling must be part of the installation design. Phone software is optional for a watch-only version; no generic APK installer or second manual Play purchase is needed for this proposed mechanism.

This is distinct from putting executable code inside our current WFF module. [Ordinary WFF packaging](https://developer.android.com/training/wearables/wff/setup) remains resource-only. The bundled Push approach puts provider logic in the host and leaves the embedded face code-free. Play submission/approval and the actual device installation flow remain untested; documentation is not proof of our future build passing review.

## Weather remains an independent data decision

A bundled provider still needs an authorized source of hourly forecasts. Neither uploaded APK grants us permission to read Samsung's protected data. The native WFF source's failure on the user's watch is separate: 0.1.5 reported unavailable while Samsung Weather had valid data. These APKs do not explain the native runtime failure. [Google's WFF weather guide](https://developer.android.com/training/wearables/wff/weather) specifies availability checks and network/phone-derived location; it does not promise that opening Samsung Weather populates the native source.

A potential independently licensed feed is MET Norway Locationforecast, which covers global coordinates. Its [data policy](https://api.met.no/doc/License) uses open attribution licenses. This is **a candidate, not a selected integration**. Its [service terms](https://api.met.no/doc/TermsOfService) require identification, attribution, caching, traffic control and may require a proxy as usage grows; delivery has no SLA. We must not promise a subscription-free, backend-free production service merely because a sample API call succeeds. [Locationforecast documentation](https://api.met.no/weatherapi/locationforecast/2.0/documentation) describes forecast data, so estimates should not be represented as measured observations.

## Evidence needed before the next implementation

1. The user returned **36** from `getprop ro.build.version.sdk` on 2026-09-21, confirming the OS/API baseline for Watch Face Push. Actual Push availability and installation behavior on that firmware still need a focused runtime check. No further OS-version guess is needed.
2. Resolve older-device support and select a weather source compatible with the intended commercial distribution and operating costs. One listing/multiple internal APKs is accepted; a paid weather contract or mandatory backend has not been authorized.
3. Build a bounded packaging/provider proof only after those decisions: fresh install, face automatically listed, setup, default provider, replacement by another provider, whole-area taps, provider update delivery, host/face upgrades and uninstall behavior. Label fixture data explicitly in any isolated test.
4. Then implement real weather caching, units/time zones, stale/offline states and original chart artwork, and test on physical Galaxy Watch. Do not treat emulator fixtures as Samsung integration.

The evidence supports a one-product **independent forecast complication** architecture. It does not support reusing Samsung's private hourly provider as the production solution.
