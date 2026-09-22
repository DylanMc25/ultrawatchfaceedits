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
import java.time.ZonedDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.TreeSet;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** A normal replaceable SMALL_IMAGE complication, backed exclusively by Samsung's cache. */
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
        observe();
        AtomicBoolean delivered = new AtomicBoolean();
        CancellationSignal cancellation = new CancellationSignal();
        ScheduledFuture<?> timeout = timer.schedule(() -> {
            cancellation.cancel();
            send(listener, delivered, unavailable("Weather unavailable"));
        }, 8, TimeUnit.SECONDS);
        worker.execute(() -> {
            try {
                SamsungWeatherReader.Result result = SamsungWeatherReader.read(this, cancellation);
                ComplicationData data = data(result);
                // The runtime advances these images at the hour boundary even if no poll arrives then.
                List<TimelineEntry> timeline = new ArrayList<>();
                if (result.state == SamsungWeatherReader.State.READY) {
                    ZonedDateTime boundary = ZonedDateTime.now().truncatedTo(ChronoUnit.HOURS);
                    TreeSet<Instant> points = new TreeSet<>();
                    long now = System.currentTimeMillis();
                    points.add(Instant.ofEpochMilli(now));
                    for (int i = 1; i <= 3; i++) points.add(boundary.plusHours(i).toInstant());
                    Instant last = points.last();
                    List<Long> expirations = new ArrayList<>();
                    expirations.add(result.snapshot.expiresAtMillis);
                    for (SamsungWeatherContract.Hour hour : result.snapshot.hours) expirations.add(hour.expiresAtMillis);
                    for (long expiry : expirations) {
                        Instant at = Instant.ofEpochMilli(expiry);
                        if (expiry > now && at.isBefore(last)) points.add(at);
                    }
                    List<Instant> ordered = new ArrayList<>(points);
                    for (int i = 0; i < ordered.size() - 1; i++) {
                        Instant start = ordered.get(i);
                        Instant end = ordered.get(i + 1);
                        SamsungWeatherContract.Snapshot snapshot = result.atTime(
                                start.toEpochMilli());
                        timeline.add(new TimelineEntry(new TimeInterval(start, end), data(snapshot,
                                result.detail, weatherTap())));
                    }
                    // If all future entries expire without an update, do not restore an old fresh image.
                    data = unavailable("Open Weather");
                }
                if (delivered.compareAndSet(false, true)) {
                    try {
                        listener.onComplicationDataTimeline(new ComplicationDataTimeline(data, timeline));
                    } catch (RemoteException ignored) { /* Watch face has disconnected. */ }
                }
            } catch (RuntimeException error) {
                send(listener, delivered, unavailable("Weather unavailable"));
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
        // Selection previews are illustrative labels, never fabricated live readings.
        return unavailable("Samsung forecast");
    }

    public static Intent weatherIntent(Context context) {
        return context.getPackageManager().getLaunchIntentForPackage(SamsungWeatherReader.PACKAGE);
    }

    private PendingIntent weatherTap() {
        Intent launch = weatherIntent(this);
        if (launch == null) launch = new Intent(this, SetupActivity.class);
        return PendingIntent.getActivity(this, 1, launch,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private PendingIntent setupTap() {
        return PendingIntent.getActivity(this, 2, new Intent(this, SetupActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private ComplicationData unavailable(String text) {
        return imageData(ForecastRenderer.render(new ForecastRenderer.RenderData(text, Collections.emptyList(), false)),
                text, SamsungWeatherReader.granted(this) ? weatherTap() : setupTap());
    }

    private ComplicationData data(SamsungWeatherReader.Result result) {
        return data(result.snapshot, result.detail,
                result.state == SamsungWeatherReader.State.PERMISSION_REQUIRED ? setupTap() : weatherTap());
    }

    private ComplicationData data(SamsungWeatherContract.Snapshot snapshot, String detail, PendingIntent tap) {
        return imageData(render(snapshot), describe(snapshot, detail), tap);
    }

    private ComplicationData imageData(Bitmap source, String description, PendingIntent tap) {
        // The physical slot is 262×60. Bound IPC memory, including the three timeline images.
        Bitmap bitmap = Bitmap.createScaledBitmap(source, 262, 60, true);
        if (bitmap != source) source.recycle();
        SmallImage image = new SmallImage.Builder(Icon.createWithBitmap(bitmap), SmallImageType.PHOTO).build();
        return new SmallImageComplicationData.Builder(image,
                new PlainComplicationText.Builder(description).build()).setTapAction(tap).build();
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
