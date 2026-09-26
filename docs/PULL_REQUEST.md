# Add Samsung forecast provider and bundled Wear OS 6 watch face

Samsung's ordinary Weather complication does not supply its native hourly panel. This change adds a standard image complication that reads Samsung Weather's saved current/hourly data after a normal user permission grant. It follows the observed favorite-location key, units, rounding, condition mapping and four-hour selection. The whole rectangle opens Samsung Weather. The rectangle supports selecting another provider to take over its content and action; stock Wear OS selection is verified, while Samsung editor behavior still needs a physical check of this revision.

A Wear OS 6 host bundles a separately signed resource-only face using Watch Face Push. Version 11 retains the two-line date and three staggered circles, reduces date/time text slightly, and enlarges the circular readings and forecast. The rectangle grows from 262 × 60 to 262 × 94; its current/temperature/hour labels grow to 20/19/15 units. The provider is named **Weather** under **Ultra Info Board Weather**. Its menu accepts `LONG_TEXT`, `SMALL_IMAGE` and Empty, with eligibility determined by Wear OS rather than an app whitelist. All seven slot IDs stay stable; incompatible older rectangle assignments may need replacing, and upgrade migration is unverified.

Missing data stays unavailable, expired data is marked, and bounded timelines handle hour and expiry transitions. Four timeline images plus a fallback stay below 512 KiB of delivered pixels; extra expiry boundaries shorten the timeline rather than merging fresh and expired data. Original vector-style weather art is drawn by the provider. No Samsung binaries, artwork or replacement weather service are shipped.

## Validation

- Current version 11 local APK, test APK, unsigned host test AAB and lint checks pass. Standalone 0.1.7 / version 8 APK/AAB, schema and memory checks also pass.
- 29 adapter/reader/timeline JVM tests and 18 layout/data/bundle checks pass.
- Google's pinned official Watch Face Push validator passes all ten checks on the exact signed embedded APK, including WFF and memory.
- [Version 11 Samsung run 36261887590](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/36261887590), source `5f9a62f`, passes both API 36 sizes, including nine Android tests each. Native selection replaces the rectangle with Battery, checks persistence and three tap positions, verifies setup preserves the selection, and restores **Weather** from our app. Reviewed delivered-size fixtures and native captures fit. DOZE illumination is 4.2378% small / 4.1484% large.
- [Standalone run 36261887593](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/36261887593) passes API 34 large and API 35 small, all seven pickers and rectangle Battery taps. DOZE illumination is 3.6426% / 1.9643%. No WFF expression failure or application crash was found in either workflow's reviewed logs.
- [Versioned screenshots and evidence](VALIDATION.md) distinguish unavailable stock-emulator weather and synthetic renderer fixtures from the earlier physical Samsung report. Active system charging/status overlays still obscure part of the bottom shortcut.


The user installed an earlier preview on the API 36 Galaxy Watch and confirmed the forecast appears correctly in the rectangle and its tap opens Samsung Weather. The version 11 Samsung picker and layout, format/refresh edge cases, upgrade persistence and battery/ambient checks remain pending on physical hardware. Stock-emulator fixtures do not establish Samsung integration. The observed OEM interface is not a published stable Samsung API; commercial support and production signing remain release questions. The CI AAB contains a debug-signed embedded face and is a test artifact only.

The GitHub connector currently returns `403 Resource not accessible by integration` when creating a draft PR. This file preserves the review description; no PR has been created by the agent.
