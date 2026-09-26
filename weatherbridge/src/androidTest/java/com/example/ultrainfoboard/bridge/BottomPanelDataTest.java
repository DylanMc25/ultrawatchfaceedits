package com.example.ultrainfoboard.bridge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.wear.watchface.complications.data.ComplicationData;
import androidx.wear.watchface.complications.data.ComplicationType;
import androidx.wear.watchface.complications.data.SmallImageComplicationData;

import org.junit.Test;
import org.junit.runner.RunWith;

import java.time.Instant;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Integration checks for the panel preference, datasource value mapping, and empty result. */
@RunWith(AndroidJUnit4.class)
public final class BottomPanelDataTest {
    private static final long NOW = Instant.parse("2026-09-26T12:00:00Z").toEpochMilli();
    private static final String LOCATION = "chart-fixture-location";

    @Test
    public void noneClearsTheImageAndTapWithAValidSmallImageResult() {
        ComplicationData data = SamsungForecastService.emptyPanel();
        assertEquals("The datasource must return its declared format", ComplicationType.SMALL_IMAGE, data.getType());
        assertNull("None must clear the previously configured weather action", data.getTapAction());
        assertTrue(data instanceof SmallImageComplicationData);
        SmallImageComplicationData imageData = (SmallImageComplicationData) data;
        Drawable drawable = imageData.getSmallImage().getImage().loadDrawable(context());
        assertTrue("The empty panel must carry a bitmap", drawable instanceof BitmapDrawable);
        Bitmap bitmap = ((BitmapDrawable) drawable).getBitmap();
        assertEquals(262, bitmap.getWidth());
        assertEquals(94, bitmap.getHeight());
        int[] pixels = new int[bitmap.getWidth() * bitmap.getHeight()];
        bitmap.getPixels(pixels, 0, bitmap.getWidth(), 0, 0, bitmap.getWidth(), bitmap.getHeight());
        for (int pixel : pixels) assertEquals("None must not leave old artwork or a placeholder", 0, Color.alpha(pixel));
    }

    @Test
    public void savedChoicesRoundTripAndUnknownValuesFallBackToWeather() throws Exception {
        Context context = context();
        SharedPreferences prefs = context.getSharedPreferences(BottomPanelPreferences.FILE, Context.MODE_PRIVATE);
        boolean hadChoice = prefs.contains(BottomPanelPreferences.KEY);
        String original = prefs.getString(BottomPanelPreferences.KEY, null);
        try {
            assertEquals(BottomPanelPreferences.Panel.WEATHER, BottomPanelPreferences.Panel.fromId(null));
            assertEquals(BottomPanelPreferences.Panel.WEATHER, BottomPanelPreferences.Panel.fromId("retired-chart"));
            assertTrue(prefs.edit().putString(BottomPanelPreferences.KEY, "retired-chart").commit());
            assertEquals(BottomPanelPreferences.Panel.WEATHER, BottomPanelPreferences.get(context));
            for (BottomPanelPreferences.Panel panel : BottomPanelPreferences.Panel.values()) {
                BottomPanelPreferences.set(context, panel);
                // A synchronous barrier flushes the asynchronous save before reopening a context.
                assertTrue(prefs.edit().commit());
                Context reopened = context.createPackageContext(context.getPackageName(), 0);
                assertEquals(panel, BottomPanelPreferences.get(reopened));
                assertEquals(panel, BottomPanelPreferences.Panel.fromId(panel.id));
                assertEquals(panel.id, prefs.getString(BottomPanelPreferences.KEY, null));
            }
        } finally {
            SharedPreferences.Editor editor = prefs.edit();
            if (hadChoice) editor.putString(BottomPanelPreferences.KEY, original);
            else editor.remove(BottomPanelPreferences.KEY);
            assertTrue("Restore the panel choice for later editor tests", editor.commit());
            SamsungForecastService.requestUpdates(context);
        }
    }

    @Test
    public void rainReadsPercentagesIndependentlyOfTemperatureAndDescribesMissingValues() {
        SamsungWeatherContract.Snapshot original = fixture(0);
        SamsungWeatherContract.Snapshot changedTemperatures = fixture(15);
        Bitmap first = SamsungForecastService.renderPanel(original, BottomPanelPreferences.Panel.RAIN);
        Bitmap changed = SamsungForecastService.renderPanel(changedTemperatures, BottomPanelPreferences.Panel.RAIN);
        assertTrue("Rain bars must never use temperature values", first.sameAs(changed));
        String description = SamsungForecastService.describePanel(original, "Fixture", BottomPanelPreferences.Panel.RAIN);
        assertTrue(description.startsWith("Chance of rain."));
        assertTrue(description.contains("12:00 0%"));
        assertTrue(description.contains("13:00 35%"));
        assertTrue(description.contains("14:00 unavailable"));
        assertTrue(description.contains("15:00 100%"));
        assertFalse("Rain accessibility text must not announce temperature readings", description.contains("°"));
        assertFalse("A missing probability must not masquerade as 0%", description.contains("14:00 0%"));
        first.recycle();
        changed.recycle();
    }

    @Test
    public void eachVisibleModeRendersWithAndWithoutDataWithinTimelineMemoryBudget() {
        SamsungWeatherContract.Snapshot snapshot = fixture(0);
        Bitmap previous = null;
        for (BottomPanelPreferences.Panel panel : new BottomPanelPreferences.Panel[] {
                BottomPanelPreferences.Panel.WEATHER, BottomPanelPreferences.Panel.TEMPERATURE,
                BottomPanelPreferences.Panel.RAIN}) {
            Bitmap rendered = SamsungForecastService.renderPanel(snapshot, panel);
            assertNotNull(rendered);
            assertEquals(786, rendered.getWidth());
            assertEquals(282, rendered.getHeight());
            if (previous != null) {
                assertFalse("Selecting a different chart must change its artwork", previous.sameAs(rendered));
                previous.recycle();
            }
            previous = rendered;
            Bitmap delivered = Bitmap.createScaledBitmap(rendered, 262, 94, true);
            assertTrue("Each mode must fit four timeline images plus the fallback under 512 KiB",
                    (long) delivered.getAllocationByteCount() * (ForecastTimeline.MAX_ENTRIES + 1) < 512 * 1024);
            delivered.recycle();
            Bitmap unavailable = SamsungForecastService.renderPanel(null, panel);
            assertNotNull(unavailable);
            assertFalse("No data must not repeat the fixture's readings", unavailable.sameAs(rendered));
            unavailable.recycle();
        }
        if (previous != null) previous.recycle();
        String temperature = SamsungForecastService.describePanel(snapshot, "Fixture",
                BottomPanelPreferences.Panel.TEMPERATURE);
        assertTrue(temperature.contains("12:00 20°"));
        assertTrue(temperature.contains("°C"));
        assertFalse(temperature.contains("%"));
    }

    private static Context context() {
        return InstrumentationRegistry.getInstrumentation().getTargetContext();
    }

    private static SamsungWeatherContract.Snapshot fixture(int temperatureOffset) {
        List<Map<String, String>> settings = Collections.singletonList(row(
                SamsungWeatherContract.SELECTED_LOCATION, LOCATION, "COL_SETTING_TEMP_SCALE", "1"));
        Map<String, String> current = row("COL_WEATHER_KEY", LOCATION,
                "COL_WEATHER_NAME", "Illustrative fixture", "COL_WEATHER_TIMEZONE", "UTC",
                "COL_WEATHER_CURRENT_TEMP", String.valueOf(20 + temperatureOffset),
                "COL_WEATHER_WEATHER_CODE", "1", "COL_WEATHER_IS_DAY_OR_NIGHT", "1",
                "COL_WEATHER_UPDATE_TIME", String.valueOf(NOW),
                "COL_WEATHER_EXPIRE_TIME", String.valueOf(NOW + 8 * 3_600_000L));
        List<Map<String, String>> hours = new ArrayList<>();
        String[] rain = {"0", "35", null, "100", "50"};
        for (int i = 0; i < rain.length; i++) {
            Map<String, String> hour = row("COL_WEATHER_KEY", LOCATION,
                    "COL_HOURLY_TIME", String.valueOf(NOW + i * 3_600_000L),
                    "COL_HOURLY_CURRENT_TEMP", String.valueOf(20 + temperatureOffset + i),
                    "COL_HOURLY_IS_DAY_OR_NIGHT", "1", "COL_HOURLY_WEATHER_CODE", "1",
                    "COL_HOURLY_EXPIRE_TIME", String.valueOf(NOW + 8 * 3_600_000L));
            if (rain[i] != null) hour.put("COL_HOURLY_RAIN_PROBABILITY", rain[i]);
            hours.add(hour);
        }
        return SamsungWeatherContract.parse(settings, Collections.singletonList(current), hours,
                NOW, Locale.US, true, ZoneId.of("UTC"));
    }

    private static Map<String, String> row(String... values) {
        Map<String, String> row = new LinkedHashMap<>();
        for (int i = 0; i < values.length; i += 2) row.put(values[i], values[i + 1]);
        return row;
    }
}
