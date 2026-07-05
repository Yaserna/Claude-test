#!/usr/bin/env python3
# -*- coding: ascii -*-
# fix_translate_source.py
# -----------------------
# Fixes "translation often does nothing" (Google returns 400 Bad Request).
#
# Root cause: when the source language cannot be determined (ML Kit language
# detection is blocked on the device, so the language comes back as "und"),
# the app sends sl=und to Google Translate. Google rejects sl=und (and an
# empty sl) with HTTP 400, so the translation silently fails.
#
# Fix: in TranslateAlert2.alternativeTranslateInternal, map an unknown source
# language (null / "" / "und" / "undefined") to "auto" so Google auto-detects
# the language. Verified against the live endpoint: sl=und -> 400, sl=auto ->
# 200. Covers both whole-chat and single-bubble translation (same code path).
#
# Safe to run multiple times (idempotent). Creates one-time .bak11 backups.
# Java-only change: a NORMAL Gradle build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

TA2_REL = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram",
                       "ui", "Components", "TranslateAlert2.java")

OLD = 'uri += "e?client=gtx&sl=" + Uri.encode(fromLng) + "&tl=" + Uri.encode(toLng)'
NEW = ('uri += "e?client=gtx&sl=" + Uri.encode((fromLng == null || fromLng.length() == 0 '
       '|| "und".equals(fromLng) || "undefined".equals(fromLng)) ? "auto" : fromLng) '
       '+ "&tl=" + Uri.encode(toLng)')
NEEDLE = '? "auto" : fromLng'


def find_project_root():
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    candidates = []
    for base in (cwd, here):
        if base not in candidates:
            candidates.append(base)
    for base in candidates:
        for direct in (base, os.path.join(base, "Telegram")):
            if os.path.isfile(os.path.join(direct, TA2_REL)):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, TA2_REL)):
                return root
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if not os.path.isfile(path + ".bak11"):
        with open(path + ".bak11", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    print("=== fix_translate_source: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    path = os.path.join(root, TA2_REL)
    print("Project root: %s\n" % root)

    text = read(path)
    if NEEDLE in text:
        print("  -- already applied, skipped")
        print("\nNothing to do.")
        return
    count = text.count(OLD)
    if count != 1:
        sys.exit("ERROR: expected the translate URL line exactly once, found %d "
                 "(source differs from the pinned version)." % count)
    write(path, text.replace(OLD, NEW, 1))
    print("  OK  unknown source language -> 'auto' (Google auto-detect)")
    print("\nDone. Java-only change: do a NORMAL build in Android Studio,")
    print("then reinstall the app.")


if __name__ == "__main__":
    main()
