package com.infinityclone.app.core

/**
 * تنها نقطه‌ی دسترسی به موتور در کل اپ.
 *
 * موتور واقعی BlackBox فعال است. برای دیباگِ UI بدون موتور، می‌توان موقتاً
 * مقدار را به NoopEngine() تغییر داد.
 */
object Engine {
    val instance: CloneEngine = BlackBoxEngine()
}
