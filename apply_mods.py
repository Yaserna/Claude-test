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
    count = text.count(old)
    if count == 0:
        if new in text:
            print(f"  - [{label}] از قبل اعمال شده، رد شد.")
            return
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

    # حلقه‌ی اصلی postInitApplication: قبل از loadConfig/MessagesController/...
    replace_once(al,
                 "            UserConfig.getInstance(a).loadConfig();",
                 "            " + guard + "\n"
                 "            UserConfig.getInstance(a).loadConfig();",
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
                 "                ConnectionsManager.getInstance(a).checkConnection();",
                 "                " + guard + "\n"
                 "                ConnectionsManager.getInstance(a).checkConnection();",
                 "lazy-init: network receiver loop", optional=True)

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
