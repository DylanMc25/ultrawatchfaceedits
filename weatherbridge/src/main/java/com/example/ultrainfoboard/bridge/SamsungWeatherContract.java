package com.example.ultrainfoboard.bridge;

import java.time.DateTimeException;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Original adapter for the permission-protected schema observed in WeatherWatch 113060000. */
public final class SamsungWeatherContract {
    public static final String AUTHORITY = "com.samsung.android.watch.weather.provider.level.dangerous";
    public static final String READ_PERMISSION =
            "com.samsung.android.watch.weather.provider.permission.READ_DANGEROUS_PROVIDER";
    public static final String LOCATION_KEY = "COL_WEATHER_KEY";
    public static final String SELECTED_LOCATION = "COL_SETTING_LAST_SEL_LOCATION";
    public static final String UNAVAILABLE = "—";

    // Presentation categories shared with ForecastRenderer, not Samsung's raw condition numbers.
    public static final int UNKNOWN = -1, CLEAR = 0, PARTLY_CLOUDY = 1, CLOUDY = 2,
            RAIN = 3, SHOWERS = 4, THUNDERSTORM = 5, SNOW = 6, SLEET = 7,
            FOG = 8, HAZE = 9, WIND = 10, HAIL = 11, DRIZZLE = 12,
            HEAVY_RAIN = 13, HEAVY_SNOW = 14, ICY = 15, HOT = 16, COLD = 17,
            SANDSTORM = 18, HURRICANE = 19, MOSTLY_CLOUDY = 20, MOSTLY_SUNNY = 21,
            SUN_SHOWERS = 22, SUN_THUNDER = 23, LIGHT_SNOW = 24, SNOW_SHOWERS = 25,
            RAIN_SNOW = 26, RAIN_THUNDER = 27, RAIN_SLEET = 28;

    private SamsungWeatherContract() {}

    public static final class Hour {
        public final long timestampMillis;
        public final String temperature;
        public final int condition;
        public final boolean day;
        public final boolean dayKnown;
        public final String localTime;
        public final String conditionText;
        public final long expiresAtMillis;
        /** Samsung's hourly precipitation percentage, or null when absent/invalid. */
        public final Integer precipitationProbability;

        private Hour(long timestampMillis, String temperature, int condition, boolean day,
                boolean dayKnown, String localTime, String conditionText, long expiresAtMillis,
                Integer precipitationProbability) {
            this.timestampMillis = timestampMillis;
            this.temperature = temperature;
            this.condition = condition;
            this.day = day;
            this.dayKnown = dayKnown;
            this.localTime = localTime;
            this.conditionText = conditionText;
            this.expiresAtMillis = expiresAtMillis;
            this.precipitationProbability = precipitationProbability;
        }
    }

    public static final class Snapshot {
        public final String locationKey;
        public final String locationName;
        public final String timeZoneId;
        public final String unit;
        public final String currentTemperature;
        public final int currentCondition;
        public final String currentConditionText;
        public final boolean currentDay;
        public final boolean currentDayKnown;
        public final long updatedAtMillis;
        public final long expiresAtMillis;
        public final List<Hour> hours;
        public final List<String> warnings;
        public final boolean usable;
        public final boolean stale;

        private Snapshot(String locationKey, String locationName, String timeZoneId, String unit,
                String currentTemperature, int currentCondition, String currentConditionText,
                boolean currentDay, boolean currentDayKnown, long updatedAtMillis,
                long expiresAtMillis, List<Hour> hours, List<String> warnings, boolean stale) {
            this.locationKey = locationKey;
            this.locationName = locationName;
            this.timeZoneId = timeZoneId;
            this.unit = unit;
            this.currentTemperature = currentTemperature;
            this.currentCondition = currentCondition;
            this.currentConditionText = currentConditionText;
            this.currentDay = currentDay;
            this.currentDayKnown = currentDayKnown;
            this.updatedAtMillis = updatedAtMillis;
            this.expiresAtMillis = expiresAtMillis;
            this.hours = Collections.unmodifiableList(new ArrayList<>(hours));
            this.warnings = Collections.unmodifiableList(new ArrayList<>(warnings));
            this.usable = !UNAVAILABLE.equals(currentTemperature) || !hours.isEmpty();
            this.stale = stale;
        }
    }

    /** Returns the exact favorite key used by Samsung's native watch-face weather model. */
    public static String selectedLocation(List<Map<String, String>> settingsRows) {
        if (settingsRows == null || settingsRows.isEmpty()) return "";
        return value(settingsRows.get(0), SELECTED_LOCATION);
    }

    public static Snapshot parse(List<Map<String, String>> settingsRows,
            List<Map<String, String>> currentRows, List<Map<String, String>> hourlyRows,
            long nowMillis, Locale locale, boolean is24Hour) {
        return parse(settingsRows, currentRows, hourlyRows, nowMillis, locale, is24Hour,
                ZoneId.systemDefault());
    }

    /** Explicit watch zone makes hour-boundary and DST behavior independently testable. */
    public static Snapshot parse(List<Map<String, String>> settingsRows,
            List<Map<String, String>> currentRows, List<Map<String, String>> hourlyRows,
            long nowMillis, Locale locale, boolean is24Hour, ZoneId watchZone) {
        List<String> warnings = new ArrayList<>();
        Map<String, String> settings = settingsRows == null || settingsRows.isEmpty()
                ? Collections.emptyMap() : settingsRows.get(0);
        String key = selectedLocation(settingsRows);
        Integer scale = integer(settings, "COL_SETTING_TEMP_SCALE");
        String unit = scale != null && scale == 0 ? "°F"
                : scale != null && scale == 1 ? "°C" : "";
        if (unit.isEmpty()) warnings.add("temperature_unit_unavailable");
        if (key.isEmpty()) {
            warnings.add("selected_location_unavailable");
            return unavailable(key, unit, warnings);
        }

        Map<String, String> current = findLocation(currentRows, key);
        if (current == null) {
            warnings.add("selected_location_not_in_cache");
            return unavailable(key, unit, warnings);
        }
        ZoneId locationZone = zone(value(current, "COL_WEATHER_TIMEZONE"));
        if (locationZone == null) locationZone = zone(value(current, "COL_WEATHER_IANA_TIMEZONE"));
        if (locationZone == null) warnings.add("location_timezone_unavailable");
        Locale displayLocale = locale == null ? Locale.getDefault() : locale;
        DateTimeFormatter timeFormat = DateTimeFormatter.ofPattern(is24Hour ? "HH:mm" : "ha",
                displayLocale);
        ZonedDateTime now = Instant.ofEpochMilli(nowMillis).atZone(watchZone);
        long hourStart = now.withMinute(0).withSecond(0).withNano(0).toInstant().toEpochMilli();
        long sunrise = timestamp(current, "COL_WEATHER_SUNRISE_TIME");
        long sunset = timestamp(current, "COL_WEATHER_SUNSET_TIME");
        int polarType = numberOr(integer(current, "COL_WEATHER_ARCTIC_NIGHT_TYPE"), 0);
        Boolean currentDay = day(integer(current, "COL_WEATHER_IS_DAY_OR_NIGHT"), polarType,
                sunrise, sunset, nowMillis);
        int currentCondition = condition(current, "COL_WEATHER_");
        if (currentDay == null && needsDay(currentCondition)) currentCondition = UNKNOWN;
        if (Boolean.FALSE.equals(currentDay)) currentCondition = nightCondition(currentCondition);
        String currentTemperature = temperature(value(current, "COL_WEATHER_CURRENT_TEMP"), scale);
        long updated = timestamp(current, "COL_WEATHER_UPDATE_TIME");
        long expires = timestamp(current, "COL_WEATHER_EXPIRE_TIME");
        boolean stale = expires > 0 && nowMillis >= expires;

        Map<Long, Hour> byTimestamp = new LinkedHashMap<>();
        if (hourlyRows != null) {
            for (Map<String, String> row : hourlyRows) {
                if (!key.equals(value(row, LOCATION_KEY))) continue;
                long timestamp = timestamp(row, "COL_HOURLY_TIME");
                if (timestamp == 0) {
                    if (!warnings.contains("invalid_hourly_timestamp")) warnings.add("invalid_hourly_timestamp");
                    continue;
                }
                Boolean daylight = day(integer(row, "COL_HOURLY_IS_DAY_OR_NIGHT"), polarType,
                        sunrise, sunset, nowMillis);
                int category = condition(row, "COL_HOURLY_");
                if (daylight == null && needsDay(category)) category = UNKNOWN;
                if (Boolean.FALSE.equals(daylight)) category = nightCondition(category);
                String time = locationZone == null ? UNAVAILABLE
                        : timeFormat.format(Instant.ofEpochMilli(timestamp).atZone(locationZone))
                                .toUpperCase(displayLocale);
                Hour hour = new Hour(timestamp, temperature(value(row, "COL_HOURLY_CURRENT_TEMP"), scale),
                        category, Boolean.TRUE.equals(daylight), daylight != null, time,
                        value(row, "COL_HOURLY_WEATHER_TEXT"), timestamp(row, "COL_HOURLY_EXPIRE_TIME"),
                        probability(row, "COL_HOURLY_RAIN_PROBABILITY"));
                if (byTimestamp.putIfAbsent(timestamp, hour) != null
                        && !warnings.contains("duplicate_hourly_timestamp")) {
                    warnings.add("duplicate_hourly_timestamp");
                }
            }
        }
        List<Hour> allHours = new ArrayList<>(byTimestamp.values());
        allHours.sort(Comparator.comparingLong(hour -> hour.timestampMillis));
        List<Hour> displayed = new ArrayList<>();
        if (!allHours.isEmpty()) {
            // Samsung's panel retains the last four cached entries if its forecast horizon is short.
            if (allHours.get(allHours.size() - 1).timestampMillis < hourStart - 1 + 4 * 3_600_000L) {
                displayed.addAll(allHours.subList(Math.max(0, allHours.size() - 4), allHours.size()));
                warnings.add("short_forecast_horizon");
            } else {
                for (Hour hour : allHours) {
                    if (hour.timestampMillis >= hourStart) displayed.add(hour);
                    if (displayed.size() == 4) break;
                }
            }
        }
        for (Hour hour : displayed) {
            if (hour.timestampMillis < hourStart
                    || (hour.expiresAtMillis > 0 && nowMillis >= hour.expiresAtMillis)) stale = true;
        }
        if (displayed.isEmpty()) warnings.add("hourly_forecast_unavailable");
        if (stale) warnings.add("cached_forecast_expired");
        return new Snapshot(key, value(current, "COL_WEATHER_NAME"),
                locationZone == null ? "" : locationZone.getId(), unit,
                currentTemperature, currentCondition, value(current, "COL_WEATHER_WEATHER_TEXT"),
                Boolean.TRUE.equals(currentDay), currentDay != null, updated, expires,
                displayed, warnings, stale);
    }

    /** The stored float is Celsius even when Samsung's presentation unit is Fahrenheit. */
    public static String temperature(String rawCelsius, Integer scale) {
        if (scale == null || (scale != 0 && scale != 1) || rawCelsius == null) return UNAVAILABLE;
        try {
            float celsius = Float.parseFloat(rawCelsius);
            if (!Float.isFinite(celsius) || celsius == 999f) return UNAVAILABLE;
            float converted = scale == 0 ? (float) (celsius * 1.8d + 32.0d) : celsius;
            if (!Float.isFinite(converted) || converted <= Integer.MIN_VALUE || converted >= Integer.MAX_VALUE) {
                return UNAVAILABLE;
            }
            return Math.round(converted) + "°";
        } catch (NumberFormatException ignored) {
            return UNAVAILABLE;
        }
    }

    private static Snapshot unavailable(String key, String unit, List<String> warnings) {
        return new Snapshot(key, "", "", unit, UNAVAILABLE, UNKNOWN, "", false, false,
                0, 0, Collections.emptyList(), warnings, false);
    }

    private static Map<String, String> findLocation(List<Map<String, String>> rows, String key) {
        if (rows != null) for (Map<String, String> row : rows) {
            if (key.equals(value(row, LOCATION_KEY))) return row;
        }
        return null;
    }

    private static ZoneId zone(String raw) {
        if (raw.isEmpty()) return null;
        try { return ZoneId.of(raw); }
        catch (DateTimeException ignored) { return null; }
    }

    private static Boolean day(Integer flag, int polarType, long sunrise, long sunset, long now) {
        if (polarType == 1) return true;
        if (polarType == 2) return false;
        if (flag != null && flag == 1) return true;
        if (flag != null && flag == 2) return false;
        if (sunrise == 0 || sunset == 0) return null;
        long time = Math.floorMod(now, 86_400_000L);
        long rise = Math.floorMod(sunrise, 86_400_000L);
        long set = Math.floorMod(sunset, 86_400_000L);
        return rise < set ? time > rise && time <= set : time > rise || time <= set;
    }

    private static boolean needsDay(int category) {
        return category == CLEAR || category == PARTLY_CLOUDY || category == MOSTLY_CLOUDY
                || category == MOSTLY_SUNNY || category == SUN_SHOWERS
                || category == SUN_THUNDER || category == SNOW_SHOWERS;
    }

    private static int nightCondition(int category) {
        return switch (category) {
            case SUN_SHOWERS -> SHOWERS;
            case SUN_THUNDER -> THUNDERSTORM;
            case SNOW_SHOWERS -> LIGHT_SNOW;
            default -> category;
        };
    }

    private static int condition(Map<String, String> row, String prefix) {
        Integer internal = integer(row, prefix + "CONVERTED_ICON_NUM");
        Integer expansion = integer(row, prefix + "EXPANSION_ICON_NUM");
        // The inspected API 36 Samsung library selects expansion codes when at least as specific.
        int selected = internal == null ? -1 : internal;
        if (expansion != null && expansion >= selected) selected = expansion;
        return switch (selected) {
            case 0 -> CLEAR;
            case 1 -> PARTLY_CLOUDY;
            case 2 -> CLOUDY;
            case 3 -> FOG;
            case 4 -> RAIN;
            case 5, 6 -> SHOWERS;
            case 7 -> SUN_SHOWERS;
            case 8 -> THUNDERSTORM;
            case 9 -> SUN_THUNDER;
            case 10, 11 -> LIGHT_SNOW;
            case 12 -> SNOW_SHOWERS;
            case 13, 14 -> SNOW;
            case 15 -> RAIN_SNOW;
            case 16 -> ICY;
            case 17 -> HOT;
            case 18 -> COLD;
            case 19 -> WIND;
            case 20 -> RAIN_THUNDER;
            case 21 -> HEAVY_RAIN;
            case 22 -> SANDSTORM;
            case 23 -> HURRICANE;
            case 24 -> MOSTLY_SUNNY;
            case 25 -> MOSTLY_CLOUDY;
            case 26 -> RAIN_SLEET;
            case 27 -> HAIL;
            case 28 -> HEAVY_SNOW;
            default -> UNKNOWN;
        };
    }

    private static Integer integer(Map<String, String> row, String field) {
        try { return Integer.valueOf(value(row, field)); }
        catch (NumberFormatException ignored) { return null; }
    }

    private static Integer probability(Map<String, String> row, String field) {
        Integer result = integer(row, field);
        // The stored value is a percentage, not a 0..1 ratio. In particular,
        // preserve genuine 0%, and never clamp Samsung's 999 sentinel to 100%.
        return result != null && result >= 0 && result <= 100 ? result : null;
    }

    private static long timestamp(Map<String, String> row, String field) {
        try {
            long value = Long.parseLong(value(row, field));
            return value > 999 ? value : 0;
        } catch (NumberFormatException ignored) { return 0; }
    }

    private static int numberOr(Integer number, int fallback) { return number == null ? fallback : number; }

    private static String value(Map<String, String> row, String field) {
        return row == null || row.get(field) == null ? "" : row.get(field).trim();
    }
}
