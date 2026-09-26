plugins { id("com.android.application") }
android {
    namespace = "com.example.ultrainfoboard.panelfixture"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.example.ultrainfoboard.panelfixture"
        minSdk = 36
        targetSdk = 36
        versionCode = 1
        versionName = "1"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies {
    implementation("androidx.wear.watchface:watchface-complications-data-source:1.3.0")
}
