# Add Samsung forecast and curated chart menu to the bundled Wear OS 6 face

The ordinary bottom complication picker offers many providers that do not suit a wide chart. Version 14 replaces it with an app-owned **Bottom panel** menu containing **Weather, Temperature trend, Chance of rain, None**. Weather retains the Samsung-source hourly forecast; the two new charts use that same cache. All chart taps open Samsung Weather (or permission setup), while None sends a transparent image with no PendingIntent. The other six complication slots and the liked version 13 layout stay unchanged.

A Wear OS 6 host bundles the separately signed resource-only WFF2 face through Watch Face Push. The host menu is required because this WFF version cannot conditionally enable whole slots or whitelist selected provider apps. The bundled face retires editable slot 7 and adds fixed slot 8 to avoid preserving an incompatible old provider assignment. The standalone legacy face retains its original rectangle behavior.

Hourly precipitation is read only from the observed permission-protected Samsung column `COL_HOURLY_RAIN_PROBABILITY`. Nullable, invalid and sentinel values stay unavailable; values are never inferred from weather icons. Original artwork, selected location, units, hourly labels, missing-data gaps, saved-data status and the delivered image-memory budget are retained. No Samsung binaries, artwork or replacement weather feed are shipped.

Preview host/face certificates are pinned and checked in CI. Normal same-key updates preserve app preferences and should preserve the existing weather permission; physical upgrade retention remains pending. Production signing and Samsung interface support remain release prerequisites.

## Validation

- Version 14 local debug APK, test APK, unsigned host AAB, JVM tests and lint pass. All 19 Python checks and all ten official Push checks, including syntax/resources and memory, pass.
- New native tests cover temperature/rain rendering, missing entries, elapsed-hour gaps, DST labels, flat/extreme values, 0/100 percentages, and transparent image bounds. Emulator execution is pending.
- Native menu automation checks the six editable slots, excluded bottom picker, each saved choice after restart, distinct visible chart content, three whole-area tap positions, and a blank/noninteractive None state. Emulator execution is pending.
- Version 13 evidence in [run 36266834935](https://github.com/DylanMc25/ultrawatchfaceedits/actions/runs/36266834935) and [versioned results](VALIDATION.md) documents the previous ordinary-picker design, not validation of this new menu.

The user previously confirmed that the forecast matches Samsung Weather and tapping opens it. The new chart menu, hourly precipitation comparison, upgrade persistence, physical readability and battery/ambient behavior remain physical-watch checks. Stock emulators lack Samsung Weather. The observed OEM data interface is not a published stable SDK. The CI AAB contains a debug-signed embedded face and is a test artifact only.

The GitHub connector previously returned `403 Resource not accessible by integration` when creating a draft PR. This file preserves the review description; no PR has been created by the agent.
