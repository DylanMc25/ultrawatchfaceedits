package com.example.ultrainfoboard.bridge;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.ContentObserver;
import android.graphics.Bitmap;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.Looper;
import android.os.RemoteException;

import androidx.wear.watchface.complications.data.ComplicationData;
import androidx.wear.watchface.complications.data.ComplicationType;
import androidx.wear.watchface.complications.data.PlainComplicationText;
import androidx.wear.watchface.complications.data.SmallImage;
import androidx.wear.watchface.complications.data.SmallImageComplicationData;
import androidx.wear.watchface.complications.data.SmallImageType;
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService;
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester;
import androidx.wear.watchface.complications.datasource.ComplicationDataTimeline;
import androidx.wear.watchface.complications.datasource.ComplicationRequest;
import androidx.wear.watchface.complications.datasource.TimeInterval;
import androidx.wear.watchface.complications.datasource.TimelineEntry;

import java.time.Instant;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Samsung-backed charts for the fixed bottom panel and compatible external faces. */
public final class SamsungForecastService extends ComplicationDataSourceService {
    private final ExecutorService worker = Executors.newFixedThreadPool(2);
    private final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable update = () -> requestUpdates(this);
    private boolean observing;
    private final ContentObserver observer = new ContentObserver(handler) {
        @Override public void onChange(boolean selfChange) {
            handler.removeCallbacks(update);
            handler.postDelayed(update, 750);
        }
    };
    private final BroadcastReceiver clockChanges = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) { requestUpdates(context); }
    };

    public static void requestUpdates(Context context) {
        ComplicationDataSourceUpdateRequester.create(context,
                new ComponentName(context, SamsungForecastService.class)).requestUpdateAll();
    }

    @Override public void onCreate() {
        super.onCreate();
        IntentFilter filter = new IntentFilter();
        filter.addAction(Intent.ACTION_TIME_CHANGED);
        filter.addAction(Intent.ACTION_TIMEZONE_CHANGED);
        filter.addAction(Intent.ACTION_LOCALE_CHANGED);
        registerReceiver(clockChanges, filter, Context.RECEIVER_NOT_EXPORTED);
        observe();
    }

    private void observe() {
        if (observing || !SamsungWeatherReader.granted(this)) return;
        try {
            getContentResolver().registerContentObserver(Uri.parse("content://" + SamsungWeatherReader.AUTHORITY),
                    true, observer);
            observing = true;
        } catch (SecurityException ignored) { /* Scheduled requests still report the access failure. */ }
    }

    @Override public void onComplicationRequest(ComplicationRequest request, ComplicationRequestListener listener) {
        if (Looper.myLooper() != Looper.getMainLooper()) {
            handler.post(() -> onComplicationRequest(request, listener));
            return;
        }
        if (BottomPanelPreferences.get(this) == BottomPanelPreferences.Panel.NONE) {
            send(listener, new AtomicBoolean(), emptyPanel());
            return;
        }
        observe();
        AtomicBoolean delivered = new AtomicBoolean();
        CancellationSignal cancellation = new CancellationSignal();
        ScheduledFuture<?> timeout = timer.schedule(() -> {
            cancellation.cancel();
            handler.post(() -> send(listener, delivered, unavailable("Weather unavailable")));
        }, 8, TimeUnit.SECONDS);
        worker.execute(() -> {
            try {
                SamsungWeatherReader.Result result = SamsungWeatherReader.read(this, cancellation);
                BottomPanelPreferences.Panel panel = BottomPanelPreferences.get(this);
                ComplicationData data = data(result.snapshot, result.detail,
                        result.state == SamsungWeatherReader.State.PERMISSION_REQUIRED ? setupTap() : weatherTap(), panel);
                // The runtime advances these images at the hour boundary even if no poll arrives then.
                List<TimelineEntry> timeline = new ArrayList<>();
                if (panel != BottomPanelPreferences.Panel.NONE && result.state == SamsungWeatherReader.State.READY) {
                    long now = System.currentTimeMillis();
                    List<Long> expirations = new ArrayList<>();
                    for (long sample : ForecastTimeline.samples(now, ZoneId.systemDefault())) {
                        SamsungWeatherContract.Snapshot future = result.atTime(sample);
                        expirations.add(future.expiresAtMillis);
                        for (SamsungWeatherContract.Hour hour : future.hours) expirations.add(hour.expiresAtMillis);
                    }
                    for (ForecastTimeline.Interval interval : ForecastTimeline.plan(now, ZoneId.systemDefault(), expirations)) {
                        SamsungWeatherContract.Snapshot snapshot = result.atTime(interval.start());
                        timeline.add(new TimelineEntry(new TimeInterval(Instant.ofEpochMilli(interval.start()),
                                Instant.ofEpochMilli(interval.end())), data(snapshot,
                                result.detail, weatherTap(), panel)));
                    }
                    // If all future entries expire without an update, do not restore an old fresh image.
                    data = unavailable("Open Weather", panel);
                }
                ComplicationData fallback = data;
                // Menu saves and final delivery share the main thread. An old
                // worker cannot restore its chart/timeline after a newer choice.
                handler.post(() -> {
                    BottomPanelPreferences.Panel latest = BottomPanelPreferences.get(this);
                    if (latest != panel) {
                        send(listener, delivered, data(result.snapshot, result.detail,
                                result.state == SamsungWeatherReader.State.PERMISSION_REQUIRED ? setupTap() : weatherTap(), latest));
                        requestUpdates(this);
                    } else if (delivered.compareAndSet(false, true)) {
                        try {
                            listener.onComplicationDataTimeline(new ComplicationDataTimeline(fallback, timeline));
                        } catch (RemoteException ignored) { /* Watch face has disconnected. */ }
                    }
                });
            } catch (RuntimeException error) {
                handler.post(() -> send(listener, delivered, unavailable("Weather unavailable")));
            } finally {
                timeout.cancel(false);
            }
        });
    }

    private static void send(ComplicationRequestListener listener, AtomicBoolean delivered, ComplicationData data) {
        if (delivered.compareAndSet(false, true)) {
            try { listener.onComplicationData(data); } catch (RemoteException ignored) { }
        }
    }

    @Override public ComplicationData getPreviewData(ComplicationType type) {
        // Cached provider previews must not depend on a saved panel preference.
        return imageData(ForecastRenderer.render(new ForecastRenderer.RenderData("Weather",
                Collections.emptyList(), false)), "Weather", null);
    }

    public static Intent weatherIntent(Context context) {
        return context.getPackageManager().getLaunchIntentForPackage(SamsungWeatherReader.PACKAGE);
    }

    private PendingIntent weatherTap() {
        Intent launch = weatherIntent(this);
        if (launch == null) return setupTap();
        return PendingIntent.getActivity(this, 1, launch,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private PendingIntent setupTap() {
        // Clear a previously opened panel menu above setup when resuming its task.
        // Use a new request code so older cached intents cannot retain old flags.
        Intent launch = new Intent(this, SetupActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return PendingIntent.getActivity(this, 3, launch,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private ComplicationData unavailable(String text) {
        return unavailable(text, BottomPanelPreferences.get(this));
    }

    private ComplicationData unavailable(String text, BottomPanelPreferences.Panel panel) {
        if (panel == BottomPanelPreferences.Panel.NONE) return emptyPanel();
        Bitmap bitmap = panel == BottomPanelPreferences.Panel.WEATHER
                ? ForecastRenderer.render(new ForecastRenderer.RenderData(text, Collections.emptyList(), false))
                : renderPanel(null, panel);
        return imageData(bitmap, panel.title + ". " + text,
                SamsungWeatherReader.granted(this) ? weatherTap() : setupTap());
    }

    private ComplicationData data(SamsungWeatherContract.Snapshot snapshot, String detail, PendingIntent tap,
            BottomPanelPreferences.Panel panel) {
        if (panel == BottomPanelPreferences.Panel.NONE) return emptyPanel();
        return imageData(renderPanel(snapshot, panel), describePanel(snapshot, detail, panel), tap);
    }

    static Bitmap renderPanel(SamsungWeatherContract.Snapshot snapshot, BottomPanelPreferences.Panel panel) {
        if (panel == BottomPanelPreferences.Panel.WEATHER) return render(snapshot);
        List<PanelChartRenderer.Point> points = new ArrayList<>();
        if (snapshot != null) for (SamsungWeatherContract.Hour hour : snapshot.hours) {
            Double value = panel == BottomPanelPreferences.Panel.RAIN
                    ? (hour.precipitationProbability == null ? null : hour.precipitationProbability.doubleValue())
                    : chartTemperature(hour.temperature);
            points.add(new PanelChartRenderer.Point(hour.localTime, value, hour.timestampMillis));
        }
        return PanelChartRenderer.render(panel == BottomPanelPreferences.Panel.RAIN ? "Chance of rain" : "Temperature",
                panel == BottomPanelPreferences.Panel.RAIN ? "%" : snapshot == null ? "" : snapshot.unit,
                points, snapshot != null && snapshot.stale, panel == BottomPanelPreferences.Panel.RAIN);
    }

    private static Double chartTemperature(String formatted) {
        if (formatted == null || !formatted.endsWith("°")) return null;
        try {
            double value = Double.parseDouble(formatted.substring(0, formatted.length() - 1));
            return Double.isFinite(value) ? value : null;
        } catch (NumberFormatException ignored) { return null; }
    }

    static String describePanel(SamsungWeatherContract.Snapshot snapshot, String detail,
            BottomPanelPreferences.Panel panel) {
        if (panel == BottomPanelPreferences.Panel.WEATHER) return describe(snapshot, detail);
        if (snapshot == null) return panel.title + ". " + detail;
        StringBuilder description = new StringBuilder(panel.title).append(". ").append(snapshot.locationName);
        for (SamsungWeatherContract.Hour hour : snapshot.hours) {
            description.append('\n').append(hour.localTime).append(' ');
            if (panel == BottomPanelPreferences.Panel.RAIN) {
                description.append(hour.precipitationProbability == null ? "unavailable"
                        : hour.precipitationProbability + "%");
            } else description.append(hour.temperature).append(' ').append(snapshot.unit);
        }
        if (snapshot.hours.isEmpty()) description.append(". Hourly data unavailable.");
        if (snapshot.stale) description.append(". Saved forecast may be out of date.");
        return description.toString();
    }

    static ComplicationData emptyPanel() {
        // Datasource 1.3 rejects TYPE_EMPTY. A transparent SMALL_IMAGE with no
        // PendingIntent clears both old artwork and its action using a valid type.
        return imageData(Bitmap.createBitmap(ForecastRenderer.SLOT_WIDTH, ForecastRenderer.SLOT_HEIGHT,
                Bitmap.Config.ARGB_8888), "No bottom panel", null);
    }

    private static ComplicationData imageData(Bitmap source, String description, PendingIntent tap) {
        // The physical slot is 262×94. Four timeline images plus one default use 492,560 pixel bytes.
        Bitmap bitmap = Bitmap.createScaledBitmap(source,
                ForecastRenderer.SLOT_WIDTH, ForecastRenderer.SLOT_HEIGHT, true);
        if (bitmap != source) source.recycle();
        SmallImage image = new SmallImage.Builder(Icon.createWithBitmap(bitmap), SmallImageType.PHOTO).build();
        SmallImageComplicationData.Builder builder = new SmallImageComplicationData.Builder(image,
                new PlainComplicationText.Builder(description).build());
        if (tap != null) builder.setTapAction(tap);
        return builder.build();
    }

    public static Bitmap render(SamsungWeatherReader.Result result) { return render(result.snapshot); }

    private static Bitmap render(SamsungWeatherContract.Snapshot snapshot) {
        if (snapshot == null) return ForecastRenderer.render(new ForecastRenderer.RenderData(
                "Weather —", Collections.emptyList(), false));
        List<ForecastRenderer.Hour> hours = new ArrayList<>();
        for (SamsungWeatherContract.Hour hour : snapshot.hours) {
            hours.add(new ForecastRenderer.Hour(hour.localTime, hour.temperature, hour.condition, hour.day, true));
        }
        return ForecastRenderer.render(new ForecastRenderer.RenderData("Now " + snapshot.currentTemperature,
                hours, snapshot.stale, snapshot.currentCondition, snapshot.currentDay));
    }

    public static String describe(SamsungWeatherReader.Result result) { return describe(result.snapshot, result.detail); }

    private static String describe(SamsungWeatherContract.Snapshot snapshot, String detail) {
        if (snapshot == null) return detail;
        StringBuilder text = new StringBuilder(snapshot.locationName).append('\n')
                .append(snapshot.currentTemperature).append(' ').append(snapshot.unit)
                .append(' ').append(snapshot.currentConditionText);
        for (SamsungWeatherContract.Hour hour : snapshot.hours) {
            text.append('\n').append(hour.localTime).append(' ').append(hour.temperature)
                    .append(' ').append(hour.conditionText);
        }
        if (snapshot.updatedAtMillis > 0) text.append("\nSaved ").append(
                java.time.format.DateTimeFormatter.ofLocalizedDateTime(java.time.format.FormatStyle.SHORT)
                        .withZone(java.time.ZoneId.systemDefault()).format(Instant.ofEpochMilli(snapshot.updatedAtMillis)));
        if (snapshot.stale) text.append("\nSaved forecast may be out of date.");
        if (!snapshot.warnings.isEmpty()) text.append("\nSome Samsung fields are unavailable.");
        return text.toString();
    }

    @Override public void onDestroy() {
        handler.removeCallbacks(update);
        if (observing) getContentResolver().unregisterContentObserver(observer);
        unregisterReceiver(clockChanges);
        worker.shutdownNow();
        timer.shutdownNow();
        super.onDestroy();
    }
}
