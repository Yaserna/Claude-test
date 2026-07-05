#!/usr/bin/env python3
# -*- coding: ascii -*-
# sleep_accounts.py
# -----------------
# Makes every logged-in account FULLY SLEEP (no connection, no data sent or
# received, no background notifications) except the one you currently have
# open in the app (UserConfig.selectedAccount). Switching to an account wakes
# it; leaving it puts it back to sleep.
#
# How it works (Java only, no native recompile):
#   * ConnectionsManager.checkConnection() is the single place that tells the
#     native layer whether the network is available. We gate it so that a
#     non-selected account reports "no network" and gets paused -> it never
#     connects and drops any existing connection.
#   * ConnectionsManager.init(...) passes hasNetwork=false for a non-selected
#     account, so it stays offline from startup.
#   * LaunchActivity.switchToAccount(...) re-applies the sleep states right
#     after selectedAccount changes, so the new account wakes and the old one
#     sleeps.
#
# Trade-off (intended): a sleeping account delivers NO notifications until you
# open it. To turn the whole feature off, set sleepInactiveAccounts = false.
#
# Safe to run multiple times (idempotent). Creates one-time .bak9 backups.
# Java-only change: a NORMAL Gradle build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

JAVA_BASE = os.path.join("TMessagesProj", "src", "main", "java")
FILES = {
    "ConnectionsManager": os.path.join("org", "telegram", "tgnet", "ConnectionsManager.java"),
    "LaunchActivity":     os.path.join("org", "telegram", "ui", "LaunchActivity.java"),
}

applied = 0
skipped = 0
warnings = []


def find_project_root():
    probe = os.path.join(JAVA_BASE, FILES["ConnectionsManager"])
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
    if not os.path.isfile(path + ".bak9"):
        with open(path + ".bak9", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def patch(root, file_key, old, new, needle, label):
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
    count = text.count(old)
    if count != 1:
        warnings.append("[%s] anchor found %d times (expected 1) in %s"
                        % (label, count, FILES[file_key]))
        print("  !! [%s] anchor found %d times, skipped" % (label, count))
        return
    write(path, text.replace(old, new, 1))
    print("  OK [%s]" % label)
    applied += 1


HELPERS = (
    "    // [mod] sleep-inactive-accounts: only the selected (currently open)\n"
    "    // account keeps a live connection; every other logged-in account is put\n"
    "    // fully to sleep -- no connection, no data in or out, no notifications --\n"
    "    // until you switch to it. Set this to false to disable the feature.\n"
    "    public static volatile boolean sleepInactiveAccounts = true;\n"
    "\n"
    "    public static boolean isAccountAwake(int account) {\n"
    "        if (!sleepInactiveAccounts || account < 0 || account == UserConfig.selectedAccount) {\n"
    "            return true;\n"
    "        }\n"
    "        return !UserConfig.getInstance(account).isClientActivated(); // logging-in accounts stay awake\n"
    "    }\n"
    "\n"
    "    public static void applyAccountSleepStates() {\n"
    "        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
    "            if (UserConfig.getInstance(a).isClientActivated()) {\n"
    "                getInstance(a).checkConnection();\n"
    "            }\n"
    "        }\n"
    "    }\n"
    "\n"
)


def main():
    print("=== sleep_accounts: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    print("0) Hotfix older sleep helper (keep logging-in accounts awake)")
    cm_path = os.path.join(root, JAVA_BASE, FILES["ConnectionsManager"])
    if os.path.isfile(cm_path) and "isAccountAwake" in read(cm_path):
        patch(root, "ConnectionsManager",
              "        return !sleepInactiveAccounts || account < 0 || account == UserConfig.selectedAccount;\n",
              "        if (!sleepInactiveAccounts || account < 0 || account == UserConfig.selectedAccount) {\n"
              "            return true;\n"
              "        }\n"
              "        return !UserConfig.getInstance(account).isClientActivated(); // logging-in accounts stay awake\n",
              "isClientActivated(); // logging-in accounts stay awake",
              "hotfix: login-aware isAccountAwake")
    else:
        print("  -- no older helper found, nothing to fix")

    print("\n1) Static helpers in ConnectionsManager")
    patch(root, "ConnectionsManager",
          "    public static void setLangCode(String langCode) {",
          HELPERS + "    public static void setLangCode(String langCode) {",
          "applyAccountSleepStates",
          "helper: isAccountAwake / applyAccountSleepStates")

    print("\n2) Gate checkConnection() for sleeping accounts")
    patch(root, "ConnectionsManager",
          "        native_setIpStrategy(currentAccount, selectedStrategy);\n"
          "        native_setNetworkAvailable(currentAccount, ApplicationLoader.isNetworkOnline(), ApplicationLoader.getCurrentNetworkType(), ApplicationLoader.isConnectionSlow());\n"
          "    }",
          "        native_setIpStrategy(currentAccount, selectedStrategy);\n"
          "        if (!isAccountAwake(currentAccount)) { // [mod] sleep inactive accounts\n"
          "            native_setNetworkAvailable(currentAccount, false, ApplicationLoader.getCurrentNetworkType(), ApplicationLoader.isConnectionSlow());\n"
          "            native_pauseNetwork(currentAccount);\n"
          "            return;\n"
          "        }\n"
          "        native_setNetworkAvailable(currentAccount, ApplicationLoader.isNetworkOnline(), ApplicationLoader.getCurrentNetworkType(), ApplicationLoader.isConnectionSlow());\n"
          "    }",
          "if (!isAccountAwake(currentAccount)) { // [mod] sleep inactive accounts",
          "gate: checkConnection")

    print("\n3) Keep a sleeping account offline from startup (init)")
    patch(root, "ConnectionsManager",
          "enablePushConnection, ApplicationLoader.isNetworkOnline(), ApplicationLoader.getCurrentNetworkType(), SharedConfig.measureDevicePerformanceClass());",
          "enablePushConnection, isAccountAwake(currentAccount) && ApplicationLoader.isNetworkOnline(), ApplicationLoader.getCurrentNetworkType(), SharedConfig.measureDevicePerformanceClass());",
          "isAccountAwake(currentAccount) && ApplicationLoader.isNetworkOnline()",
          "gate: init hasNetwork")

    print("\n4) Re-apply sleep states on account switch (LaunchActivity)")
    patch(root, "LaunchActivity",
          "        UserConfig.selectedAccount = account;\n"
          "        UserConfig.getInstance(0).saveConfig(false);",
          "        UserConfig.selectedAccount = account;\n"
          "        UserConfig.getInstance(0).saveConfig(false);\n"
          "        ConnectionsManager.applyAccountSleepStates(); // [mod] sleep inactive accounts",
          "ConnectionsManager.applyAccountSleepStates(); // [mod] sleep inactive accounts",
          "hook: switchToAccount")

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Java-only change: do a NORMAL build in Android Studio,")
        print("then reinstall the app.")


if __name__ == "__main__":
    main()
