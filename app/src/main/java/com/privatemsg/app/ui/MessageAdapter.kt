package com.privatemsg.app.ui

import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import androidx.recyclerview.widget.RecyclerView
import com.privatemsg.app.R
import com.privatemsg.app.data.Message
import com.privatemsg.app.databinding.ItemMessageBinding

class MessageAdapter(
    private val showSim: Boolean = false,
    private val slotForSub: (Int) -> Int? = { null },
    private val onLongClick: (Message) -> Unit = {},
    private val onNumberClick: (String) -> Unit = {},
    private val onSelectionChanged: () -> Unit = {}
) : RecyclerView.Adapter<MessageAdapter.VH>() {

    private val items = mutableListOf<Message>()
    private val selected = mutableSetOf<Long>()
    var selectionMode = false
        private set

    fun submit(list: List<Message>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    fun startSelection(m: Message) {
        selectionMode = true
        selected.clear()
        selected.add(m.id)
        notifyDataSetChanged()
        onSelectionChanged()
    }

    fun exitSelection() {
        selectionMode = false
        selected.clear()
        notifyDataSetChanged()
        onSelectionChanged()
    }

    fun selectAll() {
        selected.clear()
        items.forEach { selected.add(it.id) }
        notifyDataSetChanged()
        onSelectionChanged()
    }

    private fun toggle(m: Message) {
        if (!selected.add(m.id)) selected.remove(m.id)
        notifyDataSetChanged()
        onSelectionChanged()
    }

    fun selectedMessages(): List<Message> = items.filter { selected.contains(it.id) }
    fun selectedCount(): Int = selected.size

    inner class VH(val binding: ItemMessageBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val b = ItemMessageBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(b)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val m = items[position]
        // Anything that isn't an incoming message belongs on the sender's side
        // (sent / outbox / failed / queued) — so a failed send never looks "received".
        val sent = m.type != INBOX
        val failed = m.type == FAILED
        val ctx = holder.itemView.context

        Linkifier.apply(holder.binding.text, m.body.toLatinDigits(), onNumberClick)
        holder.binding.bubble.setBackgroundResource(
            if (sent) R.drawable.bubble_sent else R.drawable.bubble_received
        )
        // Sent messages on the right (START in RTL), received on the left (END).
        (holder.binding.root as LinearLayout).gravity =
            if (sent) Gravity.START else Gravity.END

        val delivered = sent && m.status == 0

        // Time: black for sent, light grey for received. Always stays black for sent.
        // Force Latin (English) digits even though the app locale is Persian.
        holder.binding.time.text = android.text.format.DateUtils.formatDateTime(
            ctx, m.date, android.text.format.DateUtils.FORMAT_SHOW_TIME
        ).toLatinDigits()
        holder.binding.time.setTextColor(if (sent) 0xFF000000.toInt() else 0xFFCFCFCF.toInt())

        // Status ticks for sent messages: red ✕ = failed, blue ✓✓ = delivered, black ✓ = sent.
        if (sent) {
            holder.binding.ticks.text = when {
                failed -> "✕"
                delivered -> "✓✓"
                else -> "✓"
            }
            holder.binding.ticks.setTextColor(
                when {
                    failed -> 0xFFE53935.toInt()
                    delivered -> 0xFF1A73E8.toInt()
                    else -> 0xFF000000.toInt()
                }
            )
            holder.binding.ticks.visibility = View.VISIBLE
        } else {
            holder.binding.ticks.visibility = View.GONE
        }

        // Tiny SIM tag inside the bubble (blue SIM-card shape, slot number), shown when 2+ SIMs.
        val slot = if (showSim) slotForSub(m.subId) else null
        if (slot != null) {
            holder.binding.simTag.text = slot.toString()
            holder.binding.simTag.visibility = View.VISIBLE
        } else {
            holder.binding.simTag.visibility = View.GONE
        }

        if (selectionMode) {
            // In selection mode: highlight selected rows; a tap anywhere toggles.
            holder.binding.root.setBackgroundColor(
                if (selected.contains(m.id)) 0x33F7A623 else 0x00000000
            )
            holder.binding.text.movementMethod = null // tap should toggle, not open links
            val toggle = View.OnClickListener { toggle(m) }
            holder.binding.root.setOnClickListener(toggle)
            holder.binding.bubble.setOnClickListener(toggle)
            holder.binding.text.setOnClickListener(toggle)
            val longSelect = View.OnLongClickListener { toggle(m); true }
            holder.binding.root.setOnLongClickListener(longSelect)
            holder.binding.bubble.setOnLongClickListener(longSelect)
            holder.binding.text.setOnLongClickListener(longSelect)
        } else {
            holder.binding.root.setBackgroundColor(0x00000000)
            holder.binding.root.setOnClickListener(null)
            holder.binding.bubble.setOnClickListener(null)
            holder.binding.text.setOnClickListener(null)
            // Long-press triggers the menu anywhere across the row: the bubble, the
            // message text, and the empty space facing the bubble.
            val longPress = View.OnLongClickListener { onLongClick(m); true }
            holder.binding.root.setOnLongClickListener(longPress)
            holder.binding.bubble.setOnLongClickListener(longPress)
            holder.binding.text.setOnLongClickListener(longPress)
        }
    }

    override fun getItemCount() = items.size

    companion object {
        private const val INBOX = 1   // Telephony.Sms.MESSAGE_TYPE_INBOX
        private const val FAILED = 5  // Telephony.Sms.MESSAGE_TYPE_FAILED
    }
}
