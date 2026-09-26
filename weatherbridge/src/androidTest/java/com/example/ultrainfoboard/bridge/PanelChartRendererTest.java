package com.example.ultrainfoboard.bridge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.Shader;
import android.graphics.Typeface;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import org.junit.Test;
import org.junit.runner.RunWith;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/** Native Android chart rendering checks; all supplied readings are illustrative test data. */
@RunWith(AndroidJUnit4.class)
public final class PanelChartRendererTest {
    private static final long HOUR = 3_600_000L;
    private static final long BASE_TIME = 1_800_000_000_000L;

    @Test
    public void temperatureLineDoesNotConnectMissingHoursOrNonconsecutiveTimestamps() {
        Bitmap consecutive = temperatures(Arrays.asList(
                point("11 PM", 12d, 0), point("12 AM", 12d, 1),
                point("1 AM", 12d, 2), point("2 AM", 12d, 3)));
        Bitmap nonconsecutive = temperatures(Arrays.asList(
                point("11 PM", 12d, 0), point("1 AM", 12d, 2),
                point("2 AM", 12d, 3), point("3 AM", 12d, 4)));
        Bitmap missing = temperatures(Arrays.asList(
                point("11 PM", 12d, 0), point("12 AM", null, 1),
                point("1 AM", 12d, 2), point("2 AM", 12d, 3)));

        // Sample only the chart between adjacent first/second markers; exclude text and dots.
        assertTrue("Consecutive hours must be joined", occupied(consecutive, 45, 43, 84, 76) > 0);
        assertEquals("An absent elapsed hour must create a real gap", 0,
                occupied(nonconsecutive, 45, 43, 84, 76));
        assertEquals("A missing value must not be interpolated", 0,
                occupied(missing, 45, 43, 151, 76));
        assertVisibleWithClearOuterBorder(consecutive);
        assertVisibleWithClearOuterBorder(nonconsecutive);
        assertVisibleWithClearOuterBorder(missing);
    }

    @Test
    public void repeatedLocalHoursRemainConnectedWhenElapsedTimeIsConsecutive() {
        Bitmap repeated = temperatures(Arrays.asList(point("1 AM", 7d, 0), point("1 AM", 8d, 1)));
        assertTrue("Clock rollback must not invent a missing elapsed hour",
                occupied(repeated, 45, 43, 84, 76) > 0);
        assertVisibleWithClearOuterBorder(repeated);
    }

    @Test
    public void rainUsesFixedScaleAndDistinguishesZeroFromMissing() {
        Bitmap rain = rainfall(Arrays.asList(point("9 AM", 0d, 0), point("10 AM", 100d, 1),
                point("11 AM", null, 2), point("12 PM", 50d, 3)));
        assertEquals("0% must not have a tall bar", 0, occupied(rain, 25, 45, 40, 67));
        assertTrue("0% should retain its zero marker", occupied(rain, 25, 72, 40, 75) > 0);
        assertTrue("100% must reach the top of the fixed scale", occupied(rain, 91, 45, 104, 48) > 0);
        assertEquals("A missing percentage must not become a zero marker", 0,
                occupied(rain, 157, 43, 170, 76));
        assertEquals("50% must not fill the upper half", 0, occupied(rain, 223, 45, 235, 57));
        assertTrue("50% must fill the lower half", occupied(rain, 223, 61, 235, 72) > 0);
        assertVisibleWithClearOuterBorder(rain);
    }

    @Test
    public void invalidNumbersAndPercentagesRenderAsUnavailable() {
        List<PanelChartRenderer.Point> invalid = Arrays.asList(point("9 AM", Double.NaN, 0),
                point("10 AM", Double.POSITIVE_INFINITY, 1), point("11 AM", -1d, 2),
                point("12 PM", 101d, 3));
        List<PanelChartRenderer.Point> missing = Arrays.asList(point("9 AM", null, 0),
                point("10 AM", null, 1), point("11 AM", null, 2), point("12 PM", null, 3));
        assertTrue("Invalid rain percentages must not be clamped into invented readings",
                rainfall(invalid).sameAs(rainfall(missing)));
        assertVisibleWithClearOuterBorder(temperatures(null));
        assertVisibleWithClearOuterBorder(rainfall(Collections.emptyList()));
    }

    @Test
    public void savedStatusPreservesValuesAndChart() {
        List<PanelChartRenderer.Point> points = Arrays.asList(point("23:00", -5d, 0),
                point("00:00", -7d, 1), point("01:00", -9d, 2), point("02:00", -6d, 3));
        Bitmap fresh = PanelChartRenderer.render("Temperature", "°C", points, false, false);
        Bitmap saved = PanelChartRenderer.render("Temperature", "°C", points, true, false);
        assertFalse("Saved weather needs its status marker", fresh.sameAs(saved));
        assertTrue("Saved status must not change the forecast",
                Bitmap.createBitmap(fresh, 0, 78, fresh.getWidth(), fresh.getHeight() - 78)
                        .sameAs(Bitmap.createBitmap(saved, 0, 78, saved.getWidth(), saved.getHeight() - 78)));
    }

    @Test
    public void extremesFlatReadingsAndLongLabelsFitTransparentPanel() {
        assertVisibleWithClearOuterBorder(PanelChartRenderer.render(
                "Temperature with an exceptionally long label", "°F",
                Arrays.asList(point("11:00 PM", -100d, 0), point("12:00 AM", 130d, 1),
                        point("午後11時00分", -40d, 2), point("A very long local time", 121d, 3)),
                true, false));
        assertVisibleWithClearOuterBorder(temperatures(Arrays.asList(point("9 AM", 5d, 0),
                point("10 AM", 5d, 1), point("11 AM", 5d, 2), point("12 PM", 5d, 3))));
        assertVisibleWithClearOuterBorder(temperatures(Arrays.asList(
                point("9 AM", -Double.MAX_VALUE, 0), point("10 AM", Double.MAX_VALUE, 1))));
    }

    @Test
    public void exportClearlyLabeledChartFixtures() throws IOException {
        exportFixture("chart-fixture-temperature-blue", PanelChartRenderer.render("Temperature", "°C",
                Arrays.asList(point("9 PM", 24d, 0), point("10 PM", 23d, 1),
                        point("11 PM", 21d, 2), point("12 AM", 20d, 3)), false, false));
        exportFixture("chart-fixture-temperature-saved-partial-blue", PanelChartRenderer.render("Temperature", "°F",
                Arrays.asList(point("23:00", -12d, 0), point("00:00", null, 1),
                        point("01:00", -17d, 2), point("03:00", -14d, 4)), true, false));
        exportFixture("chart-fixture-temperature-flat-blue", temperatures(Arrays.asList(
                point("9 AM", 18d, 0), point("10 AM", 18d, 1), point("11 AM", 18d, 2), point("12 PM", 18d, 3))));
        exportFixture("chart-fixture-rain-blue", rainfall(Arrays.asList(point("9 AM", 0d, 0),
                point("10 AM", 35d, 1), point("11 AM", 100d, 2), point("12 PM", 60d, 3))));
        exportFixture("chart-fixture-rain-missing-blue", rainfall(Arrays.asList(point("9 AM", null, 0),
                point("10 AM", 0d, 1), point("11 AM", null, 2), point("12 PM", 100d, 3))));
        exportFixture("chart-fixture-unavailable-blue", temperatures(Arrays.asList(point("9 AM", null, 0),
                point("10 AM", null, 1), point("11 AM", null, 2), point("12 PM", null, 3))));
    }

    private static PanelChartRenderer.Point point(String time, Double value, int elapsedHours) {
        return new PanelChartRenderer.Point(time, value, BASE_TIME + elapsedHours * HOUR);
    }

    private static Bitmap temperatures(List<PanelChartRenderer.Point> points) {
        return PanelChartRenderer.render("Temperature", "°C", points, false, false);
    }

    private static Bitmap rainfall(List<PanelChartRenderer.Point> points) {
        return PanelChartRenderer.render("Chance of rain", "%", points, false, true);
    }

    /** Bounds here are logical slot coordinates, not high-resolution raster pixels. */
    private static int occupied(Bitmap bitmap, int left, int top, int right, int bottom) {
        int count = 0;
        for (int y = top * 3; y < bottom * 3; y++) {
            for (int x = left * 3; x < right * 3; x++) {
                if (Color.alpha(bitmap.getPixel(x, y)) != 0) count++;
            }
        }
        return count;
    }

    private static void assertVisibleWithClearOuterBorder(Bitmap bitmap) {
        assertEquals(786, bitmap.getWidth());
        assertEquals(282, bitmap.getHeight());
        assertEquals(Bitmap.Config.ARGB_8888, bitmap.getConfig());
        int[] pixels = new int[bitmap.getWidth() * bitmap.getHeight()];
        bitmap.getPixels(pixels, 0, bitmap.getWidth(), 0, 0, bitmap.getWidth(), bitmap.getHeight());
        int occupied = 0;
        for (int y = 0; y < bitmap.getHeight(); y++) {
            for (int x = 0; x < bitmap.getWidth(); x++) {
                int alpha = Color.alpha(pixels[y * bitmap.getWidth() + x]);
                if (x == 0 || y == 0 || x == bitmap.getWidth() - 1 || y == bitmap.getHeight() - 1) {
                    assertEquals("Artwork touches boundary at " + x + "," + y, 0, alpha);
                }
                if (alpha != 0) occupied++;
            }
        }
        assertTrue("The chart needs visible text and data", occupied > 100);
        assertTrue("The face background must remain visible", occupied < pixels.length / 2);
    }

    private static void exportFixture(String name, Bitmap rendered) throws IOException {
        assertVisibleWithClearOuterBorder(rendered);
        Bitmap delivered = Bitmap.createScaledBitmap(rendered, 262, 94, true);
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        File directory = new File(context.getFilesDir(), "render-fixtures");
        assertTrue(directory.isDirectory() || directory.mkdirs());
        Bitmap fullPreview = fixturePreview(rendered, false);
        Bitmap deliveredPreview = fixturePreview(delivered, true);
        writeFixture(directory, name + ".png", fullPreview);
        writeFixture(directory, name + "-delivered.png", delivered);
        writeFixture(directory, name + "-delivered-preview.png", deliveredPreview);
        fullPreview.recycle();
        deliveredPreview.recycle();
        delivered.recycle();
        rendered.recycle();
    }

    private static Bitmap fixturePreview(Bitmap image, boolean delivered) {
        Bitmap preview = Bitmap.createBitmap(image.getWidth() + 32, image.getHeight() + 70,
                Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(preview);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setShader(new LinearGradient(0, 0, 0, preview.getHeight(),
                Color.rgb(43, 88, 135), Color.rgb(74, 145, 238), Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, preview.getWidth(), preview.getHeight(), paint);
        paint.setShader(null);
        paint.setColor(Color.WHITE);
        paint.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        paint.setTextSize(delivered ? 11f : 16f);
        canvas.drawText("ILLUSTRATIVE FIXTURE · NOT DEVICE WEATHER", 16f, delivered ? 19f : 26f, paint);
        if (delivered) canvas.drawText("262 × 94 delivered pixels · shown 1:1", 16f, 35f, paint);
        canvas.drawBitmap(image, null, new Rect(16, 48, 16 + image.getWidth(), 48 + image.getHeight()), null);
        return preview;
    }

    private static void writeFixture(File directory, String name, Bitmap bitmap) throws IOException {
        try (FileOutputStream output = new FileOutputStream(new File(directory, name))) {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output));
        }
    }
}
