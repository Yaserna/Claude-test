package com.privatemsg.app.ui

import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import com.privatemsg.app.R

/**
 * Switches the launcher icon by enabling one <activity-alias> and disabling the
 * rest. Exactly one alias is always enabled, so the app never loses its icon.
 */
object AppIcons {

    /** Alias name (matches the manifest) → preview drawable + label. */
    val options: List<Triple<String, Int, Int>> = listOf(
        Triple("IconDefault", R.drawable.ic_launcher, R.string.icon_default),
        Triple("IconPlane", R.drawable.ic_launcher_plane, R.string.icon_plane),
        Triple("IconChat", R.drawable.ic_launcher_chat, R.string.icon_chat),
        Triple("IconBubble", R.drawable.ic_launcher_bubble, R.string.icon_bubble),
        Triple("IconClassic", R.drawable.ic_launcher_classic, R.string.icon_classic)
    )

    fun apply(context: Context, chosen: String) {
        val pm = context.packageManager
        val pkg = context.packageName
        for ((alias, _, _) in options) {
            val state =
                if (alias == chosen) PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                else PackageManager.COMPONENT_ENABLED_STATE_DISABLED
            pm.setComponentEnabledSetting(
                ComponentName(pkg, "$pkg.$alias"), state, PackageManager.DONT_KILL_APP
            )
        }
    }
}
