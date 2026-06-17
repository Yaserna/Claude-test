package com.privatemsg.app.sms

import android.app.Service
import android.content.Intent
import android.os.IBinder

/**
 * Required so the app is eligible to be the default SMS app
 * (handles "respond via message" quick replies). Implemented later.
 */
class HeadlessSmsSendService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_NOT_STICKY
    }
}
