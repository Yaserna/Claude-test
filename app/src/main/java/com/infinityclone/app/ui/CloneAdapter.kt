package com.infinityclone.app.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.PopupMenu
import androidx.recyclerview.widget.RecyclerView
import com.infinityclone.app.R
import com.infinityclone.app.core.CloneInfo
import com.infinityclone.app.core.CloneNames
import com.infinityclone.app.databinding.ItemCloneBinding

/** آداپتر فهرست کلون‌های ساخته‌شده. */
class CloneAdapter(
    private val onClick: (CloneInfo) -> Unit,
    private val onRename: (CloneInfo) -> Unit,
    private val onAddShortcut: (CloneInfo) -> Unit,
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
        val context = holder.itemView.context

        val customName = CloneNames.get(context, item.packageName, item.userId)
        holder.binding.cloneName.text = customName ?: item.label
        holder.binding.clonePackage.text =
            context.getString(R.string.clone_subtitle, item.packageName, item.userId)

        holder.binding.cloneIcon.setImageDrawable(
            runCatching { context.packageManager.getApplicationIcon(item.packageName) }.getOrNull()
        )

        holder.binding.root.setOnClickListener { onClick(item) }
        holder.binding.moreButton.setOnClickListener { anchor ->
            PopupMenu(context, anchor).apply {
                menu.add(0, 1, 0, R.string.action_rename)
                menu.add(0, 2, 1, R.string.action_add_home)
                menu.add(0, 3, 2, R.string.action_remove)
                setOnMenuItemClickListener { menuItem ->
                    when (menuItem.itemId) {
                        1 -> onRename(item)
                        2 -> onAddShortcut(item)
                        3 -> onRemove(item)
                    }
                    true
                }
                show()
            }
        }
    }

    override fun getItemCount(): Int = items.size
}
