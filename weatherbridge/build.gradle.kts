plugins { id("com.android.application") }

android {
    namespace = "com.example.ultrainfoboard.bridge"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.example.ultrainfoboard.bridge"
        minSdk = 36
        targetSdk = 36
        versionCode = 8
        versionName = "0.2.0-preview.1"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    sourceSets.getByName("main") {
        assets.srcDir(layout.buildDirectory.dir("generated/watchface/assets"))
        res.srcDir(layout.buildDirectory.dir("generated/watchface/res"))
    }
    buildTypes {
        release { isMinifyEnabled = false }
    }
}

dependencies {
    implementation("androidx.wear.watchface:watchface-complications-data-source:1.3.0")
    implementation("androidx.wear.watchfacepush:watchfacepush:1.0.0")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
