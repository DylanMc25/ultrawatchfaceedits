package com.example.ultrainfoboard.bridge;

import static org.junit.Assert.*;

import java.time.Instant;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.junit.Test;

public class SamsungWeatherContractTest {
    private static final String KEY = "favorite-test-location";
    private static final ZoneId UTC = ZoneId.of("UTC");

    @Test public void usesFavoriteLocationAndRejectsOtherLocations() {
        Map<String, String> wrong = current("UTC");
        wrong.put("COL_WEATHER_KEY", "other-city");
        wrong.put("COL_WEATHER_CURRENT_TEMP", "50");
        Map<String, String> wrongHour = hour("2026-09-21T12:00:00Z", "50");
        wrongHour.put("COL_WEATHER_KEY", "other-city");
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("0"),
                Arrays.asList(wrong, current("UTC")), Arrays.asList(wrongHour,
                        hour("2026-09-21T12:00:00Z", "20")),
                epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertEquals(KEY, snapshot.locationKey);
        assertEquals("68°", snapshot.currentTemperature);
        assertEquals("68°", snapshot.hours.get(0).temperature);
        assertEquals(1, snapshot.hours.size());
    }

    @Test public void neverGuessesFavoriteLocation() {
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(
                Collections.singletonList(row("COL_SETTING_TEMP_SCALE", "1")),
                Collections.singletonList(current("UTC")), Collections.emptyList(),
                epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertFalse(snapshot.usable);
        assertEquals("—", snapshot.currentTemperature);
        assertTrue(snapshot.warnings.contains("selected_location_unavailable"));
    }

    @Test public void missingSelectedLocationDoesNotUseCurrentLocationInstead() {
        Map<String, String> other = current("UTC");
        other.put("COL_WEATHER_KEY", "cityId:current");
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("1"),
                Collections.singletonList(other), Collections.emptyList(), 1_800_000_000_000L,
                Locale.US, true, UTC);
        assertFalse(snapshot.usable);
        assertTrue(snapshot.warnings.contains("selected_location_not_in_cache"));
    }

    @Test public void roundsRawCelsiusExactlyOnceUsingSamsungScale() {
        assertEquals("68°", SamsungWeatherContract.temperature("20", 0));
        assertEquals("20°", SamsungWeatherContract.temperature("20", 1));
        assertEquals("-1°", SamsungWeatherContract.temperature("-1.5", 1));
        assertEquals("1°", SamsungWeatherContract.temperature("-17.5", 0));
        assertEquals("-40°", SamsungWeatherContract.temperature("-40", 0));
        assertEquals("122°", SamsungWeatherContract.temperature("50", 0));
    }

    @Test public void invalidOrUnknownUnitAndSentinelsAreUnavailable() {
        for (String raw : Arrays.asList("999", "NaN", "Infinity", "", "temperature", "1e30")) {
            assertEquals("—", SamsungWeatherContract.temperature(raw, 0));
        }
        assertEquals("—", SamsungWeatherContract.temperature("20", null));
        assertEquals("—", SamsungWeatherContract.temperature("20", 5));
    }

    @Test public void preservesHourlyPrecipitationPercentagesIncludingZeroAndOneHundred() {
        List<Map<String, String>> rows = hours("2026-09-21T12:00:00Z", 4);
        int[] percentages = {0, 1, 50, 100};
        for (int index = 0; index < rows.size(); index++) {
            rows.get(index).put("COL_HOURLY_RAIN_PROBABILITY", String.valueOf(percentages[index]));
        }
        SamsungWeatherContract.Snapshot snapshot = parse(rows, "2026-09-21T12:00:00Z", "UTC", false);
        for (int index = 0; index < percentages.length; index++) {
            assertEquals(Integer.valueOf(percentages[index]), snapshot.hours.get(index).precipitationProbability);
            assertEquals((20 + index) + "°", snapshot.hours.get(index).temperature);
        }
    }

    @Test public void neverInventsHourlyRainProbabilityForMissingOrInvalidValues() {
        for (String raw : Arrays.asList(null, "", "-1", "101", "999", "NaN", "Infinity",
                "0.5", "50.0", "rain", "2147483648")) {
            List<Map<String, String>> rows = hours("2026-09-21T12:00:00Z", 4);
            rows.get(0).put("COL_HOURLY_RAIN_PROBABILITY", "25");
            rows.get(1).put("COL_HOURLY_RAIN_PROBABILITY", raw);
            // Entry 2 has no column at all; entry 3 has a genuine zero.
            rows.get(3).put("COL_HOURLY_RAIN_PROBABILITY", "0");
            SamsungWeatherContract.Snapshot snapshot = parse(rows, "2026-09-21T12:00:00Z", "UTC", false);
            assertEquals(Integer.valueOf(25), snapshot.hours.get(0).precipitationProbability);
            assertNull("invalid " + raw, snapshot.hours.get(1).precipitationProbability);
            assertNull(snapshot.hours.get(2).precipitationProbability);
            assertEquals(Integer.valueOf(0), snapshot.hours.get(3).precipitationProbability);
            assertEquals("21°", snapshot.hours.get(1).temperature);
            assertEquals("1PM", snapshot.hours.get(1).localTime);
            assertTrue(snapshot.usable);
        }
    }

    @Test public void selectsCurrentHourAndNextThreeWhenHorizonIsLongEnough() {
        List<Map<String, String>> hours = hours("2026-09-21T10:00:00Z", 8);
        Collections.reverse(hours);
        SamsungWeatherContract.Snapshot snapshot = parse(hours, "2026-09-21T12:59:59Z", "UTC", false);
        assertEquals(Arrays.asList("12PM", "1PM", "2PM", "3PM"), labels(snapshot));
        assertFalse(snapshot.stale);
        assertEquals(epoch("2026-09-21T12:00:00Z"), snapshot.hours.get(0).timestampMillis);
    }

    @Test public void followsNativeTailFallbackAndLabelsOldForecastStale() {
        SamsungWeatherContract.Snapshot snapshot = parse(hours("2026-09-21T09:00:00Z", 5),
                "2026-09-21T12:30:00Z", "UTC", false);
        assertEquals(Arrays.asList("10AM", "11AM", "12PM", "1PM"), labels(snapshot));
        assertTrue(snapshot.stale);
        assertTrue(snapshot.warnings.contains("short_forecast_horizon"));
    }

    @Test public void supportsMidnightNoonAnd24HourLabels() {
        assertEquals(Arrays.asList("11PM", "12AM", "1AM", "2AM"),
                labels(parse(hours("2026-09-21T23:00:00Z", 6), "2026-09-21T23:10:00Z", "UTC", false)));
        assertEquals(Arrays.asList("11AM", "12PM", "1PM", "2PM"),
                labels(parse(hours("2026-09-21T11:00:00Z", 6), "2026-09-21T11:10:00Z", "UTC", false)));
        assertEquals(Arrays.asList("23:00", "00:00", "01:00", "02:00"),
                labels(parse(hours("2026-09-21T23:00:00Z", 6), "2026-09-21T23:10:00Z", "UTC", true)));
    }

    @Test public void usesLocationTimezoneAndPreservesRepeatedDstHour() {
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("1"),
                Collections.singletonList(current("America/New_York")),
                hours("2026-11-01T05:00:00Z", 6), epoch("2026-11-01T05:30:00Z"),
                Locale.US, false, ZoneId.of("America/New_York"));
        assertEquals(Arrays.asList("1AM", "1AM", "2AM", "3AM"), labels(snapshot));
        assertEquals(3_600_000L, snapshot.hours.get(1).timestampMillis - snapshot.hours.get(0).timestampMillis);
        SamsungWeatherContract.Snapshot remote = parse(hours("2026-09-21T12:00:00Z", 6),
                "2026-09-21T12:30:00Z", "Asia/Kolkata", true);
        assertEquals("17:30", remote.hours.get(0).localTime);
    }

    @Test public void unknownTimezoneDoesNotPretendToBeWatchTimezone() {
        SamsungWeatherContract.Snapshot snapshot = parse(hours("2026-09-21T12:00:00Z", 6),
                "2026-09-21T12:30:00Z", "invalid-zone", false);
        assertEquals("—", snapshot.hours.get(0).localTime);
        assertTrue(snapshot.warnings.contains("location_timezone_unavailable"));
    }

    @Test public void retainsMissingTemperatureEntryAtItsTrueHour() {
        List<Map<String, String>> rows = hours("2026-09-21T12:00:00Z", 6);
        rows.get(1).remove("COL_HOURLY_CURRENT_TEMP");
        SamsungWeatherContract.Snapshot snapshot = parse(rows, "2026-09-21T12:30:00Z", "UTC", false);
        assertEquals(4, snapshot.hours.size());
        assertEquals("1PM", snapshot.hours.get(1).localTime);
        assertEquals("—", snapshot.hours.get(1).temperature);
    }

    @Test public void dropsInvalidTimestampAndDeduplicatesWithoutInventingHours() {
        List<Map<String, String>> rows = hours("2026-09-21T12:00:00Z", 6);
        rows.add(row("COL_WEATHER_KEY", KEY, "COL_HOURLY_TIME", "invalid"));
        rows.add(new LinkedHashMap<>(rows.get(0)));
        SamsungWeatherContract.Snapshot snapshot = parse(rows, "2026-09-21T12:30:00Z", "UTC", false);
        assertEquals(4, snapshot.hours.size());
        assertTrue(snapshot.warnings.contains("invalid_hourly_timestamp"));
        assertTrue(snapshot.warnings.contains("duplicate_hourly_timestamp"));
    }

    @Test public void expirationIsExposedRatherThanSilentlyReplacingSamsungData() {
        Map<String, String> current = current("UTC");
        current.put("COL_WEATHER_EXPIRE_TIME", String.valueOf(epoch("2026-09-21T12:00:00Z")));
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("1"),
                Collections.singletonList(current), hours("2026-09-21T12:00:00Z", 6),
                epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertTrue(snapshot.stale);
        assertEquals("20°", snapshot.currentTemperature);
    }

    @Test public void mapsRawInternalAndExpansionCodesAndDayNight() {
        int[] expected = {0, 1, 2, 8, 3, 4, 4, 22, 5, 23, 24, 24, 25, 6, 6, 26,
                15, 16, 17, 10, 27, 13, 18, 19, 21, 20, 28, 11, 14};
        for (int code = 0; code < expected.length; code++) {
            Map<String, String> current = current("UTC");
            current.put("COL_WEATHER_CONVERTED_ICON_NUM", String.valueOf(code));
            SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("1"),
                    Collections.singletonList(current), Collections.emptyList(),
                    epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
            assertEquals("internal " + code, expected[code], snapshot.currentCondition);
        }
        Map<String, String> current = current("UTC");
        current.put("COL_WEATHER_CONVERTED_ICON_NUM", "1");
        current.put("COL_WEATHER_EXPANSION_ICON_NUM", "25");
        current.put("COL_WEATHER_IS_DAY_OR_NIGHT", "2");
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("1"),
                Collections.singletonList(current), Collections.emptyList(),
                epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertEquals(SamsungWeatherContract.MOSTLY_CLOUDY, snapshot.currentCondition);
        assertFalse(snapshot.currentDay);
        assertTrue(snapshot.currentDayKnown);
    }

    @Test public void unknownConditionOrDaylightDoesNotRenderInventedSun() {
        Map<String, String> current = current("UTC");
        current.remove("COL_WEATHER_IS_DAY_OR_NIGHT");
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("1"),
                Collections.singletonList(current), Collections.emptyList(),
                epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertEquals(SamsungWeatherContract.UNKNOWN, snapshot.currentCondition);
        assertFalse(snapshot.currentDayKnown);
        current.put("COL_WEATHER_CONVERTED_ICON_NUM", "999");
        current.put("COL_WEATHER_IS_DAY_OR_NIGHT", "1");
        snapshot = SamsungWeatherContract.parse(settings("1"), Collections.singletonList(current),
                Collections.emptyList(), epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertEquals(SamsungWeatherContract.UNKNOWN, snapshot.currentCondition);
    }

    @Test public void removesPartlySunnyPrecipitationVariantAtNightLikeNative() {
        Map<String, String> current = current("UTC");
        current.put("COL_WEATHER_CONVERTED_ICON_NUM", "7");
        current.put("COL_WEATHER_IS_DAY_OR_NIGHT", "2");
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings("1"),
                Collections.singletonList(current), Collections.emptyList(),
                epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertEquals(SamsungWeatherContract.SHOWERS, snapshot.currentCondition);
    }

    @Test public void emptyCacheAndUnknownSchemaRemainUnavailable() {
        SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(null, null, null,
                epoch("2026-09-21T12:30:00Z"), Locale.US, false, UTC);
        assertFalse(snapshot.usable);
        assertTrue(snapshot.hours.isEmpty());
    }

    private static SamsungWeatherContract.Snapshot parse(List<Map<String, String>> hours,
            String now, String locationZone, boolean is24Hour) {
        return SamsungWeatherContract.parse(settings("1"), Collections.singletonList(current(locationZone)),
                hours, epoch(now), Locale.US, is24Hour, UTC);
    }

    private static List<Map<String, String>> settings(String scale) {
        return Collections.singletonList(row("COL_SETTING_LAST_SEL_LOCATION", KEY,
                "COL_SETTING_TEMP_SCALE", scale));
    }

    private static Map<String, String> current(String zone) {
        return row("COL_WEATHER_KEY", KEY, "COL_WEATHER_NAME", "Fixture location",
                "COL_WEATHER_CURRENT_TEMP", "20", "COL_WEATHER_TIMEZONE", zone,
                "COL_WEATHER_CONVERTED_ICON_NUM", "0", "COL_WEATHER_IS_DAY_OR_NIGHT", "1");
    }

    private static Map<String, String> hour(String timestamp, String temperature) {
        return row("COL_WEATHER_KEY", KEY, "COL_HOURLY_TIME", String.valueOf(epoch(timestamp)),
                "COL_HOURLY_CURRENT_TEMP", temperature, "COL_HOURLY_CONVERTED_ICON_NUM", "1",
                "COL_HOURLY_IS_DAY_OR_NIGHT", "1");
    }

    private static List<Map<String, String>> hours(String first, int count) {
        List<Map<String, String>> rows = new ArrayList<>();
        for (int index = 0; index < count; index++) {
            rows.add(hour(Instant.ofEpochMilli(epoch(first) + index * 3_600_000L).toString(),
                    String.valueOf(20 + index)));
        }
        return rows;
    }

    private static List<String> labels(SamsungWeatherContract.Snapshot snapshot) {
        List<String> values = new ArrayList<>();
        for (SamsungWeatherContract.Hour hour : snapshot.hours) values.add(hour.localTime);
        return values;
    }

    private static long epoch(String timestamp) { return Instant.parse(timestamp).toEpochMilli(); }

    private static Map<String, String> row(String... entries) {
        Map<String, String> result = new LinkedHashMap<>();
        for (int index = 0; index < entries.length; index += 2) result.put(entries[index], entries[index + 1]);
        return result;
    }
}
