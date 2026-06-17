package com.privatemsg.app.ui

import android.os.Bundle
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.privatemsg.app.R
import com.privatemsg.app.data.SecureStore
import com.privatemsg.app.databinding.ActivitySettingsBinding
import kotlin.math.abs

class SettingsActivity : BaseActivity() {

    private lateinit var binding: ActivitySettingsBinding

    // Discrete display-size steps (kept moderate so layouts don't break).
    private val scaleValues = floatArrayOf(0.85f, 1.0f, 1.15f, 1.3f)
    private val scaleLabels by lazy {
        arrayOf(
            getString(R.string.size_small),
            getString(R.string.size_normal),
            getString(R.string.size_large),
            getString(R.string.size_xlarge)
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.toolbar.setNavigationOnClickListener { finish() }

        val secure = SecureStore(this)
        binding.deliverySwitch.isChecked = secure.deliveryReportEnabled
        binding.deliverySwitch.setOnCheckedChangeListener { _, checked ->
            secure.deliveryReportEnabled = checked
        }

        binding.textSizeValue.text = scaleLabels[nearestIndex(secure.fontScale)]
        binding.textSizeRow.setOnClickListener {
            pickScale(R.string.text_size, secure.fontScale) { secure.fontScale = it }
        }

        binding.uiSizeValue.text = scaleLabels[nearestIndex(secure.uiScale)]
        binding.uiSizeRow.setOnClickListener {
            pickScale(R.string.ui_size, secure.uiScale) { secure.uiScale = it }
        }
    }

    private fun nearestIndex(value: Float): Int {
        var best = 0
        var bestDiff = Float.MAX_VALUE
        scaleValues.forEachIndexed { i, s ->
            val d = abs(s - value)
            if (d < bestDiff) { bestDiff = d; best = i }
        }
        return best
    }

    private fun pickScale(titleRes: Int, current: Float, onPick: (Float) -> Unit) {
        MaterialAlertDialogBuilder(this)
            .setTitle(titleRes)
            .setSingleChoiceItems(scaleLabels, nearestIndex(current)) { dialog, which ->
                onPick(scaleValues[which])
                dialog.dismiss()
                // Rebuild so the new size applies immediately across the app.
                recreate()
            }
            .show()
    }
}
