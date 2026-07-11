package com.infinityclone.app.ui

import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.MotionEvent
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
    private val onHold: (CloneInfo) -> Unit,
) : RecyclerView.Adapter<CloneAdapter.VH>() {

    private val holdHandler = Handler(Looper.getMainLooper())

    private val items = mutableListOf<CloneInfo>()

    fun submit(list: List<CloneInfo>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    /** فهرست کلون‌هایی که هم‌اکنون نمایش داده می‌شوند. */
    fun currentItems(): List<CloneInfo> = items.toList()

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

        // آیکن از PM موتور خوانده شده (در listClones) تا کلون‌های APKِ نصب‌نشده هم آیکن داشته باشند
        holder.binding.cloneIcon.setImageDrawable(
            item.icon
                ?: runCatching { context.packageManager.getApplicationIcon(item.packageName) }.getOrNull()
        )

        // لمس ۲.۵ ثانیه‌ای → گزینه‌ی مخفی‌سازی. اگر hold فعال شد، کلیک عادی لغو می‌شود.
        var held = false
        val holdRunnable = Runnable { held = true; onHold(item) }
        holder.binding.root.setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    held = false
                    holdHandler.postDelayed(holdRunnable, 2500)
                }
                MotionEvent.ACTION_UP -> {
                    holdHandler.removeCallbacks(holdRunnable)
                    if (!held) v.performClick()
                }
                MotionEvent.ACTION_MOVE, MotionEvent.ACTION_CANCEL ->
                    holdHandler.removeCallbacks(holdRunnable)
            }
            true
        }
        holder.binding.root.setOnClickListener { onClick(item) }
        holder.binding.moreButton.setOnClickListener { anchor ->
            PopupMenu(context, anchor).apply {
                menu.add(0, 1, 0, R.string.action_rename)
                menu.add(0, 2, 1, R.string.action_add_home)
                menu.add(0, 4, 2, R.string.action_remove)
                setOnMenuItemClickListener { menuItem ->
                    when (menuItem.itemId) {
                        1 -> onRename(item)
                        2 -> onAddShortcut(item)
                        4 -> onRemove(item)
                    }
                    true
                }
                show()
            }
        }
    }

    override fun getItemCount(): Int = items.size
}
