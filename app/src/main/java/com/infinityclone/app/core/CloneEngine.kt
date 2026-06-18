package com.infinityclone.app.core

import android.app.Application
import android.content.Context

/**
 * یک کلون نصب‌شده در فضای مجازی.
 *
 * هر [userId] یک فضای مجازی مستقل است؛ پس «کلون نامحدود» یعنی ساختن فضاهای
 * جدید بدون سقف.
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
 * (BlackBox/NewBlackbox) وصل نیست.
 */
interface CloneEngine {

    /** آیا موتور واقعی فعال است؟ */
    val isReady: Boolean

    /** آخرین مرحله‌ای که عملیات به آن رسیده (برای تشخیص محل گیرکردن). */
    val lastStep: String

    // ── چرخه‌ی عمر (از CloneApplication صدا زده می‌شود) ────────────────
    fun attach(app: Application, base: Context)
    fun onCreate()

    // ── عملیات کلون ─────────────────────────────────────────────────

    /** فهرست همه‌ی کلون‌های ساخته‌شده در تمام فضاهای مجازی. */
    fun listClones(): List<CloneInfo>

    /**
     * یک کلون جدید از اپی که روی دستگاه نصب است می‌سازد. یک فضای مجازی تازه
     * انتخاب/ساخته می‌شود تا کلون مستقل از نسخه‌های قبلی باشد.
     * @return userId فضایی که کلون در آن نصب شد، یا -1 در صورت شکست.
     */
    fun createClone(packageName: String): Int

    /** اجرای یک کلون. */
    fun launchClone(packageName: String, userId: Int): Boolean

    /** حذف یک کلون مشخص. */
    fun removeClone(packageName: String, userId: Int)

    /** آیا این پکیج در این فضای مجازی نصب است؟ */
    fun isCloneInstalled(packageName: String, userId: Int): Boolean
}
