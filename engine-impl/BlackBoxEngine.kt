/*
 * ════════════════════════════════════════════════════════════════════════
 *  پیاده‌سازی واقعی موتور — این فایل عمداً خارج از app/src/main است تا تا وقتی
 *  AAR موتور اضافه نشده، پروژه کامپایل شود.
 *
 *  برای فعال‌سازی:
 *    1. AAR موتور (NewBlackbox) را در app/libs/ بگذار و خط مربوطه را در
 *       app/build.gradle.kts از کامنت خارج کن.
 *    2. این فایل را به مسیر زیر منتقل کن:
 *         app/src/main/java/com/infinityclone/app/core/BlackBoxEngine.kt
 *    3. در core/Engine.kt مقدار instance را به BlackBoxEngine() تغییر بده.
 *    4. importها و نام دقیق متدها را با نسخه‌ی AAR خودت تطبیق بده
 *       (نام پکیج/متدها بین فورک‌ها کمی فرق می‌کند — جاهای حساس با ⚠️ علامت خورده‌اند).
 * ════════════════════════════════════════════════════════════════════════
 */
package com.infinityclone.app.core

import android.content.Context
import android.content.res.Configuration
import android.util.Log

// ⚠️ مسیر پکیج موتور را با AAR خودت چک کن (BlackBox معمولاً top.niunaijun.blackbox).
import top.niunaijun.blackbox.BlackBoxCore
import top.niunaijun.blackbox.app.configuration.ClientConfiguration

class BlackBoxEngine : CloneEngine {

    private val core get() = BlackBoxCore.get()

    override val isReady: Boolean = true

    // ── چرخه‌ی عمر ──────────────────────────────────────────────────
    override fun attach(context: Context) {
        core.doAttachBaseContext(context, config)
    }

    override fun onCreate() {
        core.doCreate()
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        core.doOnConfigurationChanged(newConfig)
    }

    // ── عملیات کلون ─────────────────────────────────────────────────
    override fun listClones(): List<CloneInfo> {
        val result = mutableListOf<CloneInfo>()
        // ⚠️ getUsers() ممکن است List<BUserInfo> برگرداند؛ از فیلد id استفاده کن.
        for (user in core.users) {
            val userId = user.id
            for (app in core.getInstalledApplications(0, userId)) {
                val label = runCatching {
                    core.getApplicationInfo(app.packageName, 0, userId)
                        ?.loadLabel(core.packageManager)?.toString()
                }.getOrNull() ?: app.packageName
                result += CloneInfo(app.packageName, userId, label)
            }
        }
        return result
    }

    override fun createClone(packageName: String, userId: Int): Int {
        val targetUser = if (userId >= 0) userId else nextFreeUserId(packageName)
        // اگر فضای مجازی وجود ندارد، ساخته شود.
        if (core.users.none { it.id == targetUser }) {
            core.createUser(targetUser)
        }
        // ⚠️ installPackageAsUser ممکن است InstallResult با فیلد success برگرداند.
        val res = core.installPackageAsUser(packageName, targetUser)
        val ok = runCatching { res.success }.getOrDefault(true)
        return if (ok) targetUser else -1
    }

    override fun launchClone(packageName: String, userId: Int) {
        core.launchApk(packageName, userId)
    }

    override fun removeClone(packageName: String, userId: Int) {
        core.uninstallPackageAsUser(packageName, userId)
    }

    override fun isCloneInstalled(packageName: String, userId: Int): Boolean {
        return core.isInstalled(packageName, userId)
    }

    /**
     * کوچک‌ترین userId که این پکیج در آن نصب نیست را پیدا می‌کند.
     * این همان چیزی است که «کلون نامحدود» را ممکن می‌کند: هر بار یک فضای جدید.
     */
    private fun nextFreeUserId(packageName: String): Int {
        var id = 0
        while (core.isInstalled(packageName, id)) id++
        return id
    }

    // ── پیکربندی موتور ──────────────────────────────────────────────
    private val config = object : ClientConfiguration() {
        // ⚠️ نام/تعداد این متدها بسته به نسخه‌ی AAR فرق می‌کند.
        //    با ClientConfiguration نمونه‌ی موتور تطبیق بده.
        override fun getHostPackageName(): String = BuildConfigHelper.hostPackage
        override fun isHideRoot(): Boolean = true
        override fun isEnableDaemonService(): Boolean = true
    }

    private companion object {
        const val TAG = "BlackBoxEngine"
    }
}

/** نگه‌دارنده‌ی سبک برای نام پکیج میزبان بدون وابستگی مستقیم به BuildConfig. */
private object BuildConfigHelper {
    const val hostPackage = "com.infinityclone.app"
}
