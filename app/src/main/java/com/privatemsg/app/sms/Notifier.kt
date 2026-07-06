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
import androidx.core.app.RemoteInput
import com.privatemsg.app.R
import com.privatemsg.app.data.ContactsHelper
import com.privatemsg.app.data.SecureStore
import com.privatemsg.app.data.SmsRepository
import com.privatemsg.app.ui.ConversationActivity
import com.privatemsg.app.ui.MainActivity

object Notifier {

    private const val CHANNEL_ID = "incoming_sms"
    // Separate channel for decoy notifications: vibrate but NO sound, so a hidden
    // message never makes an audible alert (only the real ones do).
    private const val DECOY_CHANNEL_ID = "decoy_sms_silent"
    // Optional channel used when the user turns decoy sound ON (channels can't
    // change their sound after creation, so a sound variant needs its own id).
    private const val DECOY_SOUND_CHANNEL_ID = "decoy_sms_sound"

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

    /** Channel for decoy notifications with sound on (used when the user enables it). */
    private fun ensureDecoySoundChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                DECOY_SOUND_CHANNEL_ID,
                "Messages",
                NotificationManager.IMPORTANCE_HIGH
            )
            channel.enableVibration(true)
            context.getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    /**
     * The accent color used to tint the (monochrome) status-bar icon so the
     * notification shows in the app's orange tone instead of a flat white icon.
     */
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

        // "Reply" opens a small floating quick-reply window (not the whole app),
        // reliable on MIUI where inline-reply boxes often don't open.
        val replyOpenIntent = Intent(context, com.privatemsg.app.ui.QuickReplyActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
            putExtra("address", address)
            putExtra("thread_id", threadId)
            putExtra("notif_id", notifId)
        }
        val replyPi = PendingIntent.getActivity(
            context, notifId * 31 + 1, replyOpenIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val readPi = PendingIntent.getBroadcast(
            context, notifId * 31 + 2, actionIntent(NotificationActionReceiver.ACTION_MARK_READ),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val deletePi = PendingIntent.getBroadcast(
            context, notifId * 31 + 3, actionIntent(NotificationActionReceiver.ACTION_DELETE),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val replyAction = NotificationCompat.Action.Builder(
            R.drawable.ic_send_up, context.getString(R.string.notif_reply), replyPi
        ).build()

        val title = ContactsHelper(context).displayFor(address)
        // All still-unread messages from this sender, so several in a row show
        // together with a count instead of only the last one.
        val unread = SmsRepository(context).unreadBodies(threadId)
        val count = if (unread.isEmpty()) 1 else unread.size

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_message)
            .setColor(accentColor(context))
            .setContentTitle(title)
            .setAutoCancel(true)
            .setContentIntent(tapPi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .addAction(R.drawable.ic_mark_read, context.getString(R.string.notif_mark_read), readPi)
            .addAction(R.drawable.ic_delete, context.getString(R.string.notif_delete), deletePi)
            .addAction(replyAction)

        if (count > 1) {
            val inbox = NotificationCompat.InboxStyle()
            unread.takeLast(7).forEach { inbox.addLine(it) }
            inbox.setSummaryText(context.getString(R.string.n_new_messages, count))
            builder.setStyle(inbox)
                .setContentText(context.getString(R.string.n_new_messages, count))
                .setNumber(count)
        } else {
            builder.setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setContentText(body)
        }

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

    /** Alerts the user that an outgoing message failed to send. */
    fun showSendFailed(context: Context, address: String) {
        ensureChannel(context)
        val notifId = ("failed_" + address).hashCode()
        val title = ContactsHelper(context).displayFor(address)
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
        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_message)
            .setColor(accentColor(context))
            .setContentTitle(title)
            .setContentText(context.getString(R.string.send_failed_notif))
            .setAutoCancel(true)
            .setContentIntent(tapPi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            builder.setDefaults(NotificationCompat.DEFAULT_SOUND or NotificationCompat.DEFAULT_VIBRATE)
        }
        notify(context, notifId, builder)
    }

    /** A short vibration, used when a message arrives for the conversation already open. */
    fun vibrateTiny(context: Context) {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE)
                as android.os.VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as android.os.Vibrator
        }
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(
                    android.os.VibrationEffect.createOneShot(
                        45, android.os.VibrationEffect.DEFAULT_AMPLITUDE
                    )
                )
            } else {
                @Suppress("DEPRECATION") vibrator.vibrate(45)
            }
        } catch (e: Exception) {
            // No vibrator or permission; ignore.
        }
    }

    /**
     * Decoy notification for a hidden sender: shows the user-defined fake name
     * and fake text, and tapping it opens the chosen innocent conversation
     * (never the hidden section).
     */
    fun showDecoy(context: Context, secure: SecureStore, address: String) {
        val soundOn = secure.decoySoundEnabled
        if (soundOn) ensureDecoySoundChannel(context) else ensureDecoyChannel(context)
        val channelId = if (soundOn) DECOY_SOUND_CHANNEL_ID else DECOY_CHANNEL_ID

        // Each hidden number can have its own decoy (falls back to the global one).
        val name = secure.decoyNameFor(address).ifBlank { context.getString(R.string.app_name) }
        val rawText = secure.decoyTextFor(address)
        val text = rawText.ifBlank { " " }
        val target = secure.decoyTargetFor(address)
        val now = System.currentTimeMillis()
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
                // So tapping the decoy shows the fake text in the cover chat.
                if (rawText.isNotBlank()) {
                    putExtra("decoy_fake_text", rawText)
                    putExtra("decoy_fake_time", now)
                }
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

        val builder = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_message)
            .setColor(accentColor(context))
            .setContentTitle(name)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(pi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)

        // On pre-O devices the channel doesn't apply; set sound/vibration here to match.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            if (soundOn) {
                builder.setDefaults(NotificationCompat.DEFAULT_SOUND or NotificationCompat.DEFAULT_VIBRATE)
            } else {
                builder.setDefaults(NotificationCompat.DEFAULT_VIBRATE).setSound(null)
            }
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
