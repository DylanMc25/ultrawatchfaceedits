package com.example.ultrainfoboard.bridge;

import android.app.PendingIntent;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.drawable.Icon;
import androidx.wear.watchface.complications.data.*;
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService;
import androidx.wear.watchface.complications.datasource.ComplicationRequest;

/** Synthetic chart fixture in a separate package, not a Samsung weather mock. */
public final class ChartTestService extends ComplicationDataSourceService {
    private SmallImageComplicationData data() {
        Bitmap bitmap = Bitmap.createBitmap(262, 94, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setColor(Color.WHITE);
        paint.setTextSize(20);
        canvas.drawText("TEST CHART", 60, 24, paint);
        for (int i = 0; i < 4; i++) canvas.drawRect(35 + i * 52, 76 - i * 10, 65 + i * 52, 90, paint);
        PendingIntent tap = PendingIntent.getActivity(this, 0,
                new Intent(this, ChartTestActivity.class), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        return new SmallImageComplicationData.Builder(
                new SmallImage.Builder(Icon.createWithBitmap(bitmap), SmallImageType.PHOTO).build(),
                new PlainComplicationText.Builder("Synthetic test chart").build()).setTapAction(tap).build();
    }
    @Override public void onComplicationRequest(ComplicationRequest request, ComplicationRequestListener listener) {
        try { listener.onComplicationData(data()); }
        catch (android.os.RemoteException error) { throw new IllegalStateException(error); }
    }
    @Override public ComplicationData getPreviewData(ComplicationType type) {
        return type == ComplicationType.SMALL_IMAGE ? data() : null;
    }
}
