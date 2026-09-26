package com.example.ultrainfoboard.bridge;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

/** Explicit tap destination for an independent image provider in the test APK. */
public final class ChartTestActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        TextView label = new TextView(this);
        label.setText("Test chart opened");
        label.setGravity(android.view.Gravity.CENTER);
        setContentView(label);
    }
}
