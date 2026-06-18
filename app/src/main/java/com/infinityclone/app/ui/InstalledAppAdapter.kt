package com.infinityclone.app.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.infinityclone.app.databinding.ItemInstalledAppBinding

/** آداپتر فهرست اپ‌های نصب‌شده‌ی قابل کلون. */
class InstalledAppAdapter(
    private val onClone: (InstalledApp) -> Unit,
) : RecyclerView.Adapter<InstalledAppAdapter.VH>() {

    private val items = mutableListOf<InstalledApp>()

    fun submit(list: List<InstalledApp>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    inner class VH(val binding: ItemInstalledAppBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemInstalledAppBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        holder.binding.appIcon.setImageDrawable(item.icon)
        holder.binding.appName.text = item.label
        holder.binding.appPackage.text = item.packageName
        holder.binding.root.setOnClickListener { onClone(item) }
    }

    override fun getItemCount(): Int = items.size
}
