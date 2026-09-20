# Test the bottom panel on a Galaxy Watch

Download **watchface-build-and-reports** from the latest successful workflow for `codex/watchface-redesign`, extract it, and find `app-debug.apk`. This milestone is version **0.1.5** (version code 6). The smaller/large emulator reports are separate artifacts.

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
2. Find the **Bottom panel** setting. Choose Weather, Detailed weather, Temperature, Chance of rain, Steps, Heart rate, or None. Swipe to **Complications** to change the six normal areas.
3. Weather should show current conditions and four consecutive hours. A missing hour is a dash; `Weather —` means native weather data is unavailable. Open Samsung Weather and confirm it has a location and a recent reading. The native WFF source may update separately from Samsung's public complication provider.
4. Tap across the rectangle. Weather modes should all open Samsung Weather. Steps opens Samsung Health; Heart rate uses the system heart-rate destination. None must have no action.
5. Leave and reopen Customize to check the selected panel persists. Check 12/24-hour preference, temperature units, and always-on mode. The panel and seconds should disappear in always-on mode.

For diagnostics, the following only reads the face version and captures the screen:

```powershell
& $adb -s $watchAddress shell dumpsys package com.example.ultrainfoboard | Select-String "versionCode|versionName"
& $adb -s $watchAddress shell screencap -p /sdcard/ultra-panel.png
& $adb -s $watchAddress pull /sdcard/ultra-panel.png "$env:USERPROFILE\Downloads\ultra-panel.png"
```

Native weather availability, Samsung app destinations, real denied-permission behavior and physical AOD are **pending until tested on a Galaxy Watch**. The complete acceptance list is in [VALIDATION.md](VALIDATION.md).
