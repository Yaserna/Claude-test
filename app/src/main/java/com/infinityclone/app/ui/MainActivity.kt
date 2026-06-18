package com.infinityclone.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.infinityclone.app.R
import com.infinityclone.app.core.CloneInfo
import com.infinityclone.app.core.Engine
import com.infinityclone.app.databinding.ActivityMainBinding

/**
 * صفحه‌ی اصلی: فهرست کلون‌های ساخته‌شده + دکمه‌ی افزودن کلون جدید.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: CloneAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = CloneAdapter(
            onClick = { clone -> Engine.instance.launchClone(clone.packageName, clone.userId) },
            onRemove = { clone -> removeClone(clone) },
        )
        binding.cloneList.layoutManager = LinearLayoutManager(this)
        binding.cloneList.adapter = adapter

        binding.addCloneButton.setOnClickListener {
            startActivity(Intent(this, InstalledAppsActivity::class.java))
        }

        if (!Engine.instance.isReady) {
            binding.engineWarning.visibility = View.VISIBLE
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        val clones = Engine.instance.listClones()
        adapter.submit(clones)
        binding.emptyState.visibility = if (clones.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun removeClone(clone: CloneInfo) {
        Engine.instance.removeClone(clone.packageName, clone.userId)
        Toast.makeText(this, getString(R.string.clone_removed, clone.label), Toast.LENGTH_SHORT).show()
        refresh()
    }
}
