plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "no.roykollensvendsen.voice"
    compileSdk = 35

    defaultConfig {
        applicationId = "no.roykollensvendsen.voice"
        // Android 10: the oldest that gives a foreground service a microphone type.
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}
