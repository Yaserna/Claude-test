package com.privatemsg.app.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.SmsManager
import android.widget.Toast
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.RemoteInput
import com.privatemsg.app.R
import com.privatemsg.app.data.SmsRepository

/** Handles the Reply / Mark-read / Delete buttons on a real (non-decoy) notification. */
class NotificationActionReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val address = intent.getStringExtra("address") ?: ""
        val threadId = intent.getLongExtra("thread_id", -1)
        val messageId = intent.getLongExtra("message_id", -1)
        val notifId = intent.getIntExtra("notif_id", 0)
        val repo = SmsRepository(context)

        when (intent.action) {
            ACTION_REPLY -> {
                val reply = RemoteInput.getResultsFromIntent(intent)
                    ?.getCharSequence(KEY_REPLY)?.toString()?.trim().orEmpty()
                if (reply.isNotEmpty() && address.isNotEmpty()) {
                    try {
                        @Suppress("DEPRECATION")
                        SmsManager.getDefault().sendTextMessage(address, null, reply, null, null)
                        repo.storeSentMessage(address, reply, -1)
                        Toast.makeText(context, R.string.reply_sent, Toast.LENGTH_SHORT).show()
                    } catch (e: Exception) {
                        Toast.makeText(context, R.string.reply_failed, Toast.LENGTH_SHORT).show()
                    }
                }
            }
            ACTION_MARK_READ -> if (threadId >= 0) repo.markThreadRead(threadId)
            ACTION_DELETE -> if (messageId >= 0) repo.deleteMessage(messageId)
        }
        NotificationManagerCompat.from(context).cancel(notifId)
    }

    companion object {
        const val ACTION_REPLY = "com.privatemsg.app.NOTIF_REPLY"
        const val ACTION_MARK_READ = "com.privatemsg.app.NOTIF_READ"
        const val ACTION_DELETE = "com.privatemsg.app.NOTIF_DELETE"
        const val KEY_REPLY = "key_reply"
    }
}
