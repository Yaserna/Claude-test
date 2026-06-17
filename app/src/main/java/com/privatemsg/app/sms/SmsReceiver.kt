package com.privatemsg.app.sms

import android.content.BroadcastReceiver
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import com.privatemsg.app.data.HiddenDbHelper
import com.privatemsg.app.data.SecureStore

class SmsReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_DELIVER_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent) ?: return
        if (messages.isEmpty()) return

        val address = messages[0].originatingAddress ?: ""
        val body = StringBuilder()
        var date = System.currentTimeMillis()
        for (m in messages) {
            body.append(m.messageBody)
            date = m.timestampMillis
        }
        val text = body.toString()

        val subId = intent.getIntExtra("subscription", -1)

        val secure = SecureStore(context)
        if (secure.isHidden(address)) {
            // Hidden sender: store privately, never touch the system store,
            // and show only the decoy notification.
            HiddenDbHelper(context).insert(address, text, date, INBOX, subId)
            Notifier.showDecoy(context, secure, address)
            return
        }

        // Normal sender: as the default SMS app we write to the system store.
        val values = ContentValues().apply {
            put(Telephony.Sms.ADDRESS, address)
            put(Telephony.Sms.BODY, text)
            put(Telephony.Sms.DATE, date)
            put(Telephony.Sms.READ, 0)
            put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_INBOX)
            if (subId >= 0) put(Telephony.Sms.SUBSCRIPTION_ID, subId)
        }
        val uri = context.contentResolver.insert(Telephony.Sms.Inbox.CONTENT_URI, values)
        val messageId = uri?.lastPathSegment?.toLongOrNull() ?: -1

        Notifier.showIncoming(context, address, text, messageId)
    }

    companion object {
        private const val INBOX = 1
    }
}
