# One-product Watch Face Push build

The watch app owns the Samsung connection and forecast complication; a separate resource-only WFF APK owns the face. The user installs the host once. Wear OS 6 installs its bundled face into the picker. The original `:app` remains available while the connection is tested.

Google documents bundling a watch face with its complication provider in one app, including cases where the face is the main product. This does not establish Samsung feed access or guarantee Play review. [Official bundled-app example](https://android-developers.googleblog.com/2025/08/further-explorations-with-watch-face-push.html)

## Packages and SDK

| Module | Application ID | Function |
|---|---|---|
| `:weatherbridge` | `com.example.ultrainfoboard.bridge` | Permissions, Samsung data, forecast provider, face updates |
| `:pushface` | `com.example.ultrainfoboard.bridge.watchfacepush.board` | Bundled WFF 2 face |
| `:app` | `com.example.ultrainfoboard` | Existing standalone test face |

The new host and bundled face use API 36 as their minimum, matching the accepted Wear OS 6 requirement. Pushface retains complication IDs 1–7 and changes slot 7's default provider to `SamsungForecastService` in the host, requesting `SMALL_IMAGE`. That image fills the existing 262×60 rectangle, avoiding extra internal shrinkage. Touch areas and other slots stay unchanged. Slot 7 remains editable; each selected provider owns its tap action.

The current AGP 8.13.2 / Gradle 8.13 / Java 17 setup supports API 36. No further toolchain bump is needed. The stable `androidx.wear.watchfacepush:watchfacepush:1.0.0` artifact was checked directly: its AAR metadata requires compile SDK 36 and AGP 8.9.1. `watchface-complications-data-source:1.3.0` requires compile SDK 34 and AGP 8.1.1. [AGP compatibility](https://developer.android.com/build/releases/agp-8-13-0-release-notes), [Push release notes](https://developer.android.com/jetpack/androidx/releases/wear-watchfacepush)

## Build sequence

Run from the repository root with Java 17 and Android SDK 36 configured:

```sh
python3 tools/prepare_push_bundle.py
./gradlew :weatherbridge:assembleDebug :weatherbridge:lintDebug
```

Preparation performs these dependent steps:

1. Copy `app/src/main/res` into the pushface build directory, change slot 7's default provider and fill its existing rectangle with the small image.
2. Generate a separate local debug signing key at `.cache/pushface-debug.jks` if absent. Preserve this key between installs.
3. Build the signed `:pushface` debug APK.
4. Reject APK entries outside the official resource-only allowlist.
5. Run the official Push validator on that exact signed APK and host package name.
6. Generate the host's `assets/default_watchface.apk` plus `res/values/default_watchface.xml`, containing the token, face package, and version.

The script removes stale generated host assets before starting, and stops on any build or validation failure. Token evidence is saved beside the generated assets in `validation.json` and `validator.log`. This verifies packaging, not installation or live Samsung weather.

The host must include `build/generated/watchface/assets` as an assets source and `build/generated/watchface/res` as a resource source. It must declare `com.google.wear.permission.PUSH_WATCH_FACES` and application metadata `com.google.android.wearable.marketplace.DEFAULT_WATCHFACE_VALIDATION_TOKEN` pointing to `@string/default_wf_token`. The face enters the picker without automatically becoming active. [Host setup and default asset contract](https://developer.android.com/training/wearables/watch-face-push/wear-os-app)

## Validator and signing

The current documentation names CLI `1.0.0-alpha10`, while the actual Google Maven metadata fetched on 2026-09-21 lists latest `1.1.0-alpha01`. The script pins that published version and SHA-256, downloads from Google Maven, and rejects a hash mismatch. `--validator /path/to/official.jar` uses an existing identical JAR. The JAR was confirmed runnable on Java 17. [Published validator metadata](https://dl.google.com/dl/android/maven2/com/google/android/wearable/watchface/validator/validator-push-cli/maven-metadata.xml)

The pushed APK must have no code and use the host's `.watchfacepush.` package prefix. Its signing key must differ from the host's signing key. Any APK change requires a fresh token; sign before validating. Keep the existing syntax/resource and memory checks as well. [Package, signing, and validation rules](https://developer.android.com/training/wearables/watch-face-push)

Release preparation requires `PUSHFACE_KEYSTORE`, `PUSHFACE_STORE_PASSWORD`, `PUSHFACE_KEY_ALIAS`, and `PUSHFACE_KEY_PASSWORD`, then `--variant release`. Signing material stays outside source control. Match `--version-code` and `--version-name` to the host; current preparation defaults are 8 and 0.2.0-preview.1. A production host AAB needs its separate release signing and Play configuration. Debug CI keys need persistent secret storage before updates can preserve installed packages reliably.

## Installation lifecycle and physical checks

Host updates do not automatically replace the face. On first launch and `MY_PACKAGE_REPLACED`, obtain current Push slots, compare the installed version with `bundled_watchface_version`, and update the same face using the bundled APK/token. Never retain slot IDs between operations. Obtain user permission only if offering automatic activation; manual selection avoids that optional permission. The user must launch the host at least once for its replacement receiver to run. [Update lifecycle example](https://android-developers.googleblog.com/2025/08/further-explorations-with-watch-face-push.html)

Before release, verify fresh host installation adds the face; first setup requests Samsung permission normally; denied access remains honest; forecast matches Samsung's selected location and hours; one whole-panel tap opens Samsung Weather; replacing the provider works; ambient hides the panel; upgrading the host updates the face while retaining selections; and uninstall/reinstall behavior is acceptable. The distinct bundled face package means settings from the earlier standalone package do not automatically migrate.
