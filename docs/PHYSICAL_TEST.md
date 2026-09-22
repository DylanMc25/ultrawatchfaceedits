# Test the bottom panel on a Galaxy Watch

Download **watchface-build-and-reports** from the latest successful workflow for `codex/watchface-redesign`, extract it, and find `app-debug.apk`. This milestone is version **0.1.6** (version code 7). The smaller/large emulator reports are separate artifacts.

## Connect from Windows

Enable **Developer options → Wireless debugging** on the watch and keep the watch and computer on the same Wi-Fi. Run each PowerShell command on its own line:

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$pairAddress = Read-Host "Address and port on the watch's Pair new device screen"
& $adb pair $pairAddress
```

Enter the pairing code when prompted. Pairing and connecting use different ports. Return to the watch's main Wireless debugging screen, then run:

```powershell
$watchAddress = Read-Host "Address and port on the MAIN Wireless debugging screen"
& $adb connect $watchAddress
& $adb devices
$apkPath = Read-Host "Full path to the extracted app-debug.apk (without quote marks)"
& $adb -s $watchAddress install -r $apkPath
```

The device list must show your watch as `device`. If it disappears, read the current main-screen port and connect again. If your Android SDK is not in the default folder, use the SDK location displayed by Android Studio.

If installation reports **INSTALL_FAILED_UPDATE_INCOMPATIBLE**, the APK uses a different development signing key. To install that build, uninstall the old development face first. **This clears its saved settings**:

```powershell
& $adb -s $watchAddress uninstall com.example.ultrainfoboard
& $adb -s $watchAddress install $apkPath
```

Do not uninstall when testing preservation of complication assignments across an update; that check requires an APK signed with the same key as the installed version.

## Select and check the face

1. Long-press the current face, add/select **Ultra Info Board**, then open **Customize**.
2. Open **Complications → Bottom rectangle**, or tap the rectangle in the editor. It should open the standard installed-provider picker, not the former seven-choice Bottom panel menu.
3. Select **Weather** from Samsung Weather and grant any requested access. Return to the face. It should show the provider's current conditions; this is not the private Info Brick hourly forecast.
4. Tap the left, center and right of the rectangle. All three should open the selected provider's app, with no neighboring complication triggered.
5. Change the rectangle to a different installed provider (calendar, Alarm, or a compatible image/chart provider). Confirm both the displayed content and tap destination change. Return to Customize and verify the choice persists.
6. Choose Empty/None in the provider picker; check the subtle setup placeholder and absence of a provider tap action. Check all seven areas remain individually editable, and all complications/seconds disappear in always-on mode.

**Observed on 0.1.5, 2026-09-21:** the native Weather panel showed `Weather —`. Its tap opened Samsung Weather correctly, and Samsung Weather had current location and real hourly forecasts. This does not establish public-provider data delivery in 0.1.6; repeat steps 3–5 with this build.

For diagnostics, the following only reads the face version and captures the screen:

```powershell
& $adb -s $watchAddress shell dumpsys package com.example.ultrainfoboard | Select-String "versionCode|versionName"
& $adb -s $watchAddress shell screencap -p /sdcard/ultra-panel.png
& $adb -s $watchAddress pull /sdcard/ultra-panel.png "$env:USERPROFILE\Downloads\ultra-panel.png"
```

Public Samsung Weather data delivery, other installed providers, image/chart readability, saved assignments and physical AOD remain pending for 0.1.6. The complete validation record is in [VALIDATION.md](VALIDATION.md).
