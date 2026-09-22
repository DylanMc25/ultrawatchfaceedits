# Samsung-source forecast rectangle rendering

`ForecastRenderer` is original Android Canvas artwork for the existing transparent bottom rectangle. It is not Samsung artwork or a port of Samsung's rendering implementation. The familiar hierarchy is a current-conditions row followed by four hourly columns. Each column shows its supplied temperature, condition icon and local time. The other six complications and the clock retain their layout.

The bitmap is 786 × 180 ARGB pixels, corresponding to 262 × 60 face coordinates at 3× raster resolution. The renderer paints no background. A provider returns it as a photo-style small image, avoiding icon tint and preserving the pale blue/white text. One provider-owned tap action applies to the complete image. The renderer neither creates a separate tap target nor performs weather queries.

## Data contract

- `RenderData(currentText, hours, stale, currentCondition, currentDay)` receives already formatted current text and up to four `Hour` values. The three-argument overload uses an unknown current icon.
- `Hour(timeLabel, temperatureLabel, condition, day, available)` contains labels produced by the source adapter. The renderer does not change units, round numbers, calculate future hours or infer missing temperatures.
- Condition constants are our own semantic vocabulary, not raw Samsung or WFF codes. The adapter must map the inspected source version explicitly. Unsupported codes show a dash rather than a fabricated sunny icon.
- An absent hourly record or `available=false` renders a dash for its temperature and icon. An independently known time label can remain visible. Missing records never shift later forecasts into earlier columns.
- A stale result displays `Saved` in the current row; the provider's accessible description and setup screen must report the actual observation/update time and refresh status. The renderer does not invent an age.
- Null/empty values are accepted. Lists are defensively copied; extra records beyond four are ignored. Values are not mutated by rendering.

The current row uses 11.5 face-coordinate text, hourly temperatures 10.5 and local-time labels 9.6. Each column has its own bounded text width. Long localized values reduce to a minimum readable size and then ellipsize. Typical extreme temperatures such as `−100°` and both `12 AM`/`23:00` fit without truncation. Thin separators end above the time labels. All artwork is clipped to the bitmap, with small edge margins for antialiasing.

## Validation boundary

Compiling the renderer checks Android API compatibility; it does not establish readability on a physical Galaxy Watch. Device checks must compare four Samsung-source hourly records, current temperature and units with Samsung Weather, then inspect missing entries, long localized labels, day/night icons and stale data on the actual face. Replacing the rectangle must restore the selected provider's image and tap behavior. Ambient mode must hide the entire rectangle in the WFF layout.

No synthetic weather is used as the provider's real reading. Any rendering fixtures used for screenshots or tests must be clearly marked as fixtures, kept outside the live query path and never represented as Samsung integration evidence.

`ForecastRendererTest` exercises real Android raster/text rendering through instrumentation: both day/night variants of all supported condition categories, unusually wide and localized labels, temperature extremes, missing and partially available records, unknown codes, and the saved-data indicator. It verifies image size, transparent outer borders, visible content and preservation of background transparency. Semantic checks ensure an unknown condition cannot silently look sunny and unavailable values cannot leak into the image.

The export test writes three explicitly captioned synthetic previews inside the bridge app's private `files/render-fixtures/` directory, suitable for CI collection with `run-as`:

- `forecast-fixture-night-black.png`
- `forecast-fixture-saved-blue.png`
- `forecast-fixture-partial-blue.png`

These images are renderer fixtures. Even when generated on an Android emulator, they do not prove Samsung permission access, matching provider data, complication selection, or a successful Samsung Weather tap. Test execution and physical-watch results are recorded separately from this specification.
