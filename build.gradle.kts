// تنظیمات سطح ریشه‌ی پروژه
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.jetbrains.kotlin.android) apply false
    alias(libs.plugins.android.library) apply false
}

// نسخه‌های مشترکی که ماژول موتور (Bcore) از طریق rootProject.ext می‌خواند.
extra["compileSdkVersion"] = 35
extra["targetSdkVersion"] = 28
extra["minSdk"] = 21
extra["versionCode"] = 1
extra["versionName"] = "0.1.0"
extra["xVersion"] = "1.1.0"
extra["hiddenApiBypass"] = "4.3"
