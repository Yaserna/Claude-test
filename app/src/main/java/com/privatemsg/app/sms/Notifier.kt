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
    // Separate channel for decoy notifications: vibrate but NO sound, so a hidden
    // message never makes an audible alert (only the real ones do).
    private const val DECOY_CHANNEL_ID = "decoy_sms_silent"

    private fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Messages",
                NotificationManager.IMPORTANCE_HIGH
            )
            channel.enableVibration(true)
            context.getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    /** Channel for decoy notifications: vibration on, sound off. */
    private fun ensureDecoyChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                DECOY_CHANNEL_ID,
                "Messages",
                NotificationManager.IMPORTANCE_HIGH
            )
            channel.setSound(null, null)   // no sound
            channel.enableVibration(true)  // vibration only
            context.getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    /**
     * The colored app icon as a bitmap, used as the notification's large icon so
     * the notification always shows the orange Mi-style icon instead of a flat
     * white silhouette (some launchers render the white small-icon as the app icon).
     */
    private fun appLargeIcon(context: Context): android.graphics.Bitmap? {
        val d = androidx.core.content.ContextCompat.getDrawable(context, R.drawable.ic_launcher)
            ?: return null
        val size = (48 * context.resources.displayMetrics.density).toInt().coerceAtLeast(1)
        val bmp = android.graphics.Bitmap.createBitmap(
            size, size, android.graphics.Bitmap.Config.ARGB_8888
        )
        val canvas = android.graphics.Canvas(bmp)
        d.setBounds(0, 0, size, size)
        d.draw(canvas)
        return bmp
    }

    private fun accentColor(context: Context): Int =
        androidx.core.content.ContextCompat.getColor(context, R.color.accent)

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
            .setLargeIcon(appLargeIcon(context))
            .setColor(accentColor(context))
            .setStyle(style)
            .setAutoCancel(true)
            .setContentIntent(tapPi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .addAction(replyAction)
            .addAction(R.drawable.ic_mark_read, context.getString(R.string.notif_mark_read), readPi)
            .addAction(R.drawable.ic_delete, context.getString(R.string.notif_delete), deletePi)

        // On pre-O devices the channel doesn't exist; ask for sound + vibration here.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            builder.setDefaults(NotificationCompat.DEFAULT_SOUND or NotificationCompat.DEFAULT_VIBRATE)
        }

        notify(context, notifId, builder)
    }

    /** Removes the real notification for a normal sender (e.g. when its chat is opened). */
    fun cancelIncoming(context: Context, address: String) {
        NotificationManagerCompat.from(context).cancel(address.hashCode())
    }

    /**
     * Decoy notification for a hidden sender: shows the user-defined fake name
     * and fake text, and tapping it opens the chosen innocent conversation
     * (never the hidden section).
     */
    fun showDecoy(context: Context, secure: SecureStore, address: String) {
        ensureDecoyChannel(context)

        // Each hidden number can have its own decoy (falls back to the global one).
        val name = secure.decoyNameFor(address).ifBlank { context.getString(R.string.app_name) }
        val text = secure.decoyTextFor(address).ifBlank { " " }
        val target = secure.decoyTargetFor(address)
        // A distinct notification per hidden number, so they don't overwrite each other.
        val notifId = decoyNotifId(address)

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
            context, notifId, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(context, DECOY_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_message)
            .setLargeIcon(appLargeIcon(context))
            .setColor(accentColor(context))
            .setContentTitle(name)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(pi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)

        // On pre-O devices the channel doesn't apply; vibrate but stay silent here.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            builder.setDefaults(NotificationCompat.DEFAULT_VIBRATE).setSound(null)
        }

        notify(context, notifId, builder)
    }

    /** A distinct notification id per hidden number. */
    private fun decoyNotifId(address: String): Int =
        ("decoy_" + SecureStore.normalize(address)).hashCode()

    /** Removes the decoy notification for a hidden number (e.g. once its chat is opened). */
    fun cancelDecoy(context: Context, address: String) {
        NotificationManagerCompat.from(context).cancel(decoyNotifId(address))
    }
}
