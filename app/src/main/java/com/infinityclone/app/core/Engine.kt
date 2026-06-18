package com.infinityclone.app.core

/**
 * تنها نقطه‌ی دسترسی به موتور در کل اپ.
 *
 * برای فعال‌سازی موتور واقعی بعد از افزودن AAR:
 *   1. فایل engine-impl/BlackBoxEngine.kt را طبق README وارد سورس کن.
 *   2. مقدار [instance] را به `BlackBoxEngine()` تغییر بده.
 */
object Engine {

    // TODO(موتور): بعد از افزودن AAR به BlackBoxEngine() تغییر بده.
    val instance: CloneEngine = NoopEngine()
}
