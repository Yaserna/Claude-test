package com.infinityclone.app.core

import android.content.Context

/**
 * نگه‌دارنده‌ی نام‌های دلخواهی که کاربر برای هر کلون انتخاب می‌کند.
 * کلید هر کلون ترکیب packageName و userId است.
 */
object CloneNames {

    private const val PREFS = "clone_names"

    private fun key(packageName: String, userId: Int) = "$packageName@$userId"

    private fun prefs(context: Context) =
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** نام دلخواه این کلون، یا null اگر کاربر نامی نگذاشته باشد. */
    fun get(context: Context, packageName: String, userId: Int): String? =
        prefs(context).getString(key(packageName, userId), null)?.takeIf { it.isNotBlank() }

    fun set(context: Context, packageName: String, userId: Int, name: String) {
        prefs(context).edit().putString(key(packageName, userId), name.trim()).apply()
    }

    fun clear(context: Context, packageName: String, userId: Int) {
        prefs(context).edit().remove(key(packageName, userId)).apply()
    }
}
