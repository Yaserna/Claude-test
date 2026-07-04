#!/usr/bin/env python3
# -*- coding: ascii -*-
# update.py
# ---------
# Keeps the CORE (official Telegram source) up to date while re-applying our
# SHELL (all customizations) on top, using git's 3-way merge.
#
# How it works:
#   1) find the local Telegram git repo (the folder cloned by setup).
#   2) save whatever is currently applied to  pre_update_local_changes.patch
#      (so nothing is ever lost -- you can always get the old state back).
#   3) pick the target Telegram version:
#        update_target = "pinned"  -> the upstream_commit from build_config.json
#        update_target = "latest"  -> the newest official release tag
#   4) fetch it, hard-reset the source onto it (this updates the CORE).
#   5) apply customizations.patch with  git apply --3way  (this re-applies the
#      SHELL). git merges around upstream changes automatically; only the spots
#      upstream really rewrote come out as conflicts.
#   6) write update_report.txt: what applied cleanly and what conflicted.
#
# If there are conflicts, send update_report.txt (and the listed files) back and
# they get fixed in the patch quickly, then run this again.
#
# ASCII only. Safe to re-run. Requires git and python3.

import json
import os
import re
import subprocess
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.join(HERE, "customizations.patch")
REPORT = os.path.join(HERE, "update_report.txt")
PRE = os.path.join(HERE, "pre_update_local_changes.patch")


def load_config():
    with open(os.path.join(HERE, "build_config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    if check and r.returncode != 0:
        sys.exit("[ERROR] git %s failed:\n%s" % (" ".join(args), r.stdout))
    return r


def find_telegram_repo():
    probe = os.path.join("TMessagesProj", "src", "main", "res", "values", "strings.xml")
    for base in (HERE, os.getcwd()):
        for direct in (os.path.join(base, "Telegram"), base):
            if os.path.isfile(os.path.join(direct, probe)) and \
               os.path.isdir(os.path.join(direct, ".git")):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, probe)) and \
               os.path.isdir(os.path.join(root, ".git")):
                return root
    return None


def resolve_latest_head(repo):
    # DrKLO/Telegram no longer tags recent releases (the newest release-* tag is
    # older than our pinned commit), so "latest" means the tip of the default
    # branch (master).
    r = git(repo, "ls-remote", "origin", "HEAD")
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == "HEAD":
            return parts[0]
    return None


def find_files_with(root, marker):
    hits = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    if marker in f.read():
                        hits.append(os.path.relpath(p, root))
            except OSError:
                pass
    return hits


def main():
    cfg = load_config()
    if not os.path.isfile(PATCH):
        sys.exit("[ERROR] customizations.patch not found next to this script.")

    print("=== update: locate Telegram source ===")
    repo = find_telegram_repo()
    if repo is None:
        sys.exit("ERROR: a Telegram git repo was not found. Run setup first so "
                 "the source is cloned, then run this from the same folder.")
    print("Source repo: %s\n" % repo)

    # 1) Back up whatever is currently applied, so nothing is ever lost.
    diff = git(repo, "diff", "--binary").stdout
    with open(PRE, "w", encoding="utf-8") as f:
        f.write(diff)
    print("Saved current applied changes -> %s" % os.path.basename(PRE))

    # 2) Decide the target version.
    target_mode = cfg.get("update_target", "pinned")
    print("\n=== choose target (update_target = %s) ===" % target_mode)
    git(repo, "fetch", "--tags", "origin")
    if target_mode == "latest":
        target = resolve_latest_tag(repo)
        if not target:
            sys.exit("[ERROR] could not find any release-* tag on origin.")
        print("Latest official release: %s" % target)
    else:
        target = cfg.get("upstream_commit")
        if not target:
            sys.exit("[ERROR] upstream_commit missing in build_config.json.")
        print("Pinned target commit: %s" % target)

    # Make sure the target and the patch's base commit are present locally, so
    # 3-way merge can reconstruct the original blobs.
    base = cfg.get("upstream_commit")
    for ref in (target, base):
        if ref:
            git(repo, "fetch", "origin", ref, check=False)

    # 3) Move the CORE onto the target version.
    print("\n=== update core -> %s ===" % target)
    git(repo, "reset", "--hard", target)
    git(repo, "clean", "-fd")

    # 4) Re-apply the SHELL (our customizations) with 3-way merge.
    print("\n=== re-apply customizations (git apply --3way) ===")
    res = git(repo, "apply", "--3way", "--whitespace=nowarn", PATCH, check=False)
    apply_out = res.stdout.strip()
    if apply_out:
        print(apply_out)

    # 5) Detect conflicts.
    conflicted = sorted(set(find_files_with(repo, "<<<<<<<")))
    rejects = []
    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith(".rej"):
                rejects.append(os.path.relpath(os.path.join(dirpath, fn), repo))
    rejects.sort()

    clean = (res.returncode == 0 and not conflicted and not rejects)

    # 6) Report.
    lines = []
    lines.append("=== YasTel update report ===")
    lines.append("target version : %s" % target)
    lines.append("apply exit code: %d" % res.returncode)
    lines.append("")
    if clean:
        lines.append("RESULT: SUCCESS -- all customizations re-applied cleanly.")
        lines.append("Next: build in Android Studio.")
    else:
        lines.append("RESULT: NEEDS ATTENTION -- some spots conflicted.")
        if conflicted:
            lines.append("")
            lines.append("Files with conflict markers (<<<<<<<):")
            for c in conflicted:
                lines.append("  " + c)
        if rejects:
            lines.append("")
            lines.append("Rejected hunks (.rej files):")
            for c in rejects:
                lines.append("  " + c)
        lines.append("")
        lines.append("Send this file (update_report.txt) and the listed files "
                     "to get the patch updated, then run update again.")

    touched_native = any(c.startswith(os.path.join("TMessagesProj", "jni"))
                         for c in conflicted + rejects)
    if touched_native:
        lines.append("")
        lines.append("NOTE: native (C++) code changed. After fixing, DELETE the "
                     "folders TMessagesProj/.cxx and TMessagesProj/build and do a "
                     "full uninstall + rebuild so the native code recompiles.")

    report = "\n".join(lines) + "\n"
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print("\n" + report)
    print("Report written -> %s" % os.path.basename(REPORT))
    sys.exit(0 if clean else 2)


if __name__ == "__main__":
    main()
