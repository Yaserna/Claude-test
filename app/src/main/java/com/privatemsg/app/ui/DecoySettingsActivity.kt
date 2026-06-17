package com.privatemsg.app.ui

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.privatemsg.app.R
import com.privatemsg.app.data.ContactsHelper
import com.privatemsg.app.data.SecureStore
import com.privatemsg.app.databinding.ActivityDecoyBinding

/** Edit the global decoy notification: fake name, fake text, and which existing
 *  conversation opens when the decoy notification is tapped. */
class DecoySettingsActivity : BaseActivity() {

    override val leavesToMainOnBackground = true

    private lateinit var binding: ActivityDecoyBinding
    private lateinit var secure: SecureStore
    private var pickedTarget: String = ""

    private val pickLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val address = result.data?.getStringExtra("address")
            if (!address.isNullOrBlank()) {
                pickedTarget = address
                updateTargetLabel()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)

        binding = ActivityDecoyBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        secure = SecureStore(this)
        binding.decoyName.setText(secure.decoyName)
        binding.decoyText.setText(secure.decoyText)
        pickedTarget = secure.decoyTarget
        updateTargetLabel()

        binding.chooseTarget.setOnClickListener {
            val i = Intent(this, ConversationPickerActivity::class.java)
            i.putExtra("title", getString(R.string.choose_conversation))
            pickLauncher.launch(i)
        }

        binding.save.setOnClickListener {
            secure.decoyName = binding.decoyName.text.toString().trim()
            secure.decoyText = binding.decoyText.text.toString().trim()
            secure.decoyTarget = pickedTarget
            Toast.makeText(this, R.string.saved, Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    private fun updateTargetLabel() {
        binding.decoyTargetValue.text =
            if (pickedTarget.isBlank()) getString(R.string.not_set)
            else ContactsHelper(this).displayFor(pickedTarget)
    }
}
