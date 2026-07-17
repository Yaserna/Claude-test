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
        Triple("IconPlane", R.drawable.ic_launcher_gmsg, R.string.icon_google),
        Triple("IconChat", R.drawable.ic_launcher_samsung, R.string.icon_samsung),
        Triple("IconBubble", R.drawable.ic_launcher_huawei, R.string.icon_huawei),
        Triple("IconClassic", R.drawable.ic_launcher_poco, R.string.icon_poco)
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
