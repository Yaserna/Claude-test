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
        // If the hidden section was locked (app went to background), any hidden
        // screen that somehow survived must close itself immediately on return,
        // so the back button can never re-enter it.
        if (leavesToMainOnBackground && hiddenLocked) {
            finish()
            return
        }
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

    override fun onStart() {
        super.onStart()
        // Count how many hidden-section screens are currently on screen.
        if (leavesToMainOnBackground) startedHiddenCount++
    }

    override fun onStop() {
        super.onStop()
        if (!leavesToMainOnBackground) return
        startedHiddenCount--
        // A configuration change (rotation / display-size) recreates the SAME screen —
        // that isn't leaving the hidden section, so don't lock.
        if (isChangingConfigurations) return
        // Lock the moment no hidden screen is on top anymore. This covers BOTH:
        //  - the app going to the background (home / app switch / screen lock), and
        //  - navigating to a NON-hidden screen inside the app (e.g. tapping a normal
        //    message's notification opens that conversation).
        // Any hidden screen still sitting in the back stack will finish itself in
        // onResume because hiddenLocked is now true — so Back can never re-enter it.
        window.decorView.post {
            if (!isFinishing && startedHiddenCount <= 0) {
                hiddenLocked = true
                finish()
            }
        }
    }

    companion object {
        /**
         * True once the app left the hidden section (backgrounded, or moved to a
         * non-hidden screen). Cleared only after a successful PIN/fingerprint unlock
         * (PinActivity), so a stray hidden activity can never be reached again with Back.
         */
        @Volatile
        var hiddenLocked: Boolean = false

        /** Number of hidden-section screens currently started (visible). */
        @Volatile
        private var startedHiddenCount: Int = 0
    }

    /** Menu shown when a number (phone / card / OTP) inside a message is tapped. */
    fun showNumberMenu(raw: String) {
        val digits = raw.filter { it.isDigit() || it == '+' }
        // If the tapped number belongs to a saved contact, show that name on top.
        val contactName = com.privatemsg.app.data.ContactsHelper(this).nameFor(digits)
        val options = arrayOf(
            getString(R.string.copy),
            getString(R.string.call),
            getString(R.string.add_contact),
            getString(R.string.send_message)
        )
        showListMenu(options, title = contactName) { which ->
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
    fun showListMenu(items: Array<String>, title: String? = null, onItem: (Int) -> Unit) {
        val builder = MaterialAlertDialogBuilder(this)
            .setItems(items) { _, which -> onItem(which) }
        if (!title.isNullOrBlank()) builder.setTitle(title)
        val dialog = builder.create()
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
