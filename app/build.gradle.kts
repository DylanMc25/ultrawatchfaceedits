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
        versionCode = 10
        versionName = "0.1.9"
    }
    // Strip AGP's generated R classes: WFF packages must contain no DEX files.
    buildTypes {
        debug { isMinifyEnabled = true }
        release { isMinifyEnabled = true }
    }
}
