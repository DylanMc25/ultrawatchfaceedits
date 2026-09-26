package com.example.ultrainfoboard.bridge;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.text.TextPaint;
import android.text.TextUtils;

import java.text.NumberFormat;
import java.util.List;
import java.util.Locale;

/** Original transparent charts for the face's 262 by 94 bottom panel. */
public final class PanelChartRenderer {
    public static final int SLOT_WIDTH = 262;
    public static final int SLOT_HEIGHT = 94;
    public static final int WIDTH = SLOT_WIDTH * 3;
    public static final int HEIGHT = SLOT_HEIGHT * 3;

    private static final int TEXT = Color.rgb(220, 242, 255);
    private static final int SECONDARY = Color.rgb(161, 209, 242);
    private static final int ACCENT = Color.rgb(177, 223, 255);
    private static final String MISSING = "\u2014";
    private static final long HOUR_MILLIS = 60 * 60 * 1000L;
    private static final float CELL_WIDTH = SLOT_WIDTH / 4f;
    private static final float CHART_TOP = 45f;
    private static final float CHART_BOTTOM = 73f;

    private PanelChartRenderer() {}

    /** Values have already been converted to the user's units by the data layer. */
    public static final class Point {
        public final String timeLabel;
        public final Double value;
        public final long timestampMillis;

        public Point(String timeLabel, Double value, long timestampMillis) {
            this.timeLabel = clean(timeLabel);
            this.value = value;
            this.timestampMillis = timestampMillis;
        }
    }

    /**
     * Draws up to four supplied readings. Missing data remains missing, including rain outside
     * 0..100. Temperature lines connect only adjacent readings exactly one elapsed hour apart;
     * midnight and daylight-saving transitions therefore need no special drawing assumptions.
     */
    public static Bitmap render(String title, String unit, List<Point> points,
            boolean stale, boolean percentage) {
        Bitmap bitmap = Bitmap.createBitmap(WIDTH, HEIGHT, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        canvas.scale(3f, 3f);
        canvas.clipRect(0, 0, SLOT_WIDTH, SLOT_HEIGHT);
        new Painter(canvas).draw(clean(title), clean(unit), points, stale, percentage);
        return bitmap;
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }

    private static boolean available(Point point, boolean percentage) {
        return point != null && point.value != null && Double.isFinite(point.value)
                && (!percentage || point.value >= 0d && point.value <= 100d);
    }

    private static final class Painter {
        private final Canvas canvas;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final TextPaint text = new TextPaint(Paint.ANTI_ALIAS_FLAG);
        private final NumberFormat numbers = NumberFormat.getIntegerInstance(Locale.getDefault());

        Painter(Canvas canvas) {
            this.canvas = canvas;
            text.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
            paint.setStrokeCap(Paint.Cap.ROUND);
            numbers.setGroupingUsed(false);
        }

        void draw(String title, String unit, List<Point> supplied, boolean stale, boolean percentage) {
            Point[] points = new Point[4];
            double minimum = Double.POSITIVE_INFINITY;
            double maximum = Double.NEGATIVE_INFINITY;
            int count = 0;
            for (int i = 0; i < points.length; i++) {
                points[i] = supplied != null && i < supplied.size() ? supplied.get(i) : null;
                if (available(points[i], percentage)) {
                    minimum = Math.min(minimum, points[i].value);
                    maximum = Math.max(maximum, points[i].value);
                    count++;
                }
            }

            String heading = title.isEmpty() ? (percentage ? "Chance of rain" : "Temperature") : title;
            if (!percentage && !unit.isEmpty()) heading += " " + unit;
            label(heading, 5f, 18f, stale ? 204f : 252f, 17f, 13f, TEXT, false);
            if (stale) label("Saved", 257f, 17f, 39f, 10.5f, 10.5f, SECONDARY, true);

            if (count == 0) {
                centeredLabel("Forecast unavailable", SLOT_WIDTH / 2f, 58f,
                        SLOT_WIDTH - 12f, 17f, 14f, SECONDARY);
            } else {
                // A minimum four-degree span makes a flat or nearly flat forecast legible.
                // Scale via half-values to avoid overflow for finite extreme input values.
                double center = minimum / 2d + maximum / 2d;
                double halfSpan = Math.max(2d, maximum / 2d - minimum / 2d);
                for (int i = 0; i < points.length; i++) {
                    float x = centerX(i);
                    Point point = points[i];
                    boolean present = available(point, percentage);
                    String value = present ? numbers.format(point.value)
                            + (percentage ? "%" : "°") : MISSING;
                    centeredLabel(value, x, 39f, CELL_WIDTH - 8f, 18f, 13f,
                            present ? TEXT : SECONDARY);
                    if (!present) continue;
                    if (percentage) {
                        float y = CHART_BOTTOM - (float) (point.value / 100d)
                                * (CHART_BOTTOM - CHART_TOP);
                        paint.setColor(ACCENT);
                        paint.setStyle(Paint.Style.FILL);
                        if (point.value == 0d) {
                            // A small zero marker distinguishes 0% from a missing reading.
                            paint.setStrokeWidth(2f);
                            canvas.drawLine(x - 9f, CHART_BOTTOM, x + 9f, CHART_BOTTOM, paint);
                        } else {
                            canvas.drawRoundRect(x - 9f, y, x + 9f, CHART_BOTTOM,
                                    2f, 2f, paint);
                        }
                    } else {
                        float y = temperatureY(point.value, center, halfSpan);
                        Point previous = i > 0 ? points[i - 1] : null;
                        if (available(previous, false)
                                && point.timestampMillis > previous.timestampMillis
                                && point.timestampMillis - previous.timestampMillis == HOUR_MILLIS) {
                            paint.setColor(SECONDARY);
                            paint.setStrokeWidth(1.7f);
                            canvas.drawLine(centerX(i - 1),
                                    temperatureY(previous.value, center, halfSpan), x, y, paint);
                        }
                        paint.setStyle(Paint.Style.FILL);
                        paint.setColor(ACCENT);
                        canvas.drawCircle(x, y, 2.6f, paint);
                    }
                }
            }
            for (int i = 0; i < points.length; i++) {
                Point point = points[i];
                centeredLabel(point == null || point.timeLabel.isEmpty() ? MISSING : point.timeLabel,
                        centerX(i), 90f, CELL_WIDTH - 8f, 14.5f, 11.5f, SECONDARY);
            }
        }

        private float temperatureY(double value, double center, double halfSpan) {
            // Dividing each operand before subtracting also handles opposite extreme values.
            double relative = value / halfSpan - center / halfSpan;
            relative = Math.max(-1d, Math.min(1d, relative));
            return (CHART_TOP + CHART_BOTTOM) / 2f
                    - (float) relative * (CHART_BOTTOM - CHART_TOP) / 2f;
        }

        private float centerX(int index) {
            return CELL_WIDTH * (index + 0.5f);
        }

        private void centeredLabel(String value, float center, float baseline, float width,
                float size, float minimum, int color) {
            fittedText(value, size, minimum, width, color);
            String line = TextUtils.ellipsize(value, text, width, TextUtils.TruncateAt.END).toString();
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
            if (measured > width) text.setTextSize(Math.max(minimum, size * width / measured));
        }
    }
}
