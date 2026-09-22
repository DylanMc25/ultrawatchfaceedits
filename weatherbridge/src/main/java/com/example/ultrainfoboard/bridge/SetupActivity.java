package com.example.ultrainfoboard.bridge;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** On-watch permission setup and a local comparison view for the integration preview. */
public final class SetupActivity extends Activity {
    private final ExecutorService worker = Executors.newFixedThreadPool(2);
    private final Handler main = new Handler(Looper.getMainLooper());
    private CancellationSignal cancellation;
    private TextView status;
    private TextView detail;
    private ImageView forecast;
    private Button permission;
    private int generation;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setGravity(Gravity.CENTER_HORIZONTAL);
        int side = Math.round(getResources().getDisplayMetrics().widthPixels * .12f);
        content.setPadding(side, dp(30), side, dp(40));
        scroll.addView(content);
        TextView title = label("Samsung forecast", 20);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        content.addView(title);
        status = label("Checking weather access…", 14);
        content.addView(status);
        forecast = new ImageView(this);
        forecast.setAdjustViewBounds(true);
        forecast.setContentDescription("Forecast preview");
        content.addView(forecast, new LinearLayout.LayoutParams(-1, dp(65)));
        permission = button("Allow weather access", view -> requestWeatherPermission());
        content.addView(permission);
        content.addView(button("Read saved forecast", view -> refresh()));
        content.addView(button("Open Samsung Weather", view -> {
            Intent launch = SamsungForecastService.weatherIntent(this);
            if (launch != null) startActivity(launch);
            else status.setText("Samsung Weather is not installed.");
        }));
        content.addView(button("App permissions", view -> startActivity(new Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName())))));
        content.addView(button("Install or update watch face", view -> {
            status.setText("Preparing watch face…");
            BundledFaceInstaller.installOrUpdate(this, (success, message) -> {
                if (!isDestroyed()) status.setText(message);
            });
        }));
        detail = label("", 13);
        content.addView(detail);
        setContentView(scroll);
        BundledFaceInstaller.installOrUpdate(this, (success, message) -> {
            if (!isDestroyed() && !success) detail.setText(message);
        });
    }

    @Override protected void onResume() {
        super.onResume();
        refresh();
    }

    private void requestWeatherPermission() {
        if (!SamsungWeatherReader.available(this)) {
            status.setText("The expected Samsung Weather connection is unavailable on this watch.");
            return;
        }
        requestPermissions(new String[]{SamsungWeatherReader.PERMISSION}, 10);
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(requestCode, permissions, grants);
        refresh();
        SamsungForecastService.requestUpdates(this);
    }

    private void refresh() {
        if (isDestroyed()) return;
        final int request = ++generation;
        if (cancellation != null) cancellation.cancel();
        CancellationSignal signal = new CancellationSignal();
        cancellation = signal;
        permission.setVisibility(SamsungWeatherReader.granted(this) ? View.GONE : View.VISIBLE);
        status.setText("Reading Samsung Weather…");
        forecast.setImageDrawable(null);
        detail.setText("");
        Runnable timeout = () -> {
            if (isDestroyed() || request != generation) return;
            generation++;
            signal.cancel();
            status.setText("Samsung Weather took too long to respond. Open Weather, then retry.");
        };
        main.postDelayed(timeout, 8000);
        worker.execute(() -> {
            SamsungWeatherReader.Result result = SamsungWeatherReader.read(getApplicationContext(), signal);
            runOnUiThread(() -> {
                main.removeCallbacks(timeout);
                if (isDestroyed() || request != generation) return;
                status.setText(result.detail);
                forecast.setImageBitmap(SamsungForecastService.render(result));
                detail.setText(SamsungForecastService.describe(result));
                SamsungForecastService.requestUpdates(this);
            });
        });
    }

    private TextView label(String text, int size) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(0xffd7eeff);
        view.setGravity(Gravity.CENTER);
        view.setPadding(0, dp(6), 0, dp(6));
        return view;
    }

    private Button button(String text, View.OnClickListener listener) {
        Button view = new Button(this);
        view.setText(text);
        view.setTextSize(13);
        view.setAllCaps(false);
        view.setOnClickListener(listener);
        view.setLayoutParams(new LinearLayout.LayoutParams(-1, -2));
        return view;
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override protected void onDestroy() {
        generation++;
        main.removeCallbacksAndMessages(null);
        if (cancellation != null) cancellation.cancel();
        worker.shutdownNow();
        super.onDestroy();
    }
}
