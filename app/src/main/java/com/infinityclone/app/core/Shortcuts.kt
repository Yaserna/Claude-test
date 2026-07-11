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
    fun pin(
        context: Context,
        packageName: String,
        userId: Int,
        label: String,
        iconDrawable: Drawable? = null,
    ): Boolean {
        if (!isSupported(context)) return false

        val intent = Intent(context, ShortcutActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            putExtra(ShortcutActivity.EXTRA_PKG, packageName)
            putExtra(ShortcutActivity.EXTRA_USER, userId)
        }

        // آیکنِ خودِ کلون (از موتور) در اولویت است؛ اپ‌های کلونِ نصب‌نشده روی گوشی
        // در PM میزبان نیستند و آیکن‌شان فقط از این طریق در دسترس است.
        val icon = iconDrawable?.let { adaptiveIcon(it) }
            ?: appIcon(context, packageName)
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
            adaptiveIcon(context.packageManager.getApplicationIcon(packageName))
        }.getOrNull()
    }

    /**
     * آیکن تطبیقی (adaptive) می‌سازد تا لانچر حاشیه‌ی سفیدِ آیکن‌های legacy را اضافه
     * نکند و آیکن کل شکل را پر کند. آیکن اصلی داخل «ناحیه‌ی امن» (۷۲٪ مرکزی) رسم
     * می‌شود تا وقتی لانچر لبه‌ها را ماسک می‌کند بریده نشود.
     */
    private fun adaptiveIcon(drawable: Drawable): IconCompat {
        val size = 108
        val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, size, size)
        drawable.draw(canvas)
        return IconCompat.createWithAdaptiveBitmap(bitmap)
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
