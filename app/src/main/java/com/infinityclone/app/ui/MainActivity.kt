package com.infinityclone.app.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import java.io.File
import androidx.recyclerview.widget.LinearLayoutManager
import com.infinityclone.app.BuildConfig
import com.infinityclone.app.R
import com.infinityclone.app.core.CloneInfo
import com.infinityclone.app.core.CloneNames
import com.infinityclone.app.core.Engine
import com.infinityclone.app.core.HiddenStore
import com.infinityclone.app.core.Shortcuts
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import com.infinityclone.app.databinding.ActivityMainBinding

/**
 * صفحه‌ی اصلی: فهرست کلون‌های ساخته‌شده + دکمه‌ی افزودن کلون جدید.
 *
 * همه‌ی تماس‌های موتور (لیست/اجرا/حذف) روی نخ پس‌زمینه انجام می‌شوند تا رابط
 * کاربری هرگز فریز نشود.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: CloneAdapter

    /** فهرست کامل کلون‌ها (فیلترنشده) که آخرین بار از موتور خوانده شد. */
    private var allClones: List<CloneInfo> = emptyList()

    /** آیا بخش مخفی در این نشست باز شده است؟ با خروج از اپ دوباره قفل می‌شود. */
    private var hiddenUnlocked = false

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
            onHold = { clone -> onCloneHeld(clone) },
        )
        binding.cloneList.layoutManager = LinearLayoutManager(this)
        binding.cloneList.adapter = adapter

        // نوار جستجو: هم جستجوی واقعی، هم تشخیص رمزِ بخش مخفی.
        binding.searchBar.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) { onSearchChanged(s?.toString().orEmpty()) }
        })

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

    /** با خارج‌شدن از اپ، بخش مخفی دوباره قفل می‌شود. */
    override fun onStop() {
        super.onStop()
        hiddenUnlocked = false
        binding.searchBar.setText("")
    }

    private fun refresh() {
        lifecycleScope.launch {
            allClones = withContext(Dispatchers.IO) { Engine.instance.listClones() }
            applyFilter()
        }
    }

    /** فهرست نمایش‌داده‌شده را بر اساس متن جستجو و وضعیت مخفی‌بودن می‌سازد. */
    private fun applyFilter() {
        val q = binding.searchBar.text.toString().trim()
        val list = allClones.filter { c ->
            val hidden = HiddenStore.isHidden(this, c.packageName, c.userId)
            if (hidden && !hiddenUnlocked) return@filter false
            if (q.isEmpty()) return@filter true
            val name = CloneNames.get(this, c.packageName, c.userId) ?: c.label
            name.contains(q, true) || c.packageName.contains(q, true)
        }
        adapter.submit(list)
        binding.emptyState.visibility = if (list.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun onSearchChanged(text: String) {
        val q = text.trim()
        // اگر بخش مخفی هنوز قفل است و متنِ واردشده دقیقاً رمز است → با اثر انگشت باز کن.
        if (!hiddenUnlocked && HiddenStore.hasAnyHidden(this) &&
            HiddenStore.hasPasscode(this) && HiddenStore.checkPasscode(this, q)
        ) {
            promptBiometric(getString(R.string.unlock_hidden)) {
                hiddenUnlocked = true
                binding.searchBar.setText("") // پاک‌کردن رمز؛ فیلتر دوباره اجرا می‌شود
                Toast.makeText(this, R.string.hidden_unlocked, Toast.LENGTH_SHORT).show()
            }
            return
        }
        applyFilter()
    }

    // ── مخفی‌سازی کلون‌ها ────────────────────────────────────────────
    /** لمس ۲.۵ ثانیه‌ای روی یک کلون: مخفی‌کردن یا آشکارکردن. */
    private fun onCloneHeld(clone: CloneInfo) {
        val isHidden = HiddenStore.isHidden(this, clone.packageName, clone.userId)
        if (isHidden) {
            // این کلون هم‌اکنون در بخشِ بازشده دیده می‌شود → آشکارکردن دوباره.
            HiddenStore.setHidden(this, clone.packageName, clone.userId, false)
            Toast.makeText(this, R.string.clone_unhidden, Toast.LENGTH_SHORT).show()
            applyFilter()
            return
        }
        if (!HiddenStore.hasPasscode(this)) {
            // اولین‌بار: تنظیم رمز ورود، سپس مخفی‌کردن.
            promptSetPasscode { doHide(clone) }
        } else {
            doHide(clone)
        }
    }

    private fun doHide(clone: CloneInfo) {
        HiddenStore.setHidden(this, clone.packageName, clone.userId, true)
        Toast.makeText(this, R.string.clone_hidden, Toast.LENGTH_SHORT).show()
        applyFilter()
    }

    /** دیالوگِ تنظیم رمز ورودِ بخش مخفی (اولین‌بار). */
    private fun promptSetPasscode(onDone: () -> Unit) {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            hint = getString(R.string.set_passcode_hint)
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.set_passcode_title)
            .setMessage(R.string.set_passcode_message)
            .setView(input)
            .setPositiveButton(R.string.save) { _, _ ->
                val code = input.text.toString().trim()
                if (code.length < 3) {
                    Toast.makeText(this, R.string.passcode_too_short, Toast.LENGTH_LONG).show()
                } else {
                    HiddenStore.setPasscode(this, code)
                    onDone()
                }
            }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    /** احراز هویت با اثر انگشت (یا رمز دستگاه به‌عنوان جایگزین). */
    private fun promptBiometric(subtitle: String, onSuccess: () -> Unit) {
        val manager = BiometricManager.from(this)
        val authenticators = BiometricManager.Authenticators.BIOMETRIC_WEAK
        if (manager.canAuthenticate(authenticators) != BiometricManager.BIOMETRIC_SUCCESS) {
            // دستگاه اثر انگشت ندارد یا ثبت نشده → مستقیم اجازه بده.
            onSuccess(); return
        }
        val executor = ContextCompat.getMainExecutor(this)
        val prompt = BiometricPrompt(this, executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    onSuccess()
                }
            })
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(getString(R.string.app_name))
            .setSubtitle(subtitle)
            .setAllowedAuthenticators(authenticators)
            .setNegativeButtonText(getString(R.string.close))
            .build()
        prompt.authenticate(info)
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
