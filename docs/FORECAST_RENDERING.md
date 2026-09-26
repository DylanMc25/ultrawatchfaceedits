# Samsung-source forecast rectangle rendering

`ForecastRenderer` is original Android Canvas artwork for the transparent bottom rectangle. It is not Samsung artwork or a port of Samsung's rendering implementation. The hierarchy is a current-conditions row followed by four hourly columns. Each column shows its supplied temperature, condition icon and local time. Version 11 keeps the staggered face arrangement while reducing date/time text slightly and enlarging the three circular readings and forecast.

The renderer draws at **786 × 282 ARGB pixels**, corresponding to **262 × 94** face coordinates at 3× raster resolution. The service scales this to **262 × 94** for delivery; the earlier version used 262 × 60. It paints no background and returns a photo-style small image, avoiding icon tint and preserving pale blue/white text. One provider-owned tap action applies to the complete image. The renderer neither creates a separate tap target nor performs weather queries.

Four timeline images plus the default image require **492,560 bytes** of ARGB pixels, below the 512 KiB pixel budget. Temporary supersampled bitmaps are recycled after scaling. Timeline entries split at hour changes and known expiry boundaries. Additional expiry boundaries can shorten the three-hour horizon to stay within four entries; the fallback is unavailable data, never an old image presented as fresh. This pixel calculation does not replace official WFF memory validation or runtime checks.

## Data contract

- `RenderData(currentText, hours, stale, currentCondition, currentDay)` receives already formatted current text and up to four `Hour` values. The three-argument overload uses an unknown current icon.
- `Hour(timeLabel, temperatureLabel, condition, day, available)` contains labels produced by the source adapter. The renderer does not change units, round numbers, calculate future hours or infer missing temperatures.
- Condition constants are our own semantic vocabulary, not raw Samsung or WFF codes. The adapter must map the inspected source version explicitly. Unsupported codes show a dash rather than a fabricated sunny icon.
- An absent hourly record or `available=false` renders a dash for its temperature and icon. An independently known time label can remain visible. Missing records never shift later forecasts into earlier columns.
- A stale result displays `Saved` in the current row; the provider's accessible description and setup screen must report the actual observation/update time and refresh status. The renderer does not invent an age.
- Null/empty values are accepted. Lists are defensively copied; extra records beyond four are ignored. Values are not mutated by rendering.

The current row uses 20-unit text, hourly temperatures 19 and local-time labels 15, up from 11.5/10.5/9.6. Each column has a bounded text width. Long values shrink to configured minima and then ellipsize. Thin separators end above the time labels. All artwork is clipped to the bitmap, with small edge margins for antialiasing. Final readability must be assessed on the delivered bitmap at actual watch scale, not only the 3× rendering fixture.

The provider appears as **Weather** under **Ultra Info Board Weather**. Slot 7 accepts `LONG_TEXT`, `SMALL_IMAGE` and `EMPTY`; Wear OS filters installed sources by these types. It does not use a provider whitelist. Samsung's own Weather entry is a separate current-conditions provider.

## Validation boundary

Compiling the renderer checks Android API compatibility; it does not establish readability on a physical Galaxy Watch. Device checks must compare four Samsung-source hourly records, current temperature and units with Samsung Weather, then inspect missing entries, long localized labels, day/night icons and stale data on the actual face. Replacing the rectangle must restore the selected provider's image and tap behavior. Ambient mode must hide the entire rectangle in the WFF layout.

No synthetic weather is used as the provider's real reading. Any rendering fixtures used for screenshots or tests must be clearly marked as fixtures, kept outside the live query path and never represented as Samsung integration evidence.

`ForecastRendererTest` exercises real Android raster/text rendering through instrumentation: both day/night variants of all supported condition categories, unusually wide and localized labels, temperature extremes, missing and partially available records, unknown codes, and the saved-data indicator. It verifies image size, transparent outer borders, visible content and background transparency. A delivered-bitmap test checks the enlarged size and bounded timeline pixel allocation. Semantic checks ensure an unknown condition cannot silently look sunny and unavailable values cannot leak into the image. Adding these tests is not evidence that the current version has passed emulator execution; results are tracked in [validation evidence](VALIDATION.md).

The export test writes three explicitly captioned synthetic previews inside the bridge app's private `files/render-fixtures/` directory, suitable for CI collection with `run-as`:

- `forecast-fixture-night-black.png`
- `forecast-fixture-saved-blue.png`
- `forecast-fixture-partial-blue.png`

These images are renderer fixtures. Even when generated on an Android emulator, they do not prove Samsung permission access, matching provider data, complication selection, or a successful Samsung Weather tap. Test execution and physical-watch results are recorded separately from this specification.
