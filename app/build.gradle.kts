plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.jetbrains.kotlin.android)
}

android {
    namespace = "com.infinityclone.app"
    compileSdk = (rootProject.extra["compileSdkVersion"] as Int)
    ndkVersion = "29.0.13846066"

    defaultConfig {
        applicationId = "com.infinityclone.app"
        minSdk = 26
        // targetSdk پایین (۲۸) = محدودیت‌های کمتر سیستم‌عامل برای موتور مجازی‌سازی.
        targetSdk = (rootProject.extra["targetSdkVersion"] as Int)
        // نسخه از روی شماره‌ی بیلد CI تا نسخه‌ها قابل‌تشخیص باشند
        val buildNumber = System.getenv("BUILD_NUMBER")?.toIntOrNull()
        val buildLabel = System.getenv("BUILD_LABEL")
        versionCode = buildNumber ?: (rootProject.extra["versionCode"] as Int)
        versionName = (rootProject.extra["versionName"] as String) +
            (buildLabel?.let { " (build $it)" } ?: "")

        ndk {
            // موتور فقط برای این دو معماری lib بومی دارد.
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }
    }

    signingConfigs {
        // کلید ثابت دیباگ که در مخزن نگه داشته شده تا همه‌ی بیلدها امضای یکسان
        // داشته باشند و آپدیت‌ها بدون نیاز به حذف نسخه‌ی قبلی نصب شوند.
        getByName("debug") {
            storeFile = rootProject.file("keystore/debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    kotlinOptions {
        jvmTarget = "21"
    }
    buildFeatures {
        viewBinding = true
        buildConfig = true
    }
}

dependencies {
    // ── هسته‌ی مجازی‌سازی (NewBlackbox) به‌صورت ماژول داخل پروژه ──────────
    implementation(project(":Bcore"))

    implementation(libs.appcompat)
    implementation(libs.material)
    implementation(libs.constraintlayout)
    implementation(libs.core.ktx)

    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.biometric:biometric:1.1.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
