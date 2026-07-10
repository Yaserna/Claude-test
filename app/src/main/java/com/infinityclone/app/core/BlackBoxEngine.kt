package com.infinityclone.app.core

import android.app.Application
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import java.io.File
import top.niunaijun.blackbox.BlackBoxCore
import top.niunaijun.blackbox.app.configuration.ClientConfiguration

/**
 * پیاده‌سازی واقعی موتور روی NewBlackbox (ماژول :Bcore).
 *
 * ترتیب راه‌اندازی دقیقاً مطابق اپ نمونه‌ی موتور است.
 */
class BlackBoxEngine : CloneEngine {

    private val core: BlackBoxCore get() = BlackBoxCore.get()

    override val isReady: Boolean = true

    @Volatile
    private var step: String = "—"
    override val lastStep: String get() = step

    // ── چرخه‌ی عمر ──────────────────────────────────────────────────
    override fun attach(app: Application, base: Context) {
        runCatching { core.closeCodeInit() }
            .onFailure { Log.e(TAG, "closeCodeInit: ${it.message}") }

        runCatching { core.onBeforeMainApplicationAttach(app, base) }
            .onFailure { Log.e(TAG, "onBeforeMainApplicationAttach: ${it.message}") }

        runCatching { core.doAttachBaseContext(base, config) }
            .onFailure { Log.e(TAG, "doAttachBaseContext: ${it.message}") }

        runCatching { core.onAfterMainApplicationAttach(app, base) }
            .onFailure { Log.e(TAG, "onAfterMainApplicationAttach: ${it.message}") }
    }

    override fun onCreate() {
        runCatching { core.doCreate() }
            .onFailure { Log.e(TAG, "doCreate: ${it.message}") }

        // گرم‌کردن زودهنگام پروسه‌ی سرویس در پس‌زمینه، تا وقتی کاربر می‌خواهد کلون
        // بسازد، سرویس از قبل بالا آمده باشد (روی MIUI کمک بزرگی است).
        Thread { ensureServices() }.apply { isDaemon = true; start() }
    }

    // ── عملیات کلون ─────────────────────────────────────────────────
    override fun listClones(): List<CloneInfo> {
        ensureServices()
        val pm = BlackBoxCore.getPackageManager()
        val result = mutableListOf<CloneInfo>()
        for (user in core.users) {
            val userId = user.id
            val apps = runCatching { core.getInstalledApplications(0, userId) }.getOrNull().orEmpty()
            for (app in apps) {
                val label = runCatching { pm.getApplicationLabel(app).toString() }
                    .getOrDefault(app.packageName)
                val icon = runCatching { pm.getApplicationIcon(app) }.getOrNull()
                result += CloneInfo(app.packageName, userId, label, icon)
            }
        }
        return result
    }

    override fun createClone(packageName: String): Int {
        step = "۱) آماده‌سازی سرویس موتور"
        ensureServices()
        step = "۲) یافتن فضای آزاد"
        val userId = nextFreeUserId(packageName)
        // اگر فضای مجازی موردنظر وجود ندارد، ساخته شود.
        if (core.users.none { it.id == userId }) {
            step = "۳) ساخت فضای کاربری $userId"
            runCatching { core.createUser(userId) }
                .onFailure { Log.e(TAG, "createUser($userId): ${it.message}"); step = "خطا در ساخت فضا"; return -1 }
        }
        step = "۴) نصب کلون در فضای $userId"
        val res = runCatching { core.installPackageAsUser(packageName, userId) }.getOrNull()
        step = if (res != null && res.success) "۵) پایان موفق" else "۵) نصب ناموفق"
        return if (res != null && res.success) userId else -1
    }

    override fun launchClone(packageName: String, userId: Int): Boolean {
        return runCatching { core.launchApk(packageName, userId) }.getOrDefault(false)
    }

    override fun removeClone(packageName: String, userId: Int) {
        runCatching { core.uninstallPackageAsUser(packageName, userId) }
            .onFailure { Log.e(TAG, "uninstall: ${it.message}") }
    }

    override fun isCloneInstalled(packageName: String, userId: Int): Boolean {
        return runCatching { core.isInstalled(packageName, userId) }.getOrDefault(false)
    }

    override fun createCloneFromApk(apkPath: String): Int {
        ensureServices()
        val userId = nextFreeUserId("")
        if (core.users.none { it.id == userId }) {
            runCatching { core.createUser(userId) }
                .onFailure { Log.e(TAG, "createUser($userId): ${it.message}"); return -1 }
        }
        val res = runCatching { core.installPackageAsUser(File(apkPath), userId) }.getOrNull()
        return if (res != null && res.success) userId else -1
    }

    override fun openLinkInClone(uri: String, packageName: String, userId: Int): Boolean {
        return runCatching {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(uri)).apply {
                setPackage(packageName)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            core.startActivity(intent, userId)
        }.onFailure { Log.e(TAG, "openLinkInClone: ${it.message}") }.isSuccess
    }

    /**
     * مطمئن می‌شود سرویس داخلی موتور راه‌اندازی شده است. این فراخوانی، init را
     * به‌صورت قطعی روی همین نخ (پس‌زمینه) انجام می‌دهد تا عملیات بعدی روی یک
     * سرویسِ آماده اجرا شوند.
     */
    private fun ensureServices() {
        // پروسه‌ی سرویس را استارت می‌زند و تا ~۲.۵ ثانیه منتظر بالا آمدنش می‌ماند.
        runCatching { core.ensureBlackProcessInitialized() }
            .onFailure { Log.e(TAG, "ensureBlackProcessInitialized: ${it.message}") }
        runCatching { core.areServicesAvailable() }
            .onFailure { Log.e(TAG, "areServicesAvailable: ${it.message}") }
    }

    /**
     * اولین شناسه‌ی فضای آزاد را پیدا می‌کند تا کلون در یک فضای تازه و مستقل نصب شود.
     *
     * ⚠️ قبلاً اینجا `isInstalled` در یک حلقه صدا زده می‌شد؛ روی بعضی دستگاه‌ها موتور
     * یک پاسخ «جایگزین» می‌دهد که حلقه را بی‌نهایت می‌کرد و کلون را به گیر می‌انداخت.
     * حالا فقط از فهرست فضاهای موجود استفاده می‌کنیم (بدون فراخوانی پرهزینه/ناپایدار).
     */
    private fun nextFreeUserId(packageName: String): Int {
        val ids = runCatching { core.users.map { it.id } }.getOrDefault(emptyList())
        var id = 0
        while (id in ids) id++
        return id
    }

    // ── پیکربندی موتور ──────────────────────────────────────────────
    // مقادیر مطابق پیش‌فرض امن اپ نمونه. به‌خصوص daemon=false مهم است:
    // اندروید ۱۲ شروع سرویس foreground از پس‌زمینه را محدود می‌کند و فعال‌بودنش
    // می‌تواند نصب کلون را به گیر بیندازد.
    private val config = object : ClientConfiguration() {
        override fun getHostPackageName(): String = HOST_PACKAGE
        override fun isHideRoot(): Boolean = false
        override fun isEnableDaemonService(): Boolean = false
    }

    private companion object {
        const val TAG = "BlackBoxEngine"
        const val HOST_PACKAGE = "com.infinityclone.app"
    }
}
