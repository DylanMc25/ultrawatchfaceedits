package com.example.ultrainfoboard.bridge;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.text.TextUtils;
import android.text.TextPaint;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Draws an original, transparent forecast image for the face's 262 by 60 slot. */
public final class ForecastRenderer {
    public static final int WIDTH = 786;
    public static final int HEIGHT = 180;

    // Our semantic values, deliberately separate from Samsung's versioned icon codes.
    public static final int UNKNOWN = -1;
    public static final int CLEAR = 0;
    public static final int PARTLY_CLOUDY = 1;
    public static final int CLOUDY = 2;
    public static final int RAIN = 3;
    public static final int SHOWERS = 4;
    public static final int THUNDERSTORM = 5;
    public static final int SNOW = 6;
    public static final int SLEET = 7;
    public static final int FOG = 8;
    public static final int HAZE = 9;
    public static final int WIND = 10;
    public static final int HAIL = 11;
    public static final int DRIZZLE = 12;
    public static final int HEAVY_RAIN = 13;
    public static final int HEAVY_SNOW = 14;
    public static final int ICY = 15;
    public static final int HOT = 16;
    public static final int COLD = 17;
    public static final int SANDSTORM = 18;
    public static final int HURRICANE = 19;
    public static final int MOSTLY_CLOUDY = 20;
    public static final int MOSTLY_SUNNY = 21;
    public static final int SUN_SHOWERS = 22;
    public static final int SUN_THUNDER = 23;
    public static final int LIGHT_SNOW = 24;
    public static final int SNOW_SHOWERS = 25;
    public static final int RAIN_SNOW = 26;
    public static final int RAIN_THUNDER = 27;
    public static final int RAIN_SLEET = 28;

    private static final int TEXT = Color.rgb(220, 242, 255);
    private static final int SECONDARY = Color.rgb(161, 209, 242);
    private static final int SEPARATOR = Color.argb(82, 161, 209, 242);
    private static final String MISSING = "\u2014";
    private static final float LOGICAL_WIDTH = 262f;
    private static final float LOGICAL_HEIGHT = 60f;
    private static final float CELL_WIDTH = LOGICAL_WIDTH / 4f;

    private ForecastRenderer() {}

    /** Labels are already localized and rounded by the data layer; do not reconvert them. */
    public static final class Hour {
        public final String timeLabel;
        public final String temperatureLabel;
        public final int condition;
        public final boolean day;
        public final boolean available;

        public Hour(String timeLabel, String temperatureLabel, int condition,
                boolean day, boolean available) {
            this.timeLabel = clean(timeLabel);
            this.temperatureLabel = clean(temperatureLabel);
            this.condition = condition;
            this.day = day;
            this.available = available;
        }
    }

    public static final class RenderData {
        public final String currentText;
        public final List<Hour> hours;
        public final boolean stale;
        public final int currentCondition;
        public final boolean currentDay;

        public RenderData(String currentText, List<Hour> hours, boolean stale) {
            this(currentText, hours, stale, UNKNOWN, true);
        }

        public RenderData(String currentText, List<Hour> hours, boolean stale,
                int currentCondition, boolean currentDay) {
            this.currentText = clean(currentText);
            // Ignore entries beyond the four-column contract and never create forecast values.
            List<Hour> copy = new ArrayList<>(4);
            if (hours != null) {
                for (int i = 0; i < Math.min(4, hours.size()); i++) {
                    copy.add(hours.get(i));
                }
            }
            this.hours = Collections.unmodifiableList(copy);
            this.stale = stale;
            this.currentCondition = currentCondition;
            this.currentDay = currentDay;
        }
    }

    /** Returns ARGB_8888 artwork; there is intentionally no background or baked-in tap target. */
    public static Bitmap render(RenderData data) {
        if (data == null) {
            data = new RenderData(MISSING, Collections.emptyList(), false);
        }
        Bitmap bitmap = Bitmap.createBitmap(WIDTH, HEIGHT, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        canvas.scale(WIDTH / LOGICAL_WIDTH, HEIGHT / LOGICAL_HEIGHT);
        canvas.clipRect(0, 0, LOGICAL_WIDTH, LOGICAL_HEIGHT);
        new Painter(canvas).draw(data);
        return bitmap;
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }

    private static final class Painter {
        private final Canvas canvas;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final TextPaint text = new TextPaint(Paint.ANTI_ALIAS_FLAG);

        Painter(Canvas canvas) {
            this.canvas = canvas;
            text.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
            paint.setStrokeCap(Paint.Cap.ROUND);
            paint.setStrokeJoin(Paint.Join.ROUND);
        }

        void draw(RenderData data) {
            icon(data.currentCondition, data.currentDay, 9f, 7.7f, 11.4f);
            float headerWidth = data.stale ? 201f : 238f;
            label(data.currentText.isEmpty() ? MISSING : data.currentText,
                    19f, 12f, headerWidth, 11.5f, 9f, TEXT, false);
            if (data.stale) {
                label("Saved", 257f, 11f, 33f, 7.5f, 7.5f, SECONDARY, true);
            }

            for (int i = 0; i < 4; i++) {
                float center = CELL_WIDTH * (i + 0.5f);
                if (i > 0) {
                    stroke(SEPARATOR, 0.8f);
                    canvas.drawLine(CELL_WIDTH * i, 20f, CELL_WIDTH * i, 45.5f, paint);
                }
                Hour hour = i < data.hours.size() ? data.hours.get(i) : null;
                boolean available = hour != null && hour.available;
                String temperature = available && !hour.temperatureLabel.isEmpty()
                        ? hour.temperatureLabel : MISSING;
                centeredLabel(temperature, center, 26f, CELL_WIDTH - 7f,
                        10.5f, 8.5f, available ? TEXT : SECONDARY);
                icon(available ? hour.condition : UNKNOWN,
                        available && hour.day, center, 37f, 13.5f);
                String time = hour == null || hour.timeLabel.isEmpty() ? MISSING : hour.timeLabel;
                centeredLabel(time, center, 56f, CELL_WIDTH - 7f, 9.6f, 8f, SECONDARY);
            }
        }

        private void centeredLabel(String value, float center, float baseline, float width,
                float size, float minimum, int color) {
            fittedText(value, size, minimum, width, color);
            CharSequence shown = TextUtils.ellipsize(value, text, width, TextUtils.TruncateAt.END);
            String line = shown.toString();
            canvas.drawText(line, center - text.measureText(line) / 2f, baseline, text);
        }

        private void label(String value, float x, float baseline, float width,
                float size, float minimum, int color, boolean rightAligned) {
            fittedText(value, size, minimum, width, color);
            String line = TextUtils.ellipsize(value, text, width, TextUtils.TruncateAt.END).toString();
            canvas.drawText(line, rightAligned ? x - text.measureText(line) : x, baseline, text);
        }

        private void fittedText(String value, float size, float minimum, float width, int color) {
            text.setColor(color);
            text.setTextSize(size);
            float measured = text.measureText(value);
            if (measured > width) {
                text.setTextSize(Math.max(minimum, size * width / measured));
            }
        }

        private void stroke(int color, float width) {
            paint.setColor(color);
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(width);
        }

        private void fill(int color) {
            paint.setColor(color);
            paint.setStyle(Paint.Style.FILL);
        }

        // Icons use our own small geometric vocabulary inside a normalized 24 by 24 box.
        private void icon(int condition, boolean day, float cx, float cy, float size) {
            int saved = canvas.save();
            canvas.translate(cx - size / 2f, cy - size / 2f);
            canvas.scale(size / 24f, size / 24f);
            switch (condition) {
                case CLEAR:
                    celestial(day, 12f, 12f, 5.1f);
                    break;
                case MOSTLY_SUNNY:
                    celestial(day, 10f, 9f, 4.3f);
                    cloud(5f, 9f, 0.76f);
                    break;
                case PARTLY_CLOUDY:
                case MOSTLY_CLOUDY:
                    celestial(day, 7f, 6.8f, 3.4f);
                    cloud(1.5f, 6f, condition == MOSTLY_CLOUDY ? 1.05f : 0.95f);
                    break;
                case CLOUDY:
                    cloud(1f, 5f, 1f);
                    break;
                case FOG:
                case HAZE:
                    if (condition == FOG) cloud(2f, 1f, 0.9f);
                    else celestial(day, 12f, 7f, 3.6f);
                    stroke(SECONDARY, 1.8f);
                    canvas.drawLine(3f, 16f, 21f, 16f, paint);
                    canvas.drawLine(5f, 20f, 19f, 20f, paint);
                    break;
                case WIND:
                case SANDSTORM:
                    wind(condition == SANDSTORM);
                    break;
                case HURRICANE:
                    stroke(SECONDARY, 2.2f);
                    canvas.drawCircle(12f, 12f, 3f, paint);
                    canvas.drawArc(new RectF(4f, 3f, 20f, 20f), 30f, 210f, false, paint);
                    canvas.drawArc(new RectF(4f, 4f, 20f, 21f), 210f, 210f, false, paint);
                    break;
                case HOT:
                    celestial(true, 8f, 9f, 3.3f);
                    thermometer(true);
                    break;
                case COLD:
                    snowflake(7f, 9f, 3.6f);
                    thermometer(false);
                    break;
                case ICY:
                    snowflake(12f, 12f, 7.3f);
                    break;
                case RAIN:
                case SHOWERS:
                case THUNDERSTORM:
                case SNOW:
                case SLEET:
                case HAIL:
                case DRIZZLE:
                case HEAVY_RAIN:
                case HEAVY_SNOW:
                case SUN_SHOWERS:
                case SUN_THUNDER:
                case LIGHT_SNOW:
                case SNOW_SHOWERS:
                case RAIN_SNOW:
                case RAIN_THUNDER:
                case RAIN_SLEET:
                    precipitation(condition, day);
                    break;
                default:
                    // Unknown codes must not silently turn into a sunny forecast.
                    stroke(SECONDARY, 2f);
                    canvas.drawLine(8f, 12f, 16f, 12f, paint);
            }
            canvas.restoreToCount(saved);
        }

        private void celestial(boolean day, float x, float y, float radius) {
            if (day) {
                stroke(SECONDARY, 1.8f);
                canvas.drawCircle(x, y, radius, paint);
                for (int i = 0; i < 8; i++) {
                    double angle = i * Math.PI / 4;
                    float cos = (float) Math.cos(angle);
                    float sin = (float) Math.sin(angle);
                    canvas.drawLine(x + cos * (radius + 2f), y + sin * (radius + 2f),
                            x + cos * (radius + 3.5f), y + sin * (radius + 3.5f), paint);
                }
            } else {
                Path moon = new Path();
                moon.moveTo(x + radius * 0.4f, y - radius);
                moon.cubicTo(x - radius * 1.4f, y - radius * 1.1f,
                        x - radius * 1.5f, y + radius * 1.1f, x, y + radius);
                moon.cubicTo(x + radius * 0.8f, y + radius,
                        x + radius * 1.2f, y + radius * 0.3f, x + radius, y);
                moon.cubicTo(x, y + radius * 0.4f,
                        x - radius * 0.3f, y - radius * 0.4f, x + radius * 0.4f, y - radius);
                moon.close();
                fill(SECONDARY);
                canvas.drawPath(moon, paint);
            }
        }

        private void cloud(float x, float y, float scale) {
            int saved = canvas.save();
            canvas.translate(x, y);
            canvas.scale(scale, scale);
            Path cloud = new Path();
            cloud.moveTo(5f, 13f);
            cloud.cubicTo(-0.5f, 13f, -0.5f, 5f, 5f, 5f);
            cloud.cubicTo(5.5f, -1f, 14f, -1f, 15.5f, 5f);
            cloud.cubicTo(22f, 4f, 24f, 13f, 17f, 13f);
            cloud.close();
            fill(SECONDARY);
            canvas.drawPath(cloud, paint);
            canvas.restoreToCount(saved);
        }

        private void precipitation(int condition, boolean day) {
            boolean partly = condition == SUN_SHOWERS || condition == SUN_THUNDER
                    || condition == SNOW_SHOWERS;
            if (partly) celestial(day, 6.5f, 5.5f, 2.4f);
            cloud(2f, partly ? 3.5f : 1.5f, 0.9f);
            if (condition == THUNDERSTORM || condition == SUN_THUNDER || condition == RAIN_THUNDER) {
                Path bolt = new Path();
                bolt.moveTo(13f, 12f);
                bolt.lineTo(8f, 19f);
                bolt.lineTo(12f, 19f);
                bolt.lineTo(10f, 24f);
                bolt.lineTo(18f, 15f);
                bolt.lineTo(13f, 15f);
                bolt.close();
                fill(TEXT);
                canvas.drawPath(bolt, paint);
                if (condition == RAIN_THUNDER) drop(5f, 17f, 3f);
                return;
            }
            boolean snow = condition == SNOW || condition == HEAVY_SNOW
                    || condition == LIGHT_SNOW || condition == SNOW_SHOWERS;
            boolean mixed = condition == RAIN_SNOW || condition == SLEET || condition == RAIN_SLEET;
            if (snow || mixed) {
                snowflake(8f, 18.7f, 2.8f);
                if (mixed) drop(16f, 17f, 4f);
                else if (condition != LIGHT_SNOW) snowflake(17f, 19f, 2.8f);
                if (condition == HEAVY_SNOW) snowflake(12f, 23f, 1f);
            } else if (condition == HAIL) {
                fill(TEXT);
                canvas.drawCircle(7f, 18f, 1.5f, paint);
                canvas.drawCircle(13f, 21f, 1.5f, paint);
                canvas.drawCircle(19f, 18f, 1.5f, paint);
            } else {
                float length = condition == DRIZZLE ? 1.8f : 4f;
                drop(7f, 17f, length);
                drop(16f, 17f, length);
                if (condition == HEAVY_RAIN) drop(12f, 20f, 3f);
            }
        }

        private void drop(float x, float y, float length) {
            stroke(TEXT, 1.8f);
            canvas.drawLine(x + 1f, y, x - 0.5f, y + length, paint);
        }

        private void snowflake(float x, float y, float radius) {
            stroke(TEXT, 1.5f);
            for (int i = 0; i < 3; i++) {
                double angle = Math.PI * i / 3;
                float dx = (float) Math.cos(angle) * radius;
                float dy = (float) Math.sin(angle) * radius;
                canvas.drawLine(x - dx, y - dy, x + dx, y + dy, paint);
            }
        }

        private void wind(boolean sand) {
            stroke(SECONDARY, 1.9f);
            Path breeze = new Path();
            breeze.moveTo(2f, 8f);
            breeze.lineTo(16f, 8f);
            breeze.cubicTo(23f, 8f, 22f, 1f, 17f, 3f);
            breeze.moveTo(4f, 13f);
            breeze.lineTo(19f, 13f);
            breeze.cubicTo(25f, 13f, 22f, 21f, 18f, 18f);
            breeze.moveTo(2f, 18f);
            breeze.lineTo(11f, 18f);
            canvas.drawPath(breeze, paint);
            if (sand) {
                fill(TEXT);
                canvas.drawCircle(5f, 22f, 0.8f, paint);
                canvas.drawCircle(10f, 3f, 0.8f, paint);
                canvas.drawCircle(14f, 22f, 0.8f, paint);
            }
        }

        private void thermometer(boolean hot) {
            stroke(TEXT, 1.7f);
            canvas.drawRoundRect(new RectF(16f, 3f, 20f, 18f), 2f, 2f, paint);
            fill(TEXT);
            canvas.drawCircle(18f, 19f, 3f, paint);
            stroke(TEXT, 1.7f);
            canvas.drawLine(18f, hot ? 6f : 14f, 18f, 19f, paint);
        }
    }
}
