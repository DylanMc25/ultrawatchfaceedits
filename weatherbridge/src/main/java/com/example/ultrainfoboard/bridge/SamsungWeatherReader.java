package com.example.ultrainfoboard.bridge;

import android.content.Context;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.database.Cursor;
import android.net.Uri;
import android.os.CancellationSignal;
import android.text.format.DateFormat;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;

/** Reads only Samsung's permission-protected cache. Never fetches replacement forecasts. */
public final class SamsungWeatherReader {
    public static final String PACKAGE = "com.samsung.android.watch.weather";
    public static final String AUTHORITY = PACKAGE + ".provider.level.dangerous";
    public static final String PERMISSION = PACKAGE + ".provider.permission.READ_DANGEROUS_PROVIDER";
    private static final int MAX_ROWS = 512;
    private static final Map<String, List<String>> COLUMNS = Map.of(
            "settings", List.of("COL_SETTING_LAST_SEL_LOCATION", "COL_SETTING_TEMP_SCALE"),
            "weatherinfo", List.of("COL_WEATHER_KEY", "COL_WEATHER_NAME", "COL_WEATHER_CURRENT_TEMP",
                    "COL_WEATHER_CONVERTED_ICON_NUM", "COL_WEATHER_EXPANSION_ICON_NUM",
                    "COL_WEATHER_WEATHER_TEXT", "COL_WEATHER_IS_DAY_OR_NIGHT", "COL_WEATHER_TIMEZONE",
                    "COL_WEATHER_IANA_TIMEZONE", "COL_WEATHER_TIME", "COL_WEATHER_UPDATE_TIME",
                    "COL_WEATHER_EXPIRE_TIME", "COL_WEATHER_SUNRISE_TIME", "COL_WEATHER_SUNSET_TIME",
                    "COL_WEATHER_ARCTIC_NIGHT_TYPE"),
            "weatherinfo_hour", List.of("COL_WEATHER_KEY", "COL_HOURLY_TIME", "COL_HOURLY_CURRENT_TEMP",
                    "COL_HOURLY_CONVERTED_ICON_NUM", "COL_HOURLY_EXPANSION_ICON_NUM",
                    "COL_HOURLY_WEATHER_TEXT", "COL_HOURLY_IS_DAY_OR_NIGHT", "COL_HOURLY_EXPIRE_TIME"));

    public enum State { READY, PERMISSION_REQUIRED, UNSUPPORTED, EMPTY, INCOMPATIBLE, ERROR }
    public static final class Result {
        public final State state;
        public final SamsungWeatherContract.Snapshot snapshot;
        public final String detail;
        private List<Map<String, String>> settingsRows, currentRows, hourlyRows;
        private Locale locale;
        private boolean is24Hour;
        Result(State state, SamsungWeatherContract.Snapshot snapshot, String detail) {
            this.state = state;
            this.snapshot = snapshot;
            this.detail = detail;
        }
        public SamsungWeatherContract.Snapshot atTime(long timestamp) {
            if (settingsRows == null) return snapshot;
            return SamsungWeatherContract.parse(settingsRows, currentRows, hourlyRows, timestamp, locale, is24Hour);
        }
    }

    public static boolean available(Context context) {
        ProviderInfo info = context.getPackageManager().resolveContentProvider(AUTHORITY, 0);
        return info != null && PACKAGE.equals(info.packageName) && info.exported
                && PERMISSION.equals(info.readPermission);
    }

    public static boolean granted(Context context) {
        return context.checkSelfPermission(PERMISSION) == PackageManager.PERMISSION_GRANTED;
    }

    /** Run on a background thread; caller owns and cancels the cancellation signal. */
    public static Result read(Context context, CancellationSignal cancellation) {
        if (!available(context)) return new Result(State.UNSUPPORTED, null,
                "This Samsung Weather version does not expose the expected permission-based connection.");
        if (!granted(context)) return new Result(State.PERMISSION_REQUIRED, null,
                "Allow weather access to use Samsung’s saved forecast.");
        try {
            for (int attempt = 0; attempt < 2; attempt++) {
                cancellation.throwIfCanceled();
                List<Map<String, String>> settings = query(context, "settings", null, cancellation);
                String key = SamsungWeatherContract.selectedLocation(settings);
                // Never pick an arbitrary saved city if Samsung has not supplied its favorite.
                if (key.isEmpty()) return new Result(State.EMPTY, null,
                        "Samsung Weather has no selected location. Open Weather and refresh it.");
                List<Map<String, String>> current = query(context, "weatherinfo", key, cancellation);
                List<Map<String, String>> hourly = query(context, "weatherinfo_hour", key, cancellation);
                // Samsung offers separate queries, not an atomic combined snapshot.
                List<Map<String, String>> currentAfter = query(context, "weatherinfo", key, cancellation);
                List<Map<String, String>> settingsAfter = query(context, "settings", null, cancellation);
                if (!granted(context)) return new Result(State.PERMISSION_REQUIRED, null, "Weather access was removed.");
                if (!sameSelection(settings, settingsAfter) || !sameObservation(current, currentAfter, key)) {
                    continue;
                }
                Locale locale = Locale.getDefault();
                boolean is24Hour = DateFormat.is24HourFormat(context);
                SamsungWeatherContract.Snapshot snapshot = SamsungWeatherContract.parse(settings,
                        current, hourly, System.currentTimeMillis(), locale, is24Hour);
                Result result = new Result(snapshot.usable ? State.READY : State.EMPTY, snapshot,
                        snapshot.usable ? "Reading Samsung Weather’s saved forecast." : "Samsung forecast data is unavailable.");
                result.settingsRows = settings;
                result.currentRows = current;
                result.hourlyRows = hourly;
                result.locale = locale;
                result.is24Hour = is24Hour;
                return result;
            }
            return new Result(State.ERROR, null,
                    "Samsung Weather changed while loading. Please try again.");
        } catch (SecurityException error) {
            return new Result(State.PERMISSION_REQUIRED, null,
                    "Samsung Weather refused access. Check the permission in Settings.");
        } catch (IllegalArgumentException error) {
            return new Result(State.INCOMPATIBLE, null,
                    "This Samsung Weather data format is not supported yet.");
        } catch (RuntimeException error) {
            // Exception messages and raw rows may include saved locations. Keep them off logs/UI.
            return new Result(State.ERROR, null, "Could not read Samsung Weather. Open Weather, then retry.");
        }
    }

    static boolean sameSelection(List<Map<String, String>> before, List<Map<String, String>> after) {
        return SamsungWeatherContract.selectedLocation(before).equals(SamsungWeatherContract.selectedLocation(after))
                && Objects.equals(firstValue(before, "COL_SETTING_TEMP_SCALE"), firstValue(after, "COL_SETTING_TEMP_SCALE"));
    }

    static boolean sameObservation(List<Map<String, String>> before, List<Map<String, String>> after, String key) {
        Map<String, String> original = observation(before, key);
        Map<String, String> latest = observation(after, key);
        // Equality includes UPDATE_TIME and also catches an in-place reading change without a new timestamp.
        return Objects.equals(original, latest);
    }

    static List<String> columnsFor(String path) {
        List<String> columns = COLUMNS.get(path);
        if (columns == null) throw new IllegalArgumentException("Unsupported weather path");
        return columns;
    }

    private static Map<String, String> observation(List<Map<String, String>> rows, String key) {
        for (Map<String, String> row : rows) {
            if (key.equals(row.get("COL_WEATHER_KEY"))) return row;
        }
        return null;
    }

    private static String firstValue(List<Map<String, String>> rows, String field) {
        if (rows.isEmpty()) return null;
        String value = rows.get(0).get(field);
        return value == null ? null : value.trim();
    }

    private static List<Map<String, String>> query(Context context, String path, String key,
                                                   CancellationSignal cancellation) {
        Uri uri = Uri.parse("content://" + AUTHORITY + "/" + path);
        List<String> columns = columnsFor(path);
        String selection = key == null ? null : "COL_WEATHER_KEY = ?";
        String[] arguments = key == null ? null : new String[]{key};
        try (Cursor cursor = context.getContentResolver().query(uri, null, selection, arguments, null, cancellation)) {
            if (cursor == null) return Collections.emptyList();
            List<Map<String, String>> rows = new ArrayList<>();
            while (cursor.moveToNext()) {
                cancellation.throwIfCanceled();
                if (rows.size() >= MAX_ROWS) throw new IllegalArgumentException("Too many forecast rows");
                Map<String, String> row = new LinkedHashMap<>();
                for (String column : columns) {
                    int index = cursor.getColumnIndex(column);
                    if (index >= 0 && cursor.getType(index) != Cursor.FIELD_TYPE_BLOB) {
                        row.put(column, cursor.isNull(index) ? null : cursor.getString(index));
                    }
                }
                rows.add(row);
            }
            return rows;
        }
    }
}
