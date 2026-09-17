plugins {
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
}

android {
    namespace = "com.journeyng.app"
    compileSdk = 35
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    defaultConfig {
        applicationId = "com.journeyng.app"
        minSdk = 24
        targetSdk = 35
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // Release signing configured only when a keystore exists outside VCS
            // (spec §48: never store signing keys in repository).
            signingConfig = signingConfigs.debug
            minifyEnabled = true
            shrinkResources = true
        }
    }
}

flutter {
    source = "../.."
}

dependencies {
    implementation "com.google.android.gms:play-services-location:21.3.0"
    implementation "androidx.core:core-ktx:1.13.1"
}
