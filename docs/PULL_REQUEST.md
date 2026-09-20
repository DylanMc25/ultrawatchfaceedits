# Build blue stacked-time watch face with seven editable complications

Replaces the placeholder face with a blue gradient, large stacked time, three staggered circular complications, edge indicators and a bottom shortcut. A compact interchangeable weather slot replaces the separate current-weather/forecast grid. It accepts provider text, icons, images/charts and progress, and delegates taps to the selected provider. Heart rate, steps, sunrise/sunset and battery are default sources; weather, right edge and bottom shortcut start unassigned. Larger time, round complications and edge readings fill the familiar layout; the weather rectangle stays the same size. Black always-on mode retains thin time and date only.

![Native active face](previews/emulator-api34-active.png)
![Native always-on face](previews/emulator-api35-ambient.png)

Preserves resource-only WFF 2 packaging and stable slot IDs 1–6; adds slot 7. Restores the pinned Gradle wrapper and produces a debug APK and unsigned release AAB with no DEX. Adds GitHub build/schema/memory/lint checks, geometry regressions and two round Wear OS emulator jobs. Includes setup, installation and release documentation.

Validation: ten regression checks, official WFF syntax/resource and memory checks, builds and lint pass. Native capture provenance, individual chooser results, tap evidence and measured ambient illumination are recorded in [validation evidence](VALIDATION.md). The latest API 34/35 captures render fully; a previous API 34 partial-background redraw was not reproduced and remains a physical-device regression check. Native probes verify taps near neighboring circle edges. API 35 system status overlays can cover the bottom shortcut. Info Brick’s rich Weather presentation remains unresolved; the current basic weather card does not yet fulfill it. Samsung Weather and image/chart providers remain physical-device checks; the stock emulator tests the new slot with Alarm instead.

This is a development milestone. Physical Galaxy Watch verification, permanent branding/package identity, release signing and Play Store preparation remain required before sale.
