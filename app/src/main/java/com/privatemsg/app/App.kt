package com.privatemsg.app

import android.app.Activity
import android.app.Application
import android.os.Bundle

/**
 * Tracks whether any activity of the app is currently visible (started). Used by
 * the hidden section to detect when the app goes to the background or the screen
 * locks, so it can close itself and return to the main screen.
 */
class App : Application() {

    override fun onCreate() {
        super.onCreate()
        registerActivityLifecycleCallbacks(object : ActivityLifecycleCallbacks {
            override fun onActivityStarted(activity: Activity) { started++ }
            override fun onActivityStopped(activity: Activity) { started-- }
            override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {}
            override fun onActivityResumed(activity: Activity) {}
            override fun onActivityPaused(activity: Activity) {}
            override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}
            override fun onActivityDestroyed(activity: Activity) {}
        })
    }

    companion object {
        private var started = 0
        /** True while at least one activity is visible (the app is in the foreground). */
        val inForeground: Boolean get() = started > 0
    }
}
