plugins {
    id("com.android.application")
}

android {
    namespace = "com.example.ultrainfoboard"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.example.ultrainfoboard"
        minSdk = 34
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
    // WFF contains resources only; there is no bytecode to shrink.
    buildTypes {
        release { isMinifyEnabled = false }
    }
}
