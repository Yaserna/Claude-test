package com.infinityclone.app.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.infinityclone.app.core.CloneInfo
import com.infinityclone.app.databinding.ItemCloneBinding

/** آداپتر فهرست کلون‌های ساخته‌شده. */
class CloneAdapter(
    private val onClick: (CloneInfo) -> Unit,
    private val onRemove: (CloneInfo) -> Unit,
) : RecyclerView.Adapter<CloneAdapter.VH>() {

    private val items = mutableListOf<CloneInfo>()

    fun submit(list: List<CloneInfo>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    inner class VH(val binding: ItemCloneBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemCloneBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        holder.binding.cloneName.text = item.label
        holder.binding.clonePackage.text =
            holder.itemView.context.getString(
                com.infinityclone.app.R.string.clone_subtitle, item.packageName, item.userId
            )
        holder.binding.root.setOnClickListener { onClick(item) }
        holder.binding.removeButton.setOnClickListener { onRemove(item) }
    }

    override fun getItemCount(): Int = items.size
}
