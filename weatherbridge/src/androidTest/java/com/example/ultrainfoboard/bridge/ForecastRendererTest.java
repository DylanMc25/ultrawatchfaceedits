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

/** Exercises real Android text and raster drawing. All weather values here are test fixtures. */
@RunWith(AndroidJUnit4.class)
public final class ForecastRendererTest {
    @Test
    public void extremeTemperaturesAndLongLabelsRemainInsideTransparentRectangle() {
        ForecastRenderer.RenderData data = new ForecastRenderer.RenderData(
                "À présent −100.5 °F · Very long current-conditions description",
                Arrays.asList(
                        hour("11:00 PM", "−100.5°F", ForecastRenderer.HEAVY_SNOW, false),
                        hour("12:00 AM", "123.4°F", ForecastRenderer.HOT, false),
                        hour("午後11時00分", "−40.5°C", ForecastRenderer.ICY, true),
                        hour("A very long localized hour label", "100.5°C", ForecastRenderer.HAZE, true)),
                true, ForecastRenderer.HEAVY_SNOW, false);

        assertVisibleWithClearOuterBorder(ForecastRenderer.render(data));
    }

    @Test
    public void allSupportedConditionsRenderInBothDayAndNightWithoutFillingTheBackground() {
        int[] conditions = {
                ForecastRenderer.UNKNOWN, ForecastRenderer.CLEAR, ForecastRenderer.PARTLY_CLOUDY,
                ForecastRenderer.CLOUDY, ForecastRenderer.RAIN, ForecastRenderer.SHOWERS,
                ForecastRenderer.THUNDERSTORM, ForecastRenderer.SNOW, ForecastRenderer.SLEET,
                ForecastRenderer.FOG, ForecastRenderer.HAZE, ForecastRenderer.WIND,
                ForecastRenderer.HAIL, ForecastRenderer.DRIZZLE, ForecastRenderer.HEAVY_RAIN,
                ForecastRenderer.HEAVY_SNOW, ForecastRenderer.ICY, ForecastRenderer.HOT,
                ForecastRenderer.COLD, ForecastRenderer.SANDSTORM, ForecastRenderer.HURRICANE,
                ForecastRenderer.MOSTLY_CLOUDY, ForecastRenderer.MOSTLY_SUNNY,
                ForecastRenderer.SUN_SHOWERS, ForecastRenderer.SUN_THUNDER,
                ForecastRenderer.LIGHT_SNOW, ForecastRenderer.SNOW_SHOWERS,
                ForecastRenderer.RAIN_SNOW, ForecastRenderer.RAIN_THUNDER, ForecastRenderer.RAIN_SLEET
        };
        for (int condition : conditions) {
            for (boolean day : new boolean[] {true, false}) {
                Bitmap rendered = ForecastRenderer.render(conditionFixture(condition, day));
                assertVisibleWithClearOuterBorder(rendered);
                rendered.recycle();
            }
        }
    }

    @Test
    public void unknownConditionDoesNotPretendToBeClearWeather() {
        Bitmap unknown = ForecastRenderer.render(conditionFixture(ForecastRenderer.UNKNOWN, true));
        Bitmap unrecognized = ForecastRenderer.render(conditionFixture(99999, true));
        Bitmap sunny = ForecastRenderer.render(conditionFixture(ForecastRenderer.CLEAR, true));

        assertTrue("Unsupported source codes must use the unavailable icon", unknown.sameAs(unrecognized));
        assertFalse("Unknown weather must not show the clear-weather icon", unknown.sameAs(sunny));
    }

    @Test
    public void dayAndNightUseDifferentClearWeatherArtwork() {
        Bitmap day = ForecastRenderer.render(conditionFixture(ForecastRenderer.CLEAR, true));
        Bitmap night = ForecastRenderer.render(conditionFixture(ForecastRenderer.CLEAR, false));

        assertFalse("A nighttime forecast must not keep the daytime sun", day.sameAs(night));
    }

    @Test
    public void unavailableHoursIgnoreUnreadableWeatherValuesButKeepTheirTimeLabels() {
        List<ForecastRenderer.Hour> corrupt = Collections.singletonList(
                new ForecastRenderer.Hour("23:00", "99°", ForecastRenderer.CLEAR, true, false));
        List<ForecastRenderer.Hour> absent = Collections.singletonList(
                new ForecastRenderer.Hour("23:00", null, ForecastRenderer.UNKNOWN, false, false));
        Bitmap actual = ForecastRenderer.render(new ForecastRenderer.RenderData("Weather —", corrupt, false));
        Bitmap expected = ForecastRenderer.render(new ForecastRenderer.RenderData("Weather —", absent, false));

        assertTrue("An unavailable row must not leak stale/fabricated temperature or icons", actual.sameAs(expected));
        assertVisibleWithClearOuterBorder(actual);
        assertVisibleWithClearOuterBorder(ForecastRenderer.render(null));
        assertVisibleWithClearOuterBorder(ForecastRenderer.render(new ForecastRenderer.RenderData(
                null, Arrays.asList(null, hour("00:00", "−2°", ForecastRenderer.SNOW, false), null), false)));
    }

    @Test
    public void savedIndicatorDoesNotChangeForecastReadings() {
        ForecastRenderer.RenderData fresh = conditionFixture(ForecastRenderer.RAIN, true);
        ForecastRenderer.RenderData saved = new ForecastRenderer.RenderData(
                fresh.currentText, fresh.hours, true, fresh.currentCondition, fresh.currentDay);
        Bitmap before = ForecastRenderer.render(fresh);
        Bitmap after = ForecastRenderer.render(saved);

        assertFalse("A saved forecast needs a visible status indication", before.sameAs(after));
        // This region contains the hourly values, icons and times, below the current row.
        Bitmap hourlyBefore = Bitmap.createBitmap(before, 0, 54, before.getWidth(), before.getHeight() - 54);
        Bitmap hourlyAfter = Bitmap.createBitmap(after, 0, 54, after.getWidth(), after.getHeight() - 54);
        assertTrue("Marking data as saved must preserve its forecast", hourlyBefore.sameAs(hourlyAfter));
    }

    @Test
    public void exportClearlyLabeledIllustrativeFixtures() throws IOException {
        ForecastRenderer.RenderData nighttime = new ForecastRenderer.RenderData("Now 83°", Arrays.asList(
                hour("9 PM", "82°", ForecastRenderer.PARTLY_CLOUDY, false),
                hour("10 PM", "81°", ForecastRenderer.PARTLY_CLOUDY, false),
                hour("11 PM", "80°", ForecastRenderer.CLEAR, false),
                hour("12 AM", "79°", ForecastRenderer.CLEAR, false)),
                false, ForecastRenderer.PARTLY_CLOUDY, false);
        ForecastRenderer.RenderData mixed = new ForecastRenderer.RenderData("Now −12°", Arrays.asList(
                hour("22:00", "−14°", ForecastRenderer.SNOW, false),
                hour("23:00", "−15°", ForecastRenderer.SNOW_SHOWERS, false),
                hour("00:00", "−16°", ForecastRenderer.CLOUDY, false),
                hour("01:00", "−17°", ForecastRenderer.CLEAR, false)),
                true, ForecastRenderer.SNOW, false);
        ForecastRenderer.RenderData partial = new ForecastRenderer.RenderData("Weather —", Arrays.asList(
                new ForecastRenderer.Hour("9 PM", null, ForecastRenderer.UNKNOWN, false, false),
                hour("10 PM", "12°", ForecastRenderer.RAIN, false),
                null,
                hour("12 AM", "10°", ForecastRenderer.CLOUDY, false)),
                false, ForecastRenderer.UNKNOWN, false);

        exportFixture("forecast-fixture-night-black.png", nighttime, false);
        exportFixture("forecast-fixture-saved-blue.png", mixed, true);
        exportFixture("forecast-fixture-partial-blue.png", partial, true);
    }

    private static ForecastRenderer.Hour hour(String time, String temperature, int condition, boolean day) {
        return new ForecastRenderer.Hour(time, temperature, condition, day, true);
    }

    private static ForecastRenderer.RenderData conditionFixture(int condition, boolean day) {
        return new ForecastRenderer.RenderData("Now 21°", Arrays.asList(
                hour("11 PM", "20°", condition, day),
                hour("12 AM", "19°", condition, day),
                hour("1 AM", "18°", condition, day),
                hour("2 AM", "17°", condition, day)), false, condition, day);
    }

    private static void assertVisibleWithClearOuterBorder(Bitmap bitmap) {
        assertEquals("Image width must match the complication raster contract", 786, bitmap.getWidth());
        assertEquals("Image height must match the complication raster contract", 180, bitmap.getHeight());
        assertEquals(Bitmap.Config.ARGB_8888, bitmap.getConfig());
        int[] pixels = new int[bitmap.getWidth() * bitmap.getHeight()];
        bitmap.getPixels(pixels, 0, bitmap.getWidth(), 0, 0, bitmap.getWidth(), bitmap.getHeight());
        int occupied = 0;
        for (int y = 0; y < bitmap.getHeight(); y++) {
            for (int x = 0; x < bitmap.getWidth(); x++) {
                int alpha = Color.alpha(pixels[y * bitmap.getWidth() + x]);
                if (x == 0 || y == 0 || x == bitmap.getWidth() - 1 || y == bitmap.getHeight() - 1) {
                    assertEquals("Artwork touches the bitmap boundary at " + x + "," + y, 0, alpha);
                }
                if (alpha != 0) occupied++;
            }
        }
        assertTrue("The rectangle must actually contain visible text/artwork", occupied > 100);
        assertTrue("The image must preserve the watch-face background", occupied < pixels.length / 2);
    }

    private static void exportFixture(String name, ForecastRenderer.RenderData data, boolean blue)
            throws IOException {
        Bitmap rendered = ForecastRenderer.render(data);
        assertVisibleWithClearOuterBorder(rendered);
        Bitmap preview = Bitmap.createBitmap(rendered.getWidth() + 32, rendered.getHeight() + 70,
                Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(preview);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        if (blue) {
            paint.setShader(new LinearGradient(0, 0, 0, preview.getHeight(),
                    Color.rgb(43, 88, 135), Color.rgb(74, 145, 238), Shader.TileMode.CLAMP));
        } else {
            paint.setColor(Color.BLACK);
        }
        canvas.drawRect(0, 0, preview.getWidth(), preview.getHeight(), paint);
        paint.setShader(null);
        paint.setColor(Color.WHITE);
        paint.setTextSize(16f);
        paint.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        canvas.drawText("ILLUSTRATIVE FIXTURE · NOT DEVICE WEATHER", 16f, 26f, paint);
        canvas.drawBitmap(rendered, 16f, 48f, null);

        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        File directory = new File(context.getFilesDir(), "render-fixtures");
        assertTrue("Could not create fixture output directory", directory.isDirectory() || directory.mkdirs());
        try (FileOutputStream output = new FileOutputStream(new File(directory, name))) {
            assertTrue("Could not encode the fixture PNG", preview.compress(Bitmap.CompressFormat.PNG, 100, output));
        }
        preview.recycle();
        rendered.recycle();
    }
}
