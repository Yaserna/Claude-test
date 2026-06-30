package com.privatemsg.app.ui

import java.util.Calendar

/** Converts a timestamp to a Persian (Jalali/Shamsi) date label for chat day-separators. */
object JalaliDate {

    private val months = arrayOf(
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    )

    /** True if the two timestamps fall on the same calendar day. */
    fun sameDay(a: Long, b: Long): Boolean {
        val ca = Calendar.getInstance().apply { timeInMillis = a }
        val cb = Calendar.getInstance().apply { timeInMillis = b }
        return ca.get(Calendar.YEAR) == cb.get(Calendar.YEAR) &&
            ca.get(Calendar.DAY_OF_YEAR) == cb.get(Calendar.DAY_OF_YEAR)
    }

    /** "امروز" / "دیروز" / "10 تیر 1403" for the day of [time]. */
    fun label(time: Long): String {
        val day = atMidnight(time)
        val today = atMidnight(System.currentTimeMillis())
        val diff = (today - day) / 86_400_000L
        if (diff == 0L) return "امروز"
        if (diff == 1L) return "دیروز"
        val c = Calendar.getInstance().apply { timeInMillis = time }
        val (jy, jm, jd) = toJalali(
            c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1, c.get(Calendar.DAY_OF_MONTH)
        )
        return "$jd ${months[jm - 1]} $jy"
    }

    private fun atMidnight(t: Long): Long {
        val c = Calendar.getInstance().apply {
            timeInMillis = t
            set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
        }
        return c.timeInMillis
    }

    /** Standard Gregorian → Jalali conversion. */
    private fun toJalali(gy: Int, gm: Int, gd: Int): Triple<Int, Int, Int> {
        val gDM = intArrayOf(0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
        val gy2 = if (gm > 2) gy + 1 else gy
        var days = 355666 + (365 * gy) + ((gy2 + 3) / 4) - ((gy2 + 99) / 100) +
            ((gy2 + 399) / 400) + gd + gDM[gm - 1]
        var jy = -1595 + (33 * (days / 12053)); days %= 12053
        jy += 4 * (days / 1461); days %= 1461
        if (days > 365) { jy += (days - 1) / 365; days = (days - 1) % 365 }
        return if (days < 186) {
            Triple(jy, 1 + (days / 31), 1 + (days % 31))
        } else {
            Triple(jy, 7 + ((days - 186) / 30), 1 + ((days - 186) % 30))
        }
    }
}
