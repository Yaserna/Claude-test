package com.infinityclone.app

import android.app.Application
import android.content.Context
import com.infinityclone.app.core.Engine

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
        Engine.instance.attach(this, base)
    }

    override fun onCreate() {
        super.onCreate()
        Engine.instance.onCreate()
    }
}
