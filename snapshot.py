#!/usr/bin/env python3
# -*- coding: ascii -*-
# snapshot.py
# -----------
# A tiny "save point" system for the Telegram source, so you can roll back if
# a new build turns out broken.
#
#   snapshot.bat  -> saves the CURRENT source into _yastel_snapshots/<name>.zip
#   restore.bat   -> restores the NEWEST snapshot (or one you pick)
#
# It only saves the files our mods ever touch (all Java, every strings.xml,
# the native jni sources, and the gradle files), so snapshots are small and
# fast. Restoring puts exactly those files back to the saved state, undoing
# any change made after the snapshot.
#
# Usage:
#   python snapshot.py save            # create a snapshot (default)
#   python snapshot.py list            # list snapshots
#   python snapshot.py restore         # restore the newest snapshot
#   python snapshot.py restore <name>  # restore a specific snapshot
#
# ASCII-only, no external tools. Does NOT touch build artifacts.

import os
import sys
import time
import zipfile

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
SNAP_DIR = "_yastel_snapshots"

# Directories (recursive) and single files that our scripts can modify.
SNAP_TREES = [
    os.path.join("TMessagesProj", "src", "main", "java"),
    os.path.join("TMessagesProj", "jni"),
    os.path.join("TMessagesProj", "config"),
]
SNAP_GLOBS_RES = os.path.join("TMessagesProj", "src", "main", "res")  # only strings.xml under here
SNAP_FILES = [
    os.path.join("TMessagesProj", "build.gradle"),
    os.path.join("TMessagesProj_App", "build.gradle"),
    "gradle.properties",
]


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


def collect_files(root):
    files = []
    for tree in SNAP_TREES:
        base = os.path.join(root, tree)
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, fnames in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in fnames:
                files.append(os.path.join(dirpath, fn))
    # only strings.xml under res
    resbase = os.path.join(root, SNAP_GLOBS_RES)
    if os.path.isdir(resbase):
        for name in os.listdir(resbase):
            if name == "values" or name.startswith("values-"):
                p = os.path.join(resbase, name, "strings.xml")
                if os.path.isfile(p):
                    files.append(p)
    for rel in SNAP_FILES:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            files.append(p)
    return files


def app_version(root):
    p = os.path.join(root, "gradle.properties")
    try:
        for line in open(p, "r", encoding="utf-8"):
            if line.startswith("APP_VERSION_NAME="):
                return line.split("=", 1)[1].strip().replace("/", "_").replace(" ", "")
    except Exception:
        pass
    return "unknown"


def do_save(root):
    snapdir = os.path.join(root, SNAP_DIR)
    if not os.path.isdir(snapdir):
        os.makedirs(snapdir)
    name = time.strftime("%Y%m%d_%H%M%S") + "_v" + app_version(root)
    zip_path = os.path.join(snapdir, name + ".zip")
    files = collect_files(root)
    if not files:
        sys.exit("ERROR: no source files found to snapshot.")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, os.path.relpath(f, root))
    size_mb = os.path.getsize(zip_path) / (1024.0 * 1024.0)
    print("  OK saved snapshot: %s.zip  (%d files, %.1f MB)" % (name, len(files), size_mb))
    print("\nTo go back to this exact source later, run restore.bat")


def list_snaps(root):
    snapdir = os.path.join(root, SNAP_DIR)
    if not os.path.isdir(snapdir):
        return []
    snaps = [f for f in os.listdir(snapdir) if f.endswith(".zip")]
    snaps.sort()
    return snaps


def do_list(root):
    snaps = list_snaps(root)
    if not snaps:
        print("  (no snapshots yet -- run snapshot.bat first)")
        return
    print("  snapshots (oldest first):")
    for s in snaps:
        print("    " + s[:-4])
    print("\n  newest: " + snaps[-1][:-4])


def do_restore(root, which):
    snaps = list_snaps(root)
    if not snaps:
        sys.exit("ERROR: no snapshots found. Run snapshot.bat first.")
    target = None
    if which:
        for s in snaps:
            if s[:-4] == which or s == which:
                target = s
                break
        if target is None:
            sys.exit("ERROR: snapshot '%s' not found. Run 'list' to see names." % which)
    else:
        target = snaps[-1]  # newest
    zip_path = os.path.join(root, SNAP_DIR, target)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(root)
    print("  OK restored snapshot: %s" % target[:-4])
    print("\nDone. Now rebuild in Android Studio to get that version back.")


def main():
    print("=== snapshot: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    args = sys.argv[1:]
    cmd = args[0].lower() if args else "save"
    if cmd == "save":
        do_save(root)
    elif cmd == "list":
        do_list(root)
    elif cmd == "restore":
        do_restore(root, args[1] if len(args) > 1 else None)
    else:
        print("Unknown command '%s'. Use: save | list | restore [name]" % cmd)


if __name__ == "__main__":
    main()
