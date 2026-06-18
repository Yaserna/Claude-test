# InfinityClone

اپ متن‌باز برای **کلون کردن نامحدود** اپ‌ها روی اندروید، بر پایه‌ی روش
**مجازی‌سازی (App Virtualization)** و بدون نیاز به روت.

> هدف: اجرای چند نسخه‌ی مستقل از یک اپ (مثلاً چند واتساپ/اینستاگرام) در فضاهای
> مجازی جداگانه. هر «فضای مجازی» با یک `userId` مشخص می‌شود و تعداد آن‌ها سقفی ندارد.

---

## معماری

کل اپ فقط با اینترفیس [`CloneEngine`](app/src/main/java/com/infinityclone/app/core/CloneEngine.kt)
کار می‌کند و هیچ‌جای دیگری مستقیماً به موتور وصل نیست. این یعنی موتور قابل تعویض است.

```
UI (MainActivity, InstalledAppsActivity)
        │
        ▼
   CloneEngine (interface)
        │
        ├── BlackBoxEngine  ← پیش‌فرض؛ پیاده‌سازی واقعی روی موتور NewBlackbox
        └── NoopEngine      ← فقط برای دیباگِ UI بدون موتور
```

**موتور:** [NewBlackbox](https://github.com/ALEX5402/NewBlackbox) — فورک نگه‌داری‌شده‌ی
BlackBox. کد موتور به‌صورت ماژول‌های `Bcore`، `black-reflection` و `compiler` داخل
همین مخزن قرار دارد (شامل بخش بومی C/C++ که با NDK ساخته می‌شود). لایسنس Apache 2.0.

ماژول‌های پروژه:

| ماژول | نقش |
|-------|------|
| `app` | اپ میزبان ما (UI + لایه‌ی `CloneEngine`) |
| `Bcore` | هسته‌ی موتور مجازی‌سازی (Java/Kotlin + C/C++) |
| `black-reflection` | ابزار reflection موتور |
| `compiler` | annotation processor موتور |

> همه‌ی کامپوننت‌های پروکسی موتور از طریق manifest ماژول `Bcore` به‌صورت خودکار merge
> می‌شوند؛ نیازی به اعلام دستی در مانیفست `app` نیست.

---

## ساخت پروژه

به‌خاطر بخش بومی موتور، ساخت به **NDK 29.0.13846066** و **JDK 21** نیاز دارد.

### روش ۱: ساخت خودکار با GitHub Actions (پیشنهادی)
با هر push روی هر برنچ، workflow فایل
[`.github/workflows/android.yml`](.github/workflows/android.yml) اجرا می‌شود، NDK را
نصب و APK دیباگ را می‌سازد. خروجی را از تب **Actions → آخرین run → Artifacts → app-debug**
دانلود کن.

### روش ۲: ساخت محلی
```bash
# نیازمند Android SDK + NDK 29.0.13846066 + JDK 21
./gradlew :app:assembleDebug
# خروجی: app/build/outputs/apk/debug/app-debug.apk
```

---

## تعویض/غیرفعال‌کردن موتور (اختیاری)

برای دیباگِ UI بدون موتور، در
[`core/Engine.kt`](app/src/main/java/com/infinityclone/app/core/Engine.kt) مقدار را به
`NoopEngine()` تغییر بده.

---

## محدودیت‌های ذاتی روش مجازی‌سازی

این‌ها باگ این پروژه نیستند؛ محدودیت همه‌ی اپ‌های مجازی‌ساز هستند:

| مورد | وضعیت |
|------|--------|
| **Play Integrity / SafetyNet** | اپ‌های بانکی و حساس داخل فضای مجازی معمولاً اجرا نمی‌شوند |
| **Google Login / FCM Push** | نیاز به Play Services داخل فضای مجازی؛ گاهی ناپایدار |
| **اپ‌های با anti-tamper قوی** | ممکن است نصب شوند ولی اجرا نشوند |

اگر این محدودیت‌ها برایت مهم‌اند، روش جایگزین **بازبسته‌بندی APK** است (هر کلون یک
اپ واقعاً مستقل با package name جدید) که در برابر Play Integrity مقاوم‌تر است.

---

## نکات اندروید ۱۲

- `targetSdk = 30` عمداً پایین نگه داشته شده تا محدودیت‌های سیستم‌عامل (فیلتر
  package-visibility و scoped storage) کمتر مزاحم موتور شوند.
- `QUERY_ALL_PACKAGES` برای دیدن لیست اپ‌های قابل کلون لازم است.
- عبور از Hidden API با کتابخانه‌ی `hiddenapibypass` در `CloneApplication` انجام می‌شود.

## وضعیت

- [x] اسکلت پروژه + UI پایه (لیست اپ‌ها، لیست کلون‌ها)
- [x] لایه‌ی انتزاعی موتور (`CloneEngine`)
- [x] آوردن موتور واقعی BlackBox به‌صورت ماژول + وصل‌کردن API واقعی
- [x] workflow ساخت APK با NDK
- [ ] سبز شدن build در CI و رفع خطاهای احتمالی ساخت
- [ ] تست نصب/اجرای کلون روی دستگاه اندروید ۱۲
- [ ] مدیریت بهتر فضاها در UI (نام‌گذاری دلخواه کلون‌ها)
