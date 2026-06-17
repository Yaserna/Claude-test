package com.privatemsg.app.data

import android.content.Context
import android.net.Uri
import android.provider.ContactsContract
import java.util.concurrent.ConcurrentHashMap

/** Resolves a phone number to its saved contact name (shared thread-safe cache). */
class ContactsHelper(private val context: Context) {

    /** Contact name if known, otherwise the number itself. */
    fun displayFor(number: String): String {
        if (number.isBlank()) return "نامشخص"
        cache[number]?.let { return it }
        val resolved = nameFor(number) ?: number
        cache[number] = resolved
        return resolved
    }

    fun nameFor(number: String): String? {
        if (number.isBlank()) return null
        var name: String? = null
        try {
            val uri = Uri.withAppendedPath(
                ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                Uri.encode(number)
            )
            context.contentResolver.query(
                uri,
                arrayOf(ContactsContract.PhoneLookup.DISPLAY_NAME),
                null, null, null
            )?.use { c ->
                if (c.moveToFirst()) name = c.getString(0)
            }
        } catch (e: SecurityException) {
            // READ_CONTACTS not granted; fall back to number.
        }
        return name
    }

    companion object {
        // Shared across instances so a number is looked up at most once per session.
        private val cache = ConcurrentHashMap<String, String>()
    }
}
