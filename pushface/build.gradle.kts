plugins {
    id("com.android.application")
}

android {
    namespace = "com.example.ultrainfoboard.bridge.watchfacepush.board"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.ultrainfoboard.bridge.watchfacepush.board"
        minSdk = 36
        targetSdk = 36
        versionCode = providers.gradleProperty("pushVersionCode").orElse("13").get().toInt()
        versionName = providers.gradleProperty("pushVersionName").orElse("0.2.0-preview.6").get()
    }

    sourceSets.getByName("main").res.setSrcDirs(listOf(layout.buildDirectory.dir("generated/watchface/res")))

    signingConfigs {
        // Watch Face Push requires a different key from the host application.
        getByName("debug") {
            storeFile = rootProject.file(".cache/pushface-debug.jks")
            storePassword = "android"
            keyAlias = "pushface-debug"
            keyPassword = "android"
        }
        create("pushRelease") {
            val keyFile = providers.environmentVariable("PUSHFACE_KEYSTORE").orNull
            if (keyFile != null) {
                storeFile = rootProject.file(keyFile)
                storePassword = providers.environmentVariable("PUSHFACE_STORE_PASSWORD").orNull
                keyAlias = providers.environmentVariable("PUSHFACE_KEY_ALIAS").orNull
                keyPassword = providers.environmentVariable("PUSHFACE_KEY_PASSWORD").orNull
            }
        }
    }

    buildTypes {
        debug { isMinifyEnabled = true }
        release {
            isMinifyEnabled = true
            signingConfig = signingConfigs.getByName("pushRelease")
        }
    }
}
