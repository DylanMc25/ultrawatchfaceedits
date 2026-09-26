# Samsung weather adapter: observed contract

Investigated 2026-09-21 against the user-supplied WeatherWatch version code **113060000**, Info Brick **100104110**, Ultra Info Board **100104110**, and ComplicationHelper **100104104**. This describes observed interoperability facts, not a published Samsung SDK. APK hashes and the earlier access investigation are in [SAMSUNG_APK_FINDINGS.md](SAMSUNG_APK_FINDINGS.md).

The implementation is original. Samsung binaries, decompiled implementations, icons, and fonts are not included. Device access and comparison with Samsung Weather remain necessary before calling the integration verified.

## Permission and endpoint

The candidate authority is `com.samsung.android.watch.weather.provider.level.dangerous`. Its exported provider requires the existing permission `com.samsung.android.watch.weather.provider.permission.READ_DANGEROUS_PROVIDER`. Request that permission through Android's normal runtime permission prompt. Do not declare ownership of the permission or use a forced grant.

WeatherWatch's manifest declares this permission at protection level `0x1`. `DangerousLevelContentProvider` extends `AbsWeatherContentProvider` directly and only changes the authority; the inspected query path does not inherit or call the signature validator. Provider inheritance and dispatch were also checked against DEX in the earlier investigation. Ultra's own `data/e1.java` declares the same dangerous authority and fully qualified permission; the model has distinct DEFAULT and DANGEROUS variants. This supports the interpretation that the route is intentional, but does not prove Samsung commercially supports external applications using it.

The normal provider and ComplicationHelper are separate interfaces with signature checks. The adapter must not fall back to those protected routes if the user denies permission or the runtime route fails. Permission existence, effective protection flags, grant behavior, query success, denial, and revocation still require verification on the actual watch.

| URI suffix | Read result | Adapter use |
| --- | --- | --- |
| `/settings` | Settings rows | Favorite location and temperature scale |
| `/weatherinfo` | Current weather rows | Current reading, location metadata and cache timestamps |
| `/weatherinfo_hour` | Hourly rows | Four native-style forecast entries |
| `/settings/TEMP_SCALE` | Temperature scale only | Observed endpoint; unnecessary for the combined read |

Use `COL_WEATHER_KEY=?` and one selection argument to filter current/hourly reads. The provider recognizes this key; its data source is not a general arbitrary-SQL endpoint. The inspected base does not apply the requested `sortOrder` and ordinary projections do not limit current/hourly columns, so sort the returned hours locally and consume only needed columns. Do not log complete cursor rows or coordinates.

## Favorite location and fields

Samsung's helper obtains `WeatherSettingApi.getFavoriteKey()`, then selects weather with the same key. The library creates that setting from **`COL_SETTING_LAST_SEL_LOCATION`**. It is not equivalent to the first database row, a GPS lookup, or the currently viewed city. The literal key `cityId:current` is one possible location, not a guaranteed favorite.

The adapter uses the favorite key strictly. If it is absent, or its current row is absent, display unavailable instead of silently selecting another city. Current/hourly/settings calls are separate reads, so a settings change during a read can otherwise mix units or locations. The Android reader reads the selected current record and settings again after the hourly query. If the favorite, scale, update timestamp or selected current values changed, it discards that attempt and retries once. A second inconsistent attempt returns an error, with no mixed snapshot. This is a consistency guard, not an atomic transaction guarantee when Samsung changes hourly rows without changing the current record.

| Column | Meaning and use |
| --- | --- |
| `COL_SETTING_LAST_SEL_LOCATION` | Favorite key, required |
| `COL_SETTING_TEMP_SCALE` | `0` Fahrenheit; `1` Celsius; other/missing values are unsupported |
| `COL_WEATHER_KEY` | Join key for current and hourly rows |
| `COL_WEATHER_NAME` | Local location name; keep local to the app |
| `COL_WEATHER_CURRENT_TEMP` / `COL_HOURLY_CURRENT_TEMP` | Raw Celsius floats, **not already converted display values** |
| `COL_WEATHER_CONVERTED_ICON_NUM` / `COL_HOURLY_CONVERTED_ICON_NUM` | Internal weather condition codes described below |
| `COL_WEATHER_EXPANSION_ICON_NUM` / `COL_HOURLY_EXPANSION_ICON_NUM` | More specific condition code where present |
| `COL_WEATHER_WEATHER_TEXT` / `COL_HOURLY_WEATHER_TEXT` | Provider's condition description |
| `COL_WEATHER_IS_DAY_OR_NIGHT` / `COL_HOURLY_IS_DAY_OR_NIGHT` | `1` day; `2` night; `3` unspecified |
| `COL_WEATHER_TIMEZONE` | Native watch-face label time zone |
| `COL_WEATHER_IANA_TIMEZONE` | Additional zone field; used only if primary zone cannot be parsed |
| `COL_WEATHER_TIME` / `COL_HOURLY_TIME` | Epoch timestamps in **milliseconds** |
| `COL_WEATHER_UPDATE_TIME` | Last weather update timestamp |
| `COL_WEATHER_EXPIRE_TIME` / `COL_HOURLY_EXPIRE_TIME` | Cache expiry timestamps; zero means unspecified |
| `COL_HOURLY_RAIN_PROBABILITY` | Optional integer precipitation percentage for that exact hourly record |
| `COL_WEATHER_SUNRISE_TIME` / `COL_WEATHER_SUNSET_TIME` | Day/night fallback timestamps |
| `COL_WEATHER_ARCTIC_NIGHT_TYPE` | `1` continuous daylight; `2` polar night; otherwise normal |

`999` is a temperature/no-value sentinel and must not render as `999°`. Missing, malformed and non-finite values remain unavailable. The adapter does not synthesize an hourly record for a gap or repeat another hour's temperature to fill one.

### Hourly precipitation evidence (2026-09-26)

The supplied WeatherWatch APK also exposes actual hourly precipitation probabilities through the same authorized `/weatherinfo_hour` endpoint. This is a separate field from precipitation amount and from the condition icon; it is not calculated from either.

- `ContentProviderDataSource.getHourly` delegates to `CursorDbDao.getHourlyInfo`. `CursorRoomDao_Impl.getHourlyInfo` selects the rows of `TABLE_HOURLY_INFO`, including the selected-location variant with `COL_WEATHER_KEY = ?`.
- `WeatherDatabase_Impl$1.createAllTables` defines `COL_HOURLY_RAIN_PROBABILITY` as a nullable integer column. `HourlyEntity.rainProbability` is a nullable `Integer`.
- `DbToWeatherExtKt.toIndexList(HourlyEntity)` excludes null and negative probabilities before calling `toProbability(HourlyEntity)`, which uses the stored integer directly. `ConvertHourlyPrecipIndex.getHourlyPrecipProb` labels the corresponding forecast value with `ProbUnits.PERCENT`.
- `PrecipitationIndex` uses `999` as its absent probability default; `isEmpty` checks that sentinel. The upstream hourly precipitation model includes rain, snow, and mixed precipitation, so the stored percentage describes precipitation chance despite the historical `RAIN_PROBABILITY` column name.

The original adapter retains this optional field as `Hour.precipitationProbability`. Only integer percentages from 0 through 100 are accepted. Missing columns, nulls, negative values, values above 100 (including 999), malformed text, and fractional representations remain `null`; no value is clamped or multiplied by 100. Zero remains a real 0%. An unavailable probability does not remove that hour's temperature/icon/time or contaminate adjacent hours. Chart renderers must leave missing readings unavailable and must not join a graph across them.

This is evidence of the schema and native interpretation in WeatherWatch 113060000, not proof that every location or Samsung weather backend populates the field. Its presence and chart values still need comparison on the user's physical Galaxy Watch. Inspection used Android SDK `apkanalyzer dex code` against the supplied APK; no extracted implementation is shipped.

## Conversion and selecting the four hours

The direct WeatherWatch endpoint returns database temperatures in Celsius. Samsung's helper first constructs temperature values from those rows, then applies the selected display scale. For Fahrenheit it calculates Celsius × 1.8 + 32, casts to float, and uses Java `Math.round`; Celsius uses `Math.round` directly. This matters for negative half values: `-1.5°C` displays `-1°` under that rounding rule. Unknown units must not be guessed from locale.

Info Brick `Z1/O.q` and Ultra `p002a2/O.q` use the same four-entry rule:

1. Take the watch's current hour boundary, with minutes/seconds/milliseconds zeroed.
2. If the cached forecast extends at least four hours beyond that boundary minus one millisecond, use the first four available records at or after the boundary. This can include the **current hour**, rather than always starting one hour ahead.
3. If the forecast ends earlier, use its last four records, or fewer if fewer exist. This native fallback can display past cached hours. The adapter preserves those values and marks the snapshot stale if it contains past hours or expired data.
4. Format each actual timestamp in the weather location's time zone. Do not label a record using a calculated “now + N hours” value.

The adapter sorts and de-duplicates by timestamp before selection because the query contract does not enforce ordering. Duplicate timestamps keep the first returned record and produce a diagnostic warning. Distinct epochs during the repeated DST hour remain distinct records.

The supplied Samsung panel hardcodes English twelve-hour hour labels. This project's adapter preserves the prior requirement to respect the device's 12/24-hour setting and locale; it uses `ha` or `HH:mm`. This is an intentional presentation difference, not a claim of pixel-identical Samsung text formatting. An invalid/missing location time zone shows an unavailable label rather than pretending the watch zone belongs to the forecast location.

## Conditions and original icon rendering

The direct provider's `CONVERTED_ICON_NUM` is **not the same numbering as the helper's final icon number**. The library maps internal conditions to a visual icon, applies day/night, and then the helper exposes that result. Passing the direct number to the face's `j1.S()` interpretation would choose wrong icons.

On the inspected API 36 generation, the library selects the expansion code when it is at least the internal code, otherwise the internal code. The adapter maps that observed condition to our own renderer category. These names describe weather semantics; the renderer draws original artwork.

| Direct internal code | Condition |
| --- | --- |
| 0 | Clear/sunny |
| 1 | Partly cloudy |
| 2 | Cloudy |
| 3 | Fog |
| 4 | Rain |
| 5, 6 | Showers |
| 7 | Partly sunny with showers |
| 8 | Thunderstorm |
| 9 | Partly sunny with thunder |
| 10, 11 | Light snow |
| 12 | Partly sunny with flurries |
| 13, 14 | Snow |
| 15 | Rain and snow |
| 16 | Ice |
| 17 | Hot |
| 18 | Cold |
| 19 | Windy |
| 20 | Rain and thunder |
| 21 | Heavy rain |
| 22 | Sandstorm |
| 23 | Hurricane |
| 24 | Mostly sunny/mostly clear at night |
| 25 | Mostly cloudy |
| 26 | Rain and sleet |
| 27 | Hail |
| 28 | Heavy snow |

Unknown codes stay unknown. Do not replace an unknown weather condition with a sunny icon. For an unspecified day/night flag, the adapter consults sunrise/sunset and polar state; if those are also unavailable, it avoids fabricating a sun or moon. Native library fallback behavior can be more permissive, so this deliberately honest unavailable state is another documented difference. Night variants of partly sunny precipitation use the corresponding plain precipitation category, matching the inspected native icon conversion.

## Refresh and tap behavior

The provider assigns notification URIs to returned cursors. The native face also listens for `com.samsung.android.watch.weather.action.WEATHER_DATA_SYNC`. A notification or broadcast should only trigger a new authorized read; do not trust data sent by another broadcaster. Delivery while our provider process is absent, notification propagation across authorities, and Samsung's background limits remain physical-watch checks. Re-read on normal complication requests and refresh the selected hours when the hour changes; do not promise real-time matching before measuring delivery.

The adapter reads Samsung's cache. It does not independently request a forecast, change Samsung settings, force a location update, or call private write operations. Opening Samsung Weather is the ordinary exported launcher intent. Tapping any point within our forecast complication should open Samsung Weather; replacing the complication must restore the replacement provider's tap action.

## Evidence and validation

Relevant local inspection sources, identified for reproducibility but not redistributed:

- WeatherWatch `DangerousLevelContentProvider`, `AbsWeatherContentProvider.query`, `ContentProviderDataSource.getWeather/getHourly/getSetting`.
- ComplicationHelper library `H0/b` cursor mapping; `p008f0/c.e` settings, `.l` weather construction, `.p` condition normalization, `.r` temperature normalization; `B/i.d` display conversion.
- ComplicationHelper `WeatherComplicationContentProvider.query`: favorite-key selection and current/hourly cursor construction.
- `WeatherIconConverter`, `ForecastTime`, `ForecastTimeKt`: condition/day-night semantics.
- Info Brick `Z1/O.q` and Ultra `p002a2/O.q`: displayed hour selection and label formatting.

The pure-Java adapter tests cover favorite-location isolation, missing favorite/current rows, Celsius/Fahrenheit conversion and negative ties, extreme and invalid readings, individual missing entries, sorting/de-duplication, current-hour selection, native tail fallback, cache expiry, midnight/noon, 12/24-hour labels, location-zone differences, DST repeated hours, every observed condition code, expansion code selection, and unavailable day/night. Reader helper tests cover settings/current-record changes and the column allowlist, which excludes coordinates, addresses and web URLs from retained rows. These are fixture-based interoperability tests, not proof of Samsung permission or on-watch equivalence.

Hourly precipitation fixtures additionally cover genuine 0%, 1%, 50%, and 100%, absent columns, null, negative/out-of-range/sentinel/malformed values, and preservation of each hour's existing temperature and time when precipitation is unavailable.

Required physical comparison: grant/deny/revoke permission; compare current and four hourly values against the native panel at the same moment; repeat after a unit change, favorite-location change, hour rollover, Samsung Weather refresh, watch restart, and offline period. Confirm actual effective permission metadata, schema, update timestamps, app opening, and replacement of the rectangle by another provider. No physical comparison results are recorded yet.
