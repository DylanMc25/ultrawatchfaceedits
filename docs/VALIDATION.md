# Validation evidence

Build environment: Linux x86-64, Temurin JDK 17, Gradle 8.13, Android Gradle Plugin 8.13.2, Android platform/build-tools 35. Date: 2026-09-19.

## Completed locally

| Check | Result |
| --- | --- |
| Generated WFF matches source generator | Pass |
| Seven regression checks | Pass |
| Official WFF validator 1.7.0, format 2 | Pass |
| Debug APK and unsigned release AAB | Build successfully |
| APK/AAB contents | No DEX; referenced images present |
| Android lint | No errors; advisory warnings described below |
| Official memory evaluator, APK and AAB | Pass: active 3,551,360 bytes; ambient 3,181,712 bytes |
| Whitespace/diff check | Pass |

The regression checks cover six stable slots and their type renderers, distinct tap regions inside the circular screen, disjoint runtime rectangles and bounded rendering parts, all 16 weather conditions with day/night assets, unavailable forecast fallbacks, every hour across midnight/noon, and ambient layer visibility. Resource-label checks also prevent Android-style `@string/` references in raw WFF editor attributes; WFF expects bare resource names.

Lint advisories include newer available tool versions, raw-WFF resource references that Android lint cannot trace, and backup metadata for a code-free package. No resource shrinking is enabled, and the package check confirms referenced image resources survive packaging.

`validation/package-checksums.json` identifies the local APK/AAB deliverables. GitHub's fresh runners generate their own development signing key, so their debug APK checksum differs. GitHub artifacts include the reports produced alongside those builds.

## Platform verification

The local Wear OS API 34 emulator was launched with software CPU emulation because this host has no `/dev/kvm`. It reached Android startup, but `system_server` repeatedly exceeded its 61-second watchdog timeout before package installation was available. These are operating-system boot failures; **no successful local install, watch-face rendering, complication interaction or ambient screenshot is claimed**.

Hardware-accelerated [GitHub run 35466914072](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/35466914072), commit `e8709fc`, passed builds/validation and both emulator jobs. The actual captures were downloaded and visually reviewed:

| Check | API 34, 454 × 454 round | API 35-ext15, 384 × 384 round |
| --- | --- | --- |
| APK installation and face activation | Pass | Pass |
| Blue gradient, stacked time, date and six areas | Rendered | Rendered |
| 12/24-hour preference | 08 / 20 hours; forecast labels switch | 08 / 20 hours; forecast labels switch |
| Missing weather | `Weather —`, four dashes, future-hour labels | Same |
| Default providers | Heart rate, steps, battery; unavailable sunrise/sunset | Same |
| Black always-on with time/date only | Pass, display state `DOZE` | Pass, display state `DOZE` |
| Ambient illuminated area at captured time | 2.9378% | 2.1914% |

Illumination counts every non-black pixel within the round screen, including system overlays, with no brightness cutoff. Both captures are below the documented [15% limit](https://developer.android.com/training/wearables/wff/ambient). These measurements establish the captured date/time only, not every possible date, font or device. These captures emulate an unplugged battery so the charging overlay does not cover the shortcut; API 35 still shows the system unread-status dot.

The emulator weather service returned an internal server error; no populated native forecast is claimed. Heart rate and steps are supplied by the emulator's installed providers and are not physical health measurements. Missing provider icons render empty. No readings are fabricated by the face.

Runtime testing also caught a battery tap being dispatched from the steps circle. The edge slots and all rendering parts now have bounded, disjoint rectangles, with a dedicated regression test; the circular/arc outlines alone were insufficient for native tap dispatch. The native interaction script confirms the blue face before every coordinate tap and reports any launch from the wrong slot.

Runtime testing found a color-setting parse failure that the official schema validator did not detect. The single blue palette now renders directly from centralized source colors; it does not expose an unnecessary one-option color editor. CI rejects a startup/default face or a runtime theme parse failure, rather than accepting installation alone.

### Editor and tap verification

Both emulators opened the native editor and independently opened the provider chooser for **all six slots**. The JSON reports in `validation/api34-editor-results.json` and `validation/api35-editor-results.json` record six visible chooser results each, no tap mismatches and no automation errors. Full per-slot PNG/XML/activity captures are in the linked workflow artifacts. The probe cancels each chooser; changing providers and retaining a saved selection across updates remain physical-device checks.

Native tap logs identify the correct steps, sunrise/sunset and battery slots (2, 3, 4). Battery opens the system Battery settings page on both emulators. Steps and sunrise/sunset dispatch to their slots but do not open another foreground app in these images. The emulator placeholder heart-rate provider produces no launch event and leaves the face visible; its real-watch action is unverified. No unsupported launch is reported as successful.

The native editor supplies sample data: September 28 at 09:30, populated weather, heart rate, steps and sunset. Its captures verify the native populated-weather glyphs and spacing, including compact sunset text. These are **Wear OS editor sample readings**, not live weather or health. The actual face continues to display dashes when live weather is unavailable.

The final ambient captures show stippled text. Earlier captures of the same rendering code were also reviewed with continuous thin text and remained below 5% illumination. The measurement applies to each captured state; brightness and readability still need physical Galaxy Watch review.

### Coverage boundaries

| Scenario | Evidence / remaining check |
| --- | --- |
| September date, real device text metrics | Reviewed on both emulators; no time/date clipping |
| Longer localized dates, all wide digit pairs | Ellipsis/fit policies implemented; exhaustive native captures pending |
| Midnight/noon and forecast rollover | All 24 input hours checked against generated label expressions; native captures also show 22:00 / 00:00 / 02:00 / 04:00 forecast labels and 12-hour equivalents. Main-clock noon/midnight transitions remain pending |
| Temperature extremes and unit changes | Uses native temperature values; real weather service unavailable in these emulators |
| Empty right/bottom complications | Setup placeholders rendered |
| Unavailable weather and sunrise/sunset | Observed in native captures |
| Health permission denial | Physical provider consent flow pending |
| Six separate touch targets | Arc/oval geometry and rectangular runtime bounds pass regression checks; all six provider choosers opened independently on both emulators |
| Provider selection and tap launches | Correct slot dispatch observed for steps/sunrise/battery; Battery settings opens. Real heart-rate/app destinations and saved-provider persistence require physical hardware |

## Preview status

The files in `docs/previews/*-illustrative.png` are layout proofs drawn from the WFF geometry with explicit sample readings. They are not emulator screenshots. They cannot prove real font metrics, ambient power behavior, or provider integration. The active proof is the temporary system picker preview.

## Still required before sale

See [RELEASE.md](RELEASE.md): physical Galaxy Watch coverage, real health and app providers, permission/data-unavailable states, exact tap launches, forecast/unit/time-zone behavior, ambient illumination across other dates/times and physical battery use, permanent branding/package ID, signing, and Play submission preparation.
