package com.example.ultrainfoboard.bridge;

import android.app.Activity;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.TextView;

/** A deliberately short chart menu, separate from the system's provider picker. */
public final class BottomPanelActivity extends Activity {
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setGravity(Gravity.CENTER_HORIZONTAL);
        int side = Math.round(getResources().getDisplayMetrics().widthPixels * .13f);
        content.setPadding(side, dp(32), side, dp(40));
        scroll.addView(content);
        TextView heading = label("Bottom panel", 20);
        heading.setTypeface(null, android.graphics.Typeface.BOLD);
        content.addView(heading);
        content.addView(label("Choose a chart for your watch face. Changes save automatically.", 13));
        RadioGroup choices = new RadioGroup(this);
        choices.setOrientation(RadioGroup.VERTICAL);
        BottomPanelPreferences.Panel selected = BottomPanelPreferences.get(this);
        for (BottomPanelPreferences.Panel panel : BottomPanelPreferences.Panel.values()) {
            RadioButton button = new RadioButton(this);
            button.setId(android.view.View.generateViewId());
            button.setText(panel.title);
            button.setTextSize(16);
            button.setTextColor(0xffdaf1ff);
            button.setMinHeight(dp(48));
            button.setTag(panel.id);
            button.setContentDescription(panel.title + ". " + panel.description);
            choices.addView(button, new RadioGroup.LayoutParams(-1, -2));
            if (panel == selected) button.setChecked(true);
            button.setOnClickListener(view -> BottomPanelPreferences.set(this, panel));
        }
        content.addView(choices, new LinearLayout.LayoutParams(-1, -2));
        content.addView(label("Weather charts use Samsung Weather. Tap a chart on the face to open Weather. The six other complications stay editable on the face.", 12));
        setContentView(scroll);
    }

    private TextView label(String value, int size) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextSize(size);
        text.setTextColor(0xffb4daf6);
        text.setGravity(Gravity.CENTER);
        text.setPadding(0, dp(6), 0, dp(6));
        return text;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
