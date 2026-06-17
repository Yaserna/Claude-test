package com.privatemsg.app.ui

import android.text.SpannableString
import android.text.Spanned
import android.text.method.LinkMovementMethod
import android.text.style.ClickableSpan
import android.text.style.URLSpan
import android.text.util.Linkify
import android.view.View
import android.widget.TextView
import java.util.regex.Pattern

/** Makes URLs clickable (open browser) and number runs clickable (custom menu). */
object Linkifier {

    // A run of digits (with optional + and spaces); filtered further below.
    private val NUMBER: Pattern = Pattern.compile("\\+?\\d[\\d ]{2,}\\d")

    fun apply(tv: TextView, body: String, onNumber: (String) -> Unit) {
        val sp = SpannableString(body)
        Linkify.addLinks(sp, Linkify.WEB_URLS or Linkify.EMAIL_ADDRESSES)

        val urlSpans = sp.getSpans(0, sp.length, URLSpan::class.java)
        fun overlapsUrl(s: Int, e: Int): Boolean = urlSpans.any {
            val us = sp.getSpanStart(it)
            val ue = sp.getSpanEnd(it)
            s < ue && us < e
        }

        val m = NUMBER.matcher(body)
        while (m.find()) {
            val s = m.start()
            val e = m.end()
            if (overlapsUrl(s, e)) continue
            val raw = body.substring(s, e)
            // Need at least 4 digits to be a meaningful number.
            if (raw.count { it.isDigit() } < 4) continue
            // Skip times/dates/ranges: matches sitting next to ':' '/' '-'.
            val before = if (s > 0) body[s - 1] else ' '
            val after = if (e < body.length) body[e] else ' '
            if (before == ':' || before == '/' || before == '-' ||
                after == ':' || after == '/' || after == '-'
            ) continue
            sp.setSpan(object : ClickableSpan() {
                override fun onClick(widget: View) = onNumber(raw.trim())
                override fun updateDrawState(ds: android.text.TextPaint) {
                    ds.color = 0xFF4DA3FF.toInt()
                    ds.isUnderlineText = false
                }
            }, s, e, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }

        tv.text = sp
        tv.movementMethod = LinkMovementMethod.getInstance()
        tv.linksClickable = true
    }
}
