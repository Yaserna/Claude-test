package com.infinityclone.app.core

import android.content.Context
import java.security.MessageDigest

/**
 * وضعیت «مخفی‌بودن» کلون‌ها و رمز ورود به بخش مخفی.
 *
 * رمز به‌صورت هش SHA-256 ذخیره می‌شود (متن خام رمز هرگز نوشته نمی‌شود).
 * کلید هر کلون مخفی ترکیب packageName و userId است.
 */
object HiddenStore {

    private const val PREFS = "hidden_clones"
    private const val KEY_HASH = "passcode_hash"
    private const val KEY_SET = "hidden_keys"

    private fun key(packageName: String, userId: Int) = "$packageName@$userId"

    private fun prefs(context: Context) =
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun sha256(text: String): String =
        MessageDigest.getInstance("SHA-256").digest(text.toByteArray())
            .joinToString("") { "%02x".format(it) }

    // ── رمز ورود ────────────────────────────────────────────────────
    /** آیا کاربر تا حالا رمزی تنظیم کرده است؟ */
    fun hasPasscode(context: Context): Boolean =
        prefs(context).getString(KEY_HASH, null) != null

    fun setPasscode(context: Context, passcode: String) {
        prefs(context).edit().putString(KEY_HASH, sha256(passcode)).apply()
    }

    /** آیا متن واردشده با رمز تنظیم‌شده مطابقت دارد؟ */
    fun checkPasscode(context: Context, candidate: String): Boolean {
        if (candidate.isBlank()) return false
        val stored = prefs(context).getString(KEY_HASH, null) ?: return false
        return stored == sha256(candidate)
    }

    // ── وضعیت مخفی‌بودن ─────────────────────────────────────────────
    private fun hiddenSet(context: Context): MutableSet<String> =
        HashSet(prefs(context).getStringSet(KEY_SET, emptySet()) ?: emptySet())

    fun isHidden(context: Context, packageName: String, userId: Int): Boolean =
        hiddenSet(context).contains(key(packageName, userId))

    fun setHidden(context: Context, packageName: String, userId: Int, hidden: Boolean) {
        val set = hiddenSet(context)
        if (hidden) set.add(key(packageName, userId)) else set.remove(key(packageName, userId))
        prefs(context).edit().putStringSet(KEY_SET, set).apply()
    }

    /** آیا اصلاً کلون مخفی‌ای وجود دارد؟ */
    fun hasAnyHidden(context: Context): Boolean = hiddenSet(context).isNotEmpty()
}
