package com.infinityclone.app.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import java.io.File
import androidx.recyclerview.widget.LinearLayoutManager
import com.infinityclone.app.BuildConfig
import com.infinityclone.app.R
import com.infinityclone.app.core.CloneInfo
import com.infinityclone.app.core.CloneNames
import com.infinityclone.app.core.Engine
import com.infinityclone.app.core.Shortcuts
import com.infinityclone.app.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * صفحه‌ی اصلی: فهرست کلون‌های ساخته‌شده + دکمه‌ی افزودن کلون جدید.
 *
 * همه‌ی تماس‌های موتور (لیست/اجرا/حذف) روی نخ پس‌زمینه انجام می‌شوند تا رابط
 * کاربری هرگز فریز نشود.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: CloneAdapter

    private val pickApk = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) importAndClone(uri)
    }

    private var pendingUpdate: CloneInfo? = null
    private val pickUpdateApk = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        val clone = pendingUpdate
        pendingUpdate = null
        if (uri != null && clone != null) importAndUpdate(uri, clone)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = CloneAdapter(
            onClick = { clone -> launchClone(clone) },
            onRename = { clone -> renameClone(clone) },
            onAddShortcut = { clone -> addShortcut(clone) },
            onUpdate = { clone -> updateClone(clone) },
            onRemove = { clone -> removeClone(clone) },
        )
        binding.cloneList.layoutManager = LinearLayoutManager(this)
        binding.cloneList.adapter = adapter

        // نمایش نسخه‌ی بیلد تا نسخه‌ها قابل‌تشخیص باشند
        binding.toolbar.subtitle = "v${BuildConfig.VERSION_NAME}"
        binding.toolbar.setSubtitleTextColor(0xFFFFFFFF.toInt())
        binding.toolbar.inflateMenu(R.menu.main_menu)
        binding.toolbar.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                R.id.action_open_link -> {
                    startActivity(Intent(this, LinkRouterActivity::class.java)); true
                }
                R.id.action_clone_from_apk -> {
                    pickApk.launch("*/*"); true
                }
                R.id.action_share_log -> { captureAndShareLog(); true }
                else -> false
            }
        }

        binding.addCloneButton.setOnClickListener {
            startActivity(Intent(this, InstalledAppsActivity::class.java))
        }

        if (!Engine.instance.isReady) {
            binding.engineWarning.visibility = View.VISIBLE
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        lifecycleScope.launch {
            val clones = withContext(Dispatchers.IO) { Engine.instance.listClones() }
            adapter.submit(clones)
            binding.emptyState.visibility = if (clones.isEmpty()) View.VISIBLE else View.GONE
        }
    }

    /** آپدیت یک کلون: انتخاب منبع (نسخه‌ی نصب‌شده روی گوشی یا فایل APK). */
    private fun updateClone(clone: CloneInfo) {
        val installed = runCatching { packageManager.getPackageInfo(clone.packageName, 0) }.isSuccess
        val fromApk = getString(R.string.update_from_apk)
        val fromInstalled = getString(R.string.update_from_installed)
        val options = if (installed) arrayOf<CharSequence>(fromInstalled, fromApk)
                      else arrayOf<CharSequence>(fromApk)
        AlertDialog.Builder(this)
            .setTitle(R.string.action_update)
            .setItems(options) { _, which ->
                if (installed && which == 0) {
                    doUpdate(clone, null)
                } else {
                    pendingUpdate = clone
                    pickUpdateApk.launch("*/*")
                }
            }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    private fun importAndUpdate(uri: Uri, clone: CloneInfo) {
        lifecycleScope.launch {
            val path = withContext(Dispatchers.IO) {
                val file = copyToCache(uri) ?: return@withContext null
                if (packageManager.getPackageArchiveInfo(file.path, 0) == null) return@withContext ""
                file.path
            }
            when (path) {
                null -> Toast.makeText(this@MainActivity, R.string.clone_failed, Toast.LENGTH_LONG).show()
                "" -> Toast.makeText(this@MainActivity, R.string.apk_invalid, Toast.LENGTH_LONG).show()
                else -> doUpdate(clone, path)
            }
        }
    }

    private fun doUpdate(clone: CloneInfo, apkPath: String?) {
        Toast.makeText(this, R.string.updating_clone, Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            val ok = withContext(Dispatchers.IO) {
                Engine.instance.updateClone(clone.packageName, clone.userId, apkPath)
            }
            Toast.makeText(
                this@MainActivity,
                if (ok) R.string.update_done else R.string.clone_failed,
                Toast.LENGTH_LONG
            ).show()
            refresh()
        }
    }

    /** لاگ اخیر را روی نخ پس‌زمینه جمع می‌کند و برای اشتراک‌گذاری باز می‌کند. */
    private fun captureAndShareLog() {
        Toast.makeText(this, R.string.collecting_log, Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            val text = withContext(Dispatchers.IO) {
                val raw = runCatching {
                    val p = Runtime.getRuntime()
                        .exec(arrayOf("logcat", "-d", "-b", "crash", "-b", "main", "-v", "time", "-t", "4000"))
                    p.inputStream.bufferedReader().readText()
                }.getOrElse { "logcat error: ${it.message}" }
                val keys = listOf(
                    "FATAL", "AndroidRuntime", "Exception", "beginning of crash",
                    "telegram", "tmessages", "BlackBox", "Bcore", "infinityclone", "install"
                )
                raw.lineSequence()
                    .filter { line -> keys.any { line.contains(it, ignoreCase = true) } }
                    .toList().takeLast(400).joinToString("\n")
                    .ifBlank { "لاگ مرتبطی پیدا نشد (ممکن است MIUI دسترسی لاگ را محدود کرده باشد)." }
            }
            val share = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, text)
            }
            startActivity(Intent.createChooser(share, getString(R.string.share_error_log)))
        }
    }

    /** فایل APK انتخاب‌شده را در حافظه‌ی موقت کپی و از آن یک کلون می‌سازد. */
    private fun importAndClone(uri: Uri) {
        Toast.makeText(this, R.string.importing_apk, Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            val userId = withContext(Dispatchers.IO) {
                val file = copyToCache(uri) ?: return@withContext -2
                if (packageManager.getPackageArchiveInfo(file.path, 0) == null) return@withContext -3
                Engine.instance.createCloneFromApk(file.path)
            }
            val msg = when {
                userId >= 0 -> R.string.clone_created_apk
                userId == -3 -> R.string.apk_invalid
                else -> R.string.clone_failed
            }
            Toast.makeText(this@MainActivity, msg, Toast.LENGTH_LONG).show()
            refresh()
        }
    }

    private fun copyToCache(uri: Uri): File? = runCatching {
        val file = File(cacheDir, "import.apk")
        contentResolver.openInputStream(uri)!!.use { input ->
            file.outputStream().use { output -> input.copyTo(output) }
        }
        file
    }.getOrNull()

    private fun launchClone(clone: CloneInfo) {
        lifecycleScope.launch {
            withContext(Dispatchers.IO) {
                Engine.instance.launchClone(clone.packageName, clone.userId)
            }
        }
    }

    private fun renameClone(clone: CloneInfo) {
        val input = EditText(this).apply {
            setText(CloneNames.get(this@MainActivity, clone.packageName, clone.userId) ?: clone.label)
            setSelection(text.length)
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.action_rename)
            .setView(input)
            .setPositiveButton(R.string.save) { _, _ ->
                val name = input.text.toString().trim()
                if (name.isEmpty()) {
                    CloneNames.clear(this, clone.packageName, clone.userId)
                } else {
                    CloneNames.set(this, clone.packageName, clone.userId, name)
                }
                refresh()
            }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    private fun addShortcut(clone: CloneInfo) {
        val label = CloneNames.get(this, clone.packageName, clone.userId) ?: clone.label
        val ok = Shortcuts.pin(this, clone.packageName, clone.userId, label)
        val msg = if (ok) R.string.shortcut_requested else R.string.shortcut_unsupported
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
    }

    private fun removeClone(clone: CloneInfo) {
        lifecycleScope.launch {
            withContext(Dispatchers.IO) { Engine.instance.removeClone(clone.packageName, clone.userId) }
            Toast.makeText(
                this@MainActivity,
                getString(R.string.clone_removed, clone.label),
                Toast.LENGTH_SHORT
            ).show()
            refresh()
        }
    }
}
