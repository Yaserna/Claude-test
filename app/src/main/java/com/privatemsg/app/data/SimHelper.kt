package com.privatemsg.app.data

import android.content.Context
import android.os.Build
import android.telephony.SubscriptionManager

/** Lists the active SIM cards so the user can choose which one sends a message. */
class SimHelper(private val context: Context) {

    data class Sim(val subId: Int, val slot: Int)

    fun sims(): List<Sim> = try {
        val sm = context.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as SubscriptionManager
        (sm.activeSubscriptionInfoList ?: emptyList())
            .map { Sim(it.subscriptionId, it.simSlotIndex + 1) }
            .sortedBy { it.slot }
    } catch (e: Exception) {
        emptyList()
    }

    fun defaultSubId(): Int = try {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R)
            SubscriptionManager.getDefaultSmsSubscriptionId()
        else -1
    } catch (e: Throwable) {
        -1
    }
}
