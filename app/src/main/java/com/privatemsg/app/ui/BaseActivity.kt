package com.privatemsg.app.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.net.Uri
import android.provider.ContactsContract
import android.provider.Telephony
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.privatemsg.app.App
import com.privatemsg.app.R
import java.util.Locale

/**
 * Forces the whole app to Persian + right-to-left layout, regardless of the
 * phone's system language. Also provides the shared "tap a number" menu.
 */
abstract class BaseActivity : AppCompatActivity() {

    private var appliedFontScale = 1f
    private var appliedUiScale = 1f

    override fun attachBaseContext(newBase: Context) {
        val prefs = newBase.getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)
        appliedFontScale = prefs.getFloat("font_scale", 1f)
        appliedUiScale = prefs.getFloat("ui_scale", 1f)

        val locale = Locale("fa")
        Locale.setDefault(locale)
        val config = Configuration(newBase.resources.configuration)
        config.setLocale(locale)
        config.setLayoutDirection(locale)
        // User display-size preferences: text-only scale + whole-UI (DPI-like) scale.
        config.fontScale = config.fontScale * appliedFontScale
        config.densityDpi = (config.densityDpi * appliedUiScale).toInt()
        super.attachBaseContext(newBase.createConfigurationContext(config))
    }

    override fun onResume() {
        super.onResume()
        // If the display size changed elsewhere, rebuild this screen to apply it.
        val prefs = getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)
        if (prefs.getFloat("font_scale", 1f) != appliedFontScale ||
            prefs.getFloat("ui_scale", 1f) != appliedUiScale
        ) {
            recreate()
        }
    }

    /** Hidden-section screens override this so they auto-close when the app is backgrounded. */
    protected open val leavesToMainOnBackground: Boolean get() = false

    override fun onStop() {
        super.onStop()
        if (leavesToMainOnBackground) {
            // Check after the lifecycle settles: if the whole app went to the
            // background (home, app switch, screen lock), leave the hidden section.
            window.decorView.post {
                if (!isFinishing && !App.inForeground) {
                    startActivity(
                        Intent(this, MainActivity::class.java)
                            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                    )
                    finish()
                }
            }
        }
    }

    /** Menu shown when a number (phone / card / OTP) inside a message is tapped. */
    fun showNumberMenu(raw: String) {
        val digits = raw.filter { it.isDigit() || it == '+' }
        val options = arrayOf(
            getString(R.string.copy),
            getString(R.string.call),
            getString(R.string.add_contact),
            getString(R.string.send_message)
        )
        showListMenu(options) { which ->
            when (which) {
                0 -> {
                    val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    cm.setPrimaryClip(ClipData.newPlainText("number", raw))
                    Toast.makeText(this, R.string.copied, Toast.LENGTH_SHORT).show()
                }
                1 -> startSafely(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$digits")))
                2 -> startSafely(Intent(Intent.ACTION_INSERT).apply {
                    type = ContactsContract.Contacts.CONTENT_TYPE
                    putExtra(ContactsContract.Intents.Insert.PHONE, digits)
                })
                3 -> startSafely(
                    Intent(this, ConversationActivity::class.java)
                        .putExtra("address", digits)
                        .putExtra("thread_id", Telephony.Threads.getOrCreateThreadId(this, digits))
                )
            }
        }
    }

    /**
     * Shows a simple list menu that is always centered and a fixed width, so it
     * can't drift off the screen edge (a problem with wrap-content dialogs in RTL).
     */
    fun showListMenu(items: Array<String>, onItem: (Int) -> Unit) {
        val dialog = MaterialAlertDialogBuilder(this)
            .setItems(items) { _, which -> onItem(which) }
            .create()
        dialog.show()
        dialog.window?.let { w ->
            w.setGravity(android.view.Gravity.CENTER)
            val width = (resources.displayMetrics.widthPixels * 0.86f).toInt()
            w.setLayout(width, android.view.ViewGroup.LayoutParams.WRAP_CONTENT)
        }
    }

    private fun startSafely(intent: Intent) {
        try {
            startActivity(intent)
        } catch (e: Exception) {
            // No app to handle it; ignore.
        }
    }
}
