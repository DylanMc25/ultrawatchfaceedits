package com.example.ultrainfoboard.bridge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assume.assumeFalse;

import android.content.Context;
import android.os.CancellationSignal;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Stock emulators establish missing-provider behavior, not Samsung integration. */
@RunWith(AndroidJUnit4.class)
public final class WeatherConnectionTest {
    @Test public void absentSamsungWeatherNeverProducesInventedReadings() {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        assumeFalse(SamsungWeatherReader.available(context));
        SamsungWeatherReader.Result result = SamsungWeatherReader.read(context, new CancellationSignal());
        assertEquals(SamsungWeatherReader.State.UNSUPPORTED, result.state);
        assertNull(result.snapshot);
    }
}
