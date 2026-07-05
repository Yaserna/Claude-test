#!/usr/bin/env python3
# -*- coding: ascii -*-
# bump_version.py
# ---------------
# Adds/increments a MICRO version after Telegram's own version so every new
# build is recognizable in Settings:
#   12.8.1  ->  12.8.1.1  ->  12.8.1.2  ->  ...
# Run this ONCE BEFORE EACH BUILD (every run bumps the number by one -- this
# script is intentionally NOT idempotent). The version shown at the bottom of
# the app's Settings page comes straight from APP_VERSION_NAME in
# gradle.properties, so a normal Gradle build is enough.

import os
import re
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}


def find_project_root():
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    candidates = []
    for base in (cwd, here):
        if base not in candidates:
            candidates.append(base)
    for base in candidates:
        for direct in (base, os.path.join(base, "Telegram")):
            if os.path.isfile(os.path.join(direct, "gradle.properties")) and \
               os.path.isdir(os.path.join(direct, "TMessagesProj")):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, "gradle.properties")) and \
               os.path.isdir(os.path.join(root, "TMessagesProj")):
                return root
    return None


def main():
    print("=== bump_version: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    path = os.path.join(root, "gradle.properties")
    print("Project root: %s\n" % root)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    m = re.search(r"^APP_VERSION_NAME=(.+)$", text, flags=re.M)
    if not m:
        sys.exit("ERROR: APP_VERSION_NAME not found in gradle.properties")
    old = m.group(1).strip()

    parts = old.split(".")
    if len(parts) >= 4 and parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]) + 1)
        new = ".".join(parts)
    else:
        new = old + ".1"

    text = text.replace("APP_VERSION_NAME=" + old, "APP_VERSION_NAME=" + new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    print("  version: %s  ->  %s" % (old, new))
    print("\nDone. Build normally in Android Studio; Settings will show v%s." % new)
    print("Run this script again before the NEXT build to get the next number.")


if __name__ == "__main__":
    main()
