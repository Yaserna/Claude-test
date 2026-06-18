package com.infinityclone.app.ui

import android.content.Intent
import android.graphics.drawable.Drawable
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.infinityclone.app.R
import com.infinityclone.app.core.Engine
import com.infinityclone.app.databinding.ActivityInstalledAppsBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/** اطلاعات یک اپ نصب‌شده روی دستگاه که قابل کلون است. */
data class InstalledApp(
    val packageName: String,
    val label: String,
    val icon: Drawable,
)

/**
 * فهرست اپ‌های نصب‌شده روی دستگاه. با زدن روی هر اپ، یک کلون جدید ساخته می‌شود.
 */
class InstalledAppsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityInstalledAppsBinding
    private lateinit var adapter: InstalledAppAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityInstalledAppsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = InstalledAppAdapter { app -> cloneApp(app) }
        binding.appList.layoutManager = LinearLayoutManager(this)
        binding.appList.adapter = adapter

        loadApps()
    }

    private fun loadApps() {
        binding.progress.visibility = View.VISIBLE
        lifecycleScope.launch {
            val apps = withContext(Dispatchers.IO) { queryLaunchableApps() }
            adapter.submit(apps)
            binding.progress.visibility = View.GONE
        }
    }

    /** همه‌ی اپ‌هایی که آیکن لانچر دارند (به‌جز خود ما). */
    private fun queryLaunchableApps(): List<InstalledApp> {
        val pm = packageManager
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        return pm.queryIntentActivities(intent, 0)
            .asSequence()
            .map { it.activityInfo.packageName }
            .distinct()
            .filter { it != packageName }
            .mapNotNull { pkg ->
                runCatching {
                    val ai = pm.getApplicationInfo(pkg, 0)
                    InstalledApp(
                        packageName = pkg,
                        label = pm.getApplicationLabel(ai).toString(),
                        icon = pm.getApplicationIcon(ai),
                    )
                }.getOrNull()
            }
            .sortedBy { it.label.lowercase() }
            .toList()
    }

    private var cloning = false

    private fun cloneApp(app: InstalledApp) {
        if (cloning) return
        cloning = true
        // ساخت کلون سنگین است؛ روی نخ پس‌زمینه انجام می‌شود تا رابط کاربری فریز نشود.
        binding.progress.visibility = View.VISIBLE
        binding.appList.isEnabled = false
        lifecycleScope.launch {
            // کار سنگین در یک کوروتین جدا اجرا می‌شود تا بتوان با مهلت زمانی آن را
            // رها کرد (تماس بلاک‌کننده‌ی موتور خودش لغو نمی‌شود، ولی رابط کاربری
            // آزاد می‌شود و پیام واضح نشان داده می‌شود).
            val work = async(Dispatchers.IO) { Engine.instance.createClone(app.packageName) }
            val userId = withTimeoutOrNull(CLONE_TIMEOUT_MS) { work.await() }

            binding.progress.visibility = View.GONE
            binding.appList.isEnabled = true
            cloning = false

            when {
                userId != null && userId >= 0 -> {
                    Toast.makeText(
                        this@InstalledAppsActivity,
                        getString(R.string.clone_created, app.label),
                        Toast.LENGTH_SHORT
                    ).show()
                    finish()
                }
                userId == null -> showDiagnostics(getString(R.string.clone_timeout, app.label))
                !Engine.instance.isReady -> showDiagnostics(getString(R.string.engine_disabled))
                else -> showDiagnostics(getString(R.string.clone_failed))
            }
        }
    }

    /** پنجره‌ی تشخیص: پیام + لاگ موتور، با امکان اشتراک‌گذاری برای عیب‌یابی. */
    private fun showDiagnostics(message: String) {
        val logs = captureLogs()
        val body = "$message\n\n──────── لاگ موتور ────────\n$logs"
        AlertDialog.Builder(this)
            .setTitle(R.string.diag_title)
            .setMessage(body)
            .setPositiveButton(R.string.share) { _, _ ->
                val share = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, body)
                }
                startActivity(Intent.createChooser(share, getString(R.string.share)))
            }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    /** آخرین خطوط مرتبط لاگِ پروسه‌ی خودمان (شامل پروسه‌های موتور با همان UID). */
    private fun captureLogs(): String {
        return try {
            val process = Runtime.getRuntime().exec(arrayOf("logcat", "-d", "-v", "time"))
            val text = process.inputStream.bufferedReader().readText()
            val keys = listOf(
                "BlackBox", "Bcore", "BPackage", "BActivity", "Slog",
                "AndroidRuntime", "infinityclone", "BlackBoxEngine", "FATAL"
            )
            text.lineSequence()
                .filter { line -> keys.any { line.contains(it, ignoreCase = true) } }
                .toList()
                .takeLast(120)
                .joinToString("\n")
                .ifBlank { "لاگ مرتبطی پیدا نشد." }
        } catch (e: Exception) {
            "خطا در خواندن لاگ: ${e.message}"
        }
    }

    private companion object {
        const val CLONE_TIMEOUT_MS = 90_000L
    }
}
