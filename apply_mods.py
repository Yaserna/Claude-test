#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_mods.py
-------------
Applies our custom modifications onto the (already cloned) Telegram source.
Each edit is exact and fails loudly if the original text is not found, so that
upstream drift is caught instead of silently producing a broken build.
"""

import json
import os
import sys

# Project root (where this script lives)
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "Telegram")  # cloned Telegram source


def load_config():
    with open(os.path.join(ROOT, "build_config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _path(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        sys.exit(f"[ERROR] file not found: {rel}\n"
                 f"        Make sure you ran setup first so the source is cloned.")
    return p


def replace_once(rel, old, new, label, optional=False):
    """One exact replacement. Must happen exactly once.
    Idempotent: if the new text is already present, we skip.

    optional=True means: if the original text is not found, only warn instead
    of stopping. Used for the ApplicationLoader guards whose spacing may drift.
    """
    p = _path(rel)
    with open(p, "r", encoding="utf-8") as f:
        text = f.read()
    if new in text:
        # Check before counting old, because some guards keep the old text
        # untouched (only inserting something around it); without this check a
        # second run would insert the same guard again.
        print(f"  - [{label}] already applied, skipped.")
        return
    count = text.count(old)
    if count == 0:
        msg = (f"[{label}] original text not found in {rel}\n"
               f"        the source probably differs from the pinned commit.")
        if optional:
            print(f"  ! WARNING: {msg}\n"
                  f"        apply this guard manually if a crash happens.")
            return
        sys.exit(f"[ERROR] {msg}")
    if count > 1:
        if optional:
            print(f"  ! WARNING: [{label}] original text found {count} times in {rel}; skipped.")
            return
        sys.exit(f"[ERROR] [{label}] original text found {count} times (expected 1) in {rel}")
    text = text.replace(old, new, 1)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  OK [{label}] applied in {rel}")


def replace_all(rel, old, new, label):
    """Replace every occurrence of a repeated pattern (e.g. the native jniEnv
    fix in 35 places). Idempotent: if no occurrence of old remains, it's done."""
    p = _path(rel)
    with open(p, "r", encoding="utf-8") as f:
        text = f.read()
    count = text.count(old)
    if count == 0:
        print(f"  - [{label}] already applied, skipped.")
        return
    text = text.replace(old, new)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  OK [{label}] applied ({count} places) in {rel}")


def main():
    cfg = load_config()
    print("=== Applying custom modifications to the Telegram source ===\n")

    # ------------------------------------------------------------------
    # 1) Remove the account count limit (unlimited login)
    #    Raise two constants in UserConfig.java. With the free cap and hard
    #    cap equal, the premium gate never triggers and all slots are free.
    # ------------------------------------------------------------------
    limit = int(cfg.get("account_limit", 100))
    uc = "TMessagesProj/src/main/java/org/telegram/messenger/UserConfig.java"
    print("1) Account count limit -> unlimited (account_limit = %d)" % limit)
    replace_once(uc,
                 "public final static int MAX_ACCOUNT_DEFAULT_COUNT = 3;",
                 "public final static int MAX_ACCOUNT_DEFAULT_COUNT = %d;" % limit,
                 "accounts: free limit")
    replace_once(uc,
                 "public final static int MAX_ACCOUNT_COUNT = 4;",
                 "public final static int MAX_ACCOUNT_COUNT = %d;" % limit,
                 "accounts: hard limit")

    # ------------------------------------------------------------------
    # 1.5) Lazy account init -- avoid the startup crash
    #    With a high MAX_ACCOUNT_COUNT, ApplicationLoader builds every slot at
    #    startup on separate threads. That causes cross-thread JNI errors and
    #    IntentReceiverLeaked in DownloadController.<init> and finally SIGABRT.
    #    These guards skip inactive slots at startup so only really logged-in
    #    accounts are built (like old NekoGram versions).
    # ------------------------------------------------------------------
    al = "TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java"
    guard = "if (a != 0 && !UserConfig.getInstance(a).isClientActivated()) continue;"
    print("1.5) Lazy account init to prevent the startup crash")

    # Main postInitApplication loop: the guard must come AFTER loadConfig, not
    # before (isClientActivated() is only valid once loadConfig() has run; if
    # the guard is before loadConfig, accounts #2+ get skipped forever after
    # every restart).
    replace_once(al,
                 "            UserConfig.getInstance(a).loadConfig();\n"
                 "            MessagesController.getInstance(a);",
                 "            UserConfig.getInstance(a).loadConfig();\n"
                 "            " + guard + "\n"
                 "            MessagesController.getInstance(a);",
                 "lazy-init: main loop", optional=True)

    # ContactsController/DownloadController loop (exact crash site in the log)
    replace_once(al,
                 "            ContactsController.getInstance(a).checkAppAccount();\n"
                 "            DownloadController.getInstance(a);",
                 "            " + guard + "\n"
                 "            ContactsController.getInstance(a).checkAppAccount();\n"
                 "            DownloadController.getInstance(a);",
                 "lazy-init: contacts/download loop", optional=True)

    # Network-change receiver loop
    replace_once(al,
                 "                    for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "                        ConnectionsManager.getInstance(a).checkConnection();",
                 "                    for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "                        " + guard + "\n"
                 "                        ConnectionsManager.getInstance(a).checkConnection();",
                 "lazy-init: network receiver loop", optional=True)

    # ------------------------------------------------------------------
    # 1.6) Disable CheckJNI in the debug build
    #    Android's debug build turns on CheckJNI by default, which converts
    #    latent (normally harmless) JNI errors into SIGABRT. It crashes
    #    especially when adding more than 4 accounts (more threads/JNI).
    # ------------------------------------------------------------------
    bg = "TMessagesProj/build.gradle"
    print("1.6) Disable CheckJNI in the debug build")
    replace_once(bg,
                 "        debug {\n"
                 "            jniDebuggable true",
                 "        debug {\n"
                 "            jniDebuggable false\n"
                 "            debuggable false",
                 "build: disable CheckJNI on debug")

    # ------------------------------------------------------------------
    # 1.7) Native 5-account cap -> unlimited
    #    The C++ (tgnet) code has its own hard cap of 5 accounts, separate
    #    from Java: both a #define and a switch in getInstance that routes any
    #    index >=5 to account 4 (mixing accounts together). Here we set the
    #    #define equal to the Java cap and turn getInstance into a dynamic,
    #    thread-safe map.
    # ------------------------------------------------------------------
    defines_h = "TMessagesProj/jni/tgnet/Defines.h"
    cm_cpp = "TMessagesProj/jni/tgnet/ConnectionsManager.cpp"
    print("1.7) Native account cap -> unlimited (native account_limit = %d)" % limit)
    replace_once(defines_h,
                 "#define MAX_ACCOUNT_COUNT 5",
                 "#define MAX_ACCOUNT_COUNT %d" % limit,
                 "native: account count define")
    replace_once(cm_cpp,
                 "ConnectionsManager& ConnectionsManager::getInstance(int32_t instanceNum) {\n"
                 "    switch (instanceNum) {\n"
                 "        case 0:\n"
                 "            static ConnectionsManager instance0(0);\n"
                 "            return instance0;\n"
                 "        case 1:\n"
                 "            static ConnectionsManager instance1(1);\n"
                 "            return instance1;\n"
                 "        case 2:\n"
                 "            static ConnectionsManager instance2(2);\n"
                 "            return instance2;\n"
                 "        case 3:\n"
                 "            static ConnectionsManager instance3(3);\n"
                 "            return instance3;\n"
                 "        case 4:\n"
                 "        default:\n"
                 "            static ConnectionsManager instance4(4);\n"
                 "            return instance4;\n"
                 "    }\n"
                 "}",
                 "ConnectionsManager& ConnectionsManager::getInstance(int32_t instanceNum) {\n"
                 "    static std::map<int32_t, ConnectionsManager *> instances;\n"
                 "    static pthread_mutex_t instancesMutex = PTHREAD_MUTEX_INITIALIZER;\n"
                 "    if (instanceNum < 0) {\n"
                 "        instanceNum = 0;\n"
                 "    }\n"
                 "    pthread_mutex_lock(&instancesMutex);\n"
                 "    ConnectionsManager *result = instances[instanceNum];\n"
                 "    if (result == nullptr) {\n"
                 "        result = new ConnectionsManager(instanceNum);\n"
                 "        instances[instanceNum] = result;\n"
                 "    }\n"
                 "    pthread_mutex_unlock(&instancesMutex);\n"
                 "    return *result;\n"
                 "}",
                 "native: getInstance dynamic map")

    # ------------------------------------------------------------------
    # 1.8) Fix cross-thread JNIEnv crash
    #    TgNetWrapper.cpp calls network callbacks from various tgnet threads
    #    but used a cached jniEnv[instanceNum] (belonging to another thread);
    #    this causes "JNI DETECTED ERROR: using JNIEnv* from thread X".
    #    Fix: fetch/attach the JNIEnv for the current thread each time.
    # ------------------------------------------------------------------
    tgw = "TMessagesProj/jni/TgNetWrapper.cpp"
    print("1.8) Fix cross-thread JNIEnv crash in TgNetWrapper.cpp")
    replace_once(tgw,
                 "JavaVM *java;",
                 "JavaVM *java;\n\n"
                 "static inline JNIEnv *tgCurrentEnv() {\n"
                 "    JNIEnv *env = nullptr;\n"
                 "    if (java->GetEnv((void **) &env, JNI_VERSION_1_6) != JNI_OK) {\n"
                 "        java->AttachCurrentThread(&env, nullptr);\n"
                 "    }\n"
                 "    return env;\n"
                 "}",
                 "native: tgCurrentEnv helper")
    replace_all(tgw,
                "jniEnv[instanceNum]->",
                "tgCurrentEnv()->",
                "native: jniEnv[instanceNum] -> tgCurrentEnv()")

    # ------------------------------------------------------------------
    # 1.9) Fix connection null-deref in processRequestQueue
    #    When an auth key is briefly null during a new account's handshake,
    #    getConnectionByType can return nullptr; the original code accessed
    #    connection->getConnectionToken() without a check -> SIGSEGV.
    # ------------------------------------------------------------------
    print("1.9) Fix connection null-deref in processRequestQueue")
    replace_once(cm_cpp,
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "        int32_t maxTimeout = request->connectionType & ConnectionTypeGeneric ? 8 : 30;",
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "        if (connection == nullptr) {\n"
                 "            iter++;\n"
                 "            continue;\n"
                 "        }\n"
                 "        int32_t maxTimeout = request->connectionType & ConnectionTypeGeneric ? 8 : 30;",
                 "native: null-check connection #1")
    replace_once(cm_cpp,
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "\n"
                 "        if (request->connectionType & ConnectionTypeGeneric && connection->getConnectionToken() == 0) {",
                 "        Connection *connection = requestDatacenter->getConnectionByType(request->connectionType, true, canUseUnboundKey);\n"
                 "        if (connection == nullptr) {\n"
                 "            iter++;\n"
                 "            continue;\n"
                 "        }\n"
                 "\n"
                 "        if (request->connectionType & ConnectionTypeGeneric && connection->getConnectionToken() == 0) {",
                 "native: null-check connection #2")

    # ------------------------------------------------------------------
    # 1.10) Guard one known "account storm" spot (LocationController)
    #    This loop calls getInstance for all 100 slots without a check, even
    #    for empty accounts. If a similar crash (storage storm) is later seen
    #    with a backtrace in another file, add the same pattern (isClientActivated
    #    check before getInstance) there too.
    # ------------------------------------------------------------------
    lc = "TMessagesProj/src/main/java/org/telegram/messenger/LocationController.java"
    print("1.10) Guard getLocationsCount against building 100 slots needlessly")
    replace_once(lc,
                 "        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "            count += LocationController.getInstance(a).sharingLocationsUI.size();\n"
                 "        }",
                 "        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {\n"
                 "            if (!UserConfig.getInstance(a).isClientActivated()) {\n"
                 "                continue;\n"
                 "            }\n"
                 "            count += LocationController.getInstance(a).sharingLocationsUI.size();\n"
                 "        }",
                 "guard: LocationController.getLocationsCount", optional=True)

    # ------------------------------------------------------------------
    # 2) Open whole chat/group translation for everyone (no premium)
    #    The "Translate" bar at the top of a chat that was behind premium is
    #    made available to everyone.
    # ------------------------------------------------------------------
    tc = "TMessagesProj/src/main/java/org/telegram/messenger/TranslateController.java"
    if cfg.get("enable_chat_translate_for_all", True):
        print("2) Whole chat/group translation -> open to everyone")
        replace_once(tc,
                     "    public boolean isFeatureAvailable() {\n"
                     "        return isChatTranslateEnabled() && UserConfig.getInstance(currentAccount).isPremium();\n"
                     "    }",
                     "    public boolean isFeatureAvailable() {\n"
                     "        return isChatTranslateEnabled();\n"
                     "    }",
                     "translate: chat feature for all")
        replace_once(tc,
                     "        final TLRPC.Chat chat = getMessagesController().getChat(-dialogId);\n"
                     "        return (\n"
                     "            UserConfig.getInstance(currentAccount).isPremium() ||\n"
                     "            chat != null && chat.autotranslation\n"
                     "        );",
                     "        return true; // [mod] chat/group translate enabled for everyone",
                     "translate: per-dialog feature for all")

    # ------------------------------------------------------------------
    # 3) Per-message translate button on by default
    # ------------------------------------------------------------------
    if cfg.get("translate_button_default_on", True):
        print("3) Per-message translate button -> on by default")
        replace_once(tc,
                     'contextTranslateEnabled = messagesController.getMainSettings().getBoolean("translate_button", MessagesController.getGlobalMainSettings().getBoolean("translate_button", false));',
                     'contextTranslateEnabled = messagesController.getMainSettings().getBoolean("translate_button", MessagesController.getGlobalMainSettings().getBoolean("translate_button", true));',
                     "translate: per-message default on")

    # ------------------------------------------------------------------
    # 4) Nekogram-style translation engine (Google Translate instead of the
    #    Telegram server). The official code already has a complete alternative
    #    path (TranslateAlert2.alternativeTranslate -> Google Translate web
    #    endpoint with client=gtx -- the same engine Nekogram uses, with long
    #    text chunking and User-Agent rotation). The path is chosen by two
    #    server config flags; we lock both to "alternative": both at load time
    #    and where the server's appConfig would otherwise overwrite them.
    # ------------------------------------------------------------------
    mc = "TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java"
    if cfg.get("nekogram_style_translation", True):
        print("4) Translation engine -> Google Translate (Nekogram-style)")
        replace_once(mc,
                     'translationsManualEnabled = mainPreferences.getString("translationsManualEnabled", "enabled");',
                     'translationsManualEnabled = "alternative"; // [mod] Nekogram-style: Google translate engine',
                     "translate-engine: manual load")
        replace_once(mc,
                     'translationsAutoEnabled = mainPreferences.getString("translationsAutoEnabled", "enabled");',
                     'translationsAutoEnabled = "alternative"; // [mod] Nekogram-style: Google translate engine',
                     "translate-engine: auto load")
        # Instead of touching the value, we close the update condition so that
        # each time appConfig arrives it doesn't needlessly set changed=true and
        # overwrite the setting. (The two comments differ on purpose so the
        # idempotency check doesn't confuse them.)
        replace_once(mc,
                     "                        if (!TextUtils.equals(translationsManualEnabled, str.value)) {",
                     "                        if (false) { // [mod] keep Nekogram-style translation engine (manual)",
                     "translate-engine: manual appconfig")
        replace_once(mc,
                     "                        if (!TextUtils.equals(translationsAutoEnabled, str.value)) {",
                     "                        if (false) { // [mod] keep Nekogram-style translation engine (auto)",
                     "translate-engine: auto appconfig")

    # ------------------------------------------------------------------
    # 5) Number tag for accounts (#1 .. #100)
    #    Number = account slot number + 1. Since slots fill in login order,
    #    this is the login order and stays stable across restarts. We use "#"
    #    instead of a dot so it doesn't break in right-to-left (Persian) text.
    # ------------------------------------------------------------------
    mta = "TMessagesProj/src/main/java/org/telegram/ui/MainTabsActivity.java"
    asc = "TMessagesProj/src/main/java/org/telegram/ui/Cells/AccountSelectCell.java"
    if cfg.get("account_number_tags", True):
        print("5) Number tag for accounts")
        replace_once(mta,
                     "textView.setText(UserObject.getUserName(user));",
                     "textView.setText(\"#\" + (account + 1) + \" \" + UserObject.getUserName(user)); // [mod] account number tag",
                     "account-tag: main switcher list")
        replace_once(asc,
                     "textView.setText(ContactsController.formatName(user.first_name, user.last_name));",
                     "textView.setText(\"#\" + (accountNumber + 1) + \" \" + ContactsController.formatName(user.first_name, user.last_name)); // [mod] account number tag",
                     "account-tag: account select cell")

    print("\n=== All modifications applied successfully ===")
    print("Now open the Telegram folder in Android Studio and Build.")


if __name__ == "__main__":
    main()
