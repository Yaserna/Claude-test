#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_crash.py
------------
One-click fixer for the app startup crash.

This script locates ApplicationLoader.java itself and applies the three
"lazy account init" guards so that not all account slots are built at once
(the cause of the JNI / SIGABRT crash).

Features:
  - whitespace-tolerant (uses per-line indentation).
  - idempotent: re-running does not apply a duplicate change.
  - makes a backup (.bak) before editing.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GUARD = "if (a != 0 && !UserConfig.getInstance(a).isClientActivated()) continue;"
GUARD_MARK = "isClientActivated()) continue;"


def find_app_loader():
    """Find ApplicationLoader.java in likely paths or by walking the tree."""
    rel = os.path.join("TMessagesProj", "src", "main", "java", "org",
                       "telegram", "messenger", "ApplicationLoader.java")
    candidates = [
        os.path.join(ROOT, "Telegram", rel),
        os.path.join(ROOT, rel),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # general walk from the root
    for base, _dirs, files in os.walk(ROOT):
        if "ApplicationLoader.java" in files:
            norm = base.replace("\\", "/")
            if norm.endswith("org/telegram/messenger"):
                return os.path.join(base, "ApplicationLoader.java")
    return None


def apply_guard(lines, anchor, where, label):
    """Insert the guard before/after the line containing anchor.
    where = 'before' or 'after'. Returns (changed?, message)."""
    for i, line in enumerate(lines):
        if anchor in line:
            indent = line[:len(line) - len(line.lstrip())]
            guard_line = indent + GUARD + "\n"
            if where == "before":
                if i > 0 and GUARD_MARK in lines[i - 1]:
                    return False, f"[{label}] already applied -- skipped"
                lines.insert(i, guard_line)
                return True, f"[{label}] OK applied"
            else:  # after
                if i + 1 < len(lines) and GUARD_MARK in lines[i + 1]:
                    return False, f"[{label}] already applied -- skipped"
                lines.insert(i + 1, guard_line)
                return True, f"[{label}] OK applied"
    return False, f"[{label}] ! anchor not found"


def main():
    print("=== Startup crash fix (lazy account init) ===\n")
    path = find_app_loader()
    if not path:
        print("[ERROR] ApplicationLoader.java not found.")
        print("        Put this script in the same folder as setup.bat and run it.")
        sys.exit(1)

    print("File found:")
    print("  " + path + "\n")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    original = list(lines)

    # 1) ContactsController/DownloadController loop (exact crash site)
    changed1, msg1 = apply_guard(
        lines, "ContactsController.getInstance(a).checkAppAccount();",
        "before", "contacts/download loop")
    print("  " + msg1)

    # 2) Main postInitApplication loop (after loadConfig)
    changed2, msg2 = apply_guard(
        lines, "UserConfig.getInstance(a).loadConfig();",
        "after", "main loop")
    print("  " + msg2)

    # 3) Network-change receiver loop
    changed3, msg3 = apply_guard(
        lines, "ConnectionsManager.getInstance(a).checkConnection();",
        "before", "network loop")
    print("  " + msg3)

    if not (changed1 or changed2 or changed3):
        print("\nNo new change was needed (everything already applied).")
        print("If it still crashes, send me the log.")
        return

    # backup and save
    bak = path + ".bak"
    if not os.path.isfile(bak):
        with open(bak, "w", encoding="utf-8") as f:
            f.writelines(original)
        print("\nBackup created: ApplicationLoader.java.bak")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("\n=== Done ===")
    print("Now Build the project in Android Studio again and install on the phone.")
    print("(build task: gradle :TMessagesProj_App:assembleAfatDebug )")


if __name__ == "__main__":
    main()
