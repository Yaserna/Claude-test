package com.privatemsg.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.WindowManager
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import com.privatemsg.app.R
import com.privatemsg.app.data.SecureStore
import com.privatemsg.app.databinding.ActivityPinBinding

/** Lock-screen style PIN keypad. Sets a PIN on first use, otherwise asks for it. */
class PinActivity : BaseActivity() {

    private lateinit var binding: ActivityPinBinding
    private lateinit var secure: SecureStore
    private var settingUp = false
    private var promptedFingerprint = false
    private val entered = StringBuilder()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)

        binding = ActivityPinBinding.inflate(layoutInflater)
        setContentView(binding.root)

        secure = SecureStore(this)
        settingUp = !secure.hasPin()
        binding.title.setText(if (settingUp) R.string.pin_create else R.string.pin_enter)

        val digits = mapOf(
            binding.key0 to '0', binding.key1 to '1', binding.key2 to '2',
            binding.key3 to '3', binding.key4 to '4', binding.key5 to '5',
            binding.key6 to '6', binding.key7 to '7', binding.key8 to '8',
            binding.key9 to '9'
        )
        digits.forEach { (view, d) -> view.setOnClickListener { append(d) } }
        binding.keyBack.setOnClickListener {
            if (entered.isNotEmpty()) entered.deleteCharAt(entered.length - 1)
            updateDots()
        }
        binding.keyOk.setOnClickListener { submit() }

        // Offer fingerprint unlock (when enabled and we're not creating a new PIN).
        if (!settingUp && secure.fingerprintEnabled && !promptedFingerprint) {
            promptedFingerprint = true
            tryFingerprint()
        }
    }

    private fun tryFingerprint() {
        val canUse = BiometricManager.from(this).canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_WEAK
        ) == BiometricManager.BIOMETRIC_SUCCESS
        if (!canUse) return

        val prompt = BiometricPrompt(
            this, ContextCompat.getMainExecutor(this),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    openHidden()
                }
            }
        )
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(getString(R.string.fingerprint_title))
            .setNegativeButtonText(getString(R.string.fingerprint_use_pin))
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_WEAK)
            .build()
        prompt.authenticate(info)
    }

    private fun append(d: Char) {
        if (entered.length < 12) entered.append(d)
        binding.error.text = ""
        updateDots()
        // When unlocking, enter as soon as the correct PIN is typed (no confirm tap).
        if (!settingUp && secure.checkPin(entered.toString())) openHidden()
    }

    private fun updateDots() {
        binding.dots.text = "●".repeat(entered.length)
    }

    private fun submit() {
        val pin = entered.toString()
        if (settingUp) {
            if (pin.length < 4) {
                binding.error.setText(R.string.pin_too_short)
                return
            }
            secure.setPin(pin)
            openHidden()
        } else {
            if (secure.checkPin(pin)) {
                openHidden()
            } else {
                binding.error.setText(R.string.pin_wrong)
                entered.clear()
                updateDots()
            }
        }
    }

    private fun openHidden() {
        startActivity(Intent(this, HiddenActivity::class.java))
        finish()
    }
}
