plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.infinityclone.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.infinityclone.app"
        minSdk = 23
        // targetSdk پایین‌تر = محدودیت‌های کمتر سیستم‌عامل برای موتور مجازی‌سازی
        // (بدون فیلتر package-visibility و با دسترسی legacy storage).
        // این عمداً روی 30 نگه داشته شده؛ بالا بردنش restrictionهای بیشتری اضافه می‌کند.
        targetSdk = 30
        versionCode = 1
        versionName = "0.1.0"

        ndk {
            // موتور فقط برای این ABIها lib دارد؛ بقیه را حذف می‌کنیم تا حجم کم شود
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
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
            // موتور مجازی‌سازی به استخراج کتابخانه‌های native نیاز دارد
            useLegacyPackaging = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    // ── هسته‌ی مجازی‌سازی (NewBlackbox) ───────────────────────────────
    // AAR را در app/libs/ قرار بده و نام فایل را اینجا مطابقت بده.
    // راهنمای کامل در README.md بخش «افزودن موتور».
    // implementation(files("libs/blackbox.aar"))

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // عبور از محدودیت Hidden API در اندروید 9+ (برای انعکاس‌های موتور)
    implementation("org.lsposed.hiddenapibypass:hiddenapibypass:4.3")
}
