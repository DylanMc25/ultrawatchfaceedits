package com.example.ultrainfoboard.bridge;

import static org.junit.Assert.*;
import java.time.Instant;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import org.junit.Test;

public class ForecastTimelineTest {
    private static long t(String iso) { return Instant.parse(iso).toEpochMilli(); }
    @Test public void expiryInsideHourChangesImageAtExpiryNotAtNextPoll() {
        long now = t("2026-09-21T10:05:00Z");
        long expiry = t("2026-09-21T10:07:00Z");
        List<ForecastTimeline.Interval> result = ForecastTimeline.plan(now, ZoneId.of("UTC"), List.of(expiry));
        assertEquals(new ForecastTimeline.Interval(now, expiry), result.get(0));
        assertEquals(new ForecastTimeline.Interval(expiry, t("2026-09-21T11:00:00Z")), result.get(1));
        // The extra expiry image consumes the fourth entry; the fallback begins five minutes early.
        assertEquals(t("2026-09-21T13:00:00Z"), result.get(result.size() - 1).end());
        assertTrue(result.get(result.size() - 1).end() < now + 3 * 3_600_000L);
    }
    @Test public void unexpiredForecastStillCoversThreeHoursAcrossHourRollover() {
        long now = t("2026-09-21T10:05:00Z");
        var result = ForecastTimeline.plan(now, ZoneId.of("UTC"), List.of());
        assertEquals(4, result.size());
        assertEquals(new ForecastTimeline.Interval(now, t("2026-09-21T11:00:00Z")), result.get(0));
        assertEquals(now + 3 * 3_600_000L, result.get(3).end());
    }
    @Test public void duplicatePastAndUnspecifiedExpiriesDoNotProduceEmptyIntervals() {
        long now = t("2026-09-21T10:05:00Z");
        long expiry = now + 60_000L;
        var result = ForecastTimeline.plan(now, ZoneId.of("UTC"), List.of(0L, now - 1, now, expiry, expiry));
        assertEquals(4, result.size());
        for (int i = 0; i < result.size(); i++) {
            assertTrue(result.get(i).start() < result.get(i).end());
            if (i > 0) assertEquals(result.get(i-1).end(), result.get(i).start());
        }
    }
    @Test public void excessExpiriesShortenTimelineInsteadOfShowingUnmarkedExpiredData() {
        long now = t("2026-09-21T10:05:00Z");
        List<Long> expirations = new ArrayList<>();
        for (int i = 1; i <= 20; i++) expirations.add(now + i * 60_000L);
        var result = ForecastTimeline.plan(now, ZoneId.of("UTC"), expirations);
        assertEquals(4, result.size());
        assertEquals(now + 4 * 60_000L, result.get(3).end());
    }
    @Test public void repeatedDstHourIsADistinctDisplayBoundary() {
        var samples = ForecastTimeline.samples(t("2026-11-01T05:30:00Z"), ZoneId.of("America/New_York"));
        assertTrue(samples.contains(t("2026-11-01T06:00:00Z")));
        assertTrue(samples.contains(t("2026-11-01T07:00:00Z")));
    }
    @Test public void halfHourDaylightSavingShiftDoesNotSkipFollowingHour() {
        var samples = ForecastTimeline.samples(t("2026-10-03T15:20:00Z"), ZoneId.of("Australia/Lord_Howe"));
        assertTrue(samples.contains(t("2026-10-03T15:30:00Z")));
        assertTrue(samples.contains(t("2026-10-03T16:00:00Z")));
    }
}
