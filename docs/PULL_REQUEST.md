# Add Samsung forecast provider and bundled Wear OS 6 watch face

Samsung's ordinary Weather complication does not supply its native hourly panel. This change adds a standard image complication that reads Samsung Weather's saved current/hourly data after a normal user permission grant. It follows the observed favorite-location key, units, rounding, condition mapping and four-hour selection. The whole rectangle opens Samsung Weather. The rectangle supports selecting another provider to take over its content and action; stock Wear OS selection is verified, while Samsung editor behavior still needs a physical check of this revision.

A Wear OS 6 host bundles a separately signed resource-only face using Watch Face Push. Version 13 keeps the two-line date and staggered circles, makes the active date bold, and makes all three circles 96 units with equal gaps. The forecast remains 262 × 94. Its provider is named **Weather** under **Ultra Info Board Weather**. The rectangle accepts image panels (`SMALL_IMAGE`) or Empty; the shortcut accepts only small-image icons or Empty, and all seven IDs stay stable. Both edge gauges extend farther around the rim; the minutes are slightly smaller and inset to clear the left ticks. Wear OS determines eligible apps. Older long-text rectangle assignments need replacing.

The v10/v11 downloaded host APKs had different signing certificates, explaining failed updates and permission loss after reinstalling. The preview now explicitly signs with its cached host key, verifies host/face APK certificates, and pins public identities so a lost/changed key blocks CI. Existing v11 installations require one migration reinstall; subsequent same-key updates should preserve permission. Persistent production signing and a secure key backup remain release requirements.

Missing data stays unavailable, expired data is marked, and bounded timelines handle hour and expiry transitions. Four timeline images plus a fallback stay below 512 KiB of delivered pixels; extra expiry boundaries shorten the timeline rather than merging fresh and expired data. Original vector-style weather art is drawn by the provider. No Samsung binaries, artwork or replacement weather service are shipped.

## Validation

- Version 13 local APK, test APK, unsigned host AAB and lint checks pass; 29 JVM and 19 Python tests pass.
- Official Push validation passes all ten checks on the signed embedded face. Standalone v10 APK/AAB, WFF schema and memory checks pass.
- [Run 36266834935](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/36266834935), source `a88249d`, passes both API 36 sizes and nine Android tests each. The normal rectangle picker selects a separate test-only image chart app, persists its choice through setup, opens its activity from three tap positions, and restores Weather. The shortcut picker retains App shortcut. The fixture app is a separate test artifact and is not bundled in the user APK.
- [Standalone run 36266834989](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/36266834989) passes API 34 large and API 35 small, including all seven choosers and rectangle Battery taps.
- Captured DOZE illumination is 4.0849% / 4.0082% on API 36 small/large, 4.1333% on API 35 small, and 3.7296% on API 34 large. These states are below 15%; they do not cover every time/date. No app crash or WFF expression failure was found. System charging overlays obscure part of the empty shortcut in active captures.
- [Versioned evidence](https://github.com/DylanMc25/ultrawatchfaceedits/blob/codex/watchface-redesign/docs/VALIDATION.md) distinguishes stock-emulator unavailable weather and synthetic images from physical Samsung reports.


The user installed an earlier preview on the API 36 Galaxy Watch and confirmed the forecast appears correctly in the rectangle and its tap opens Samsung Weather. The version 13 Samsung picker and layout, format/refresh edge cases, upgrade persistence and battery/ambient checks remain pending on physical hardware. Stock-emulator fixtures do not establish Samsung integration. The observed OEM interface is not a published stable Samsung API; commercial support and production signing remain release questions. The CI AAB contains a debug-signed embedded face and is a test artifact only.

The GitHub connector currently returns `403 Resource not accessible by integration` when creating a draft PR. This file preserves the review description; no PR has been created by the agent.
