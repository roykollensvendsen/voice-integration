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

dependencies {
    // Runs the three small wake-word models on the phone. ADR-VI-033.
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.19.2")
}

// openWakeWord's models are CC BY-NC-SA 4.0, not Apache-2.0 like this
// repository, so they are fetched when the app is built, never committed.
val wakeWordModels = layout.buildDirectory.dir("wakeword")
val fetchWakeWordModels by tasks.registering {
    val names = listOf("melspectrogram.onnx", "embedding_model.onnx", "hey_jarvis_v0.1.onnx")
    outputs.dir(wakeWordModels)
    doLast {
        val into = wakeWordModels.get().asFile.resolve("wakeword").apply { mkdirs() }
        for (name in names) {
            val file = into.resolve(name)
            if (!file.exists()) {
                uri("https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/$name")
                    .toURL().openStream().use { input -> file.outputStream().use { input.copyTo(it) } }
            }
        }
    }
}
android.sourceSets["main"].assets.srcDir(wakeWordModels)
tasks.named("preBuild") { dependsOn(fetchWakeWordModels) }
