#!/usr/bin/env python3
# -*- coding: ascii -*-
# ai_debug.py
# -----------
# Diagnostic: makes AI translation failures VISIBLE instead of failing
# silently. On any failure it:
#   * includes the server's response body in the error,
#   * logs it to Logcat (tag "translate"), and
#   * shows a Toast on screen with the exact reason (e.g. "AI HTTP 401",
#     "AI HTTP 404: No endpoints found", "AI HTTP 402 ... credits").
# Use this to find out WHY a model doesn't work, then tell me the message.
#
# Patches TranslateAlert2.aiTranslate (added by ai_translate.py). Safe to run
# multiple times (idempotent). Creates one-time .bak16 backups.
# Java-only change: a NORMAL Gradle build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
TA2_REL = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram",
                       "ui", "Components", "TranslateAlert2.java")

applied = 0
warnings = []

THROW_OLD = '                        throw new Exception("AI HTTP " + status);\n'
THROW_NEW = '                        throw new Exception("AI HTTP " + status + ": " + sb);\n'

CATCH_OLD = (
    "                } catch (Exception e) {\n"
    "                    AndroidUtilities.runOnUIThread(() -> {\n"
    "                        if (done != null) done.run(null, false);\n"
    "                    });\n"
    "                } finally {\n"
)
CATCH_NEW = (
    "                } catch (Exception e) {\n"
    "                    Log.e(\"translate\", \"YasTel AI translate failed\", e);\n"
    "                    final String _err = e.getMessage();\n"
    "                    AndroidUtilities.runOnUIThread(() -> {\n"
    "                        try { android.widget.Toast.makeText(org.telegram.messenger.ApplicationLoader.applicationContext, \"AI translate: \" + _err, android.widget.Toast.LENGTH_LONG).show(); } catch (Exception ignore) {}\n"
    "                        if (done != null) done.run(null, false);\n"
    "                    });\n"
    "                } finally {\n"
)


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
    if not os.path.isfile(path + ".bak16"):
        with open(path + ".bak16", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def do(text, old, new, needle, label):
    global applied
    if needle in text:
        print("  -- [%s] already applied, skipped" % label)
        return text
    if text.count(old) != 1:
        warnings.append("[%s] anchor found %d times (expected 1)" % (label, text.count(old)))
        print("  !! [%s] anchor not found once, skipped" % label)
        return text
    print("  OK [%s]" % label)
    applied += 1
    return text.replace(old, new, 1)


def main():
    print("=== ai_debug: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    path = os.path.join(root, TA2_REL)
    print("Project root: %s\n" % root)
    text = read(path)
    if "aiTranslate" not in text:
        sys.exit("ERROR: aiTranslate not found. Run ai_translate.py first.")

    print("1) Include server response body in the error")
    text = do(text, THROW_OLD, THROW_NEW, '"AI HTTP " + status + ": " + sb', "error body")
    print("\n2) Log + on-screen Toast on failure")
    text = do(text, CATCH_OLD, CATCH_NEW, "YasTel AI translate failed", "visible error")

    write(path, text)
    print("\n=== RESULT: %d applied, %d warnings ===" % (applied, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Build, then tap-translate one message; a Toast will show")
        print("the exact error. Send me that text.")


if __name__ == "__main__":
    main()
