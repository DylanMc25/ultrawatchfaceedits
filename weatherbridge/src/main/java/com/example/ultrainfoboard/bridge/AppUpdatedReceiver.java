package com.example.ultrainfoboard.bridge;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import java.util.concurrent.atomic.AtomicBoolean;

/** The system installs the default face once; subsequent host updates must update it explicitly. */
public final class AppUpdatedReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (!Intent.ACTION_MY_PACKAGE_REPLACED.equals(intent.getAction())) return;
        PendingResult pending = goAsync();
        AtomicBoolean finished = new AtomicBoolean();
        Runnable finish = () -> { if (finished.compareAndSet(false, true)) pending.finish(); };
        Handler handler = new Handler(Looper.getMainLooper());
        // Release the broadcast deadline; first launch retries any unfinished system update.
        handler.postDelayed(finish, 8000);
        BundledFaceInstaller.installOrUpdate(context, (success, message) -> {
            SamsungForecastService.requestUpdates(context);
            handler.removeCallbacks(finish);
            finish.run();
        });
    }
}
