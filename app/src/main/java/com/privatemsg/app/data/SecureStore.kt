package com.privatemsg.app.data

import android.content.Context
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * Stores secret settings in private SharedPreferences:
 *  - the PIN (as a salted SHA-256 hash, never in plain text)
 *  - the global decoy notification (fake name, fake text, target conversation)
 *  - the set of hidden phone numbers
 */
class SecureStore(context: Context) {

    private val prefs = context.getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)

    // ---- PIN ----

    fun hasPin(): Boolean = prefs.contains(KEY_PIN_HASH)

    fun setPin(pin: String) {
        val salt = newSalt()
        prefs.edit()
            .putString(KEY_PIN_SALT, salt)
            .putString(KEY_PIN_HASH, hash(pin, salt))
            .apply()
    }

    fun checkPin(pin: String): Boolean {
        val salt = prefs.getString(KEY_PIN_SALT, null) ?: return false
        val stored = prefs.getString(KEY_PIN_HASH, null) ?: return false
        return stored == hash(pin, salt)
    }

    // ---- Decoy settings ----

    var decoyName: String
        get() = prefs.getString(KEY_DECOY_NAME, "") ?: ""
        set(v) = prefs.edit().putString(KEY_DECOY_NAME, v).apply()

    var decoyText: String
        get() = prefs.getString(KEY_DECOY_TEXT, "") ?: ""
        set(v) = prefs.edit().putString(KEY_DECOY_TEXT, v).apply()

    var decoyTarget: String
        get() = prefs.getString(KEY_DECOY_TARGET, "") ?: ""
        set(v) = prefs.edit().putString(KEY_DECOY_TARGET, v).apply()

    // ---- Per-number decoy (overrides the global decoy for that one number) ----

    /** Fake sender name for this number; falls back to the global decoy name. */
    fun decoyNameFor(address: String): String =
        prefs.getString(KEY_DECOY_NAME + "_" + normalize(address), null) ?: decoyName

    /** Fake message text for this number; falls back to the global decoy text. */
    fun decoyTextFor(address: String): String =
        prefs.getString(KEY_DECOY_TEXT + "_" + normalize(address), null) ?: decoyText

    /** Conversation opened when this number's decoy is tapped; falls back to global. */
    fun decoyTargetFor(address: String): String =
        prefs.getString(KEY_DECOY_TARGET + "_" + normalize(address), null) ?: decoyTarget

    /** True if this number has its own decoy notification configured. */
    fun hasCustomDecoy(address: String): Boolean {
        val n = normalize(address)
        return prefs.contains(KEY_DECOY_NAME + "_" + n) ||
            prefs.contains(KEY_DECOY_TEXT + "_" + n) ||
            prefs.contains(KEY_DECOY_TARGET + "_" + n)
    }

    fun setDecoyFor(address: String, name: String, text: String, target: String) {
        val n = normalize(address)
        prefs.edit()
            .putString(KEY_DECOY_NAME + "_" + n, name)
            .putString(KEY_DECOY_TEXT + "_" + n, text)
            .putString(KEY_DECOY_TARGET + "_" + n, target)
            .apply()
    }

    fun clearDecoyFor(address: String) {
        val n = normalize(address)
        prefs.edit()
            .remove(KEY_DECOY_NAME + "_" + n)
            .remove(KEY_DECOY_TEXT + "_" + n)
            .remove(KEY_DECOY_TARGET + "_" + n)
            .apply()
    }

    // ---- Hidden numbers ----

    fun getHiddenNumbers(): Set<String> =
        prefs.getStringSet(KEY_HIDDEN, emptySet())?.toSet() ?: emptySet()

    fun addHiddenNumber(number: String) {
        val set = getHiddenNumbers().toMutableSet()
        // Store the original address (for display); matching is done via normalize().
        set.add(number.trim())
        prefs.edit().putStringSet(KEY_HIDDEN, set).apply()
    }

    fun removeHiddenNumber(number: String) {
        val target = normalize(number)
        val set = getHiddenNumbers().filterNot { normalize(it) == target }.toSet()
        prefs.edit().putStringSet(KEY_HIDDEN, set).apply()
        // Drop any custom decoy that belonged to this number.
        clearDecoyFor(number)
    }

    fun isHidden(address: String): Boolean {
        val n = normalize(address)
        return getHiddenNumbers().any { normalize(it) == n }
    }

    // ---- Pinned conversations (by thread id) ----

    fun getPinned(): Set<Long> =
        prefs.getStringSet(KEY_PINNED, emptySet())?.mapNotNull { it.toLongOrNull() }?.toSet()
            ?: emptySet()

    fun togglePin(threadId: Long) {
        val set = getPinned().toMutableSet()
        if (!set.add(threadId)) set.remove(threadId)
        prefs.edit().putStringSet(KEY_PINNED, set.map { it.toString() }.toSet()).apply()
    }

    fun isPinned(threadId: Long): Boolean = getPinned().contains(threadId)

    // ---- App settings ----

    var deliveryReportEnabled: Boolean
        get() = prefs.getBoolean(KEY_DELIVERY, true)
        set(v) = prefs.edit().putBoolean(KEY_DELIVERY, v).apply()

    // ---- Display size ----

    /** Extra scaling applied to text only (sp). 1.0 = normal. */
    var fontScale: Float
        get() = prefs.getFloat(KEY_FONT_SCALE, 1f)
        set(v) = prefs.edit().putFloat(KEY_FONT_SCALE, v).apply()

    /** Scaling applied to the whole UI (like changing screen DPI). 1.0 = normal. */
    var uiScale: Float
        get() = prefs.getFloat(KEY_UI_SCALE, 1f)
        set(v) = prefs.edit().putFloat(KEY_UI_SCALE, v).apply()

    /** Allow unlocking the hidden section with a fingerprint (in addition to the PIN). */
    var fingerprintEnabled: Boolean
        get() = prefs.getBoolean(KEY_FINGERPRINT, false)
        set(v) = prefs.edit().putBoolean(KEY_FINGERPRINT, v).apply()

    // ---- Bubble colors ----

    /** Background color of messages I send (default Mi green). */
    var sentBubbleColor: Int
        get() = prefs.getInt(KEY_SENT_COLOR, DEFAULT_SENT_COLOR)
        set(v) = prefs.edit().putInt(KEY_SENT_COLOR, v).apply()

    /** Background color of messages I receive (default Mi grey). */
    var receivedBubbleColor: Int
        get() = prefs.getInt(KEY_RECEIVED_COLOR, DEFAULT_RECEIVED_COLOR)
        set(v) = prefs.edit().putInt(KEY_RECEIVED_COLOR, v).apply()

    // ---- Per-conversation preferred SIM ----

    fun getThreadSim(address: String): Int =
        if (address.isBlank()) -1 else prefs.getInt("sim_" + normalize(address), -1)

    fun setThreadSim(address: String, subId: Int) {
        if (address.isBlank()) return
        prefs.edit().putInt("sim_" + normalize(address), subId).apply()
    }

    companion object {
        private const val KEY_PIN_HASH = "pin_hash"
        private const val KEY_PIN_SALT = "pin_salt"
        private const val KEY_DECOY_NAME = "decoy_name"
        private const val KEY_DECOY_TEXT = "decoy_text"
        private const val KEY_DECOY_TARGET = "decoy_target"
        private const val KEY_HIDDEN = "hidden_numbers"
        private const val KEY_PINNED = "pinned_threads"
        private const val KEY_DELIVERY = "delivery_report"
        private const val KEY_FONT_SCALE = "font_scale"
        private const val KEY_UI_SCALE = "ui_scale"
        private const val KEY_FINGERPRINT = "fingerprint_unlock"
        private const val KEY_SENT_COLOR = "sent_bubble_color"
        private const val KEY_RECEIVED_COLOR = "received_bubble_color"

        /** Default sent bubble = Mi green; received = Mi grey pill. */
        const val DEFAULT_SENT_COLOR = 0xFF1FA055.toInt()
        const val DEFAULT_RECEIVED_COLOR = 0xFF2C2C2E.toInt()

        /**
         * Normalize an address for matching.
         * - Real phone numbers (only digits and separators, 7+ digits) -> last 10 digits.
         * - Operator/alphanumeric sender IDs (e.g. names with letters) -> lowercased text.
         */
        fun normalize(address: String): String {
            val trimmed = address.trim()
            val digits = trimmed.filter { it.isDigit() }
            val nonDigitNonSep = trimmed.count { !it.isDigit() && it !in "+-() " }
            return if (nonDigitNonSep == 0 && digits.length >= 7) {
                digits.takeLast(10)
            } else {
                trimmed.lowercase()
            }
        }

        private fun newSalt(): String {
            val bytes = ByteArray(16)
            SecureRandom().nextBytes(bytes)
            return bytes.joinToString("") { "%02x".format(it) }
        }

        private fun hash(pin: String, salt: String): String {
            val md = MessageDigest.getInstance("SHA-256")
            val out = md.digest((salt + pin).toByteArray())
            return out.joinToString("") { "%02x".format(it) }
        }
    }
}
