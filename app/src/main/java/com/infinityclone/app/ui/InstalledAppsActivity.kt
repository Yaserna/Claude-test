package com.infinityclone.app.ui

import android.content.Intent
import android.graphics.drawable.Drawable
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.infinityclone.app.R
import com.infinityclone.app.core.Engine
import com.infinityclone.app.databinding.ActivityInstalledAppsBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

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

    private fun cloneApp(app: InstalledApp) {
        val userId = Engine.instance.createClone(app.packageName)
        if (userId >= 0) {
            Toast.makeText(this, getString(R.string.clone_created, app.label), Toast.LENGTH_SHORT).show()
            finish()
        } else {
            val msg = if (Engine.instance.isReady) R.string.clone_failed else R.string.engine_disabled
            Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
        }
    }
}
