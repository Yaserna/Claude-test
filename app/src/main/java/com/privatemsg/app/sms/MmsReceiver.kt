package com.privatemsg.app.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Required so the app is eligible to be the default SMS app.
 * Full MMS handling will be added later.
 */
class MmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        // MMS handling to be implemented in a later milestone.
    }
}
