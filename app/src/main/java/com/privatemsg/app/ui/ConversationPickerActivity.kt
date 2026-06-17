package com.privatemsg.app.ui

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.privatemsg.app.data.ContactsHelper
import com.privatemsg.app.data.SmsRepository
import com.privatemsg.app.databinding.ActivityPickerBinding

/** Lets the user pick one of their existing conversations and returns its address. */
class ConversationPickerActivity : BaseActivity() {

    override val leavesToMainOnBackground = true

    private lateinit var binding: ActivityPickerBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPickerBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }
        intent.getStringExtra("title")?.let { binding.toolbar.title = it }

        val repo = SmsRepository(this)
        val adapter = ConversationAdapter(
            contacts = ContactsHelper(this),
            onClick = { conv ->
                setResult(Activity.RESULT_OK, Intent().putExtra("address", conv.address))
                finish()
            }
        )
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter
        adapter.submit(repo.getConversations())
    }
}
