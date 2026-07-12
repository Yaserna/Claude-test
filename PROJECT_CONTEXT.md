# پروژه: فورک سفارشی تلگرام اندروید (نامحدود اکانت + ترجمه + شماره‌گذاری)

> این فایل کلِ زمینه، پیشرفت‌ها، قوانین و راه‌حل‌های پروژه را با ریزترین جزئیات نگه می‌دارد.
> برای بارگذاری در بخش **Projects** کلاد ساخته شده تا هر گفتگوی جدید کاملاً در جریان باشد.
> آخرین به‌روزرسانی: بعد از رفعِ فریزِ چت + گزینه‌ی «Show Original» + برچسبِ شماره‌تلفنِ اکانت‌ها
> (اسکریپت‌های `bubble_translate_and_tags` نسخه‌ی ۳ و `phone_labels`).

---

## ۱) هدف پروژه
ساخت یک اپ اندرویدیِ **دقیقاً مثل تلگرام رسمی** ولی با چند قابلیتِ اختصاصی:
1. ✅ **لاگین نامحدود اکانت** (حداقل ۱۰۰) بدون کرش — مثل نکوگرامِ قدیمی.
2. ✅ **ترجمه‌ی پیام‌ها** (تک‌پیام داخلِ حباب + کلِ گروه/کانال) با موتورِ گوگل، بدونِ Premium.
3. ✅ **نوار/دکمه‌ی ترجمه‌ی کلِ گروه** بالای صفحه (حالا در همه‌ی چت‌ها می‌آید).
4. ⏳ مکالمه‌های **ترکیبیِ فارسی/انگلیسی (bidi/RTL-LTR)** موقع ترجمه نباید به‌هم بریزد (هنوز مانده).
5. ✅ **شماره‌گذاریِ اکانت‌ها** به ترتیبِ لاگین + نمایش با **شماره‌تلفنِ محلی** در UIِ مدیریتی.
6. احتمال افزودنِ شخصی‌سازیِ بیشتر در آینده (ری‌برندینگ — هنوز مانده).

## ۲) پروفایل کاربر و قوانینِ کار (بسیار مهم)
- کاربر **دانشِ برنامه‌نویسی ندارد** → همه‌ی تغییرات باید به‌صورتِ **اسکریپتِ آماده** داده شود
  (فایلِ `.py` + یک `.bat` که با دابل‌کلیک اجرا شود).
- **قانونِ اجباری:** داخلِ اسکریپت‌ها **هیچ حرف/کلمه‌ی فارسی یا کاراکترِ غیرASCII** نباشد.
  علت: `cmd.exe` ویندوز متنِ فارسیِ داخلِ `.bat` را به‌عنوان دستور تفسیر می‌کند و خطای
  «'...' is not recognized as an internal or external command» می‌دهد. همه‌ی پیام‌ها و
  کامنت‌ها باید انگلیسی باشند. فایل‌های `.bat` باید **CRLF** و شاملِ `chcp 65001 >nul` باشند.
- توضیحاتِ کلاد به کاربر: **خیلی کوتاه** و به **فارسی** (اما نه داخلِ اسکریپت).
- کاربر در **ایران** است → لینک‌های `raw.githubusercontent.com` فیلترند؛ فایل را **مستقیم بفرست**
  (SendUserFile)، نه لینکِ دانلود.
- برای اتصال نیاز به **VPN/پروکسی MTProto** دارد (اتصال مستقیم فیلتر است). سرویس‌های گوگل
  (Firebase/ML Kit) روی گوشی‌اش بلاک‌اند — این روی قابلیت‌ها اثرِ واقعی داشت (بخش ۶، باگ ۱۱).
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
- **دستورِ صریحِ کاربر: دقیقاً روی همین شاخه ادامه بده و شاخه‌ی جدید نساز** (حتی اگر محیطِ
  اجرا شاخه‌ی دیگری پیشنهاد بدهد).
- پوش از طریقِ گیتِ محلی. کامیت‌ها ممکن است «Unverified» باشند (بدونِ GPG) — بی‌ضرر.
- **مهم:** کاربر معمولاً `apply_mods.py` (بیلدِ کامل) را اجرا نمی‌کند؛ روی سورسِ محلیِ
  از قبل موجودش، **اسکریپت‌های مستقلِ تک‌منظوره** را اجرا می‌کند که برایش می‌فرستیم.
- آخرین کامیت‌های شاخه (از قدیم به جدید):
  `12c510c` (PROJECT_CONTEXT اولیه) → `2956885` (bubble/bar/tags v1) →
  `0b64f37` (فیکس repaint/retry v2) → `511f20d` (فیکس فریز + undo v3) →
  `699992b` (برچسبِ شماره‌تلفن phone_labels).

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
تغییراتِ **فقط جاوا** این نیاز را ندارند (بیلدِ عادی کافی است) — همه‌ی کارهای این جلسه فقط جاوا بود.

### ج) گرفتنِ backtrace نیتیو (طلا)
کرش‌های نیتیو (SIGSEGV/SIGABRT) خطِ `Fatal signal` را نشان می‌دهند ولی backtrace را پروسه‌ی
جدا (`crash_dump64`، تگِ `DEBUG`) لاگ می‌کند که اندروید استودیو پیش‌فرض مخفیش می‌کند.
**روش:** کادرِ فیلترِ Logcat را **خالی** کن، تایپ کن `DEBUG` (یا `libtmessages`)، بلوکِ
`backtrace:` با خط‌های `#00 pc ... libtmessages.49.so (نام‌تابع+عدد)` را بردار.

### د) فیلترینگ ایران (کاذب/غیرکد)
- `Firebase 403 / API_KEY_ANDROID_APP_BLOCKED / Failed to get regid` = پوشِ گوگل بلاک، بی‌ضرر.
- `libEGL no current context`, `libmigui.so`, `MiuiNotification`, `Slow Binder` = هشدارهای شیائومی، بی‌ضرر.
- اتصالِ کند / `TLS hash mismatch` / `unable to decrypt` = فیلترینگ؛ نیازمندِ VPN/پروکسی.
- **بلاک‌بودنِ گوگل فقط «نویزِ لاگ» نیست:** تشخیصِ زبانِ ML Kit هم کار نمی‌کند → ریشه‌ی باگ ۱۱.

### ه) اسلاتِ اکانت ترتیبی نیست
تلگرام هنگامِ «افزودن اکانت» اسلاتِ خالی را از **بالای** آرایه پیدا می‌کند
(`for (int a = MAX_ACCOUNT_COUNT - 1; a >= 0; a--)`)، پس با MAX=100 اکانت‌ها در اسلاتِ
`0, 99, 98, 97, ...` می‌نشینند. شماره‌گذاریِ درست بر اساسِ **loginTime** است (بخش ۷).

### و) semantics مهمِ ChatActivity: منو و scrim
منوی لمسِ طولانیِ پیام یک لایه‌ی تاریک (scrim/dim) پشتِ خودش می‌گذارد.
`closeMenu()` = بستنِ منو + برداشتنِ scrim؛ `closeMenu(false)` = بستنِ منو ولی **نگه‌داشتنِ scrim**
(برای وقتی که قرار است پنجره‌ای مثل TranslateAlert2 رویش باز شود و موقعِ بسته‌شدن خودش
`dimBehindView(false)` را صدا بزند). اگر پنجره حذف شود ولی `closeMenu(false)` بماند → چت فریز
به‌نظر می‌رسد (باگ ۱۴).

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
   علت: دو `getConnectionByType` در `ConnectionsManager.cpp` وقتی auth key موقتاً هنگامِ
   handshakeِ اکانتِ جدید null است، `nullptr` برمی‌گردانند. فیکس بعد از هر دو:
   `if (connection == nullptr) { iter++; continue; }`
   (این همان کرشِ `tele_log.txt` بود؛ بیلدِ کش‌خورده‌ی C++ هم قصه‌اش در ۵-ب.)

7. **جای‌گذاریِ گاردِ lazy-init:** گاردِ حلقه‌ی اصلی باید **بعد** از
   `UserConfig.getInstance(a).loadConfig();` باشد (isClientActivated فقط بعد از loadConfig معتبر
   است)، وگرنه اکانت‌های ۲+ بعد از هر ری‌استارت برای همیشه غیب می‌شوند.

8. **گاردِ طوفانِ storage:** `LocationController.getLocationsCount` با چکِ `isClientActivated` گارد شد.

9. **تگِ شماره‌ی معکوس (۱۰۰،۹۹،۹۸):** علت در ۵-ه؛ فیکس: helper بر اساسِ `loginTime` (بخش ۷).
   ✅ کاربر تأیید کرد ترتیب درست شد.

10. **ترجمه‌ی کلِ چت در دسترس نبود / به‌خاطر نمی‌ماند:** قفلِ Premium در
    `TranslateController.isFeatureAvailable()` (هر دو overload). حذف شد؛ مکانیزمِ به‌خاطرسپاری
    (`translatingDialogs` + `saveTranslatingDialogsCache`) از قبل در کد بود.

11. **نوارِ Translate بالای چت با وجودِ فیکسِ ۱۰ هم نمی‌آمد (کشفِ ریشه‌ایِ مهم):**
    نوار ۳ لایه گیتِ **جدا از هم** داشت:
    - `TranslateController.isDialogTranslatable` شرطِ `translatableDialogs.contains(dialogId)` داشت
      که فقط با **تشخیصِ زبانِ ML Kit گوگل** پر می‌شود (چند پیام باید تشخیص داده شوند و از
      آستانه‌ها بگذرند) — روی گوشیِ کاربر با گوگلِ بلاک، **هرگز** پر نمی‌شد. فیکس: حذفِ این شرط
      → نوار در همه‌ی دیالوگ‌های عادی (به‌جز Saved Messages و چتِ مخفی).
    - `ChatActivity`: شرطِ `showTranslate` برای غیرِ Premium فقط بعد از صفرشدنِ یک شمارنده‌ی
      تبلیغی نوار را نشان می‌داد، و `onButtonClick` برای غیرِ Premium به‌جای toggle، شیتِ خریدِ
      Premium باز می‌کرد. هر دو ساده شدند (toggle مستقیم).
    - `TranslateButton.java`: ۳ گیتِ Premium (کلیکِ آیکنِ منو، آیکنِ customize/close، گزینه‌ی
      «Do not translate X») — هر سه باز شدند.

12. **رفرش‌نشدنِ حباب بعد از لغو/ترجمه‌ی مجدد (پیدا شده در حلقه‌ی بازبینی):**
    helperِ `toggleManualMessageTranslation` خودش `updateTranslation(true)` را صدا می‌زد و گذارِ
    وضعیت را «مصرف» می‌کرد؛ بعد handlerِ `updateMessageTranslation` در ChatActivity که با
    `updateTranslation(false)` چک می‌کند، تغییری نمی‌دید و سلول را بازرسم نمی‌کرد.
    **قانون:** helper فقط notification (`messageTranslated`) بفرستد؛ گذارِ وضعیت را خودِ
    handlerِ ChatActivity انجام بدهد تا `cell.setMessageObject/updateRowAtPosition` اجرا شود.

13. **گیرکردنِ پیام بعد از شکستِ ترجمه (حلقه‌ی بازبینی):** اگر ترجمه fail می‌شد (بدونِ VPN)،
    پیام در `manualTranslatedMessages` علامت‌خورده می‌ماند و لمسِ بعدی بی‌صدا فقط علامت را
    برمی‌داشت. فیکس: undo فقط وقتی `set.contains(messageId) && messageObject.translated`؛
    در غیرِ این صورت retry.

14. **فریزِ کلِ چت بعد از ترجمه‌ی حباب (گزارشِ کاربر):** شاخه‌ی [mod] از `closeMenu(false)`
    استفاده می‌کرد → scrim تاریک برای همیشه می‌ماند و چت به لمس جواب نمی‌داد (شرح در ۵-و).
    فیکس: `closeMenu()`.

15. **نبودِ گزینه‌ی لغو بعد از ورودِ مجدد به چت (گزارشِ کاربر):**
    `MessageObject.getMessageTextToTranslate` برای پیامِ `translated` مقدارِ **null** برمی‌گرداند
    → شرطِ ساختِ منو (`!TextUtils.isEmpty(...)`) گزینه‌ی Translate را برای پیامِ ترجمه‌شده اصلاً
    اضافه نمی‌کرد → برچسبِ «Show Original» هیچ‌وقت فرصتِ نمایش نداشت. فیکس دوتکه:
    - شرطِ ساختِ منو (هر ۲ سایت): `isMessageManuallyTranslated(selectedObject) || !TextUtils.isEmpty(...)`.
    - یک **شاخه‌ی کلیکِ اختصاصیِ undo** قبل از بلوکِ عادیِ `OPTION_TRANSLATE` (چون مسیرِ عادی به
      `finalMessageText` و چکِ زبان تکیه دارد که برای پیامِ ترجمه‌شده null/نامعتبر است).

16. **باگِ idempotency در apply_mods (حلقه‌ی بازبینی):** بعد از افزودنِ بخشِ 5.7 (phone-label)،
    اجرای دومِ apply_mods helperِ تگ را **دوباره** درج می‌کرد (چون متنِ سایت‌ها به phone-label
    تبدیل شده بود و چکِ `new in text` دیگر skip نمی‌کرد) و بعد ERROR می‌داد.
    فیکس: گاردِ `file_contains(...)` قبل از پچ‌های تگ در بخش‌های 5/5.5/5.7 («superseded by
    phone label, skipped») و همان الگو در اسکریپت‌های مستقل.

---

## ۷) شماره‌گذاری و برچسبِ اکانت‌ها

### helperِ شماره‌ی ترتیبی (بر اساسِ لاگین) — در `UserConfig.java`
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
- `loginTime` یک `public int` در UserConfig است (timestamp لاگین) — همان که سوییچرِ اکانت
  برای مرتب‌سازی استفاده می‌کند. شماره پایدار است مگر اکانتِ قبلی logout شود.

### helperِ برچسبِ شماره‌تلفن (جدید) — در `UserConfig.java`، بعد از helper بالا
```java
public static String getAccountLabel(int account, String fallbackName) {
    String label = fallbackName;
    try {
        TLRPC.User user = getInstance(account).getCurrentUser();
        if (user != null && user.phone != null && user.phone.length() > 0) {
            String formatted = org.telegram.PhoneFormat.PhoneFormat.getInstance().format("+" + user.phone);
            // اولین توکنِ فرمت‌شده = کدِ کشور؛ بقیه = شماره‌ی محلی
            int space = formatted.indexOf(' ');
            String local = space > 0 ? formatted.substring(space + 1) : formatted;
            ... (trim + حذفِ + ابتدایی؛ خالی بود → همان نام)
        }
    } catch (Exception e) { /* keep name */ }
    return "#" + getAccountTagNumber(account) + " " + label;
}
```
- خروجی (فرمتِ جدید، به‌درخواستِ کاربر): `9123456789  #1` — شماره‌ی محلی **بدونِ فاصله/خط‌تیره**،
  بعد **دو فاصله**، بعد تگِ `#N` در **آخر**. (فرمتِ قدیمی `#1 912 345 6789` بود؛ با
  `label_format.py` یا نسخه‌ی جدیدِ `phone_labels.py`/apply_mods تعمیر می‌شود —
  خطوطِ کلیدی: `local.replace(" ", "").replace("-", "")` و `return label + "  #" + tag`.)
- با `PhoneFormat` خودِ تلگرام، پس برای هر کشوری درست است.
- **فقط UIِ مدیریتیِ خودمان**؛ نام در چت/گروه/مخاطبین دست‌نخورده.

### استثنا: هدرِ پروفایلِ خود + هدرِ تنظیمات = اسمِ واقعی + تگ (به‌درخواستِ کاربر)
- این دو محل به‌جای شماره، **نامِ واقعی + `"  #N"`** نشان می‌دهند (مثل `Ali Rezaei  #1`):
  - `ProfileActivity`: `newString = newString.toString() + "  #" + UserConfig.getAccountTagNumber(currentAccount);` — کامنت `[mod] account name tag (own profile)`
  - `SettingsActivity` (titleView): `UserObject.getUserName(user) + "  #" + ...` — کامنت `[mod] account name tag (settings header)`
- اسکریپتِ مستقل: `profile_name_tag.py/.bat` (بکاپ `.bak10`؛ سه‌حالته: phone/tag/خام).
- `phone_labels.py` و apply_mods (5.5 گاردها + 5.7) هم به همین حالت به‌روز شدند.

### ۴ محلِ دیگر (همچنان از `getAccountLabel` = شماره‌تلفن استفاده می‌کنند)
- `ui/MainTabsActivity.java` → `accountView` (شیتِ لمسِ طولانی روی آواتار).
- `ui/DialogsActivity.java` → `accountView` (منوی کشویی/Drawer).
- `ui/Cells/AccountSelectCell.java` → `setAccount` (شیتِ «Send as»؛ متغیرِ اکانت: `accountNumber`).
- `ui/ProfileActivity.java` → بلوکِ `CharSequence newString = UserObject.getUserName(user);`
  (فقط وقتی `user.id == getUserConfig().getClientUserId()`؛ پروفایلِ دیگران دست‌نخورده).
- `ui/SettingsActivity.java` → `setInfo` (هدرِ تنظیمات، `titleView`).
- `ui/SettingsActivity.java` → `AccountCell.set` (لیستِ حساب‌های داخلِ تنظیمات، `textView`).

---

## ۸) معماریِ ترجمه (دقیق)

### فلگ‌های موتور (در `MessagesController.java`)
- دو رشته: `translationsManualEnabled` (تک‌پیام) و `translationsAutoEnabled` (کلِ چت).
  هر دو روی `"alternative"` قفل شدند (= موتورِ گوگل، سبکِ نکوگرام): در `loadConfig` مقداردهیِ
  مستقیم؛ در appConfigِ سرور شرطِ به‌روزرسانی → `if (false)` (کامنت‌های `(manual)`/`(auto)` عمداً متفاوت‌اند).

### مسیرِ موتورِ گوگل (کدِ رسمیِ موجود)
- `ui/Components/TranslateAlert2.java` → `alternativeTranslate`: endpointِ
  `https://translate.googleapis.com/translate_a/single?client=gtx&...` با chunking و چرخشِ UA.
- `TranslateController.pushToTranslate` وقتی method == "alternative" از همین مسیر می‌رود
  (هم برای کلِ چت، هم برای ترجمه‌ی دستیِ تک‌پیام).

### قفل‌های Premium (همه حذف شدند)
- `TranslateController.isFeatureAvailable()` (۲ overload) — جلسه‌ی قبل.
- `ChatActivity.showTranslate` و `TranslateButton.onButtonClick` و ۳ جای `TranslateButton.java` — این جلسه (باگ ۱۱).

### نوارِ ترجمه‌ی کلِ چت
- `isDialogTranslatable` دیگر به تشخیصِ زبان وابسته نیست → نوار در همه‌ی چت‌ها/گروه‌ها/کانال‌ها.
- لمسِ نوار → `toggleTranslatingDialog` → همه‌ی حباب‌های قابلِ ترجمه inline ترجمه می‌شوند؛
  وضعیت per-dialog در `translating_dialog_languages2` ذخیره و بعد از ری‌استارت لود می‌شود.
- آیکنِ کنارِ نوار → منوی انتخابِ زبانِ مقصد + «Hide» برای مخفی‌کردنِ نوارِ همان چت.

### ترجمه‌ی دستیِ تک‌پیام داخلِ حباب (ساختِ خودمان)
- state: `manualTranslatedMessages` (HashMap<Long dialogId, HashSet<Integer msgId>>) در
  TranslateController — **در حافظه**؛ بعد از ری‌استارتِ کاملِ اپ پاک می‌شود (متنِ ترجمه در DB
  می‌ماند ولی حباب به اصل برمی‌گردد) — **عمدی**.
- `toggleManualMessageTranslation(messageObject)`:
  - علامت‌خورده و `translated` → undo: حذفِ علامت + notification (بدونِ دست‌زدن به وضعیت — باگ ۱۲).
  - ترجمه‌ی کش‌شده با زبانِ درست → فقط notification.
  - وگرنه → `messageTranslating` + `pushToTranslate` (callback: ست‌کردنِ
    `translatedText/translatedToLanguage` + `updateMessageCustomParams` + `messageTranslated`).
- زبانِ مقصد همیشه `getDialogTranslateTo(dialogId)` تا شرطِ
  `TextUtils.equals(getDialogTranslateTo(...), translatedToLanguage)` در `updateTranslation` برقرار بماند.
- شرطِ `MessageObject.updateTranslation` (شاخه‌ی سوم) این‌طور باز شد:
  `(isMessageManuallyTranslated(dialogId, id) || isTranslatingDialog && !isTranslateDialogHidden)`.
- ChatActivity: **۳ سایتِ** `TranslateAlert2.showAlert` (زبانِ معلوم / تشخیص‌شده / بدونِ detector)
  هر سه با شاخه‌ی `if (TranslateController.isTranslatable(selectedObject)) { toggle; closeMenu(); } else { پنجره }`
  پچ شدند + **شاخه‌ی چهارمِ undo** قبل از کلِ بلوک (باگ ۱۵) + برچسبِ منو
  (`ShowOriginalButton` وقتی manual && translated) در ۲ سایتِ ساختِ منو.
- **fallback به پنجره:** پیام‌های خودِ کاربر (`isOutOwner`) و انواعِ غیرقابلِ ترجمه‌ی inline —
  محدودیتِ `TranslateController.isTranslatable` است، عمدی.
- رفتارهای عمدی: در چتی که کلش ترجمه است، toggleِ تک‌پیام اثرِ دیداری ندارد (ترجمه‌ی کلِ چت غالب
  است)؛ shimmer «در حالِ ترجمه» برای تک‌پیامِ دستی نمایش داده نمی‌شود (isTranslating به
  isTranslatingDialog گره خورده) — بی‌اهمیت.

### دکمه‌ی ترجمه‌ی تک‌پیام پیش‌فرض روشن
`TranslateController`: پیش‌فرضِ `translate_button` → true.

### موتورِ ترجمه‌ی هوشِ مصنوعی (اختیاری، کیفیتِ بالا)
- گلوگاهِ هر دو مسیرِ ترجمه `TranslateAlert2.alternativeTranslate(text, from, to, cb)` است
  (کلِ چت: `TranslateController` خطِ ~۱۰۶۰؛ حباب: از همان مسیر). پس یک متدِ AI هر دو را می‌گیرد.
- افزوده شد: `aiTranslate(text, toLng, done)` که POST به یک endpointِ **OpenAI-compatible**
  (chat/completions) می‌زند؛ ۳ ثابت: `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY`. اگر کلید خالی باشد
  `isAiTranslateEnabled()=false` و به گوگل fallback می‌شود. در ابتدای `alternativeTranslate`:
  `if (isAiTranslateEnabled()) { aiTranslate(text, toLng, done); return; }`.
- از نامِ کاملِ کلاس (`org.json.JSONObject`, `java.io.OutputStream/InputStream`) استفاده شد تا
  **نیازی به تغییرِ importها نباشد**. پارس: `choices[0].message.content`.
- کلید داخلِ کد **کامیت نمی‌شود**؛ اسکریپتِ مستقلِ `ai_translate.py/.bat` (بکاپ `.bak12`) کلید را
  از کاربر می‌پرسد و در سورسِ محلی می‌گذارد (interactive). apply_mods بخش ۴.۵ از `build_config.json`
  می‌خواند (`ai_translate`/`ai_base_url`/`ai_model`/`ai_api_key`؛ کلیدِ خالیِ پیش‌فرض = رفتارِ گوگل).
- پیش‌فرض: OpenRouter + مدلِ رایگانِ `:free`. هشدار: ترجمه‌ی **کلِ چت** هر پیام = یک درخواست؛
  مدلِ رایگان سقفِ نرخ دارد، پس ممکن است چند پیام fail شود (تک‌پیام مشکلی ندارد).
- **باقی‌مانده:** دکمه‌ی ترجمه‌ی کادرِ تایپ (compose) با همین موتور — مرحله‌ی بعد.

### باگ `sl=und` (ترجمه اغلب انجام نمی‌شد — رفع شد)
- علت: وقتی تشخیصِ زبانِ مبدأ قطعی نیست (ML Kit روی گوشیِ کاربر بلاک است) زبان `und` می‌شود
  و کد `sl=und` می‌فرستد؛ گوگل `sl=und` و `sl=""` را با **HTTP 400** رد می‌کند → ترجمه بی‌صدا شکست می‌خورد.
  با curl تأیید شد: `und`→400، `auto`→200.
- فیکس (در `TranslateAlert2.alternativeTranslateInternal`، خطِ ساختِ URL): زبانِ مبدأِ ناشناخته
  (`null`/`""`/`und`/`undefined`) → `auto` تا گوگل خودش تشخیص دهد. یک نقطه، همه‌ی مسیرها (کلِ چت و حباب).
- اسکریپت مستقل: `fix_translate_source.py/.bat` (بکاپ `.bak11`)؛ در apply_mods بخش ۴ هم اضافه شد.

---

## ۹) مجموعه‌ی اسکریپت‌ها

### الف) در ریپو (برای بیلدِ کامل از صفر)
- `setup.bat` / `setup.sh` — clone سورس روی کامیتِ ثابت + اجرای `apply_mods.py`.
- `apply_mods.py` — **همه‌ی** تغییرات (جاوا + نیتیو + gradle)، ~۴۹ پچِ idempotent با برچسب:
  1) سقفِ اکانتِ جاوا؛ 1.5) گاردهای lazy-init؛ 1.6) خاموشیِ CheckJNI؛ 1.7) سقفِ نیتیو + map؛
  1.8) tgCurrentEnv (۳۵ جایگزینی)؛ 1.9) دو null-check؛ 1.10) گاردِ LocationController؛
  2) حذفِ قفلِ Premium ترجمه؛ 3) دکمه‌ی تک‌پیام پیش‌فرض روشن؛ 4) موتورِ گوگل (۴ پچ)؛
  5) تگِ شماره (helper + ۳ محل)؛ 5.5) تگ در پروفایل/تنظیمات (۳ محل)؛
  5.7) برچسبِ شماره‌تلفن (helper + ۶ محل)؛ 6) نوارِ ترجمه در همه‌ی چت‌ها (۶ پچ)؛
  7) ترجمه‌ی حبابِ تک‌پیام + undo (helper و MessageObject و ۳+۲+۲+۱ پچِ ChatActivity + hotfixها).
  پچ‌های تگِ 5/5.5 با `file_contains` گارد شده‌اند (باگ ۱۶). روی سورسِ pinned تستِ کامل:
  اجرای اول ۴۹ OK، اجرای دوم صفر تغییر، توازنِ کد سالم.
- `fix_crash.py` / `fix_crash.bat` — ابزارِ کمکیِ فقط گاردهای lazy-init.
- `build_config.json` — کلیدها: `account_limit=100`, `enable_chat_translate_for_all`,
  `translate_button_default_on`, `nekogram_style_translation`, `account_number_tags`,
  `account_phone_labels`, `translate_bar_for_all`, `bubble_translate`.
- `bubble_translate_and_tags.py/.bat` و `phone_labels.py/.bat` — در ریپو هم هستند (پایین).
- `README.md`, `BUILD-GUIDE-FA.md`, `conversation.md`.

### ب) اسکریپت‌های مستقلِ فرستاده‌شده به کاربر (روی سورسِ محلیِ او)
> همه انگلیسی/ASCII، `find_project_root` خودشان پوشه را پیدا می‌کنند، idempotent، بکاپِ یک‌باره.
- `fix_native_crash.py/.bat` — نامحدودسازی + فیکس‌های کرش (معادلِ ۱ تا ۱.۱۰). بکاپ: `.bak`.
- `fix_round2.py/.bat` — پاک‌سازیِ ترکیبِ اسکریپت‌های قدیمی + گزارشِ تشخیصی. بکاپ: `.bak2`.
- `add_features.py/.bat` — موتورِ گوگل + تگِ شماره (نسخه‌ی باگ‌دارِ اسلاتی). بکاپ: `.bak3`.
- `fix_translate_and_tags.py/.bat` — حذفِ قفلِ Premium + helperِ loginTime + اصلاحِ تگ‌ها. بکاپ: `.bak4`.
- `bubble_translate_and_tags.py/.bat` — **نسخه‌ی ۳ (فایلِ نهایی که کاربر باید داشته باشد):**
  ۱۹ پچِ اصلی (تگ در پروفایل/تنظیمات + نوارِ ترجمه‌ی همه‌ی چت‌ها + ترجمه‌ی حباب) به‌علاوه‌ی
  hotfixهای v2 (repaint/retry — باگ‌های ۱۲/۱۳) و v3 (فریز/undo — باگ‌های ۱۴/۱۵).
  **خود-تعمیرگر است:** روی سورسِ v1 یا v2 یا خام، خودش تشخیص می‌دهد و فقط لازم‌ها را می‌زند
  (hotfixها *قبل از* insert اجرا می‌شوند تا helperِ قدیمی درجا تعمیر شود، نه تکراری).
  روی سورسِ phone_labels-خورده هم پچ‌های تگش را skip می‌کند («superseded»). بکاپ: `.bak5`. فقط جاوا.
- `phone_labels.py/.bat` — **آخرین:** برچسبِ «#N شماره‌ی محلی» در ۶ محلِ مدیریتی (بخش ۷).
  پچ‌ها **دو-حالته** (`patch_first`): هم سورسِ تگ‌دار هم خام را می‌گیرند. بکاپ: `.bak6`. فقط جاوا.
  ترتیبِ درستِ اجرا برای کاربر: اول bubble (v3) بعد phone_labels — ولی برعکس هم نمی‌شکند.

### الگوهای امنِ پچ (در همه‌ی اسکریپت‌ها)
- `replace_once/patch`: اول چکِ متنِ **جدید** (skip)، بعد شمارشِ **قدیم**؛ ۰ یا >۱ → هشدار، نه توقف.
- `patch_first` (جدید): لیستی از جفت‌های (old,new) + یک needle برای idempotency — برای
  سورس‌هایی که ممکن است در حالت‌های پچِ مختلف باشند.
- `patch_multi/replace_all`: برای متن‌های عمداً تکراری (مثلِ ۳ سایتِ closeMenu).
- hotfixِ نسخه‌های قبلیِ خودِ اسکریپت‌ها همیشه **قبل از** insertِ متنِ کامل اجرا شود.

---

## ۱۰) وضعیت فعلی
- ✅ لاگین نامحدود + رفعِ کرش‌ها: با ۵ اکانت تست شده و پایدار است.
- ✅ موتورِ ترجمه‌ی گوگل + دکمه‌ی تک‌پیام پیش‌فرض روشن.
- ✅ تگِ شماره به ترتیبِ درستِ لاگین (تأییدِ کاربر).
- ✅ ترجمه‌ی حبابِ تک‌پیام **کار می‌کند** (تأییدِ کاربر) — ولی بیلدِ قبلی‌اش فریز/بی‌undo بود (باگ ۱۴/۱۵، رفع شد).
- 🔄 **در انتظارِ بیلد و تستِ کاربر:**
  - `bubble_translate_and_tags` نسخه‌ی ۳: بدونِ فریز + «Show Original» حتی بعد از ورودِ مجدد به چت.
  - نوارِ Translate بالای همه‌ی چت‌ها (لمس → کلِ چت داخلِ حباب‌ها؛ ماندگاری per-dialog).
  - تگ در پروفایلِ خود/هدرِ تنظیمات/لیستِ حساب‌ها.
  - `phone_labels`: نمایشِ «#N شماره‌ی محلی» در ۶ محلِ مدیریتی.

## ۱۱) کارهای باقی‌مانده (Pending)
1. تأییدِ تستِ کاربر: bubble v3 (فریز رفته؟ Show Original هست؟) + phone_labels (شماره‌ها درست‌اند؟).
2. رفعِ به‌هم‌ریختنِ **bidi فارسی/انگلیسی** موقعِ ترجمه.
3. ✅ **«فقط اکانتِ فعال زنده باشد»** انجام شد (`sleep_accounts.py` + بخشِ ۹ apply_mods، فقط جاوا).
   ریشه: `ConnectionsManager.checkConnection()` تنها جایی است که `native_setNetworkAvailable`
   را صدا می‌زند. گیت شد: اگر `isAccountAwake(account)` نبود (یعنی `account != UserConfig.selectedAccount`)
   → `native_setNetworkAvailable(false)` + `native_pauseNetwork` و return. هلپرها
   (`sleepInactiveAccounts`/`isAccountAwake`/`applyAccountSleepStates`) در ConnectionsManager؛
   `init()` هم برای اکانتِ خواب `hasNetwork=false` می‌فرستد (آفلاین از استارتاپ)؛ و
   `LaunchActivity.switchToAccount` بعد از ستِ `selectedAccount` تابعِ
   `applyAccountSleepStates()` را صدا می‌زند تا اکانتِ جدید بیدار و قبلی بخوابد. بکاپ `.bak9`.
   عمدی: اکانتِ خواب هیچ نوتیفیکیشنی نمی‌دهد تا بازش کنی. خاموش‌کردن: `sleepInactiveAccounts=false`.
4. **ری‌برندینگ:** ✅ نام = **YasTel** و بسته = رسمی (`org.telegram.messenger`) انجام شد
   (اسکریپت `rebrand.py` + بخشِ ۸ در apply_mods). باقی‌مانده: **آیکون**. توجه: چون بسته رسمی شد،
   قبلِ نصب باید تلگرامِ رسمی **حذف** شود (امضاها فرق دارد؛ نصبِ روی‌هم نمی‌شود).
5. راهنمای اتصالِ سریع/پروکسیِ MTProto زیرِ فیلترینگ.

## ۱۲) درس‌های کلیدی برای گفتگوهای بعدی
- همیشه اسکریپت + `.bat`، **کاملاً انگلیسی (ASCII)**، فایل را مستقیم بفرست (نه لینک).
- سورسِ اصلی را پچ کن، نه کپیِ build. تغییرِ C++ = پاک‌کردنِ `.cxx`+`build`؛ فقط جاوا = بیلدِ عادی.
- کرشِ نیتیو بدونِ backtrace قابلِ حل نیست (فیلترِ `DEBUG`).
- قبل از هر پچ، متنِ دقیقِ سورس را از کامیتِ ثابت بگیر (clone/curl) و پچ را همان‌جا تست کن؛
  به خروجیِ WebFetch برای متنِ عینِ کد تکیه نکن.
- اسلاتِ اکانت ترتیبی نیست؛ برای «شماره/ترتیب» از `loginTime` استفاده کن.
- ریشه‌ی خیلی از «کار نمی‌کند»ها اجرانشدنِ apply_mods است؛ هر قابلیت را اسکریپتِ مستقل هم بکن.
- **در بازبینی، مسیرِ UI را هم ردگیری کن نه فقط مسیرِ داده:** فریزِ چت (scrim/closeMenu) و
  غیب‌شدنِ گزینه‌ی منو (getMessageTextToTranslate=null) هر دو در لایه‌ی UI بودند و ردِ داده‌ایِ
  «ترجمه انجام می‌شود» آن‌ها را نشان نمی‌داد.
- **هر نسخه‌ی جدیدِ اسکریپت باید سورسِ پچ‌شده با نسخه‌های قبلیِ خودش را تعمیر کند** (hotfix قبل
  از insert)، وگرنه درجِ تکراریِ helper = خطای کامپایل.
- بعد از هر تغییرِ notification-محور، چک کن گذارِ وضعیت در **handler** اتفاق بیفتد نه قبل از آن
  (الگوی باگ ۱۲).
- چکِ توازنِ آکولاد/پرانتز باید **اول کامنت‌ها** را بردارد؛ آپاستروفِ داخلِ کامنتِ جاوا
  (مثل «Telegram's») با regexِ ساده false-positive می‌دهد.
- اسکریپت‌ها را در هر ۳ سناریو تست کن: سورسِ خام، سورسِ نیمه‌پچ (نسخه‌های قبلی)، اجرای مجدد.
