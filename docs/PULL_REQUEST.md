# Build blue stacked-time watch face with weather and six complications

Replaces the placeholder Ultra Info Board layout with a blue gradient, oversized stacked time, three staggered circular complications, editable left/right edge indicators, and a bottom shortcut. Adds native current weather and four forecasts (+2/+4/+6/+8 hours), plus a black always-on time/date display. Default readings are heart rate, steps, sunrise/sunset and battery; the right edge and shortcut start unassigned.

![Actual API 34 active face](https://raw.githubusercontent.com/DylanMc25/ultrawatchfaceedits/codex/watchface-redesign/docs/previews/emulator-api34-active.png)
![Actual API 35 ambient face](https://raw.githubusercontent.com/DylanMc25/ultrawatchfaceedits/codex/watchface-redesign/docs/previews/emulator-api35-ambient.png)

These are actual Wear OS emulator captures. Weather is unavailable in the emulator; health readings come from its installed providers. Live readings are not hard-coded. A separately labeled illustrative populated-weather preview is also included.

Repairs resource-only WFF 2 packaging, restores the pinned Gradle wrapper, produces a code-free debug APK and unsigned release AAB, and adds build/schema/memory checks plus round Wear OS emulator capture jobs. Includes editable-slot geometry checks, forecast rollover checks, original weather assets, picker preview, and installation/release documentation.

Validation evidence and platform-test limitations are tracked in [docs/VALIDATION.md](https://github.com/DylanMc25/ultrawatchfaceedits/blob/codex/watchface-redesign/docs/VALIDATION.md). Local builds, lint (no errors), seven regression tests, official schema validation, package resource checks, and memory validation pass.

Both API 34 (454 px round) and API 35 (384 px round) render the face, follow 12/24-hour settings and enter the black ambient display. Reviewed ambient captures illuminate under 5% of the round screen, including system indicators. Complete evidence and untested cases are documented rather than inferred from build success.

All six slots independently open their native provider chooser on both emulators. Steps, sunrise/sunset and battery taps dispatch to the correct slots, and battery opens system Battery settings. The native editor also renders the populated weather layout using its own sample data. Real health-provider launches, live weather and saved-provider persistence remain physical-device checks. [Passing build, validation and emulator run](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/35466914072).

This is a development milestone. Physical Galaxy Watch testing, live weather and Samsung provider/permission flows, final store identity, release signing and Play listing preparation remain required before sale.
