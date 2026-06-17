package com.privatemsg.app.ui

import android.text.format.DateUtils
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.privatemsg.app.R
import com.privatemsg.app.data.Conversation
import com.privatemsg.app.data.ContactsHelper
import com.privatemsg.app.databinding.ItemConversationBinding

class ConversationAdapter(
    private val contacts: ContactsHelper,
    private val onClick: (Conversation) -> Unit,
    private val onLongClick: (Conversation) -> Unit = {},
    private val onSelectionChanged: () -> Unit = {}
) : RecyclerView.Adapter<ConversationAdapter.VH>() {

    private val items = mutableListOf<Conversation>()
    private val selected = mutableSetOf<Long>()
    var selectionMode = false
        private set

    fun submit(list: List<Conversation>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    fun startSelection(conv: Conversation) {
        selectionMode = true
        selected.clear()
        selected.add(conv.threadId)
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
        items.forEach { selected.add(it.threadId) }
        notifyDataSetChanged()
        onSelectionChanged()
    }

    fun selectedThreadIds(): Set<Long> = selected.toSet()
    fun selectedCount(): Int = selected.size

    private fun toggle(conv: Conversation) {
        if (!selected.add(conv.threadId)) selected.remove(conv.threadId)
        notifyDataSetChanged()
        onSelectionChanged()
    }

    inner class VH(val binding: ItemConversationBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val b = ItemConversationBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(b)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val c = items[position]
        val display = contacts.displayFor(c.address)
        holder.binding.name.text = display
        holder.binding.snippet.text = c.snippet.toLatinDigits()
        holder.binding.time.text =
            if (c.date > 0) DateUtils.getRelativeTimeSpanString(c.date).toString().toLatinDigits() else ""

        // Unread conversations: dot, bold name, and a brighter snippet.
        holder.binding.unreadDot.visibility = if (c.unread) View.VISIBLE else View.GONE
        holder.binding.name.setTypeface(
            null, if (c.unread) android.graphics.Typeface.BOLD else android.graphics.Typeface.NORMAL
        )
        holder.binding.snippet.setTextColor(
            holder.itemView.context.getColor(
                if (c.unread) R.color.textPrimary else R.color.textSecondary
            )
        )

        val first = display.trim().firstOrNull()
        if (first != null && first.isLetter()) {
            holder.binding.avatarLetter.text = first.uppercaseChar().toString()
            holder.binding.avatarLetter.visibility = View.VISIBLE
            holder.binding.avatarIcon.visibility = View.GONE
        } else {
            holder.binding.avatarLetter.visibility = View.GONE
            holder.binding.avatarIcon.visibility = View.VISIBLE
        }

        if (selectionMode) {
            holder.binding.checkBox.visibility = View.VISIBLE
            holder.binding.checkBox.setImageResource(
                if (selected.contains(c.threadId)) R.drawable.ic_check_on else R.drawable.ic_check_off
            )
        } else {
            holder.binding.checkBox.visibility = View.GONE
        }

        holder.binding.root.setOnClickListener {
            if (selectionMode) toggle(c) else onClick(c)
        }
        holder.binding.root.setOnLongClickListener {
            if (!selectionMode) onLongClick(c)
            true
        }
    }

    override fun getItemCount() = items.size
}
