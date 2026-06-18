package com.infinityclone.app

import android.app.Application
import android.content.Context
import android.content.res.Configuration
import android.os.Build
import com.infinityclone.app.core.Engine
import org.lsposed.hiddenapibypass.HiddenApiBypass

/**
 * نقطه‌ی ورود اپ.
 *
 * موتور مجازی‌سازی باید *قبل* از هر کار دیگری در [attachBaseContext] راه‌اندازی شود،
 * چون لازم است پروسه‌های مجازی را در همان ابتدای چرخه‌ی عمر شناسایی کند.
 *
 * این کلاس فقط با [Engine] حرف می‌زند و هیچ ارجاع مستقیمی به موتور ندارد.
 */
class CloneApplication : Application() {

    override fun attachBaseContext(base: Context) {
        super.attachBaseContext(base)

        // عبور از محدودیت Hidden API در اندروید 9+ تا انعکاس‌های داخلی موتور کار کنند.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            HiddenApiBypass.addHiddenApiExemptions("")
        }

        Engine.instance.attach(base)
    }

    override fun onCreate() {
        super.onCreate()
        Engine.instance.onCreate()
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        Engine.instance.onConfigurationChanged(newConfig)
    }
}
