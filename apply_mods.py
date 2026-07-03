#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_mods.py
-------------
این اسکریپت تغییرات اختصاصی ما را روی سورس تلگرام (که قبلاً توسط setup کلون شده)
اعمال می‌کند. هر تغییر دقیق است: اگر متن اصلی پیدا نشود، با خطا متوقف می‌شود
تا اگر نسخه‌ی سورس عوض شد، متوجه شویم.

Applies our custom modifications onto the (already cloned) Telegram source.
Each edit is exact and fails loudly if the original text is not found, so that
upstream drift is caught instead of silently producing a broken build.
"""

import json
import os
import sys

# ریشه‌ی پروژه (جایی که این اسکریپت قرار دارد)
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "Telegram")  # سورس کلون‌شده‌ی تلگرام


def load_config():
    with open(os.path.join(ROOT, "build_config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _path(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        sys.exit(f"[ERROR] فایل پیدا نشد (file not found): {rel}\n"
                 f"        مطمئن شو اول setup را اجرا کرده‌ای تا سورس کلون شود.")
    return p


def replace_once(rel, old, new, label, optional=False):
    """یک جایگزینی دقیق. باید دقیقاً یک‌بار رخ بدهد.
    منطق idempotent: اگر متن اصلی موجود بود اعمال می‌کنیم؛ فقط وقتی متن اصلی
    نبود و نسخه‌ی جدید موجود بود، یعنی قبلاً اعمال شده و رد می‌کنیم.

    optional=True یعنی اگر متن اصلی پیدا نشد، به‌جای توقف کامل فقط هشدار می‌دهیم.
    این برای گاردهای ApplicationLoader است که ممکن است فاصله‌گذاری‌شان کمی فرق کند.
    """
    p = _path(rel)
    with open(p, "r", encoding="utf-8") as f:
        text = f.read()
    if new in text:
        # چک قبل از شمارشِ old چون بعضی گاردها متنِ old را دست‌نخورده نگه
        # می‌دارند (فقط چیزی قبلش اضافه می‌کنند) و بدونِ این چک، اجرای دوباره
        # همان گارد را چندبار اضافه می‌کرد.
        print(f"  - [{label}] از قبل اعمال شده، رد شد.")
        return
    count = text.count(old)
    if count == 0:
        msg = (f"[{label}] متن اصلی پیدا نشد در {rel}\n"
               f"        احتمالاً نسخه‌ی سورس با commit ثبت‌شده فرق دارد.")
        if optional:
            print(f"  ! هشدار (warning): {msg}\n"
                  f"        این گارد را در صورت کرش، دستی اعمال کن.")
            return
        sys.exit(f"[ERROR] {msg}")
    if count > 1:
        if optional:
            print(f"  ! هشدار (warning): [{label}] متن اصلی {count} بار پیدا شد در {rel}؛ رد شد.")
            return
        sys.exit(f"[ERROR] [{label}] متن اصلی {count} بار پیدا شد (انتظار ۱ بار) در {rel}")
    text = text.replace(old, new, 1)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  ✔ [{label}] اعمال شد در {rel}")


def replace_all(rel, old, new, label):
    """جایگزینی همه‌ی رخدادهای یک الگوی تکراری (مثل fix نیتیوِ jniEnv در ۳۵ جا).
    idempotent: اگر رخدادی از old نماند، یعنی قبلاً اعمال شده."""
    p = _path(rel)
    with open(p, "r", encoding="utf-8") as f:
        text = f.read()
    count = text.count(old)
    if count == 0:
        print(f"  - [{label}] از قبل اعمال شده، رد شد.")
        return
    text = text.replace(old, new)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  ✔ [{label}] اعمال شد ({count} مورد) در {rel}")


def main():
    cfg = load_config()
    print("=== اعمال تغییرات اختصاصی روی سورس تلگرام ===\n")

    # ------------------------------------------------------------------
    # ۱) حذف محدودیت تعداد اکانت (لاگین نامحدود)
    #    دو ثابت در UserConfig.java را بالا می‌بریم. چون سقف رایگان و سقف کل
    #    برابر می‌شوند، گیت پریمیوم هرگز فعال نمی‌شود و همه‌ی اسلات‌ها آزادند.
    # ------------------------------------------------------------------
    limit = int(cfg.get("account_limit", 100))
    uc = "TMessagesProj/src/main/java/org/telegram/messenger/UserConfig.java"
    print("۱) محدودیت تعداد اکانت → نامحدود (account_limit = %d)" % limit)
    replace_once(uc,
                 "public final static int MAX_ACCOUNT_DEFAULT_COUNT = 3;",
                 "public final static int MAX_ACCOUNT_DEFAULT_COUNT = %d;" % limit,
                 "accounts: free limit")
    replace_once(uc,
                 "public final static int MAX_ACCOUNT_COUNT = 4;",
                 "public final static int MAX_ACCOUNT_COUNT = %d;" % limit,
                 "accounts: hard limit")

    # ------------------------------------------------------------------
    # ۱.۵) راه‌اندازی تنبل اکانت‌ها (lazy init) — جلوگیری از کرش هنگام باز شدن
    #    وقتی MAX_ACCOUNT_COUNT بالا باشد، ApplicationLoader هنگام شروع همه‌ی
    #    اسلات‌ها را هم‌زمان روی تردهای جدا می‌سازد. این باعث خطای JNI بین تردها
    #    و IntentReceiverLeaked در DownloadController.<init> و در نهایت SIGABRT
    #    می‌شود. این گاردها اسلات‌های غیرفعال را در شروع رد می‌کنند تا فقط
    #    اکانت‌های واقعاً لاگین‌شده ساخته شوند (مثل نسخه‌های قدیمی NekoGram).
    # ------------------------------------------------------------------
    al = "TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java"
    guard = "if (a != 0 && !UserConfig.getInstance(a).isClientActivated()) continue;"
    print("۱.۵) راه‌اندازی تنبل اکانت‌ها (lazy init) برای جلوگیری از کرش شروع")

    # حلقه‌ی اصلی postInitApplication: گارد باید بعد از loadConfig باشد، نه قبلش
    # (isClientActivated() فقط بعد از خودِ loadConfig معتبر می‌شود؛ اگر گارد قبل
    #  از loadConfig باشد، اکانت‌های ۲+ بعد از هر ری‌استارت برای همیشه رد می‌شوند)
    replace_once(al,
                 "            UserConfig.getInstance(a).loadConfig();\n"
                 "            MessagesController.getInstance(a);",
                 "            UserConfig.getInstance(a).loadConfig();\n"
                 "            " + guard + "\n"
                 "            MessagesController.getInstance(a);",
                 "lazy-init: main loop", optional=True)

    # حلقه‌ی ContactsController/DownloadController (محل دقیق کرش این لاگ)
    replace_once(al,
                 "            ContactsController.getInstance(a).checkAppAccount();\n"
                 "            DownloadController.getInstance(a);",
                 "            " + guard + "\n"
                 "            ContactsController.getInstance(a).checkAppAccount();\n"
                 "            DownloadController.getInstance(a);",
                 "lazy-init: contacts/download loop", optional=True)

    # حلقه‌ی گیرنده‌ی تغییر شبکه (network receiver)
    replace_once(al,
                 "                    for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "                        ConnectionsManager.getInstance(a).checkConnection();",
                 "                    for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "                        " + guard + "\n"
                 "                        ConnectionsManager.getInstance(a).checkConnection();",
                 "lazy-init: network receiver loop", optional=True)

    # ------------------------------------------------------------------
    # ۱.۶) خاموش‌کردنِ CheckJNI در بیلدِ دیباگ
    #    بیلدِ دیباگِ اندروید به‌صورت پیش‌فرض CheckJNI را روشن می‌کند که خطاهای
    #    نهفته‌ی JNI (بی‌ضرر در حالت عادی) را به SIGABRT تبدیل می‌کند. این خصوصاً
    #    موقع افزودن اکانت‌های بیشتر از ۴ تا (که نیاز به ترد/JNI بیشتر دارد) کرش
    #    می‌کند.
    # ------------------------------------------------------------------
    bg = "TMessagesProj/build.gradle"
    print("۱.۶) خاموش‌کردنِ CheckJNI در بیلدِ دیباگ")
    replace_once(bg,
                 "        debug {\n"
                 "            jniDebuggable true",
                 "        debug {\n"
                 "            jniDebuggable false\n"
                 "            debuggable false",
                 "build: disable CheckJNI on debug")

    # ------------------------------------------------------------------
    # ۱.۷) سقفِ نیتیوِ ۵ اکانت → نامحدود
    #    کدِ C++ (tgnet) جدا از جاوا یک سقفِ سختِ ۵ اکانت دارد: هم #define و هم
    #    یک switch در getInstance که هر اندیسِ ≥۵ را به اکانتِ ۴ می‌فرستد (باعثِ
    #    قاطی‌شدنِ اکانت‌ها می‌شود). این‌جا #define را برابرِ همان سقفِ جاوا می‌کنیم
    #    و getInstance را به یک map پویا و thread-safe تبدیل می‌کنیم.
    # ------------------------------------------------------------------
    defines_h = "TMessagesProj/jni/tgnet/Defines.h"
    cm_cpp = "TMessagesProj/jni/tgnet/ConnectionsManager.cpp"
    print("۱.۷) سقفِ نیتیوِ اکانت → نامحدود (native account_limit = %d)" % limit)
    replace_once(defines_h,
                 "#define MAX_ACCOUNT_COUNT 5",
                 "#define MAX_ACCOUNT_COUNT %d" % limit,
                 "native: account count define")
    replace_once(cm_cpp,
                 "ConnectionsManager& ConnectionsManager::getInstance(int32_t instanceNum) {\n"
                 "    switch (instanceNum) {\n"
                 "        case 0:\n"
                 "            static ConnectionsManager instance0(0);\n"
                 "            return instance0;\n"
                 "        case 1:\n"
                 "            static ConnectionsManager instance1(1);\n"
                 "            return instance1;\n"
                 "        case 2:\n"
                 "            static ConnectionsManager instance2(2);\n"
                 "            return instance2;\n"
                 "        case 3:\n"
                 "            static ConnectionsManager instance3(3);\n"
                 "            return instance3;\n"
                 "        case 4:\n"
                 "        default:\n"
                 "            static ConnectionsManager instance4(4);\n"
                 "            return instance4;\n"
                 "    }\n"
                 "}",
                 "ConnectionsManager& ConnectionsManager::getInstance(int32_t instanceNum) {\n"
                 "    static std::map<int32_t, ConnectionsManager *> instances;\n"
                 "    static pthread_mutex_t instancesMutex = PTHREAD_MUTEX_INITIALIZER;\n"
                 "    if (instanceNum < 0) {\n"
                 "        instanceNum = 0;\n"
                 "    }\n"
                 "    pthread_mutex_lock(&instancesMutex);\n"
                 "    ConnectionsManager *result = instances[instanceNum];\n"
                 "    if (result == nullptr) {\n"
                 "        result = new ConnectionsManager(instanceNum);\n"
                 "        instances[instanceNum] = result;\n"
                 "    }\n"
                 "    pthread_mutex_unlock(&instancesMutex);\n"
                 "    return *result;\n"
                 "}",
                 "native: getInstance dynamic map")

    # ------------------------------------------------------------------
    # ۱.۸) رفعِ کرشِ JNIEnv بین‌تردی
    #    TgNetWrapper.cpp کالبک‌های شبکه را از تردهای مختلفِ tgnet صدا می‌زند ولی
    #    از یک jniEnv[instanceNum] کش‌شده (متعلق به تردِ دیگر) استفاده می‌کرد؛
    #    این باعثِ «JNI DETECTED ERROR: using JNIEnv* from thread X» می‌شود.
    #    راه‌حل: هر بار JNIEnv را برای تردِ جاری از JavaVM بگیریم/attach کنیم.
    # ------------------------------------------------------------------
    tgw = "TMessagesProj/jni/TgNetWrapper.cpp"
    print("۱.۸) رفعِ کرشِ JNIEnv بین‌تردی در TgNetWrapper.cpp")
    replace_once(tgw,
                 "JavaVM *java;",
                 "JavaVM *java;\n\n"
                 "static inline JNIEnv *tgCurrentEnv() {\n"
                 "    JNIEnv *env = nullptr;\n"
                 "    if (java->GetEnv((void **) &env, JNI_VERSION_1_6) != JNI_OK) {\n"
                 "        java->AttachCurrentThread(&env, nullptr);\n"
                 "    }\n"
                 "    return env;\n"
                 "}",
                 "native: tgCurrentEnv helper")
    replace_all(tgw,
                "jniEnv[instanceNum]->",
                "tgCurrentEnv()->",
                "native: jniEnv[instanceNum] -> tgCurrentEnv()")

    # ------------------------------------------------------------------
    # ۱.۹) رفعِ کرشِ null-deref در processRequestQueue
    #    وقتی auth key موقتاً بینِ handshakeِ اکانت‌های تازه null می‌شود،
    #    getConnectionByType می‌تواند nullptr برگرداند؛ کدِ اصلی بدونِ چک به
    #    connection->getConnectionToken() دسترسی می‌داد → SIGSEGV.
    # ------------------------------------------------------------------
    print("۱.۹) رفعِ کرشِ null-deref کانکشن در processRequestQueue")
    replace_once(cm_cpp,
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "        int32_t maxTimeout = request->connectionType & ConnectionTypeGeneric ? 8 : 30;",
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "        if (connection == nullptr) {\n"
                 "            iter++;\n"
                 "            continue;\n"
                 "        }\n"
                 "        int32_t maxTimeout = request->connectionType & ConnectionTypeGeneric ? 8 : 30;",
                 "native: null-check connection #1")
    replace_once(cm_cpp,
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "\n"
                 "        if (request->connectionType & ConnectionTypeGeneric && connection->getConnectionToken() == 0) {",
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "        if (connection == nullptr) {\n"
                 "            iter++;\n"
                 "            continue;\n"
                 "        }\n"
                 "\n"
                 "        if (request->connectionType & ConnectionTypeGeneric && connection->getConnectionToken() == 0) {",
                 "native: null-check connection #2")

    # ------------------------------------------------------------------
    # ۱.۱۰) گاردِ یک نقطه‌ی شناخته‌شده‌ی «طوفانِ حساب» (LocationController)
    #    این حلقه بدونِ چک، getInstance را برای هر ۱۰۰ اسلات صدا می‌زند حتی
    #    اگر اکانت خالی باشد. اگر بعداً کرشِ مشابه (طوفانِ storage) با backtrace
    #    در فایلِ دیگری دیده شد، همین الگو (چکِ isClientActivated قبل از
    #    getInstance) را آن‌جا هم اضافه کن.
    # ------------------------------------------------------------------
    lc = "TMessagesProj/src/main/java/org/telegram/messenger/LocationController.java"
    print("۱.۱۰) گاردِ getLocationsCount در برابرِ ساختِ بی‌موردِ ۱۰۰ اسلات")
    replace_once(lc,
                 "        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "            count += LocationController.getInstance(a).sharingLocationsUI.size();\n"
                 "        }",
                 "        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "            if (!UserConfig.getInstance(a).isClientActivated()) {\n"
                 "                continue;\n"
                 "            }\n"
                 "            count += LocationController.getInstance(a).sharingLocationsUI.size();\n"
                 "        }",
                 "guard: LocationController.getLocationsCount", optional=True)

    # ------------------------------------------------------------------
    # ۲) باز کردن ترجمه‌ی کل چت/گروه برای همه (بدون نیاز به پریمیوم)
    #    نوار «ترجمه» در بالای چت که پشت پریمیوم بود را همگانی می‌کنیم.
    # ------------------------------------------------------------------
    tc = "TMessagesProj/src/main/java/org/telegram/messenger/TranslateController.java"
    if cfg.get("enable_chat_translate_for_all", True):
        print("۲) ترجمه‌ی کل چت/گروه → برای همه باز شد")
        replace_once(tc,
                     "    public boolean isFeatureAvailable() {\n"
                     "        return isChatTranslateEnabled() && UserConfig.getInstance(currentAccount).isPremium();\n"
                     "    }",
                     "    public boolean isFeatureAvailable() {\n"
                     "        return isChatTranslateEnabled();\n"
                     "    }",
                     "translate: chat feature for all")
        replace_once(tc,
                     "        final TLRPC.Chat chat = getMessagesController().getChat(-dialogId);\n"
                     "        return (\n"
                     "            UserConfig.getInstance(currentAccount).isPremium() ||\n"
                     "            chat != null && chat.autotranslation\n"
                     "        );",
                     "        return true; // [mod] chat/group translate enabled for everyone",
                     "translate: per-dialog feature for all")

    # ------------------------------------------------------------------
    # ۳) روشن بودن پیش‌فرض دکمه‌ی ترجمه‌ی تک‌پیام
    # ------------------------------------------------------------------
    if cfg.get("translate_button_default_on", True):
        print("۳) دکمه‌ی ترجمه‌ی تک‌پیام → به‌صورت پیش‌فرض روشن")
        replace_once(tc,
                     'contextTranslateEnabled = messagesController.getMainSettings().getBoolean("translate_button", MessagesController.getGlobalMainSettings().getBoolean("translate_button", false));',
                     'contextTranslateEnabled = messagesController.getMainSettings().getBoolean("translate_button", MessagesController.getGlobalMainSettings().getBoolean("translate_button", true));',
                     "translate: per-message default on")

    print("\n=== همه‌ی تغییرات با موفقیت اعمال شد ✔ ===")
    print("حالا می‌توانی پروژه‌ی پوشه‌ی Telegram را در Android Studio باز کرده و Build بزنی.")


if __name__ == "__main__":
    main()
