#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_crash.py
------------
دکمه‌ی «فشار بده تمام» برای رفع کرش باز شدن برنامه.

این اسکریپت خودش فایل ApplicationLoader.java را پیدا می‌کند و سه گارد
«راه‌اندازی تنبل اکانت» را اعمال می‌کند تا دیگر همه‌ی اسلات‌های اکانت
هم‌زمان ساخته نشوند (علت کرش JNI / SIGABRT).

ویژگی‌ها:
  - حساس به فاصله‌گذاری نیست (با regex و حفظ تورفتگی هر خط).
  - idempotent است: اگر دوباره اجرا شود، تغییر تکراری اعمال نمی‌کند.
  - پیش از تغییر، یک نسخه‌ی پشتیبان (.bak) می‌سازد.

One-click fixer: locates ApplicationLoader.java and inserts the three
lazy-init account guards (whitespace-tolerant, idempotent, makes a .bak).
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GUARD = "if (a != 0 && !UserConfig.getInstance(a).isClientActivated()) continue;"
GUARD_MARK = "isClientActivated()) continue;"


def find_app_loader():
    """پیدا کردن ApplicationLoader.java در مسیرهای محتمل یا با جستجو."""
    rel = os.path.join("TMessagesProj", "src", "main", "java", "org",
                       "telegram", "messenger", "ApplicationLoader.java")
    candidates = [
        os.path.join(ROOT, "Telegram", rel),
        os.path.join(ROOT, rel),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # جستجوی کلی از ریشه
    for base, _dirs, files in os.walk(ROOT):
        if "ApplicationLoader.java" in files:
            norm = base.replace("\\", "/")
            if norm.endswith("org/telegram/messenger"):
                return os.path.join(base, "ApplicationLoader.java")
    return None


def apply_guard(lines, anchor, where, label):
    """درج گارد قبل/بعد از خطی که شامل anchor است.
    where = 'before' یا 'after'. خروجی: (تغییریافته؟, پیام)"""
    for i, line in enumerate(lines):
        if anchor in line:
            indent = line[:len(line) - len(line.lstrip())]
            guard_line = indent + GUARD + "\n"
            if where == "before":
                if i > 0 and GUARD_MARK in lines[i - 1]:
                    return False, f"[{label}] از قبل اعمال شده — رد شد"
                lines.insert(i, guard_line)
                return True, f"[{label}] ✔ اعمال شد"
            else:  # after
                if i + 1 < len(lines) and GUARD_MARK in lines[i + 1]:
                    return False, f"[{label}] از قبل اعمال شده — رد شد"
                lines.insert(i + 1, guard_line)
                return True, f"[{label}] ✔ اعمال شد"
    return False, f"[{label}] ! لنگر (anchor) پیدا نشد"


def main():
    print("=== رفع کرش باز شدن (lazy-init اکانت‌ها) ===\n")
    path = find_app_loader()
    if not path:
        print("[خطا] فایل ApplicationLoader.java پیدا نشد.")
        print("      این اسکریپت را در همان پوشه‌ای که setup.bat هست بگذار و اجرا کن.")
        sys.exit(1)

    print("فایل پیدا شد:")
    print("  " + path + "\n")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    original = list(lines)

    # ۱) حلقه‌ی ContactsController/DownloadController (محل دقیق کرش)
    changed1, msg1 = apply_guard(
        lines, "ContactsController.getInstance(a).checkAppAccount();",
        "before", "حلقه contacts/download")
    print("  " + msg1)

    # ۲) حلقه‌ی اصلی postInitApplication (بعد از loadConfig)
    changed2, msg2 = apply_guard(
        lines, "UserConfig.getInstance(a).loadConfig();",
        "after", "حلقه اصلی")
    print("  " + msg2)

    # ۳) حلقه‌ی گیرنده‌ی تغییر شبکه
    changed3, msg3 = apply_guard(
        lines, "ConnectionsManager.getInstance(a).checkConnection();",
        "before", "حلقه شبکه")
    print("  " + msg3)

    if not (changed1 or changed2 or changed3):
        print("\nهیچ تغییر جدیدی لازم نبود (همه از قبل اعمال شده بود).")
        print("اگر باز کرش می‌کند، پیام را برای من بفرست.")
        return

    # پشتیبان و ذخیره
    bak = path + ".bak"
    if not os.path.isfile(bak):
        with open(bak, "w", encoding="utf-8") as f:
            f.writelines(original)
        print("\nنسخه‌ی پشتیبان ساخته شد: ApplicationLoader.java.bak")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("\n=== تمام ✔ ===")
    print("حالا دوباره در Android Studio پروژه را Build کن و روی گوشی نصب کن.")
    print("(دستور بیلد: gradle :TMessagesProj_App:assembleAfatDebug )")


if __name__ == "__main__":
    main()
