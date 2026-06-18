package com.infinityclone.app.core

import android.app.Application
import android.content.Context
import android.util.Log

/**
 * پیاده‌سازی خالی برای دیباگِ UI بدون موتور واقعی. به‌صورت پیش‌فرض استفاده نمی‌شود
 * (به [Engine] نگاه کن)؛ فقط برای زمانی که بخواهی موتور را موقتاً غیرفعال کنی.
 */
class NoopEngine : CloneEngine {

    override val isReady: Boolean = false
    override val lastStep: String = "—"

    override fun attach(app: Application, base: Context) {
        Log.w(TAG, "NoopEngine — موتور واقعی غیرفعال است.")
    }

    override fun onCreate() = Unit
    override fun listClones(): List<CloneInfo> = emptyList()
    override fun createClone(packageName: String): Int = -1
    override fun launchClone(packageName: String, userId: Int): Boolean = false
    override fun removeClone(packageName: String, userId: Int) = Unit
    override fun isCloneInstalled(packageName: String, userId: Int): Boolean = false

    private companion object {
        const val TAG = "NoopEngine"
    }
}
