#!/usr/bin/env python3
# -*- coding: ascii -*-
# label_format.py
# ---------------
# Changes the account label format in the management UI:
#   before:  "#1 903 550 5150"   (tag first, spaces inside the number)
#   after:   "9035505150  #1"    (no spaces in the number, tag moved to the
#                                 end, separated by TWO spaces)
# Only touches the getAccountLabel helper in UserConfig.java that was added
# by phone_labels.py (or apply_mods.py). Run phone_labels first if you have
# never applied it.
#
# Safe to run multiple times (idempotent). Creates a one-time .bak8 backup.
# Java-only change: a NORMAL Gradle build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

UC_REL = os.path.join("TMessagesProj", "src", "main", "java",
                      "org", "telegram", "messenger", "UserConfig.java")

applied = 0
skipped = 0
warnings = []


def find_project_root():
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    candidates = []
    for base in (cwd, here):
        if base not in candidates:
            candidates.append(base)
    for base in candidates:
        for direct in (base, os.path.join(base, "Telegram")):
            if os.path.isfile(os.path.join(direct, UC_REL)):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, UC_REL)):
                return root
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if not os.path.isfile(path + ".bak8"):
        with open(path + ".bak8", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def patch(path, old, new, needle, label):
    global applied, skipped
    text = read(path)
    if needle in text:
        print("  -- [%s] already applied, skipped" % label)
        skipped += 1
        return
    count = text.count(old)
    if count != 1:
        warnings.append("[%s] anchor found %d times (expected 1); not patched"
                        % (label, count))
        print("  !! [%s] anchor found %d times, skipped" % (label, count))
        return
    write(path, text.replace(old, new, 1))
    print("  OK [%s]" % label)
    applied += 1


def main():
    print("=== label_format: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    path = os.path.join(root, UC_REL)
    if "getAccountLabel" not in read(path):
        sys.exit("ERROR: getAccountLabel helper not found in UserConfig.java.\n"
                 "Run phone_labels.py first, then run this script again.")

    print("1) Strip spaces inside the local phone number")
    patch(path,
          "                    local = local.trim();\n",
          '                    local = local.replace(" ", "").replace("-", "");\n',
          'local.replace(" ", "")',
          "label format: no spaces in number")

    print("\n2) Move the #N tag to the end (two spaces before it)")
    patch(path,
          '        return "#" + getAccountTagNumber(account) + " " + label;',
          '        return label + "  #" + getAccountTagNumber(account);',
          'return label + "  #" + getAccountTagNumber(account);',
          "label format: tag at end")

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Java-only change: do a NORMAL build in Android Studio,")
        print("then reinstall the app.")


if __name__ == "__main__":
    main()
