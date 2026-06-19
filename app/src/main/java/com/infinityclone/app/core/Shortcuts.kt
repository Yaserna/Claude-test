package com.infinityclone.app.core

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat
import com.infinityclone.app.R
import com.infinityclone.app.ui.ShortcutActivity

/** ابزارهای ساختن آیکن کلون روی صفحه‌ی اصلی. */
object Shortcuts {

    /** آیا سیستم اجازه‌ی افزودن آیکن (pinned shortcut) را می‌دهد؟ */
    fun isSupported(context: Context): Boolean =
        ShortcutManagerCompat.isRequestPinShortcutSupported(context)

    /**
     * یک آیکن روی صفحه‌ی اصلی می‌سازد که با لمس، این کلون را اجرا می‌کند.
     * آیکن و نام، از اپ اصلی + نام دلخواه کاربر گرفته می‌شوند.
     */
    fun pin(context: Context, packageName: String, userId: Int, label: String): Boolean {
        if (!isSupported(context)) return false

        val intent = Intent(context, ShortcutActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            putExtra(ShortcutActivity.EXTRA_PKG, packageName)
            putExtra(ShortcutActivity.EXTRA_USER, userId)
        }

        val icon = appIcon(context, packageName)
            ?: IconCompat.createWithResource(context, R.mipmap.ic_launcher)

        val shortcut = ShortcutInfoCompat.Builder(context, "clone_${packageName}_$userId")
            .setShortLabel(label)
            .setLongLabel(label)
            .setIcon(icon)
            .setIntent(intent)
            .build()

        return ShortcutManagerCompat.requestPinShortcut(context, shortcut, null)
    }

    private fun appIcon(context: Context, packageName: String): IconCompat? {
        return runCatching {
            val drawable = context.packageManager.getApplicationIcon(packageName)
            IconCompat.createWithBitmap(drawableToBitmap(drawable))
        }.getOrNull()
    }

    private fun drawableToBitmap(drawable: Drawable): Bitmap {
        if (drawable is BitmapDrawable && drawable.bitmap != null) return drawable.bitmap
        val width = drawable.intrinsicWidth.takeIf { it > 0 } ?: 108
        val height = drawable.intrinsicHeight.takeIf { it > 0 } ?: 108
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, canvas.width, canvas.height)
        drawable.draw(canvas)
        return bitmap
    }
}
