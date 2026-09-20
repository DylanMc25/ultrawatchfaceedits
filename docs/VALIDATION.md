# Validation evidence

Version 0.1.4, 2026-09-19. Resource-only WFF 2; Temurin JDK 17, Gradle 8.13, AGP 8.13.2, Android platform/build-tools 35.

## Local checks

| Check | Result |
| --- | --- |
| Generated XML matches generator | Pass |
| Ten geometry/complication regression checks | Pass |
| Official WFF validator 1.7.0, format 2 | Pass |
| Debug APK / unsigned release AAB / Android lint | Pass |
| Package resources and absence of DEX | Pass |
| Official APK/AAB memory evaluator | Pass: active 2,371,712 bytes; ambient 3,181,712 bytes |

Regression coverage includes all seven named slots and renderers, non-overlapping editor bounds and runtime slot rectangles, bounded rendering parts, complete rotated edge labels and gauge clearance, separated minutes/seconds, time/circle clearance, device time-format synchronization, and time/date-only ambient visibility. The weather-slot contract rejects any hard-coded app launch or native forecast data: the selected complication provider owns its data and tap action. It also checks short/long text, images and progress support. There are no longer any forecast rollover expressions to test.

The layout retains the previous stacked time and three staggered circles. Hours/minutes increase from 126 to 142 units, seconds from 32 to 36, and the three circles to 90 units. Readings of up to three characters increase to 38; four- and five-character values use 30, and longer text uses 22. Month/date, edge readings, gauge strokes and the bottom shortcut are also larger. The left battery caption moves lower to clear the wider minutes. Slot 7 remains exactly 262 × 60 below the main readings, as requested. Slot IDs 1–6 are preserved. Weather starts empty because WFF has no portable system WEATHER provider; choose an installed source in Customize. Image providers may use the area for a chart, but the face does not generate chart history. The basic Weather card still does not reproduce Samsung Info Brick’s hourly forecast; [provider investigation](SAMSUNG_WEATHER.md) records the physical-watch diagnostics and inspection of the supplied Weather and Info Brick APKs. Info Brick draws its hourly panel from a Samsung content-provider model; the public Weather complication sends current conditions only.

Lint advisories include available dependency updates, resource references inside raw WFF that lint cannot trace, and backup metadata for a code-free package. Resource shrinking remains disabled. `validation/package-checksums.json` identifies local deliverables; CI APK checksums differ because its debug signing keys are temporary.

## Native emulator evidence

[GitHub run 35481758095](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/35481758095), source commit `eea5ffb`, passed the build job and both emulator jobs. Captures were downloaded and visually reviewed.

| Check | API 34, 454 × 454 | API 35-ext15, 384 × 384 |
| --- | --- | --- |
| Install, activate and render blue face | Pass | Pass |
| Device 12/24-hour preference | Pass | Pass |
| Native editor: all seven provider choosers | Pass | Pass |
| Weather-area reassignment to Alarm | Pass | Pass |
| Assigned weather-area tap dispatches slot 7 | Pass | Pass |
| Circle-boundary taps between neighboring slots | Pass | Pass |
| Wrong complication dispatch | None | None |
| Angled battery and assigned right-edge text | Visible | Visible |
| Black time/date-only ambient, display state | DOZE | DOZE |
| Ambient lit pixels, including overlays | 3.3819% | 5.0986% |

The native editor's four-digit step count is shown in full with the compact numeric size. Larger stacked digits, seconds, circle readings and angled captions were visually reviewed on both display sizes. The empty weather panel and the assigned Alarm panel both render within their bounds. The earlier API 34 partial-background redraw anomaly was not reproduced in this run: active and assigned-provider backgrounds render fully. Its cause remains unknown, so retain a physical-device regression check. API 35's system status overlays cover part of the bottom shortcut; this is still a physical-device review item.

Steps, sunrise/sunset, battery and the assigned weather slot dispatch to IDs 2, 3, 4 and 7 respectively. Battery opens native Battery settings. The emulator's heart-rate provider emits no tap launch at its center or boundary; these probes establish no wrong-slot dispatch, not a successful heart-rate app launch. Real health/app destinations remain unverified.

The intermediate corrected-layout run `35481411856` stopped at an outdated screenshot smoke check: its old sample positions were covered by the enlarged circle and weather panel. Both captured active faces rendered correctly. The smoke check now samples exposed background and was checked against those active images and an ambient image (which it correctly rejects).

A preliminary enlarged layout (`6759277`, [run 35480895592](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/35480895592)) exposed a native hit-testing issue: API 35 routed taps from the upper circle to slot 2 and from the middle circle to slot 3 where the slot rectangles overlapped. The visible ovals were separate. The corrected layout keeps the enclosing rectangles separate too; circle-boundary probes remain in the native test. This is why geometric oval separation alone is not accepted as validation.

The local host lacks `/dev/kvm`; software-emulated Android startup previously hit system-server watchdog failures. Native evidence therefore comes from hardware-accelerated GitHub emulators, not the illustrative renderer.

The automation opens all seven native provider choosers independently. It assigns Alarm to the right edge to check the angled label, then assigns Alarm to the weather area to exercise an actual provider selection and tap. The stock emulator does not include Samsung Weather. An Alarm test establishes the interchangeable slot contract; it does **not** establish live Samsung Weather, chart-provider rendering, or Samsung app launches.

The editor displays Wear OS sample time/health readings, not live measurements. Active health values come from emulator providers. Empty/unavailable data is never replaced with fabricated readings by the face. The illustrative preview uses explicitly supplied sample weather.

Ambient illumination counts every non-black pixel inside the circular screen, including system indicators. The [15% limit](https://developer.android.com/training/wearables/wff/ambient) applies; measurements establish only the captured time/date/device, not every possible state. The emulator simulates an unplugged battery to avoid the charging overlay. Wear OS status indicators may still overlay the bottom shortcut.

## Remaining physical-device coverage

- Check for the recorded API 34 background redraw anomaly after changing providers, including returning from the editor and crossing a minute boundary.
- Choose Weather in the new slot on the user's Galaxy Watch, check permissions, live readings, units, unavailable state and the provider's tap destination.
- Assign a compatible image/chart provider and inspect its aspect ratio and readability. This is not guaranteed for every third-party provider.
- Check long localized month/day strings, wide digits, large steps and provider text, midnight/noon, time-zone changes and temperature extremes.
- Check real heart-rate consent/actions, provider settings persistence across updates/reboots and battery consumption.
- Review ambient legibility and illumination at other times/dates on Galaxy Watch hardware.

The previous layout's physical user feedback informed the revision, but the revised layout is not yet verified on a physical Galaxy Watch. See [release prerequisites](RELEASE.md) before selling.

## Preview status

`docs/previews/*-illustrative.png` are approximate layout proofs from WFF geometry and explicit sample data. They do not prove native font metrics, provider compatibility or battery behavior. The active illustration is the temporary system picker preview; use verified device screenshots before publishing.
