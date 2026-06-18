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
        ├── NoopEngine      ← پیش‌فرض؛ اپ بدون موتور هم build/اجرا می‌شود
        └── BlackBoxEngine  ← پیاده‌سازی واقعی روی موتور NewBlackbox/BlackBox
```

**موتور انتخابی:** [NewBlackbox](https://github.com/ALEX5402/NewBlackbox) — فورک
نگه‌داری‌شده‌ی BlackBox.
- پشتیبانی اندروید ۵ تا ۱۵ (شامل اندروید ۱۲) · بدون روت · لایسنس Apache 2.0
- چرا این روش؟ نوشتن موتور مجازی‌سازی از صفر عملاً چندسال کار است؛ سوار شدن روی یک
  موتور متن‌باز فعال، کم‌مشکل‌ترین مسیر روی اندروید مدرن است.

---

## ساخت پروژه (همین الان، بدون موتور)

اپ با `NoopEngine` کامپایل و اجرا می‌شود تا بتوانی UI را ببینی:

```bash
./gradlew assembleDebug
# خروجی: app/build/outputs/apk/debug/app-debug.apk
```

در این حالت لیست اپ‌های نصب‌شده را می‌بینی، ولی ساخت کلون کاری نمی‌کند
(یک هشدار زرد بالای صفحه نشان داده می‌شود).

---

## افزودن موتور (فعال‌سازی کلون واقعی)

۱. **گرفتن AAR:** از مخزن [NewBlackbox](https://github.com/ALEX5402/NewBlackbox)
   فایل AAR موتور را build/دانلود کن و در `app/libs/blackbox.aar` بگذار.

۲. **فعال‌سازی وابستگی** در `app/build.gradle.kts`:
   ```kotlin
   implementation(files("libs/blackbox.aar"))
   ```

۳. **افزودن پیاده‌سازی موتور:** فایل
   [`engine-impl/BlackBoxEngine.kt`](engine-impl/BlackBoxEngine.kt) را به مسیر
   `app/src/main/java/com/infinityclone/app/core/` منتقل کن.

۴. **سوییچ موتور** در
   [`core/Engine.kt`](app/src/main/java/com/infinityclone/app/core/Engine.kt):
   ```kotlin
   val instance: CloneEngine = BlackBoxEngine()
   ```

۵. **تطبیق API:** نام پکیج importها و امضای متدهای موتور (جاهای علامت‌خورده با ⚠️)
   را با نسخه‌ی AAR خودت چک کن. این بخش‌ها بین فورک‌های مختلف BlackBox کمی فرق دارند.

۶. **کامپوننت‌های پروکسی:** اگر نسخه‌ی موتور نیاز داشت Stubها را صریحاً در مانیفست
   اعلام کنی، طبق مانیفست ماژول `app` نمونه‌ی موتور به
   [`AndroidManifest.xml`](app/src/main/AndroidManifest.xml) اضافه کن.

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
- [x] لایه‌ی انتزاعی موتور (`CloneEngine`) + پیاده‌سازی Noop
- [x] کد پیاده‌سازی موتور BlackBox (آماده برای وصل‌کردن)
- [ ] وصل‌کردن AAR واقعی و تست روی دستگاه اندروید ۱۲
- [ ] مدیریت چند فضای مجازی در UI (نام‌گذاری دلخواه کلون‌ها)
