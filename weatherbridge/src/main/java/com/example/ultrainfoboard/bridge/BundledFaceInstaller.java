package com.example.ultrainfoboard.bridge;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.os.ParcelFileDescriptor;

import androidx.wear.watchfacepush.WatchFacePushManager;
import androidx.wear.watchfacepush.WatchFacePushManagerFactory;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

import kotlin.ResultKt;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.CoroutineContext;
import kotlin.coroutines.intrinsics.IntrinsicsKt;
import kotlinx.coroutines.Dispatchers;

/** Installs or upgrades our bundled WFF package without changing the active face. */
public final class BundledFaceInstaller {
    private static final ExecutorService IO = Executors.newSingleThreadExecutor();
    private static final AtomicBoolean RUNNING = new AtomicBoolean();
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    private BundledFaceInstaller() {}

    public interface Callback {
        /** Always called on the main thread. */
        void onComplete(boolean success, String message);
    }

    public static void installOrUpdate(Context context, Callback callback) {
        if (!WatchFacePushManagerFactory.isSupported()) {
            MAIN.post(() -> callback.onComplete(false, "Wear OS 6 is required for this watch face."));
            return;
        }
        if (!RUNNING.compareAndSet(false, true)) {
            MAIN.post(() -> callback.onComplete(false, "The watch face is already being prepared."));
            return;
        }
        Context appContext = context.getApplicationContext();
        Operation operation = new Operation(appContext, callback);
        IO.execute(operation::start);
    }

    private static final class Operation {
        private final Context context;
        private final Callback callback;
        private final AtomicBoolean finished = new AtomicBoolean();
        private File temporaryApk;
        private ParcelFileDescriptor apkFd;

        Operation(Context context, Callback callback) {
            this.context = context;
            this.callback = callback;
        }

        void start() {
            try {
                WatchFacePushManager manager = WatchFacePushManagerFactory.createWatchFacePushManager(context);
                BundledFaceInstaller.<WatchFacePushManager.ListWatchFacesResponse>call(
                        manager::listWatchFaces, response -> chooseOperation(manager, response), this::fail);
            } catch (Exception error) {
                fail(error);
            }
        }

        void chooseOperation(WatchFacePushManager manager, WatchFacePushManager.ListWatchFacesResponse response) {
            String packageName = context.getString(R.string.bundled_watchface_package);
            int versionCode = context.getResources().getInteger(R.integer.bundled_watchface_version);
            WatchFacePushManager.WatchFaceDetails existing = null;
            for (WatchFacePushManager.WatchFaceDetails candidate : response.getInstalledWatchFaceDetails()) {
                if (packageName.equals(candidate.getPackageName())) {
                    existing = candidate;
                    break;
                }
            }
            if (existing != null && existing.getVersionCode() >= versionCode) {
                finish(true, "Watch face is ready. Select " + context.getString(R.string.forecast_face_name)
                        + " in your watch-face picker.");
                return;
            }
            if (existing == null && response.getRemainingSlotCount() < 1) {
                finish(false, "This app's watch-face slot is occupied by another face. It was left unchanged.");
                return;
            }
            WatchFacePushManager.WatchFaceDetails current = existing;
            IO.execute(() -> install(manager, current));
        }

        void install(WatchFacePushManager manager, WatchFacePushManager.WatchFaceDetails existing) {
            try {
                temporaryApk = File.createTempFile("bundled-watchface-", ".apk", context.getCacheDir());
                try (InputStream input = context.getAssets().open("default_watchface.apk");
                     FileOutputStream output = new FileOutputStream(temporaryApk)) {
                    byte[] buffer = new byte[16384];
                    int count;
                    while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                }
                apkFd = ParcelFileDescriptor.open(temporaryApk, ParcelFileDescriptor.MODE_READ_ONLY);
                String token = context.getString(R.string.default_wf_token);
                if (existing == null) {
                    BundledFaceInstaller.<WatchFacePushManager.WatchFaceDetails>call(
                            continuation -> manager.addWatchFace(apkFd, token, continuation),
                            details -> finish(true, "Watch face installed. Select "
                                    + context.getString(R.string.forecast_face_name) + " in your watch-face picker."),
                            this::fail);
                } else {
                    // The slot was read for this operation; it is never persisted or reused later.
                    BundledFaceInstaller.<WatchFacePushManager.WatchFaceDetails>call(
                            continuation -> manager.updateWatchFace(existing.getSlotId(), apkFd, token, continuation),
                            details -> finish(true, "Watch face updated."),
                            this::fail);
                }
            } catch (Exception error) {
                fail(error);
            }
        }

        void fail(Throwable error) {
            String detail = error.getMessage();
            if (detail == null || detail.isBlank()) detail = error.getClass().getSimpleName();
            finish(false, "Watch-face setup failed: " + detail);
        }

        void finish(boolean success, String message) {
            if (!finished.compareAndSet(false, true)) return;
            if (apkFd != null) {
                try { apkFd.close(); } catch (IOException ignored) { }
            }
            if (temporaryApk != null) temporaryApk.delete();
            RUNNING.set(false);
            MAIN.post(() -> callback.onComplete(success, message));
        }
    }

    @FunctionalInterface
    private interface SuspendCall<T> {
        Object invoke(Continuation<? super T> continuation) throws Exception;
    }

    /** Bridge the released Kotlin suspend API without adding a Kotlin source/plugin dependency. */
    private static <T> void call(SuspendCall<T> action, Consumer<T> success, Consumer<Throwable> failure) {
        Continuation<T> continuation = new Continuation<T>() {
            @Override public CoroutineContext getContext() {
                // Push derives its callback executor from this dispatcher; EmptyCoroutineContext is invalid.
                return Dispatchers.getIO();
            }

            @Override @SuppressWarnings("unchecked") public void resumeWith(Object result) {
                try {
                    ResultKt.throwOnFailure(result);
                    success.accept((T) result);
                } catch (Throwable error) {
                    failure.accept(error);
                }
            }
        };
        try {
            Object result = action.invoke(continuation);
            if (result != IntrinsicsKt.getCOROUTINE_SUSPENDED()) continuation.resumeWith(result);
        } catch (Throwable error) {
            failure.accept(error);
        }
    }
}
