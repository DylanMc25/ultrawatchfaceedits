# Ultra Info Board with an Info Brick-style bottom panel

Build a resource-only WFF 2 Galaxy Watch face with large stacked time, six independently editable complications and a compact **Bottom panel** menu. Weather is the default and shows current conditions plus four consecutive hourly forecasts as one tap area. Other choices are Detailed weather, Temperature, Chance of rain, Steps, Heart rate and None. The blue active face switches to black, thin time/date in always-on mode.

Samsung APK inspection confirmed that Info Brick supplies a curated internal rectangle menu; its ordinary public Weather complication supplies current conditions only. This implementation uses native WFF sources and original vector icons. It preserves complication IDs 1–6 and removes generic slot 7, so an existing rectangle assignment is replaced by the new menu. It uses no Samsung private data API, companion app or backend. Health panels show current native readings, not historical charts.

## Validation

- Local debug APK, unsigned release AAB, Android lint, no-DEX/package checks, official WFF 2 syntax/resource and memory checks pass.
- Eighteen regression and fixture checks cover geometry/taps, menu/ambient structure, partial or stale weather, units/extreme values, zero/empty health readings, trend gaps, midnight/noon and daylight-saving rollover.
- Fixture tests model documented WFF expressions; illustrative previews use explicit sample data. Neither establishes native weather availability.
- Native emulator evidence and remaining checks are versioned in [VALIDATION.md](VALIDATION.md).
- Physical Galaxy Watch native weather, panel editor persistence, app launches, permission denial and update behavior remain pending. Release signing, final package identity and store preparation are separate prerequisites.

![Illustrative Weather panel](https://raw.githubusercontent.com/DylanMc25/ultrawatchfaceedits/codex/watchface-redesign/docs/previews/panel-weather-illustrative.png)

This image is a layout proof, not a live-data or emulator capture. Build artifacts are available from the successful branch workflow linked in VALIDATION.md.
