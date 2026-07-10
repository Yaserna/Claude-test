package com.infinityclone.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = CloneAdapter(
            onClick = { clone -> launchClone(clone) },
            onRename = { clone -> renameClone(clone) },
            onAddShortcut = { clone -> addShortcut(clone) },
            onRemove = { clone -> removeClone(clone) },
        )
        binding.cloneList.layoutManager = LinearLayoutManager(this)
        binding.cloneList.adapter = adapter

        // نمایش نسخه‌ی بیلد تا نسخه‌ها قابل‌تشخیص باشند
        binding.toolbar.subtitle = "v${BuildConfig.VERSION_NAME}"
        binding.toolbar.setSubtitleTextColor(0xFFFFFFFF.toInt())
        binding.toolbar.inflateMenu(R.menu.main_menu)
        binding.toolbar.setOnMenuItemClickListener { item ->
            if (item.itemId == R.id.action_open_link) {
                startActivity(Intent(this, LinkRouterActivity::class.java))
                true
            } else false
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
