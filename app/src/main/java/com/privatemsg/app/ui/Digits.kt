package com.privatemsg.app.ui

/** Converts Persian/Arabic-Indic digits to Latin (English) digits; other chars are kept. */
fun String.toLatinDigits(): String {
    val sb = StringBuilder(length)
    for (ch in this) {
        sb.append(
            when (ch) {
                in '۰'..'۹' -> '0' + (ch - '۰') // Persian digits
                in '٠'..'٩' -> '0' + (ch - '٠') // Arabic-Indic digits
                else -> ch
            }
        )
    }
    return sb.toString()
}
