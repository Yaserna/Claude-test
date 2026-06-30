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

        // Visible version so an update can be confirmed at a glance.
        binding.versionText.text =
            getString(R.string.app_version, com.privatemsg.app.BuildConfig.VERSION_NAME)

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

        // Bubble colors.
        setSwatch(binding.sentColorSwatch, secure.sentBubbleColor)
        binding.sentColorRow.setOnClickListener {
            pickColor(secure.sentBubbleColor) { c ->
                secure.sentBubbleColor = c
                setSwatch(binding.sentColorSwatch, c)
            }
        }
        setSwatch(binding.receivedColorSwatch, secure.receivedBubbleColor)
        binding.receivedColorRow.setOnClickListener {
            pickColor(secure.receivedBubbleColor) { c ->
                secure.receivedBubbleColor = c
                setSwatch(binding.receivedColorSwatch, c)
            }
        }

        // Contact info: tap to dial / email.
        binding.phoneRow.setOnClickListener {
            startSafely(
                android.content.Intent(
                    android.content.Intent.ACTION_DIAL,
                    android.net.Uri.parse("tel:" + getString(R.string.contact_phone))
                )
            )
        }
        binding.emailRow.setOnClickListener {
            startSafely(
                android.content.Intent(
                    android.content.Intent.ACTION_SENDTO,
                    android.net.Uri.parse("mailto:" + getString(R.string.contact_email))
                )
            )
        }
    }

    private fun startSafely(intent: android.content.Intent) {
        try {
            startActivity(intent)
        } catch (e: Exception) {
            // No app to handle it; ignore.
        }
    }

    /** A palette of preset bubble colors offered in the picker. */
    private val palette = intArrayOf(
        0xFF1FA055.toInt(), // green (default sent)
        0xFF1A73E8.toInt(), // blue
        0xFFF7A623.toInt(), // orange
        0xFF8E44AD.toInt(), // purple
        0xFFE53935.toInt(), // red
        0xFF009688.toInt(), // teal
        0xFFE91E63.toInt(), // pink
        0xFF795548.toInt(), // brown
        0xFF455A64.toInt(), // blue-grey
        0xFF2C2C2E.toInt(), // grey (default received)
        0xFF3A3A3C.toInt(), // light grey
        0xFF000000.toInt()  // black
    )

    private fun setSwatch(view: android.view.View, color: Int) {
        val d = android.graphics.drawable.GradientDrawable()
        d.shape = android.graphics.drawable.GradientDrawable.OVAL
        d.setColor(color)
        d.setStroke((1 * resources.displayMetrics.density).toInt(), 0xFF666666.toInt())
        view.background = d
    }

    /** Shows a grid of color circles; calls [onPick] with the chosen color. */
    private fun pickColor(current: Int, onPick: (Int) -> Unit) {
        val density = resources.displayMetrics.density
        val cell = (56 * density).toInt()
        val dot = (40 * density).toInt()
        val grid = android.widget.GridLayout(this).apply {
            columnCount = 4
            val p = (12 * density).toInt()
            setPadding(p, p, p, p)
        }
        val dialog = MaterialAlertDialogBuilder(this)
            .setTitle(R.string.pick_color)
            .setView(grid)
            .create()
        for (color in palette) {
            val circle = android.graphics.drawable.GradientDrawable().apply {
                shape = android.graphics.drawable.GradientDrawable.OVAL
                setColor(color)
                if (color == current) setStroke((3 * density).toInt(), 0xFFFFFFFF.toInt())
                else setStroke((1 * density).toInt(), 0xFF666666.toInt())
            }
            val v = android.view.View(this).apply {
                background = circle
                layoutParams = android.widget.GridLayout.LayoutParams().apply {
                    width = dot
                    height = dot
                    setMargins((cell - dot) / 2, (cell - dot) / 2, (cell - dot) / 2, (cell - dot) / 2)
                }
                setOnClickListener {
                    onPick(color)
                    dialog.dismiss()
                }
            }
            grid.addView(v)
        }
        dialog.show()
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
