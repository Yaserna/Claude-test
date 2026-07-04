#!/usr/bin/env python3
# -*- coding: ascii -*-
# rebrand.py
# ----------
# Renames the app to "YasTel" and switches the package id to the OFFICIAL
# Telegram package so the build installs over / replaces the official app.
#
# What it changes:
#   1) TMessagesProj/src/main/res/values*/strings.xml
#        <string name="AppName">...</string>      -> YasTel
#        <string name="AppNameBeta">...</string>  -> YasTel
#      (the afat-debug build shows AppNameBeta as the launcher name, so both
#       are set to keep the name correct in every variant/locale)
#   2) TMessagesProj_App/build.gradle
#        removes  applicationIdSuffix ".beta"  from the debug build type.
#      APP_PACKAGE is already "org.telegram.messenger", so with the ".beta"
#      suffix gone the afat-debug package becomes exactly the official one.
#
# NOTE (important): a package that matches the official app can only be
# installed if the official Telegram is UNINSTALLED first (Android refuses to
# replace an app that was signed with a different key). Uninstall the Play
# Store Telegram, then install this build.
#
# Safe to run multiple times (idempotent). Creates one-time .bak7 backups.
# Resource + gradle change only: a NORMAL Gradle build is enough (no native
# recompile). A full uninstall + reinstall is required because the package id
# changed.

import os
import re
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

APP_NAME = "YasTel"

applied = 0
skipped = 0
warnings = []


def find_project_root():
    probe = os.path.join("TMessagesProj", "src", "main", "res", "values", "strings.xml")
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
    if not os.path.isfile(path + ".bak7"):
        with open(path + ".bak7", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def find_strings_files(root):
    res = os.path.join(root, "TMessagesProj", "src", "main", "res")
    found = []
    if not os.path.isdir(res):
        return found
    for name in sorted(os.listdir(res)):
        if name == "values" or name.startswith("values-"):
            p = os.path.join(res, name, "strings.xml")
            if os.path.isfile(p):
                found.append(p)
    return found


def patch_app_name(root):
    global applied, skipped
    files = find_strings_files(root)
    if not files:
        warnings.append("no strings.xml found under TMessagesProj/src/main/res")
        print("  !! strings.xml NOT FOUND")
        return
    for path in files:
        text = read(path)
        new = text
        for key in ("AppName", "AppNameBeta"):
            new = re.sub(r'(<string name="%s">).*?(</string>)' % key,
                         r'\g<1>' + APP_NAME + r'\g<2>', new, count=1, flags=re.S)
        rel = os.path.relpath(path, root)
        if new == text:
            # nothing to change here (either no AppName in this locale, or
            # already renamed)
            continue
        write(path, new)
        print("  OK  app name -> %s  (%s)" % (APP_NAME, rel))
        applied += 1


def patch_package(root):
    global applied, skipped
    path = os.path.join(root, "TMessagesProj_App", "build.gradle")
    if not os.path.isfile(path):
        warnings.append("TMessagesProj_App/build.gradle not found")
        print("  !! build.gradle NOT FOUND")
        return
    text = read(path)
    if "[mod] YasTel" in text:
        print("  --  package already official, skipped")
        skipped += 1
        return
    old = 'applicationIdSuffix ".beta"'
    count = text.count(old)
    if count == 0:
        warnings.append("debug applicationIdSuffix \".beta\" not found in "
                        "TMessagesProj_App/build.gradle (source differs)")
        print("  !!  '.beta' suffix anchor not found, skipped")
        return
    if count > 1:
        warnings.append("applicationIdSuffix \".beta\" found %d times; not patched"
                        % count)
        print("  !!  '.beta' suffix found %d times, skipped" % count)
        return
    new = ('// applicationIdSuffix ".beta" // [mod] YasTel: use official '
           'package to install over official Telegram')
    write(path, text.replace(old, new, 1))
    print("  OK  package -> org.telegram.messenger (official)")
    applied += 1


def main():
    print("=== rebrand: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    print("1) App name -> %s" % APP_NAME)
    patch_app_name(root)

    print("\n2) Package -> official Telegram (org.telegram.messenger)")
    patch_package(root)

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Do a NORMAL build in Android Studio.")
        print("IMPORTANT: uninstall the official Telegram first, then install this")
        print("build (the package id now matches the official app).")


if __name__ == "__main__":
    main()
