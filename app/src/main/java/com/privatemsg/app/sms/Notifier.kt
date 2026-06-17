package com.privatemsg.app.sms

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Telephony
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.Person
import androidx.core.app.RemoteInput
import com.privatemsg.app.R
import com.privatemsg.app.data.ContactsHelper
import com.privatemsg.app.data.SecureStore
import com.privatemsg.app.ui.ConversationActivity
import com.privatemsg.app.ui.MainActivity

object Notifier {

    private const val CHANNEL_ID = "incoming_sms"
    private const val DECOY_ID = 424242

    private fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Messages",
                NotificationManager.IMPORTANCE_HIGH
            )
            context.getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun notify(context: Context, id: Int, builder: NotificationCompat.Builder) {
        try {
            NotificationManagerCompat.from(context).notify(id, builder.build())
        } catch (e: SecurityException) {
            // POST_NOTIFICATIONS not granted yet; ignore.
        }
    }

    /** Real notification for a normal (non-hidden) sender, with action buttons. */
    fun showIncoming(context: Context, address: String, body: String, messageId: Long) {
        ensureChannel(context)

        val notifId = address.hashCode()
        val threadId = Telephony.Threads.getOrCreateThreadId(context, address)

        val tapIntent = Intent(context, ConversationActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("address", address)
            putExtra("thread_id", threadId)
        }
        val tapPi = PendingIntent.getActivity(
            context, notifId, tapIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        fun actionIntent(action: String): Intent =
            Intent(context, NotificationActionReceiver::class.java).apply {
                setAction(action)
                putExtra("address", address)
                putExtra("thread_id", threadId)
                putExtra("message_id", messageId)
                putExtra("notif_id", notifId)
            }

        val replyPi = PendingIntent.getBroadcast(
            context, notifId * 31 + 1, actionIntent(NotificationActionReceiver.ACTION_REPLY),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
        )
        val readPi = PendingIntent.getBroadcast(
            context, notifId * 31 + 2, actionIntent(NotificationActionReceiver.ACTION_MARK_READ),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val deletePi = PendingIntent.getBroadcast(
            context, notifId * 31 + 3, actionIntent(NotificationActionReceiver.ACTION_DELETE),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val remoteInput = RemoteInput.Builder(NotificationActionReceiver.KEY_REPLY)
            .setLabel(context.getString(R.string.notif_reply)).build()
        val replyAction = NotificationCompat.Action.Builder(
            R.drawable.ic_send_up, context.getString(R.string.notif_reply), replyPi
        ).addRemoteInput(remoteInput).build()

        val title = ContactsHelper(context).displayFor(address)
        // MessagingStyle makes the system show an inline reply input for the reply action.
        val sender = Person.Builder().setName(title).build()
        val me = Person.Builder().setName(context.getString(R.string.app_name)).build()
        val style = NotificationCompat.MessagingStyle(me)
            .addMessage(body, System.currentTimeMillis(), sender)

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_message)
            .setStyle(style)
            .setAutoCancel(true)
            .setContentIntent(tapPi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .addAction(replyAction)
            .addAction(R.drawable.ic_mark_read, context.getString(R.string.notif_mark_read), readPi)
            .addAction(R.drawable.ic_delete, context.getString(R.string.notif_delete), deletePi)

        notify(context, notifId, builder)
    }

    /**
     * Decoy notification for a hidden sender: shows the user-defined fake name
     * and fake text, and tapping it opens the chosen innocent conversation
     * (never the hidden section).
     */
    fun showDecoy(context: Context, secure: SecureStore) {
        ensureChannel(context)

        val name = secure.decoyName.ifBlank { context.getString(R.string.app_name) }
        val text = secure.decoyText.ifBlank { " " }
        val target = secure.decoyTarget

        val intent = if (target.isNotBlank()) {
            Intent(context, ConversationActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("address", target)
                putExtra(
                    "thread_id",
                    Telephony.Threads.getOrCreateThreadId(context, target)
                )
            }
        } else {
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
        }

        val pi = PendingIntent.getActivity(
            context, 1, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_message)
            .setContentTitle(name)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(pi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)

        notify(context, DECOY_ID, builder)
    }
}
