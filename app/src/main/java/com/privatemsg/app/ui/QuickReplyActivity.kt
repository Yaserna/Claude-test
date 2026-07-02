package com.privatemsg.app.ui

import android.os.Build
import android.os.Bundle
import android.telephony.SmsManager
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Toast
import androidx.core.app.NotificationManagerCompat
import com.privatemsg.app.R
import com.privatemsg.app.data.ContactsHelper
import com.privatemsg.app.data.Message
import com.privatemsg.app.data.SimHelper
import com.privatemsg.app.data.SmsRepository
import com.privatemsg.app.databinding.ActivityQuickReplyBinding

/**
 * A small floating window opened from the notification's Reply button: shows the
 * last two messages and a reply box, so the user can answer without opening the app.
 */
class QuickReplyActivity : BaseActivity() {

    private lateinit var binding: ActivityQuickReplyBinding
    private var address: String = ""
    private var threadId: Long = -1
    private var notifId: Int = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityQuickReplyBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Dock the floating panel to the bottom, full width, and close on tap-outside.
        window.setGravity(Gravity.BOTTOM)
        window.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE)
        setFinishOnTouchOutside(true)

        address = intent.getStringExtra("address") ?: ""
        threadId = intent.getLongExtra("thread_id", -1)
        notifId = intent.getIntExtra("notif_id", 0)

        binding.title.text = ContactsHelper(this).displayFor(address)
        showLastMessages()

        binding.sendButton.setOnClickListener { send() }
        binding.input.requestFocus()
    }

    private fun showLastMessages() {
        if (threadId <= 0) return
        val last = SmsRepository(this).getMessages(threadId).takeLast(2)
        if (last.size >= 2) bindLine(binding.msgOlder, last[0])
        if (last.isNotEmpty()) bindLine(binding.msgNewer, last.last())
    }

    private fun bindLine(view: android.widget.TextView, m: Message) {
        val prefix = if (m.type != 1) getString(R.string.you_prefix) else ""
        view.text = (prefix + m.body).toLatinDigits()
        view.visibility = View.VISIBLE
    }

    private fun send() {
        val body = binding.input.text.toString().trim()
        if (body.isEmpty() || address.isEmpty()) return
        try {
            val subId = SimHelper(this).defaultSubId()
            SmsRepository(this).storeSentMessage(address, body, subId)
            val sm = smsManager(subId)
            val parts = sm.divideMessage(body)
            if (parts.size > 1) sm.sendMultipartTextMessage(address, null, parts, null, null)
            else sm.sendTextMessage(address, null, body, null, null)
            Toast.makeText(this, R.string.reply_sent, Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, R.string.reply_failed, Toast.LENGTH_SHORT).show()
        }
        NotificationManagerCompat.from(this).cancel(notifId)
        finish()
    }

    private fun smsManager(subId: Int): SmsManager {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val base = getSystemService(SmsManager::class.java)
            if (subId >= 0) base.createForSubscriptionId(subId) else base
        } else {
            @Suppress("DEPRECATION")
            if (subId >= 0) SmsManager.getSmsManagerForSubscriptionId(subId) else SmsManager.getDefault()
        }
    }
}
