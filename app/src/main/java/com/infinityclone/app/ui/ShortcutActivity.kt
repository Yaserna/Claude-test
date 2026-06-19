package com.infinityclone.app.ui

import android.app.Activity
import android.os.Bundle
import com.infinityclone.app.core.Engine

/**
 * اکتیویتی نامرئی که از طریق آیکن صفحه‌ی اصلی صدا زده می‌شود و فقط کلون موردنظر
 * را اجرا می‌کند، بعد بسته می‌شود.
 *
 * عمداً از android.app.Activity (نه AppCompat) با تم NoDisplay استفاده می‌کند و
 * در همان onCreate finish() را صدا می‌زند تا چیزی روی صفحه نشان داده نشود.
 */
class ShortcutActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pkg = intent?.getStringExtra(EXTRA_PKG)
        val userId = intent?.getIntExtra(EXTRA_USER, -1) ?: -1
        if (!pkg.isNullOrEmpty() && userId >= 0) {
            // اجرای کلون روی نخ پس‌زمینه (تماس موتور نباید روی نخ اصلی باشد).
            Thread {
                runCatching { Engine.instance.launchClone(pkg, userId) }
            }.apply { isDaemon = true; start() }
        }
        finish()
    }

    companion object {
        const val EXTRA_PKG = "pkg"
        const val EXTRA_USER = "userId"
    }
}
