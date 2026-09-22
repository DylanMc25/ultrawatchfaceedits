package com.example.ultrainfoboard.bridge;

import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeSet;

/** Bounded display intervals; never merge across a cache expiry to save an image. */
public final class ForecastTimeline {
    public static final int MAX_ENTRIES = 7;
    private static final long HORIZON = 3 * 3_600_000L;
    public record Interval(long start, long end) { }
    private ForecastTimeline() { }

    /** Samples exactly where the adapter's watch-hour floor changes, including DST transitions. */
    public static List<Long> samples(long now, ZoneId zone) {
        List<Long> result = new ArrayList<>();
        result.add(now);
        long previous = hourFloor(now, zone);
        long end = now + HORIZON;
        for (long at = Math.floorDiv(now, 60_000L) * 60_000L + 60_000L; at < end; at += 60_000L) {
            long floor = hourFloor(at, zone);
            if (floor != previous) result.add(at);
            previous = floor;
        }
        return result;
    }

    public static List<Interval> plan(long now, ZoneId zone, List<Long> expirations) {
        TreeSet<Long> points = new TreeSet<>(samples(now, zone));
        long end = now + HORIZON;
        points.add(end);
        for (Long at : expirations) if (at != null && at > now && at < end) points.add(at);
        List<Long> sorted = new ArrayList<>(points);
        List<Interval> result = new ArrayList<>();
        for (int i = 0; i + 1 < sorted.size() && result.size() < MAX_ENTRIES; i++) {
            result.add(new Interval(sorted.get(i), sorted.get(i + 1)));
        }
        return result;
    }

    private static long hourFloor(long at, ZoneId zone) {
        ZonedDateTime time = Instant.ofEpochMilli(at).atZone(zone);
        return time.withMinute(0).withSecond(0).withNano(0).toInstant().toEpochMilli();
    }
}
