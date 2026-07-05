#!/usr/bin/env python3
# -*- coding: ascii -*-
# profile_name_tag.py
# -------------------
# In TWO places only -- your own profile page header and the Settings screen
# header -- show the account's REAL NAME with the #N login-order tag after it
# (two spaces before the tag), instead of the phone number:
#   before:  "9035505150  #1"
#   after:   "Ali Rezaei  #1"
# All other management places (account switcher, drawer, send-as sheet,
# accounts list inside Settings) keep showing the phone-number label.
#
# Handles sources in any earlier patch state (phone label / number tag / raw).
# Safe to run multiple times (idempotent). Creates one-time .bak10 backups.
# Java-only change: a NORMAL Gradle build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

JAVA_BASE = os.path.join("TMessagesProj", "src", "main", "java")
FILES = {
    "ProfileActivity":  os.path.join("org", "telegram", "ui", "ProfileActivity.java"),
    "SettingsActivity": os.path.join("org", "telegram", "ui", "SettingsActivity.java"),
}

applied = 0
skipped = 0
warnings = []


def find_project_root():
    probe = os.path.join(JAVA_BASE, FILES["SettingsActivity"])
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    candidates = []
    for base in (cwd, here):
        if base not in candidates:
            candidates.append(base)
    for base in candidates:
        for direct in (base, os.path.join(base, "Telegram")):
            if os.path.isfile(os.path.join(direct, probe)):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, probe)):
                return root
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if not os.path.isfile(path + ".bak10"):
        with open(path + ".bak10", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def patch_first(root, file_key, pairs, needle, label):
    """If `needle` is already present the patch is done; otherwise the first
    (old, new) pair whose old text occurs exactly once is applied."""
    global applied, skipped
    path = os.path.join(root, JAVA_BASE, FILES[file_key])
    if not os.path.isfile(path):
        warnings.append("[%s] file not found: %s" % (label, path))
        print("  !! [%s] FILE NOT FOUND" % label)
        return
    text = read(path)
    if needle in text:
        print("  -- [%s] already applied, skipped" % label)
        skipped += 1
        return
    for old, new in pairs:
        count = text.count(old)
        if count == 1:
            write(path, text.replace(old, new, 1))
            print("  OK [%s]" % label)
            applied += 1
            return
        if count > 1:
            warnings.append("[%s] anchor found %d times in %s; patch not applied"
                            % (label, count, FILES[file_key]))
            print("  !! [%s] anchor found %d times, skipped" % (label, count))
            return
    warnings.append("[%s] no known anchor found in %s (source differs; "
                    "patch not applied)" % (label, FILES[file_key]))
    print("  !! [%s] anchor NOT FOUND, skipped" % label)


PROFILE_NAME_TAG = '            if (user.id == getUserConfig().getClientUserId()) { newString = newString.toString() + "  #" + UserConfig.getAccountTagNumber(currentAccount); } // [mod] account name tag (own profile)'
SETTINGS_NAME_TAG = '        titleView.setText(UserObject.getUserName(user) + "  #" + UserConfig.getAccountTagNumber(currentAccount)); // [mod] account name tag (settings header)'


def main():
    print("=== profile_name_tag: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    print("1) Own profile header -> real name + #N tag")
    patch_first(root, "ProfileActivity",
                [('            if (user.id == getUserConfig().getClientUserId()) { newString = UserConfig.getAccountLabel(currentAccount, newString.toString()); } // [mod] account phone label (own profile)',
                  PROFILE_NAME_TAG),
                 ('            if (user.id == getUserConfig().getClientUserId()) { newString = "#" + UserConfig.getAccountTagNumber(currentAccount) + " " + newString; } // [mod] account number tag (own profile)',
                  PROFILE_NAME_TAG),
                 ("            CharSequence newString = UserObject.getUserName(user);\n            String newString2;",
                  "            CharSequence newString = UserObject.getUserName(user);\n"
                  + PROFILE_NAME_TAG + "\n"
                  "            String newString2;")],
                "account name tag (own profile)",
                "name tag: own profile header")

    print("\n2) Settings header -> real name + #N tag")
    patch_first(root, "SettingsActivity",
                [('        titleView.setText(UserConfig.getAccountLabel(currentAccount, UserObject.getUserName(user))); // [mod] account phone label (settings header)',
                  SETTINGS_NAME_TAG),
                 ('        titleView.setText("#" + UserConfig.getAccountTagNumber(currentAccount) + " " + UserObject.getUserName(user)); // [mod] account number tag (settings header)',
                  SETTINGS_NAME_TAG),
                 ('        titleView.setText(UserObject.getUserName(user));',
                  SETTINGS_NAME_TAG)],
                "account name tag (settings header)",
                "name tag: settings header")

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Java-only change: do a NORMAL build in Android Studio,")
        print("then reinstall the app.")


if __name__ == "__main__":
    main()
