package com.infinityclone.app.core

import android.content.Context
import android.content.res.Configuration

/**
 * یک کلون نصب‌شده در فضای مجازی.
 *
 * @param packageName نام پکیج اپ اصلی که کلون شده.
 * @param userId شناسه‌ی فضای مجازی. هر userId یک نسخه‌ی مستقل است؛
 *               پس «کلون نامحدود» = ساختن userIdهای جدید بدون سقف.
 */
data class CloneInfo(
    val packageName: String,
    val userId: Int,
    val label: String,
)

/**
 * قرارداد بین اپ میزبان و موتور مجازی‌سازی.
 *
 * کل برنامه فقط با این اینترفیس کار می‌کند و هیچ‌جای دیگری مستقیماً به موتور
 * (BlackBox/NewBlackbox) وصل نیست. این یعنی تعویض یا به‌روزرسانی موتور فقط یک
 * پیاده‌سازی جدید از این اینترفیس می‌خواهد.
 */
interface CloneEngine {

    /** آیا موتور واقعی فعال است؟ (false یعنی پیاده‌سازی Noop در حال اجراست) */
    val isReady: Boolean

    // ── چرخه‌ی عمر (از CloneApplication صدا زده می‌شود) ────────────────
    fun attach(context: Context)
    fun onCreate()
    fun onConfigurationChanged(newConfig: Configuration)

    // ── عملیات کلون ─────────────────────────────────────────────────

    /** فهرست همه‌ی کلون‌های ساخته‌شده در تمام فضاهای مجازی. */
    fun listClones(): List<CloneInfo>

    /**
     * یک کلون جدید از اپی که روی دستگاه نصب است می‌سازد.
     * اگر [userId] برابر -1 باشد، یک فضای مجازی جدید (کلون بعدی) ساخته می‌شود.
     * @return userId فضایی که کلون در آن نصب شد، یا -1 در صورت شکست.
     */
    fun createClone(packageName: String, userId: Int = -1): Int

    /** اجرای یک کلون. */
    fun launchClone(packageName: String, userId: Int)

    /** حذف یک کلون مشخص. */
    fun removeClone(packageName: String, userId: Int)

    /** آیا این پکیج در این فضای مجازی نصب است؟ */
    fun isCloneInstalled(packageName: String, userId: Int): Boolean
}
