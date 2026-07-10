package com.infinityclone.app.ui

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.infinityclone.app.R
import com.infinityclone.app.core.CloneInfo
import com.infinityclone.app.core.CloneNames
import com.infinityclone.app.core.Engine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * لینک اسکن‌شده را از Share/ACTION_VIEW/کلیپ‌بورد می‌گیرد، از کاربر می‌پرسد کدام
 * کلون، و لینک را به‌صورت deep link داخل همان کلون باز می‌کند.
 */
class LinkRouterActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val link = extractLink()
        if (link.isNullOrBlank()) {
            Toast.makeText(this, R.string.no_link, Toast.LENGTH_LONG).show()
            finish()
            return
        }
        pickCloneThenOpen(link)
    }

    /** لینک را از حالت‌های مختلف ورودی استخراج می‌کند. */
    private fun extractLink(): String? {
        intent?.let { i ->
            when (i.action) {
                Intent.ACTION_SEND -> i.getStringExtra(Intent.EXTRA_TEXT)?.let { return it }
                Intent.ACTION_VIEW -> i.dataString?.let { return it }
            }
        }
        // در غیر این صورت از کلیپ‌بورد
        val clip = (getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager)
            ?.primaryClip
        if (clip != null && clip.itemCount > 0) {
            return clip.getItemAt(0).coerceToText(this)?.toString()
        }
        return null
    }

    private fun pickCloneThenOpen(link: String) {
        lifecycleScope.launch {
            val clones = withContext(Dispatchers.IO) { Engine.instance.listClones() }
            if (clones.isEmpty()) {
                Toast.makeText(this@LinkRouterActivity, R.string.no_clones, Toast.LENGTH_LONG).show()
                finish()
                return@launch
            }
            val labels = clones.map { c ->
                val name = CloneNames.get(this@LinkRouterActivity, c.packageName, c.userId) ?: c.label
                "$name · ${c.packageName} (${c.userId})"
            }.toTypedArray()

            AlertDialog.Builder(this@LinkRouterActivity)
                .setTitle(R.string.pick_clone_for_link)
                .setItems(labels) { _, which -> openIn(clones[which], link) }
                .setOnCancelListener { finish() }
                .show()
        }
    }

    private fun openIn(clone: CloneInfo, link: String) {
        lifecycleScope.launch {
            val ok = withContext(Dispatchers.IO) {
                Engine.instance.openLinkInClone(link, clone.packageName, clone.userId)
            }
            Toast.makeText(
                this@LinkRouterActivity,
                if (ok) R.string.link_opened else R.string.link_failed,
                Toast.LENGTH_SHORT
            ).show()
            finish()
        }
    }
}
