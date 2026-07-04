# پروژه: فورک سفارشی تلگرام اندروید (نامحدود اکانت + ترجمه + شماره‌گذاری)

> این فایل کلِ زمینه، پیشرفت‌ها، قوانین و راه‌حل‌های پروژه را با ریزترین جزئیات نگه می‌دارد.
> برای بارگذاری در بخش **Projects** کلاد ساخته شده تا هر گفتگوی جدید کاملاً در جریان باشد.
> آخرین به‌روزرسانی: بعد از رفعِ باگِ تگِ معکوس و باز کردنِ ترجمه‌ی کلِ چت/گروه + inline + به‌خاطرسپاری.

---

## ۱) هدف پروژه
ساخت یک اپ اندرویدیِ **دقیقاً مثل تلگرام رسمی** ولی با چند قابلیتِ اختصاصی:
1. **لاگین نامحدود اکانت** (حداقل ۱۰۰) بدون کرش — مثل نکوگرامِ قدیمی.
2. **ترجمه‌ی پیام‌ها** (تک‌پیام + کلِ گروه/کانال) با موتورِ گوگل، بدونِ Premium.
3. یک **دکمه‌ی ترجمه‌ی کلِ گروه** در بالای صفحه (هنوز مانده).
4. مکالمه‌های **ترکیبیِ فارسی/انگلیسی (bidi/RTL-LTR)** موقع ترجمه نباید به‌هم بریزد (هنوز مانده).
5. **شماره‌گذاریِ اکانت‌ها** به ترتیبِ لاگین تا بشود اکانتِ بیستم را شناخت.
6. احتمال افزودنِ شخصی‌سازیِ بیشتر در آینده (ری‌برندینگ).

## ۲) پروفایل کاربر و قوانینِ کار (بسیار مهم)
- کاربر **دانشِ برنامه‌نویسی ندارد** → همه‌ی تغییرات باید به‌صورتِ **اسکریپتِ آماده** داده شود
  (فایلِ `.py` + یک `.bat` که با دابل‌کلیک اجرا شود).
- **قانونِ اجباری (جدید):** داخلِ اسکریپت‌ها **هیچ حرف/کلمه‌ی فارسی یا کاراکترِ غیرASCII** نباشد.
  علت: `cmd.exe` ویندوز متنِ فارسیِ داخلِ `.bat` را به‌عنوان دستور تفسیر می‌کند و خطای
  «'...' is not recognized as an internal or external command» می‌دهد. همه‌ی پیام‌ها و
  کامنت‌ها باید انگلیسی باشند. فایل‌های `.bat` باید **CRLF** و شاملِ `chcp 65001 >nul` باشند.
- توضیحاتِ کلاد به کاربر: **خیلی کوتاه** و به **فارسی** (اما نه داخلِ اسکریپت).
- کاربر در **ایران** است → لینک‌های `raw.githubusercontent.com` فیلترند؛ محتوای اسکریپت
  باید کاملِ متن باشد یا فایل مستقیم برایش فرستاده شود، نه لینکِ دانلود.
- برای اتصال نیاز به **VPN/پروکسی MTProto** دارد (اتصال مستقیم فیلتر است).
- بیلد روی سیستمِ خودِ کاربر (ویندوز) با Android Studio؛ لاگ‌ها از Logcat می‌آیند.
- **نکردنی‌ها:** گشتن دنبالِ توکن/کلید در لاگ‌ها یا env؛ دستکاریِ دستیِ credentialهای گیت.

## ۳) ساختار پروژه (Lightweight Fork)
- ریپو فقط **اسکریپت‌ها** را نگه می‌دارد؛ خودِ سورسِ تلگرام داخلِ ریپو نیست.
- اسکریپت‌ها ریپوی رسمی **DrKLO/Telegram** را روی یک کامیتِ ثابت clone می‌کنند داخلِ
  پوشه‌ی `./Telegram` و بعد تغییرات را اعمال می‌کنند.
- **کامیتِ ثابت (pinned):** `9b50143d8896d255d03155598937e4f3e28afd86` (نسخه‌ی v12.8.1، build 6916).
- **پکیج در زمانِ اجرا:** `org.telegram.messenger.beta`
- **تسکِ بیلد:** `:TMessagesProj_App:assembleAfatDebug` (خروجی افت/دیباگ).
- مسیرِ محلیِ کاربر: `C:\Users\Arbab\Desktop\Claude-test\Coding\Telegram-App\Telegram`
- دستگاهِ تست: Redmi (joyeuse) اندروید ۱۲ (MIUI V14).

## ۴) گیت / برنچ / Workflow
- ریپو: `yaserna/yaser-d.z`
- **برنچِ کاریِ فعلی:** `claude/telegram-app-continuation-lvgts5`
  (ادامه‌ی برنچِ قدیمی‌ترِ `Telegram-App`؛ همه‌ی کارها اینجا commit/push می‌شود).
- پوش از طریقِ گیتِ محلی. کامیت‌ها ممکن است «Unverified» باشند (بدونِ GPG) — بی‌ضرر.
- **مهم:** کاربر معمولاً `apply_mods.py` (بیلدِ کامل) را اجرا نمی‌کند؛ روی سورسِ محلیِ
  از قبل موجودش، **اسکریپت‌های مستقلِ تک‌منظوره** را اجرا می‌کند که برایش می‌فرستیم.

---

## ۵) نکاتِ کلیدیِ فنی (که خیلی وقت‌گیر بودند تا کشف شوند)

### الف) کپی‌های بیلد (تله‌ی بزرگ)
Gradle موقعِ بیلد از سورس‌ها **کپی** می‌سازد در مسیرهایی مثل `.../build/intermediates/...`.
اسکریپت‌های اولیه به‌جای سورسِ اصلی، این کپی‌ها را پچ می‌کردند → تغییرات هیچ‌وقت وارد اپ نمی‌شد.
**قانون:** هر اسکریپت باید مسیرهای شاملِ `/build/`, `/.cxx/`, `/intermediates/`, `/.gradle/`
را نادیده بگیرد و فقط سورسِ اصلی (`src/main/java/...` و `jni/...`) را پچ کند. (تابعِ
`find_project_root` در اسکریپت‌ها دقیقاً همین پوشه‌ها را از `os.walk` حذف می‌کند.)

### ب) رفرش‌نشدنِ کدِ نیتیو (C++)
گاهی «Rebuild» کدِ C++ را دوباره کامپایل نمی‌کند (از کش می‌خواند). نشانه: Rebuild چند ثانیه‌ای تمام می‌شود.
**راه‌حل:** پوشه‌های `TMessagesProj/.cxx` و `TMessagesProj/build` پاک شوند تا از صفر کامپایل شود
(باید چند دقیقه طول بکشد). بعد از تغییرِ نیتیو **حتماً** این کار + Uninstall کامل لازم است.
تغییراتِ **فقط جاوا** این نیاز را ندارند (بیلدِ عادی کافی است).

### ج) گرفتنِ backtrace نیتیو (طلا)
کرش‌های نیتیو (SIGSEGV/SIGABRT) خطِ `Fatal signal` را نشان می‌دهند ولی backtrace را پروسه‌ی
جدا (`crash_dump64`، تگِ `DEBUG`) لاگ می‌کند که اندروید استودیو پیش‌فرض مخفیش می‌کند.
**روش:** کادرِ فیلترِ Logcat را **خالی** کن، تایپ کن `DEBUG` (یا `libtmessages`)، بلوکِ
`backtrace:` با خط‌های `#00 pc ... libtmessages.49.so (نام‌تابع+عدد)` را بردار.

### د) فیلترینگ ایران (کاذب/غیرکد)
- `Firebase 403 / API_KEY_ANDROID_APP_BLOCKED / Failed to get regid` = پوشِ گوگل بلاک، بی‌ضرر.
- `libEGL no current context`, `libmigui.so`, `MiuiNotification`, `Slow Binder` = هشدارهای شیائومی، بی‌ضرر.
- اتصالِ کند / `TLS hash mismatch` / `unable to decrypt` = فیلترینگ؛ نیازمندِ VPN/پروکسی.

### ه) نکته‌ی کلیدیِ اسلاتِ اکانت (تازه کشف شد)
اسلات‌های اکانت **ترتیبی نیستند**. تلگرام هنگامِ «افزودن اکانت» اسلاتِ خالی را از **بالای**
آرایه پیدا می‌کند (`for (int a = MAX_ACCOUNT_COUNT - 1; a >= 0; a--)`)، پس با MAX=100 اکانت‌ها
در اسلاتِ `0, 99, 98, 97, ...` می‌نشینند. برای همین شماره‌گذاری بر اساسِ «شماره‌ی اسلات + ۱»
خروجیِ `1, 100, 99, 98` می‌داد. شماره‌گذاریِ درست باید بر اساسِ **زمانِ لاگین** باشد.

---

## ۶) تاریخچه‌ی کاملِ باگ‌ها و فیکس‌ها (به‌ترتیب)

1. **کرشِ استارتاپ اولیه** (`DownloadController.<init>` → `IntentReceiverLeaked` → SIGABRT):
   علت: `ApplicationLoader.postInitApplication` همه‌ی اسلات‌ها را eager می‌ساخت.
   فیکس: گاردِ lazy-init → `if (a != 0 && !UserConfig.getInstance(a).isClientActivated()) continue;`

2. **محدودیتِ اکانت (جاوا):** `UserConfig.MAX_ACCOUNT_DEFAULT_COUNT` (۳→۱۰۰) و `MAX_ACCOUNT_COUNT` (۴→۱۰۰).

3. **CheckJNI / debuggable:** بیلدِ debug باعثِ CheckJNI می‌شود که خطاهای نهفته‌ی JNI را به
   SIGABRT تبدیل می‌کند. فیکس: در `TMessagesProj/build.gradle` بلوکِ `debug` →
   `jniDebuggable false` + `debuggable false`.

4. **سقفِ ۵ اکانتِ نیتیو (کشفِ کلیدی):**
   - `jni/tgnet/Defines.h`: `#define MAX_ACCOUNT_COUNT 5` → ۱۰۰.
   - `jni/tgnet/ConnectionsManager.cpp`: تابعِ `getInstance` یک `switch` بود که فقط ۰–۴ را
     می‌شناخت (هر اندیسِ ≥۵ می‌رفت روی instance4). بازنویسی به یک map پویا و thread-safe:
   ```cpp
   ConnectionsManager& ConnectionsManager::getInstance(int32_t instanceNum) {
       static std::map<int32_t, ConnectionsManager *> instances;
       static pthread_mutex_t instancesMutex = PTHREAD_MUTEX_INITIALIZER;
       if (instanceNum < 0) { instanceNum = 0; }
       pthread_mutex_lock(&instancesMutex);
       ConnectionsManager *result = instances[instanceNum];
       if (result == nullptr) { result = new ConnectionsManager(instanceNum); instances[instanceNum] = result; }
       pthread_mutex_unlock(&instancesMutex);
       return *result;
   }
   ```

5. **باگِ cross-thread JNIEnv** (`JNI DETECTED ERROR: using JNIEnv* from thread X`):
   علت: در `jni/TgNetWrapper.cpp` کالبک‌ها از آرایه‌ی کش‌شده‌ی `jniEnv[instanceNum]` استفاده
   می‌کردند. فیکس: helper اضافه شد و همه‌ی `jniEnv[instanceNum]->` → `tgCurrentEnv()->` (۳۵ مورد):
   ```cpp
   static inline JNIEnv *tgCurrentEnv() {
       JNIEnv *env = nullptr;
       if (java->GetEnv((void **) &env, JNI_VERSION_1_6) != JNI_OK) { java->AttachCurrentThread(&env, nullptr); }
       return env;
   }
   ```
   (نکته: در `TgNetWrapper.cpp` نامِ متغیرِ JavaVM سراسری `java` است، نه `javaVm`.)

6. **کرشِ نیتیو `processRequestQueue` null-deref** (SIGSEGV، fault addr نزدیک صفر مثل `0x32`؛
   backtrace: processRequestQueue → select → ThreadProc):
   علت: دو `getConnectionByType` در `ConnectionsManager.cpp` (خطوطِ ~۲۵۶۹ و ~۲۸۲۰) وقتی auth key
   موقتاً هنگامِ handshakeِ اکانتِ جدید null است، `nullptr` برمی‌گردانند و کد بدونِ چک به
   `connection->getConnectionToken()` دسترسی می‌داد. فیکس: بعد از هر دو، چکِ null:
   ```cpp
   if (connection == nullptr) { iter++; continue; }
   ```
   **این همان کرشی بود که کاربر در `tele_log.txt` فرستاد** — و چون بیلد از کشِ قدیمیِ C++ ساخته
   شده بود، فیکس در آن بیلد نبود؛ با پاک‌کردنِ `.cxx`/`build` حل شد.

7. **باگِ جای‌گذاریِ گاردِ lazy-init (کشفِ مهم):** گاردِ حلقه‌ی اصلی باید **بعد** از
   `UserConfig.getInstance(a).loadConfig();` باشد، نه قبلش. چون `isClientActivated()` فقط بعد از
   `loadConfig()` معتبر است؛ اگر گارد قبل باشد، اکانت‌های ۲+ بعد از هر ری‌استارتِ اپ **برای
   همیشه غیب می‌شوند**. همچنین گاردِ حلقه‌ی شبکه، تورفتگیِ اشتباهی داشت که باعث می‌شد اصلاً اعمال نشود.

8. **گاردِ طوفانِ storage:** یک نقطه‌ی مطمئن `LocationController.getLocationsCount` گارد شد
   (چکِ `isClientActivated` قبل از `getInstance`). اگر کرشِ مشابه با backtrace در فایلِ دیگری
   دیده شد، همین الگو آنجا هم اضافه شود. (گاردِ گسترده‌ی `guardall/fixguard/uirevert` از جلسه‌ی
   اول عمداً بازتولید نشد چون بدونِ backtraceِ واقعی ریسک دارد.)

9. **تگِ شماره‌ی معکوس (۱۰۰،۹۹،۹۸):** علت در بخشِ ۵-ه توضیح داده شد (اسلات‌ها 0,99,98,...).
   فیکس: helper بر اساسِ `loginTime` (بخشِ ۷).

10. **ترجمه‌ی کلِ چت در دسترس نبود / inline کار نمی‌کرد / وضعیت به‌خاطر نمی‌ماند:**
    هر سه یک ریشه داشتند: قفلِ **Premium** در `TranslateController.isFeatureAvailable()`.
    چون کاربر `apply_mods.py` را اجرا نکرده بود، این قفل هنوز روی سیستمش بود. حذفِ قفل هر سه را
    حل کرد (مکانیزمِ به‌خاطرسپاری از قبل در کد بود). جزئیات در بخشِ ۸.

---

## ۷) شماره‌گذاریِ اکانت (بر اساسِ ترتیبِ لاگین)

helperِ اضافه‌شده به `UserConfig.java` (درست قبل از `getActivatedAccountsCount`):
```java
public static int getAccountTagNumber(int account) {
    if (account < 0 || account >= MAX_ACCOUNT_COUNT) { return account + 1; }
    long myLogin = getInstance(account).loginTime;
    int rank = 1;
    for (int a = 0; a < MAX_ACCOUNT_COUNT; a++) {
        if (a == account) { continue; }
        if (!getInstance(a).isClientActivated()) { continue; }
        long other = getInstance(a).loginTime;
        if (other < myLogin || (other == myLogin && a < account)) { rank++; }
    }
    return rank;
}
```
- `loginTime` یک `public int` در UserConfig است که هنگامِ لاگین برابرِ timestamp می‌شود.
  همان چیزی که خودِ سوییچرِ اکانت هم برای مرتب‌سازی استفاده می‌کند → ترتیبِ لاگین.
- شماره پایدار است (بعد از ری‌استارت عوض نمی‌شود، مگر اکانتِ قبلی logout شود).

**محل‌های نمایشِ تگ (باید در همه باشد):**
- `ui/MainTabsActivity.java` → متد `accountView`، خطِ `textView.setText(...UserObject.getUserName(user))`.
- `ui/DialogsActivity.java` → متد `accountView` (منوی کشویی/Drawer)، همان الگو.
- `ui/Cells/AccountSelectCell.java` → متد `setAccount`، خطِ `...formatName(user.first_name, user.last_name)`.
  (این سلول در «Send as»/انتخابِ اکانت استفاده می‌شود.)
همه به شکلِ `"#" + UserConfig.getAccountTagNumber(account) + " " + <نام>` تغییر کردند.
(هر سه فایل `import org.telegram.messenger.UserConfig;` را از قبل دارند.)

---

## ۸) معماریِ ترجمه (دقیق)

### فلگ‌های موتور (در `MessagesController.java`)
- دو رشته: `translationsManualEnabled` (تک‌پیام) و `translationsAutoEnabled` (کلِ چت).
  مقادیرِ ممکن: `"enabled"`, `"alternative"`, `"system"`, `"disabled"`.
- ما هر دو را روی `"alternative"` قفل کردیم (سبکِ نکوگرام = موتورِ گوگل):
  - در `loadConfig` (خطوطِ ~۱۶۹۹): `... = mainPreferences.getString(..., "enabled");` → `... = "alternative";`
  - در appConfigِ سرور (خطوطِ ~۴۸۶۷): شرطِ `if (!TextUtils.equals(...))` → `if (false)` تا سرور
    نتواند مقدار را برگرداند. (کامنتِ دو پچ متفاوت است: `(manual)` و `(auto)` تا idempotency قاطی نشود.)

### مسیرِ موتورِ گوگل (کدِ رسمیِ موجود)
- `ui/Components/TranslateAlert2.java` → `alternativeTranslate` / `alternativeTranslateInternal`:
  endpointِ `https://translate.googleapis.com/translate_a/single?client=gtx&...` (همان نکوگرام)،
  با تکه‌تکه‌کردنِ متنِ بلند (`cut`) و چرخشِ User-Agent.
- `TranslateController.java` وقتی `method == "alternative"` باشد از همین مسیر استفاده می‌کند.

### قفلِ Premium (باگِ اصلی)
در `TranslateController.java`:
```java
public boolean isFeatureAvailable() {
    return isChatTranslateEnabled() && UserConfig.getInstance(currentAccount).isPremium(); // <-- premium gate
}
public boolean isFeatureAvailable(long dialogId) {
    if (!isChatTranslateEnabled()) return false;
    final TLRPC.Chat chat = getMessagesController().getChat(-dialogId);
    return (UserConfig.getInstance(currentAccount).isPremium() || chat != null && chat.autotranslation); // <-- premium gate
}
```
فیکس:
- اولی → `return isChatTranslateEnabled();`
- دومی (کلِ بلوکِ chat/return) → `return true; // [mod] chat/group translate enabled for everyone`
- (یک `isPremium()` دیگر در `isLanguageRestricted` می‌ماند و **بی‌ضرر** است — فقط تعیین می‌کند
  زبانِ خودِ کاربر ترجمه نشود.)

### به‌خاطرسپاریِ وضعیتِ per-dialog (از قبل در کد بود، فقط پشتِ قفل)
- `translatingDialogs` (LongSparseArray) + `toggleTranslatingDialog(dialogId, value)` که
  `saveTranslatingDialogsCache()` را صدا می‌زند.
- ذخیره در setting: `translating_dialog_languages2` (و `hidden_translation_at`).
- بارگذاری در استارت: `loadTranslatingDialogsCached()`.
- `isChatTranslateEnabled()`: بستگی به `isTranslationsAutoEnabled()` (= true چون "alternative")
  و settingِ `translate_chat_button` (پیش‌فرض true).

### تفاوتِ تک‌پیام و کلِ چت (برای رفعِ سوءتفاهمِ کاربر)
- **تک‌پیام** (لمسِ طولانی روی پیام → Translate) → همیشه پنجره‌ی `TranslateAlert2` (طراحیِ تلگرام).
- **ترجمه‌ی inline داخلِ حباب** = همان قابلیتِ «ترجمه‌ی کلِ چت»: نوارِ Translate بالای چت →
  لمس → پیام‌ها داخلِ حباب ترجمه می‌شوند. این پشتِ قفلِ Premium بود.

### دکمه‌ی ترجمه‌ی تک‌پیام پیش‌فرض روشن
`TranslateController.java`: مقدارِ پیش‌فرضِ `translate_button` از `false` به `true`.

---

## ۹) مجموعه‌ی اسکریپت‌ها

### الف) در ریپو (برای بیلدِ کامل از صفر)
- `setup.bat` / `setup.sh` — clone سورس روی کامیتِ ثابت + اجرای `apply_mods.py`.
- `apply_mods.py` — **همه‌ی** تغییرات (جاوا + نیتیو + gradle). ساختار (idempotent، هر پچ برچسب دارد):
  1. سقفِ اکانتِ جاوا (۲ ثابت)
  1.5 گاردهای lazy-init (۳ حلقه، گاردِ اصلی بعد از loadConfig)
  1.6 خاموش‌کردنِ CheckJNI
  1.7 سقفِ نیتیو + map پویا
  1.8 helperِ tgCurrentEnv + جایگزینیِ ۳۵ موردِ jniEnv
  1.9 دو null-check کانکشن
  1.10 گاردِ getLocationsCount
  2. حذفِ قفلِ Premiumِ ترجمه (۲ پچ)
  3. دکمه‌ی ترجمه‌ی تک‌پیام پیش‌فرض روشن
  4. موتورِ گوگل (۴ پچ در MessagesController)
  5. شماره‌گذاریِ اکانت (helper در UserConfig + ۳ محلِ نمایش)
  مجموعاً ۲۴ پچ؛ روی سورسِ کامیتِ ثابت تست شده (اعمالِ تمیز + idempotent + توازنِ `{}`/`()`).
- `fix_crash.py` / `fix_crash.bat` — ابزارِ کمکیِ فقط گاردهای lazy-init.
- `build_config.json` — کلیدها: `account_limit=100`, `enable_chat_translate_for_all`,
  `translate_button_default_on`, `nekogram_style_translation`, `account_number_tags`.
- `README.md`, `BUILD-GUIDE-FA.md`, `conversation.md`.

### ب) اسکریپت‌های مستقلِ فرستاده‌شده به کاربر (روی سورسِ محلیِ او)
> همه انگلیسی‌اند، `find_project_root` خودشان پوشه را پیدا می‌کند، idempotent، بکاپ می‌سازند.
- `fix_native_crash.py/.bat` — همه‌ی فیکس‌های نامحدودسازی + کرش (معادلِ بخش‌های ۱ تا ۱.۱۰ apply_mods). بکاپ: `.bak`.
- `fix_round2.py/.bat` — پاک‌سازیِ بعد از ترکیبِ اسکریپت‌های قدیمی: حذفِ تعریفِ تکراریِ
  `tgCurrentEnv`، جابه‌جاییِ گاردِ اصلی به بعد از loadConfig، حذفِ گاردهای تکراری، و یک
  **گزارشِ تشخیصی**. بکاپ: `.bak2`.
- `add_features.py/.bat` — موتورِ گوگل + تگِ شماره (نسخه‌ی اولِ تگ که باگِ اسلات داشت). بکاپ: `.bak3`.
- `fix_translate_and_tags.py/.bat` — حذفِ قفلِ Premium (۲ پچ) + helperِ loginTime در
  UserConfig + اصلاحِ تگ‌های باگ‌دار به helper + افزودنِ تگ به DialogsActivity. بکاپ: `.bak4`.
- `bubble_translate_and_tags.py/.bat` — **آخرین** (این یکی در ریپو هم هست): ۱۹ پچ در ۳ گروه:
  (A) تگِ شماره در پروفایلِ خود (ProfileActivity)، هدرِ تنظیمات (SettingsActivity.setInfo) و
  لیستِ اکانت‌های داخلِ تنظیمات (SettingsActivity.AccountCell.set).
  (B) نوارِ Translate بالای **همه‌ی** چت‌ها: حذفِ شرطِ `translatableDialogs.contains` از
  `isDialogTranslatable` (تشخیصِ زبانِ ML گوگل روی گوشیِ بدونِ سرویسِ گوگل هیچ‌وقت کامل
  نمی‌شود — ریشه‌ی «نوار نمی‌آید» همین بود، نه فقط قفلِ Premium) + حذفِ شرطِ premium از
  `showTranslate` و `onButtonClick` در ChatActivity + ۳ گیتِ premium در TranslateButton.
  (C) ترجمه‌ی داخلِ حباب برای تک‌پیام: helperِ `toggleManualMessageTranslation` در
  TranslateController (از همان pushToTranslate/موتورِ کلِ چت استفاده می‌کند) + پذیرشِ ترجمه‌ی
  دستی در شرطِ `MessageObject.updateTranslation` + جایگزینیِ ۳ محلِ بازشدنِ TranslateAlert2 در
  ChatActivity با toggle (با fallback به پنجره برای پیام‌های غیرقابل‌ترجمه مثل پیامِ خودِ کاربر)
  + برچسبِ منو «Show Original» وقتی پیام دستی ترجمه شده. بکاپ: `.bak5`. فقط جاوا → بیلدِ عادی.

### الگوی امنِ replace_once (در همه‌ی اسکریپت‌ها)
اول چک می‌کند متنِ **جدید** موجود است (→ skip، برای idempotency)، بعد شمارشِ متنِ **قدیم**؛
اگر ۰ بار → WARNING (نه توقف)، اگر >۱ بار → WARNING. این باعث می‌شود روی سورسِ نیمه‌پچ‌شده هم امن باشد.

---

## ۱۰) وضعیت فعلی
- ✅ لاگین نامحدود + رفعِ کرش‌ها: کاربر با **۵ اکانت** تست کرد و پایدار است.
- ✅ موتورِ ترجمه‌ی گوگل (سبکِ نکوگرام): اعمال شد.
- ✅ دکمه‌ی ترجمه‌ی تک‌پیام پیش‌فرض روشن.
- ✅ **تگِ شماره به ترتیبِ لاگین درست شد** (تأییدِ کاربر) — ولی فقط در شیتِ لمسِ طولانیِ آواتار
  دیده می‌شد.
- ❌ بازخوردِ کاربر بعد از `fix_translate_and_tags`: نوارِ Translate بالای چت نیامد (ریشه:
  وابستگی به تشخیصِ زبانِ ML گوگل که روی گوشیِ او کار نمی‌کند + گیت‌های premium در ChatActivity
  و TranslateButton که جدا از TranslateController بودند) و ترجمه‌ی تک‌پیام هنوز پنجره‌ی بازشو بود.
- 🔄 **در حال تستِ کاربر (آخرین اسکریپت `bubble_translate_and_tags`):**
  - تگ در پروفایلِ خود + هدرِ تنظیمات + لیستِ اکانت‌های تنظیمات.
  - نوارِ Translate بالای همه‌ی چت‌ها (لمس → کلِ چت داخلِ حباب‌ها ترجمه، دوباره → Show Original).
  - ترجمه‌ی تک‌پیام داخلِ خودِ حباب + «Show Original» در لمسِ طولانیِ دوباره.

## ۱۱) کارهای باقی‌مانده (Pending)
1. تأییدِ کاربر برای اسکریپتِ `bubble_translate_and_tags` (تگ‌ها در همه‌جا + نوار + ترجمه‌ی حباب).
2. اگر کاربر خواست تگ در جاهای بیشتری هم باشد (مثلاً صفحه‌ی ویرایشِ پروفایل)، محلِ نمایشِ
   جدید را پیدا و پچ کن (الگو: `getAccountTagNumber`).
3. رفعِ به‌هم‌ریختنِ **bidi فارسی/انگلیسی** موقعِ ترجمه.
4. **«فقط اکانتِ فعال زنده باشد»** (پیشنهادِ کاربر): برای مصرفِ منابع در ۱۰۰ اکانت.
5. **ری‌برندینگ:** نامِ اپ، آیکون، `applicationId` (تا کنارِ تلگرام رسمی نصب شود). نام هنوز انتخاب نشده.
6. راهنمای اتصالِ سریع/پروکسیِ MTProto زیرِ فیلترینگ.

### نکته‌های فنیِ این دور (برای ادامه)
- «ترجمه‌ی کلِ چت» رسمی = نوارِ بالای چت؛ فعال‌شدنش ۳ لایه گیت داشت: TranslateController
  (premium — قبلاً حذف شد)، ChatActivity (`showTranslate` و `onButtonClick` — premium جدا)،
  TranslateButton (۳ جای premium) + شرطِ `translatableDialogs.contains` که فقط با تشخیصِ
  زبانِ ML Kit گوگل پر می‌شود (روی گوشیِ کاربر با گوگلِ بلاک‌شده هرگز پر نمی‌شد).
- ترجمه‌ی دستیِ تک‌پیام in-bubble: state در `manualTranslatedMessages` (حافظه، per-dialog+msgId)؛
  بعد از ری‌استارتِ اپ پاک می‌شود (متنِ ترجمه در DB می‌ماند ولی حباب به اصل برمی‌گردد) — عمدی.
- `MessageObject.updateTranslation` شرطش `isTranslatingDialog && !hidden` بود؛ حالا
  `isMessageManuallyTranslated || (…)`. زبانِ مقصدِ ترجمه‌ی دستی همان `getDialogTranslateTo` است
  تا شرطِ `TextUtils.equals(...)` برقرار بماند.
- در ChatActivity سه محلِ `TranslateAlert2.showAlert` برای تک‌پیام هست (زبانِ معلوم/تشخیص/بدونِ
  detector) — هر سه باید پچ شوند وگرنه بعضی پیام‌ها هنوز پنجره باز می‌کنند.

## ۱۲) درس‌های کلیدی برای گفتگوهای بعدی
- همیشه اسکریپت + `.bat`، **کاملاً انگلیسی (ASCII)**، فایل را مستقیم بفرست (نه لینک).
- سورسِ اصلی را پچ کن، نه کپیِ build.
- تغییرِ C++ = پاک‌کردنِ `.cxx`+`build` + Rebuild چند دقیقه‌ای + Uninstall. تغییرِ فقط جاوا = بیلدِ عادی.
- کرشِ نیتیو بدونِ backtrace قابلِ حل نیست (فیلترِ `DEBUG`).
- قبل از هر پچ، متنِ دقیقِ سورس را از کامیتِ ثابت با `curl` بگیر و تست کن؛ روی خروجیِ WebFetch
  برای متنِ عینِ کد تکیه نکن (خلاصه/ناقص می‌دهد).
- اسلاتِ اکانت ترتیبی نیست (0,99,98,...)؛ برای هر منطقِ «شماره/ترتیب» از `loginTime` استفاده کن.
- ریشه‌ی خیلی از «کار نمی‌کند»ها این است که کاربر `apply_mods.py` را اجرا نکرده و فقط
  اسکریپت‌های مستقل را دارد؛ پس هر قابلیت را در اسکریپتِ مستقلِ جدید هم بگنجان.
