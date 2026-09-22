package com.example.ultrainfoboard.bridge;

import static org.junit.Assert.*;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.junit.Test;

/** Pure consistency/privacy checks; Android query and permission behavior require device tests. */
public class SamsungWeatherReaderTest {
    @Test public void rejectsUnitAndFavoriteChangesDuringRead() {
        List<Map<String, String>> before = settings("first", "0");
        assertTrue(SamsungWeatherReader.sameSelection(before, settings("first", "0")));
        assertFalse(SamsungWeatherReader.sameSelection(before, settings("first", "1")));
        assertFalse(SamsungWeatherReader.sameSelection(before, settings("second", "0")));
        assertFalse(SamsungWeatherReader.sameSelection(before, Collections.emptyList()));
    }

    @Test public void rejectsChangedObservationUpdateTimestamp() {
        assertFalse(SamsungWeatherReader.sameObservation(observation("first", "1000", "20"),
                observation("first", "2000", "20"), "first"));
        assertTrue(SamsungWeatherReader.sameObservation(observation("first", "1000", "20"),
                observation("first", "1000", "20"), "first"));
    }

    @Test public void rejectsChangedValuesEvenWithoutChangedTimestamp() {
        assertFalse(SamsungWeatherReader.sameObservation(observation("first", "1000", "20"),
                observation("first", "1000", "21"), "first"));
    }

    @Test public void rejectsRemovedOrReplacedLocationRow() {
        List<Map<String, String>> before = observation("first", "1000", "20");
        assertFalse(SamsungWeatherReader.sameObservation(before, Collections.emptyList(), "first"));
        assertFalse(SamsungWeatherReader.sameObservation(before,
                observation("second", "1000", "20"), "first"));
    }

    @Test public void retainsOnlyFieldsNeededForDisplayAndConsistency() {
        assertEquals(List.of("COL_SETTING_LAST_SEL_LOCATION", "COL_SETTING_TEMP_SCALE"),
                SamsungWeatherReader.columnsFor("settings"));
        assertTrue(SamsungWeatherReader.columnsFor("weatherinfo").contains("COL_WEATHER_UPDATE_TIME"));
        assertTrue(SamsungWeatherReader.columnsFor("weatherinfo_hour").contains("COL_HOURLY_TIME"));
        for (String path : List.of("settings", "weatherinfo", "weatherinfo_hour")) {
            for (String column : SamsungWeatherReader.columnsFor(path)) {
                assertFalse(column.contains("LATITUDE"));
                assertFalse(column.contains("LONGITUDE"));
                assertFalse(column.contains("ADDRESS"));
                assertFalse(column.endsWith("_URL"));
            }
        }
    }

    @Test(expected = IllegalArgumentException.class)
    public void rejectsUnneededEndpoint() {
        SamsungWeatherReader.columnsFor("profile_local");
    }

    private static List<Map<String, String>> settings(String key, String unit) {
        return List.of(Map.of("COL_SETTING_LAST_SEL_LOCATION", key, "COL_SETTING_TEMP_SCALE", unit));
    }

    private static List<Map<String, String>> observation(String key, String time, String temp) {
        return List.of(Map.of("COL_WEATHER_KEY", key, "COL_WEATHER_UPDATE_TIME", time,
                "COL_WEATHER_CURRENT_TEMP", temp));
    }
}
