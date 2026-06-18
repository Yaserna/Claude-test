package com.infinityclone.app.core

import android.content.Context
import android.content.res.Configuration
import android.util.Log

/**
 * پیاده‌سازی پیش‌فرض وقتی موتور واقعی هنوز اضافه نشده است.
 *
 * هدف: اپ میزبان بدون AAR موتور هم build و اجرا شود تا بتوانی UI را ببینی و
 * توسعه بدهی. همه‌ی عملیات کلون اینجا فقط لاگ می‌شوند و کاری انجام نمی‌دهند.
 *
 * بعد از افزودن موتور واقعی، در [Engine] این را با BlackBoxEngine جایگزین کن.
 */
class NoopEngine : CloneEngine {

    override val isReady: Boolean = false

    override fun attach(context: Context) {
        Log.w(TAG, "NoopEngine.attach — موتور واقعی اضافه نشده است.")
    }

    override fun onCreate() = Unit
    override fun onConfigurationChanged(newConfig: Configuration) = Unit

    override fun listClones(): List<CloneInfo> = emptyList()

    override fun createClone(packageName: String, userId: Int): Int {
        Log.w(TAG, "createClone($packageName) نادیده گرفته شد — موتور غیرفعال.")
        return -1
    }

    override fun launchClone(packageName: String, userId: Int) {
        Log.w(TAG, "launchClone($packageName, $userId) نادیده گرفته شد.")
    }

    override fun removeClone(packageName: String, userId: Int) = Unit

    override fun isCloneInstalled(packageName: String, userId: Int): Boolean = false

    private companion object {
        const val TAG = "NoopEngine"
    }
}
