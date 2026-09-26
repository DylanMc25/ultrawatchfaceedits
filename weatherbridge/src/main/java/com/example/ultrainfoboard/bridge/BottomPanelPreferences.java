package com.example.ultrainfoboard.bridge;

import android.content.Context;

/** Local choice for the one bundled face; persisted independently of weather access. */
public final class BottomPanelPreferences {
    static final String FILE = "bottom_panel";
    static final String KEY = "chart";

    public enum Panel {
        WEATHER("weather", "Weather", "Current conditions and four hourly forecasts"),
        TEMPERATURE("temperature", "Temperature trend", "Four hourly temperatures on a line chart"),
        RAIN("rain", "Chance of rain", "Four hourly precipitation probabilities"),
        NONE("none", "None", "Leave the bottom area empty");

        public final String id;
        public final String title;
        public final String description;

        Panel(String id, String title, String description) {
            this.id = id;
            this.title = title;
            this.description = description;
        }

        static Panel fromId(String id) {
            for (Panel panel : values()) if (panel.id.equals(id)) return panel;
            return WEATHER;
        }
    }

    private BottomPanelPreferences() {}

    public static Panel get(Context context) {
        return Panel.fromId(context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
                .getString(KEY, Panel.WEATHER.id));
    }

    public static void set(Context context, Panel panel) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putString(KEY, panel.id).apply();
        SamsungForecastService.requestUpdates(context);
    }
}
