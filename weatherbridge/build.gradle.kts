import groovy.json.JsonSlurper
import java.security.MessageDigest
import javax.xml.parsers.DocumentBuilderFactory

plugins { id("com.android.application") }

android {
    namespace = "com.example.ultrainfoboard.bridge"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.example.ultrainfoboard.bridge"
        minSdk = 36
        targetSdk = 36
        versionCode = 12
        versionName = "0.2.0-preview.5"
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
    signingConfigs.getByName("debug") {
        // Match the explicit CI cache path; do not depend on AGP's Android user home.
        storeFile = File(System.getProperty("user.home"), ".android/debug.keystore")
        storePassword = "android"
        keyAlias = "androiddebugkey"
        keyPassword = "android"
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

val verifyBundledWatchFace by tasks.registering {
    doLast {
        val generated = layout.buildDirectory.dir("generated/watchface").get().asFile
        val asset = generated.resolve("assets/default_watchface.apk")
        val report = generated.resolve("validation.json")
        val values = generated.resolve("res/values/default_watchface.xml")
        check(asset.isFile && report.isFile && values.isFile) {
            "Prepare the validated embedded face first: python3 tools/prepare_push_bundle.py"
        }
        val evidence = JsonSlurper().parse(report) as Map<*, *>
        val digest = MessageDigest.getInstance("SHA-256").digest(asset.readBytes())
            .joinToString("") { "%02x".format(it) }
        check(digest == evidence["watchface_apk_sha256"]) {
            "Embedded face changed after validation. Run python3 tools/prepare_push_bundle.py again."
        }
        check(evidence["host_package"] == "com.example.ultrainfoboard.bridge") {
            "Embedded face was validated for a different host."
        }
        val document = DocumentBuilderFactory.newInstance().apply {
            setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
        }.newDocumentBuilder().parse(values)
        fun resource(name: String): String? {
            val nodes = document.documentElement.childNodes
            return (0 until nodes.length).map { nodes.item(it) }
                .firstOrNull { it.attributes?.getNamedItem("name")?.nodeValue == name }?.textContent
        }
        check(resource("default_wf_token") == evidence["validation_token"] &&
            resource("bundled_watchface_package") == evidence["watchface_package"] &&
            resource("bundled_watchface_version") == evidence["watchface_version_code"].toString()) {
            "Embedded face metadata does not match its validation. Run python3 tools/prepare_push_bundle.py again."
        }
    }
}
tasks.named("preBuild").configure { dependsOn(verifyBundledWatchFace) }
