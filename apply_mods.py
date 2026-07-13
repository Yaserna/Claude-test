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


def file_contains(rel, needle):
    with open(_path(rel), "r", encoding="utf-8") as f:
        return needle in f.read()


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
        # When the source language cannot be detected (ML Kit is blocked on the
        # device) it comes back as "und"; Google rejects sl=und with HTTP 400 so
        # translation silently fails. Map an unknown source to "auto".
        ta2 = "TMessagesProj/src/main/java/org/telegram/ui/Components/TranslateAlert2.java"
        replace_once(ta2,
                     'uri += "e?client=gtx&sl=" + Uri.encode(fromLng) + "&tl=" + Uri.encode(toLng)',
                     'uri += "e?client=gtx&sl=" + Uri.encode((fromLng == null || fromLng.length() == 0 || "und".equals(fromLng) || "undefined".equals(fromLng)) ? "auto" : fromLng) + "&tl=" + Uri.encode(toLng)',
                     "translate-engine: unknown source language -> auto")

    if cfg.get("ai_translate", True):
        print("4.5) AI translation engine + in-app settings (falls back to Google)")
        ta2 = "TMessagesProj/src/main/java/org/telegram/ui/Components/TranslateAlert2.java"
        lsa = "TMessagesProj/src/main/java/org/telegram/ui/LanguageSelectActivity.java"
        default_model = "openrouter/free"
        # AI method reads key/model from the app settings (SharedPreferences),
        # set in-app at Settings > Language > translate icon. No key in code.
        ai_block = (
            '    // [mod] AI translation: key/model come from the app settings.\n'
            '    public static boolean isAiTranslateEnabled() {\n'
            '        android.content.SharedPreferences p = org.telegram.messenger.MessagesController.getGlobalMainSettings();\n'
            '        return p.getBoolean("ai_translate_enabled", false) && p.getString("ai_translate_key", "").length() > 0;\n'
            '    }\n'
            '\n'
            '    public static void aiTranslate(String text, String toLng, Utilities.Callback2<String, Boolean> done) {\n'
            '        if (done == null) return;\n'
            '        new Thread() {\n'
            '            @Override\n'
            '            public void run() {\n'
            '                HttpURLConnection connection = null;\n'
            '                try {\n'
            '                    android.content.SharedPreferences p = org.telegram.messenger.MessagesController.getGlobalMainSettings();\n'
            '                    String apiKey = p.getString("ai_translate_key", "");\n'
            '                    String model = p.getString("ai_translate_model", "' + default_model + '");\n'
            '                    String baseUrl = p.getString("ai_translate_url", "https://openrouter.ai/api/v1/chat/completions");\n'
            '                    String target = (toLng == null || toLng.length() == 0) ? "en" : toLng;\n'
            '                    org.json.JSONObject sys = new org.json.JSONObject();\n'
            '                    sys.put("role", "system");\n'
            '                    sys.put("content", "You are a professional translation engine. Translate the user\'s message into the language with ISO 639-1 code \\"" + target + "\\". Output only the translation itself, with no quotes and no extra words. Preserve line breaks, emojis, @mentions, #hashtags and links exactly.");\n'
            '                    org.json.JSONObject usr = new org.json.JSONObject();\n'
            '                    usr.put("role", "user");\n'
            '                    usr.put("content", text);\n'
            '                    org.json.JSONArray messages = new org.json.JSONArray();\n'
            '                    messages.put(sys);\n'
            '                    messages.put(usr);\n'
            '                    org.json.JSONObject bodyJson = new org.json.JSONObject();\n'
            '                    bodyJson.put("model", model);\n'
            '                    bodyJson.put("messages", messages);\n'
            '                    bodyJson.put("temperature", 0.2);\n'
            '                    byte[] payload = bodyJson.toString().getBytes("UTF-8");\n'
            '\n'
            '                    connection = (HttpURLConnection) new URI(baseUrl).toURL().openConnection();\n'
            '                    connection.setRequestMethod("POST");\n'
            '                    connection.setRequestProperty("Content-Type", "application/json");\n'
            '                    connection.setRequestProperty("Authorization", "Bearer " + apiKey);\n'
            '                    connection.setConnectTimeout(15000);\n'
            '                    connection.setReadTimeout(40000);\n'
            '                    connection.setDoOutput(true);\n'
            '                    java.io.OutputStream os = connection.getOutputStream();\n'
            '                    os.write(payload);\n'
            '                    os.close();\n'
            '\n'
            '                    int status = connection.getResponseCode();\n'
            '                    java.io.InputStream is = (status >= 200 && status < 300) ? connection.getInputStream() : connection.getErrorStream();\n'
            '                    StringBuilder sb = new StringBuilder();\n'
            '                    if (is != null) {\n'
            '                        Reader reader = new BufferedReader(new InputStreamReader(is, Charsets.UTF_8));\n'
            '                        int c;\n'
            '                        while ((c = reader.read()) != -1) {\n'
            '                            sb.append((char) c);\n'
            '                        }\n'
            '                        reader.close();\n'
            '                    }\n'
            '                    if (status < 200 || status >= 300) {\n'
            '                        throw new Exception("AI HTTP " + status);\n'
            '                    }\n'
            '                    org.json.JSONObject resp = new org.json.JSONObject(sb.toString());\n'
            '                    String out = resp.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim();\n'
            '                    final String finalOut = out;\n'
            '                    AndroidUtilities.runOnUIThread(() -> {\n'
            '                        if (done != null) done.run(finalOut, false);\n'
            '                    });\n'
            '                } catch (Exception e) {\n'
            '                    AndroidUtilities.runOnUIThread(() -> {\n'
            '                        if (done != null) done.run(null, false);\n'
            '                    });\n'
            '                } finally {\n'
            '                    if (connection != null) {\n'
            '                        try { connection.disconnect(); } catch (Exception ignore) {}\n'
            '                    }\n'
            '                }\n'
            '            }\n'
            '        }.start();\n'
            '    }\n'
            '\n'
        )
        anchor = "    public static void alternativeTranslate(String text, String fromLng, String toLng, Utilities.Callback2<String, Boolean> done) {"
        if not file_contains(ta2, "isAiTranslateEnabled"):
            replace_once(ta2, anchor, ai_block + anchor, "ai-translate: method")
        else:
            print("  - [ai-translate: method] already present, skipped.")
        replace_once(ta2,
                     "        if (done == null) return;\n        if (fromLng == null) {",
                     "        if (done == null) return;\n"
                     "        if (isAiTranslateEnabled()) { aiTranslate(text, toLng, done); return; } // [mod] AI translation engine\n"
                     "        if (fromLng == null) {",
                     "ai-translate: routing")
        # In-app settings dialog in Settings > Language (a translate icon in the
        # top bar opens it). Fully-qualified names avoid touching imports.
        lsa_method = (
            '    private void showAiTranslateSettings() {\n'
            '        android.content.Context context = getParentActivity();\n'
            '        if (context == null) {\n'
            '            return;\n'
            '        }\n'
            '        final android.content.SharedPreferences prefs = MessagesController.getGlobalMainSettings();\n'
            '        android.widget.LinearLayout ll = new android.widget.LinearLayout(context);\n'
            '        ll.setOrientation(android.widget.LinearLayout.VERTICAL);\n'
            '        int pad = org.telegram.messenger.AndroidUtilities.dp(22);\n'
            '        ll.setPadding(pad, org.telegram.messenger.AndroidUtilities.dp(8), pad, 0);\n'
            '        final android.widget.CheckBox enableBox = new android.widget.CheckBox(context);\n'
            '        enableBox.setText("Use AI translation (off = Google)");\n'
            '        enableBox.setChecked(prefs.getBoolean("ai_translate_enabled", false));\n'
            '        ll.addView(enableBox);\n'
            '        final EditText keyEdit = new EditText(context);\n'
            '        keyEdit.setHint("API key (sk-or-v1-...)");\n'
            '        keyEdit.setSingleLine(true);\n'
            '        keyEdit.setText(prefs.getString("ai_translate_key", ""));\n'
            '        ll.addView(keyEdit);\n'
            '        final EditText modelEdit = new EditText(context);\n'
            '        modelEdit.setHint("Model id");\n'
            '        modelEdit.setSingleLine(true);\n'
            '        modelEdit.setText(prefs.getString("ai_translate_model", "' + default_model + '"));\n'
            '        ll.addView(modelEdit);\n'
            '        final EditText composeEdit = new EditText(context);\n'
            '        composeEdit.setHint("Compose translate target (e.g. en)");\n'
            '        composeEdit.setSingleLine(true);\n'
            '        composeEdit.setText(prefs.getString("compose_translate_to", "en"));\n'
            '        ll.addView(composeEdit);\n'
            '        AlertDialog.Builder builder = new AlertDialog.Builder(context);\n'
            '        builder.setTitle("YasTel AI Translate");\n'
            '        builder.setView(ll);\n'
            '        builder.setPositiveButton(LocaleController.getString(R.string.Save), (dialog, which) -> {\n'
            '            prefs.edit()\n'
            '                .putBoolean("ai_translate_enabled", enableBox.isChecked())\n'
            '                .putString("ai_translate_key", keyEdit.getText().toString().trim())\n'
            '                .putString("ai_translate_model", modelEdit.getText().toString().trim())\n'
            '                .putString("compose_translate_to", composeEdit.getText().toString().trim())\n'
            '                .apply();\n'
            '        });\n'
            '        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);\n'
            '        showDialog(builder.create());\n'
            '    }\n'
            '\n'
        )
        if not file_contains(lsa, "showAiTranslateSettings"):
            replace_once(lsa,
                         "        ActionBarMenu menu = actionBar.createMenu();\n",
                         "        ActionBarMenu menu = actionBar.createMenu();\n"
                         "        menu.addItem(1001, R.drawable.msg_translate); // [mod] YasTel AI translate settings\n",
                         "ai-translate: settings menu item")
            replace_once(lsa,
                         "                if (id == -1) {\n"
                         "                    finishFragment();\n"
                         "                }",
                         "                if (id == -1) {\n"
                         "                    finishFragment();\n"
                         "                } else if (id == 1001) { // [mod] YasTel AI translate settings\n"
                         "                    showAiTranslateSettings();\n"
                         "                }",
                         "ai-translate: settings click")
            replace_once(lsa,
                         "    @Override\n    public View createView(Context context) {",
                         lsa_method + "    @Override\n    public View createView(Context context) {",
                         "ai-translate: settings method")
        else:
            print("  - [ai-translate: in-app settings] already present, skipped.")

    if cfg.get("fix_bidi", True):
        print("4.6) Fix mixed RTL/LTR scrambling in translated text")
        ta2 = "TMessagesProj/src/main/java/org/telegram/ui/Components/TranslateAlert2.java"
        fixbidi_method = (
            '    // [mod] fix bidi: keep mixed RTL/LTR translated text from scrambling.\n'
            '    public static String fixBidi(String text, String toLng) {\n'
            '        if (text == null || text.length() == 0) {\n'
            '            return text;\n'
            '        }\n'
            '        String lng = toLng == null ? "" : toLng.toLowerCase();\n'
            '        boolean rtl = lng.startsWith("fa") || lng.startsWith("ar") || lng.startsWith("he") || lng.startsWith("iw") || lng.startsWith("ur") || lng.startsWith("ps") || lng.startsWith("ckb") || lng.startsWith("sd") || lng.startsWith("ug") || lng.startsWith("yi") || lng.startsWith("dv");\n'
            '        if (!rtl) {\n'
            '            return text;\n'
            '        }\n'
            "        final char RLM = '\\u200F';\n"
            "        final char LRI = '\\u2066';\n"
            "        final char PDI = '\\u2069';\n"
            '        String[] lines = text.split("\\n", -1);\n'
            '        StringBuilder out = new StringBuilder();\n'
            '        for (int li = 0; li < lines.length; li++) {\n'
            '            if (li > 0) {\n'
            "                out.append('\\n');\n"
            '            }\n'
            '            String line = lines[li];\n'
            '            out.append(RLM);\n'
            '            int i = 0, n = line.length();\n'
            '            while (i < n) {\n'
            '                char c = line.charAt(i);\n'
            '                if (c >= 0x20 && c <= 0x7E) {\n'
            '                    int j = i;\n'
            '                    boolean alnum = false;\n'
            '                    while (j < n && line.charAt(j) >= 0x20 && line.charAt(j) <= 0x7E) {\n'
            '                        char cj = line.charAt(j);\n'
            "                        if ((cj >= 'A' && cj <= 'Z') || (cj >= 'a' && cj <= 'z') || (cj >= '0' && cj <= '9')) {\n"
            '                            alnum = true;\n'
            '                        }\n'
            '                        j++;\n'
            '                    }\n'
            '                    String run = line.substring(i, j);\n'
            '                    if (alnum) {\n'
            '                        out.append(LRI).append(run).append(PDI);\n'
            '                    } else {\n'
            '                        out.append(run);\n'
            '                    }\n'
            '                    i = j;\n'
            '                } else {\n'
            '                    out.append(c);\n'
            '                    i++;\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '        return out.toString();\n'
            '    }\n'
            '\n'
        )
        method_anchor = "    public static void alternativeTranslate(String text, String fromLng, String toLng, Utilities.Callback2<String, Boolean> done) {"
        if not file_contains(ta2, "public static String fixBidi("):
            replace_once(ta2, method_anchor, fixbidi_method + method_anchor, "bidi: helper")
        else:
            print("  - [bidi: helper] already present, skipped.")
        if file_contains(ta2, 'String out = resp.getJSONArray("choices")') and \
           not file_contains(ta2, "out = fixBidi(out, toLng);"):
            replace_once(ta2,
                         '                    String out = resp.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim();\n',
                         '                    String out = resp.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim();\n'
                         '                    out = fixBidi(out, toLng);\n',
                         "bidi: AI output")
        replace_once(ta2,
                     "                    if (text.length() > 0 && text.charAt(0) == '\\n')\n"
                     '                        result = "\\n" + result;\n'
                     "                    final String finalResult = result;",
                     "                    if (text.length() > 0 && text.charAt(0) == '\\n')\n"
                     '                        result = "\\n" + result;\n'
                     "                    result = fixBidi(result, toLng);\n"
                     "                    final String finalResult = result;",
                     "bidi: Google output")

    if cfg.get("compose_translate", True):
        print("4.7) Translate button for the message input bar (left, no overlap)")
        cev = "TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java"
        cev_anchor = "        setEmojiButtonImage(false, false);\n"
        cev_button = (
            '        final android.widget.ImageView translateComposeButton = new android.widget.ImageView(context); // [mod] compose translate (left)\n'
            '        translateComposeButton.setImageResource(R.drawable.msg_translate);\n'
            '        translateComposeButton.setScaleType(android.widget.ImageView.ScaleType.CENTER);\n'
            '        translateComposeButton.setColorFilter(new PorterDuffColorFilter(getThemedColor(Theme.key_glass_defaultIcon), PorterDuff.Mode.MULTIPLY));\n'
            '        translateComposeButton.setBackground(Theme.createSelectorDrawable(getThemedColor(Theme.key_listSelector), Theme.RIPPLE_MASK_CIRCLE_20DP, dp(16)));\n'
            '        messageEditTextContainer.addView(translateComposeButton, LayoutHelper.createFrame(DEFAULT_HEIGHT, DEFAULT_HEIGHT, Gravity.BOTTOM | Gravity.LEFT, 52, 0, 0, 0));\n'
            '        translateComposeButton.setContentDescription("Translate typed text");\n'
            '        ScaleStateListAnimator.apply(translateComposeButton);\n'
            '        translateComposeButton.setOnClickListener(v -> {\n'
            '            if (messageEditText == null) return;\n'
            '            CharSequence cs = messageEditText.getText();\n'
            '            if (cs == null || cs.length() == 0) return;\n'
            '            String toLng = MessagesController.getGlobalMainSettings().getString("compose_translate_to", "en");\n'
            '            final String src = cs.toString();\n'
            '            org.telegram.messenger.Utilities.Callback2<String, Boolean> cb = (res, rl) -> {\n'
            '                if (res != null && messageEditText != null) {\n'
            '                    messageEditText.setText(res);\n'
            '                    try { messageEditText.setSelection(messageEditText.length()); } catch (Exception ignore) {}\n'
            '                }\n'
            '            };\n'
            '            TranslateAlert2.alternativeTranslate(src, null, toLng, cb);\n'
            '        });\n'
        )
        if not file_contains(cev, "translateComposeButton"):
            replace_once(cev, cev_anchor, cev_anchor + cev_button, "compose: input-bar button")
        else:
            print("  - [compose: input-bar button] already present, skipped.")
        replace_once(cev,
                     "Gravity.BOTTOM, 52, 0, isChat ? 50 : 2, 1.5f",
                     "Gravity.BOTTOM, 96, 0, isChat ? 50 : 2, 1.5f",
                     "compose: text field left margin")

    if cfg.get("sequential_translate", True):
        print("4.8) Whole-chat translation: one bubble at a time (no batch fail)")
        tc = "TMessagesProj/src/main/java/org/telegram/messenger/TranslateController.java"
        tc_old = (
            "                    for (int i = 0; i < pendingTranslation1.messageIds.size(); ++i) {\n"
            "                        final int id = pendingTranslation1.messageIds.get(i);\n"
            "                        final Utilities.Callback4<Boolean, Integer, TLRPC.TL_textWithEntities, String> _callback = pendingTranslation1.callbacks.get(i);\n"
            "                        final String _text = pendingTranslation1.messageTexts.get(i).text;\n"
            "                        TranslateAlert2.alternativeTranslate(_text, null, toLanguage, (result, rateLimit) -> {\n"
            "                            if (result != null) {\n"
            "                                final TLRPC.TL_textWithEntities resultWithEntities = new TLRPC.TL_textWithEntities();\n"
            "                                resultWithEntities.text = result;\n"
            "                                _callback.run(isTranscription, id, resultWithEntities, toLanguage);\n"
            "                            } else {\n"
            "                                toggleTranslatingDialog(dialogId, false);\n"
            "                                NotificationCenter.getGlobalInstance().postNotificationName(NotificationCenter.showBulletin, Bulletin.TYPE_ERROR, getString(rateLimit ? R.string.TranslationFailedAlert1 : R.string.TranslationFailedAlert2));\n"
            "                            }\n"
            "                        });\n"
            "                    }\n"
        )
        tc_new = (
            "                    // [mod] translate bubbles one-by-one; a slow/rate-limited failure is\n"
            "                    // skipped silently and does NOT turn off the dialog translation.\n"
            "                    final int[] _seqIndex = new int[]{0};\n"
            "                    final Runnable[] _seqNext = new Runnable[1];\n"
            "                    _seqNext[0] = () -> {\n"
            "                        int i = _seqIndex[0]++;\n"
            "                        if (i >= pendingTranslation1.messageIds.size()) {\n"
            "                            return;\n"
            "                        }\n"
            "                        final int id = pendingTranslation1.messageIds.get(i);\n"
            "                        final Utilities.Callback4<Boolean, Integer, TLRPC.TL_textWithEntities, String> _callback = pendingTranslation1.callbacks.get(i);\n"
            "                        final String _text = pendingTranslation1.messageTexts.get(i).text;\n"
            "                        TranslateAlert2.alternativeTranslate(_text, null, toLanguage, (result, rateLimit) -> {\n"
            "                            if (result != null) {\n"
            "                                final TLRPC.TL_textWithEntities resultWithEntities = new TLRPC.TL_textWithEntities();\n"
            "                                resultWithEntities.text = result;\n"
            "                                _callback.run(isTranscription, id, resultWithEntities, toLanguage);\n"
            "                            }\n"
            "                            AndroidUtilities.runOnUIThread(_seqNext[0]);\n"
            "                        });\n"
            "                    };\n"
            "                    _seqNext[0].run();\n"
        )
        if not file_contains(tc, "_seqNext"):
            replace_once(tc, tc_old, tc_new, "sequential whole-chat translate")
        else:
            print("  - [sequential whole-chat translate] already present, skipped.")

    # ------------------------------------------------------------------
    # 5) Number tag for accounts (#1 .. #100)
    #    Number = account slot number + 1. Since slots fill in login order,
    #    this is the login order and stays stable across restarts. We use "#"
    #    instead of a dot so it doesn't break in right-to-left (Persian) text.
    # ------------------------------------------------------------------
    mta = "TMessagesProj/src/main/java/org/telegram/ui/MainTabsActivity.java"
    asc = "TMessagesProj/src/main/java/org/telegram/ui/Cells/AccountSelectCell.java"
    da = "TMessagesProj/src/main/java/org/telegram/ui/DialogsActivity.java"
    # Login-order number helper. Account slots are NOT sequential (Telegram
    # fills "add account" from the top of the array, so slots end up 0,99,98,
    # ...), which is why slot+1 gave 1,100,99,98. We rank by loginTime instead,
    # matching the order the account switcher already sorts by, so it reads
    # 1,2,3,... in login order and stays stable across restarts.
    tag_helper = (
        "    public static int getAccountTagNumber(int account) {\n"
        "        if (account < 0 || account >= MAX_ACCOUNT_COUNT) {\n"
        "            return account + 1;\n"
        "        }\n"
        "        long myLogin = getInstance(account).loginTime;\n"
        "        int rank = 1;\n"
        "        for (int a = 0; a < MAX_ACCOUNT_COUNT; a++) {\n"
        "            if (a == account) {\n"
        "                continue;\n"
        "            }\n"
        "            if (!getInstance(a).isClientActivated()) {\n"
        "                continue;\n"
        "            }\n"
        "            long other = getInstance(a).loginTime;\n"
        "            if (other < myLogin || (other == myLogin && a < account)) {\n"
        "                rank++;\n"
        "            }\n"
        "        }\n"
        "        return rank;\n"
        "    }\n"
    )
    if cfg.get("account_number_tags", True):
        print("5) Number tag for accounts (login order)")
        # Each patch is skipped once the 5.7 phone-label patch has replaced the
        # same display site (rerun on an already fully patched source).
        if not file_contains(uc, "getAccountTagNumber("):
            replace_once(uc,
                         "    public static int getActivatedAccountsCount() {",
                         tag_helper + "\n    public static int getActivatedAccountsCount() {",
                         "account-tag: login-order helper")
        else:
            print("  - [account-tag: login-order helper] already applied, skipped.")
        if not file_contains(mta, "getAccountLabel("):
            replace_once(mta,
                         "textView.setText(UserObject.getUserName(user));",
                         "textView.setText(\"#\" + UserConfig.getAccountTagNumber(account) + \" \" + UserObject.getUserName(user)); // [mod] account number tag",
                         "account-tag: main switcher list")
        else:
            print("  - [account-tag: main switcher list] superseded by phone label, skipped.")
        if not file_contains(asc, "getAccountLabel("):
            replace_once(asc,
                         "textView.setText(ContactsController.formatName(user.first_name, user.last_name));",
                         "textView.setText(\"#\" + UserConfig.getAccountTagNumber(accountNumber) + \" \" + ContactsController.formatName(user.first_name, user.last_name)); // [mod] account number tag",
                         "account-tag: account select cell")
        else:
            print("  - [account-tag: account select cell] superseded by phone label, skipped.")
        if not file_contains(da, "getAccountLabel("):
            replace_once(da,
                         "textView.setText(UserObject.getUserName(user));",
                         "textView.setText(\"#\" + UserConfig.getAccountTagNumber(account) + \" \" + UserObject.getUserName(user)); // [mod] account number tag",
                         "account-tag: dialogs drawer switcher")
        else:
            print("  - [account-tag: dialogs drawer switcher] superseded by phone label, skipped.")

    # ------------------------------------------------------------------
    # 5.5) Number tag in MORE places: own profile header, Settings header,
    #      and the accounts list inside Settings.
    # ------------------------------------------------------------------
    pa = "TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java"
    sa = "TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java"
    if cfg.get("account_number_tags", True):
        print("5.5) Number tag in profile/settings")
        if not file_contains(pa, "(own profile)"):
            replace_once(pa,
                         "            CharSequence newString = UserObject.getUserName(user);\n"
                         "            String newString2;",
                         "            CharSequence newString = UserObject.getUserName(user);\n"
                         "            if (user.id == getUserConfig().getClientUserId()) { newString = \"#\" + UserConfig.getAccountTagNumber(currentAccount) + \" \" + newString; } // [mod] account number tag (own profile)\n"
                         "            String newString2;",
                         "account-tag: own profile header")
        else:
            print("  - [account-tag: own profile header] superseded by phone label, skipped.")
        if not file_contains(sa, "(settings header)"):
            replace_once(sa,
                         "        titleView.setText(UserObject.getUserName(user));",
                         "        titleView.setText(\"#\" + UserConfig.getAccountTagNumber(currentAccount) + \" \" + UserObject.getUserName(user)); // [mod] account number tag (settings header)",
                         "account-tag: settings header")
        else:
            print("  - [account-tag: settings header] superseded by phone label, skipped.")
        if not file_contains(sa, "textView.setText(UserConfig.getAccountLabel(account"):
            replace_once(sa,
                         "            textView.setText(UserObject.getUserName(user));",
                         "            textView.setText(\"#\" + UserConfig.getAccountTagNumber(account) + \" \" + UserObject.getUserName(user)); // [mod] account number tag (settings accounts list)",
                         "account-tag: settings accounts list")
        else:
            print("  - [account-tag: settings accounts list] superseded by phone label, skipped.")

    # ------------------------------------------------------------------
    # 5.7) Account label = "#N <local phone number>" in our management UI
    #      (switcher, drawer, send-as, own profile, settings). Uses Telegram's
    #      own PhoneFormat to strip the country code, name stays as fallback.
    #      Chats/groups keep showing the real name.
    # ------------------------------------------------------------------
    phone_helper = (
        "    // [mod] account label: \"<local phone number>  #N\" for our own management UI.\n"
        "    // Uses Telegram's own PhoneFormat to find the country code prefix, so it\n"
        "    // works for any country; falls back to the display name without a phone.\n"
        "    public static String getAccountLabel(int account, String fallbackName) {\n"
        "        String label = fallbackName;\n"
        "        try {\n"
        "            TLRPC.User user = getInstance(account).getCurrentUser();\n"
        "            if (user != null && user.phone != null && user.phone.length() > 0) {\n"
        "                String formatted = org.telegram.PhoneFormat.PhoneFormat.getInstance().format(\"+\" + user.phone);\n"
        "                if (formatted != null && formatted.length() > 0) {\n"
        "                    int space = formatted.indexOf(' ');\n"
        "                    String local = space > 0 ? formatted.substring(space + 1) : formatted;\n"
        "                    local = local.replace(\" \", \"\").replace(\"-\", \"\");\n"
        "                    if (local.startsWith(\"+\")) {\n"
        "                        local = local.substring(1);\n"
        "                    }\n"
        "                    if (local.length() > 0) {\n"
        "                        label = local;\n"
        "                    }\n"
        "                }\n"
        "            }\n"
        "        } catch (Exception e) {\n"
        "            // keep the name if the phone cannot be formatted\n"
        "        }\n"
        "        return label + \"  #\" + getAccountTagNumber(account);\n"
        "    }\n"
    )
    if cfg.get("account_phone_labels", True):
        print("5.7) Account labels -> local phone number in management UI")
        if not file_contains(uc, "getAccountLabel("):
            replace_once(uc,
                         "    public static int getActivatedAccountsCount() {",
                         phone_helper + "\n    public static int getActivatedAccountsCount() {",
                         "phone-label: helper in UserConfig")
        else:
            print("  - [phone-label: helper in UserConfig] already applied, skipped.")
        # Hotfix for sources patched with the older helper: strip spaces from
        # the number and move the #N tag to the end (two spaces before it).
        replace_once(uc,
                     "                    local = local.trim();\n",
                     '                    local = local.replace(" ", "").replace("-", "");\n',
                     "phone-label: no spaces in number")
        replace_once(uc,
                     '        return "#" + getAccountTagNumber(account) + " " + label;',
                     '        return label + "  #" + getAccountTagNumber(account);',
                     "phone-label: tag at end")
        replace_once(mta,
                     'textView.setText("#" + UserConfig.getAccountTagNumber(account) + " " + UserObject.getUserName(user)); // [mod] account number tag',
                     'textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user))); // [mod] account phone label',
                     "phone-label: main switcher list")
        replace_once(da,
                     'textView.setText("#" + UserConfig.getAccountTagNumber(account) + " " + UserObject.getUserName(user)); // [mod] account number tag',
                     'textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user))); // [mod] account phone label',
                     "phone-label: dialogs drawer switcher")
        replace_once(asc,
                     'textView.setText("#" + UserConfig.getAccountTagNumber(accountNumber) + " " + ContactsController.formatName(user.first_name, user.last_name)); // [mod] account number tag',
                     'textView.setText(UserConfig.getAccountLabel(accountNumber, ContactsController.formatName(user.first_name, user.last_name))); // [mod] account phone label',
                     "phone-label: send-as account select")
        # Own profile + Settings headers show the REAL NAME with the #N tag
        # after it (user's choice); the phone label stays everywhere else.
        profile_name_tag = '            if (user.id == getUserConfig().getClientUserId()) { newString = newString.toString() + "  #" + UserConfig.getAccountTagNumber(currentAccount); } // [mod] account name tag (own profile)'
        settings_name_tag = '        titleView.setText(UserObject.getUserName(user) + "  #" + UserConfig.getAccountTagNumber(currentAccount)); // [mod] account name tag (settings header)'
        if file_contains(pa, "account phone label (own profile)"):
            replace_once(pa,
                         '            if (user.id == getUserConfig().getClientUserId()) { newString = UserConfig.getAccountLabel(currentAccount, newString.toString()); } // [mod] account phone label (own profile)',
                         profile_name_tag,
                         "name-tag: own profile header (from phone label)")
        else:
            replace_once(pa,
                         '            if (user.id == getUserConfig().getClientUserId()) { newString = "#" + UserConfig.getAccountTagNumber(currentAccount) + " " + newString; } // [mod] account number tag (own profile)',
                         profile_name_tag,
                         "name-tag: own profile header")
        if file_contains(sa, "account phone label (settings header)"):
            replace_once(sa,
                         '        titleView.setText(UserConfig.getAccountLabel(currentAccount, UserObject.getUserName(user))); // [mod] account phone label (settings header)',
                         settings_name_tag,
                         "name-tag: settings header (from phone label)")
        else:
            replace_once(sa,
                         '        titleView.setText("#" + UserConfig.getAccountTagNumber(currentAccount) + " " + UserObject.getUserName(user)); // [mod] account number tag (settings header)',
                         settings_name_tag,
                         "name-tag: settings header")
        replace_once(sa,
                     '            textView.setText("#" + UserConfig.getAccountTagNumber(account) + " " + UserObject.getUserName(user)); // [mod] account number tag (settings accounts list)',
                     '            textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user))); // [mod] account phone label (settings accounts list)',
                     "phone-label: settings accounts list")

    # ------------------------------------------------------------------
    # 6) Translate bar at the top of EVERY chat/group.
    #    Officially the bar only appears after Google-ML language detection
    #    marks the dialog as translatable, and only for premium users. ML
    #    detection never completes on devices without Google services (our
    #    case), so the bar never appeared. We show it in every normal dialog;
    #    it can still be hidden per chat from its own menu.
    # ------------------------------------------------------------------
    ca = "TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java"
    tb = "TMessagesProj/src/main/java/org/telegram/ui/Components/TranslateButton.java"
    if cfg.get("translate_bar_for_all", True):
        print("6) Translate bar on top of every chat")
        replace_once(tc,
                     "        return (\n"
                     "            translatableDialogs.contains(dialogId) &&\n"
                     "            isFeatureAvailable(dialogId) &&",
                     "        return (\n"
                     "            isFeatureAvailable(dialogId) && // [mod] translate bar in all chats (no language detection needed)",
                     "translate-bar: isDialogTranslatable without detection")
        replace_once(ca,
                     "        boolean showTranslate = (\n"
                     "            getUserConfig().isPremium() || currentChat != null && currentChat.autotranslation ?\n"
                     "                getMessagesController().getTranslateController().isDialogTranslatable(getDialogId()) && !getMessagesController().getTranslateController().isTranslateDialogHidden(getDialogId()) :\n"
                     "                !getMessagesController().premiumFeaturesBlocked() && preferences.getInt(\"dialog_show_translate_count\" + did, 5) <= 0\n"
                     "        ) || DEBUG_TOP_PANELS;",
                     "        boolean showTranslate = (\n"
                     "            getMessagesController().getTranslateController().isDialogTranslatable(getDialogId()) && !getMessagesController().getTranslateController().isTranslateDialogHidden(getDialogId()) // [mod] translate bar for everyone\n"
                     "        ) || DEBUG_TOP_PANELS;",
                     "translate-bar: show condition without premium")
        replace_once(ca,
                     "            protected void onButtonClick() {\n"
                     "                if (getUserConfig().isPremium() || currentChat != null && currentChat.autotranslation) {\n"
                     "                    getMessagesController().getTranslateController().toggleTranslatingDialog(getDialogId());\n"
                     "                } else {\n"
                     "                    MessagesController.getNotificationsSettings(currentAccount).edit().putInt(\"dialog_show_translate_count\" + getDialogId(), 14).commit();\n"
                     "                    showDialog(new PremiumFeatureBottomSheet(ChatActivity.this, PremiumPreviewFragment.PREMIUM_FEATURE_TRANSLATIONS, false));\n"
                     "                }\n"
                     "                updateTopPanel(true);\n"
                     "            }",
                     "            protected void onButtonClick() {\n"
                     "                getMessagesController().getTranslateController().toggleTranslatingDialog(getDialogId()); // [mod] translate for everyone\n"
                     "                updateTopPanel(true);\n"
                     "            }",
                     "translate-bar: button toggles translation")
        replace_once(tb,
                     "            if (UserConfig.getInstance(currentAccount).isPremium() || chat != null && chat.autotranslation) {\n"
                     "                onMenuClick();",
                     "            if (true) { // [mod] translate settings menu for everyone\n"
                     "                onMenuClick();",
                     "translate-bar: settings menu for everyone")
        replace_once(tb,
                     "        menuView.setImageResource(UserConfig.getInstance(currentAccount).isPremium() || chat != null && chat.autotranslation ? R.drawable.msg_mini_customize : R.drawable.msg_close);",
                     "        menuView.setImageResource(R.drawable.msg_mini_customize); // [mod] translate settings menu for everyone",
                     "translate-bar: customize icon for everyone")
        replace_once(tb,
                     "        if (UserConfig.getInstance(currentAccount).isPremium() && detectedLanguageNameAccusative != null) {",
                     "        if (detectedLanguageNameAccusative != null) { // [mod] no premium",
                     "translate-bar: do-not-translate option for everyone")

    # ------------------------------------------------------------------
    # 7) In-bubble translation for a SINGLE message (+ Show Original).
    #    Long press -> Translate now translates the bubble itself (using the
    #    same engine as whole-chat translation) instead of opening the popup;
    #    long press again shows "Show Original" which restores the text.
    # ------------------------------------------------------------------
    mo = "TMessagesProj/src/main/java/org/telegram/messenger/MessageObject.java"
    manual_helper = (
        "    // [mod] manual single-message bubble translation\n"
        "    private final HashMap<Long, HashSet<Integer>> manualTranslatedMessages = new HashMap<>();\n"
        "\n"
        "    public boolean isMessageManuallyTranslated(long dialogId, int messageId) {\n"
        "        HashSet<Integer> set = manualTranslatedMessages.get(dialogId);\n"
        "        return set != null && set.contains(messageId);\n"
        "    }\n"
        "\n"
        "    public boolean isMessageManuallyTranslated(MessageObject messageObject) {\n"
        "        return messageObject != null && messageObject.messageOwner != null && isMessageManuallyTranslated(messageObject.getDialogId(), messageObject.getId());\n"
        "    }\n"
        "\n"
        "    public void toggleManualMessageTranslation(MessageObject messageObject) {\n"
        "        if (messageObject == null || messageObject.messageOwner == null) {\n"
        "            return;\n"
        "        }\n"
        "        final long dialogId = messageObject.getDialogId();\n"
        "        HashSet<Integer> set = manualTranslatedMessages.get(dialogId);\n"
        "        if (set == null) {\n"
        "            manualTranslatedMessages.put(dialogId, set = new HashSet<>());\n"
        "        }\n"
        "        final int messageId = messageObject.getId();\n"
        "        if (set.contains(messageId) && messageObject.translated) {\n"
        "            set.remove(messageId);\n"
        "            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslated, messageObject, false);\n"
        "            return;\n"
        "        }\n"
        "        set.add(messageId);\n"
        "        final String language = getDialogTranslateTo(dialogId);\n"
        "        final TLRPC.TL_textWithEntities existing = messageObject.messageOwner.voiceTranscriptionOpen ? messageObject.messageOwner.translatedVoiceTranscription : messageObject.messageOwner.translatedText;\n"
        "        if (existing != null && language.equals(messageObject.messageOwner.translatedToLanguage)) {\n"
        "            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslated, messageObject, false);\n"
        "            return;\n"
        "        }\n"
        "        NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslating, messageObject);\n"
        "        final MessageObject finalMessageObject = messageObject;\n"
        "        pushToTranslate(finalMessageObject, language, (isTranscription, id, text, lang) -> {\n"
        "            finalMessageObject.messageOwner.translatedToLanguage = lang;\n"
        "            if (isTranscription) {\n"
        "                finalMessageObject.messageOwner.translatedVoiceTranscription = text;\n"
        "            } else {\n"
        "                finalMessageObject.messageOwner.translatedText = text;\n"
        "            }\n"
        "            getMessagesStorage().updateMessageCustomParams(dialogId, finalMessageObject.messageOwner);\n"
        "            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslated, finalMessageObject, false);\n"
        "        });\n"
        "    }\n"
        "\n"
    )
    bubble_call = (
        "                                if (TranslateController.isTranslatable(selectedObject)) { // [mod] bubble translate\n"
        "                                    getMessagesController().getTranslateController().toggleManualMessageTranslation(selectedObject);\n"
        "                                    closeMenu();\n"
        "                                } else {\n"
    )
    label_new = "                    items.add(LocaleController.getString(getMessagesController().getTranslateController().isMessageManuallyTranslated(selectedObject) && selectedObject.translated ? R.string.ShowOriginalButton : R.string.TranslateMessage)); // [mod] bubble translate label"
    if cfg.get("bubble_translate", True):
        print("7) In-bubble single message translation")
        # Hotfixes in case a previous version of the helper is already in the
        # source (it called updateTranslation(true) itself, which consumed the
        # state change so the chat screen never repainted the bubble; and a
        # failed translation left the message flagged so the next tap did
        # nothing). Must run BEFORE the insert below.
        if file_contains(tc, "manualTranslatedMessages"):
            replace_once(tc,
                         "        final int messageId = messageObject.getId();\n"
                         "        if (set.contains(messageId)) {\n"
                         "            set.remove(messageId);\n"
                         "            messageObject.updateTranslation(true);\n"
                         "            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslated, messageObject, false);\n"
                         "            return;\n"
                         "        }",
                         "        final int messageId = messageObject.getId();\n"
                         "        if (set.contains(messageId) && messageObject.translated) {\n"
                         "            set.remove(messageId);\n"
                         "            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslated, messageObject, false);\n"
                         "            return;\n"
                         "        }",
                         "bubble: hotfix undo repaint + failure retry", optional=True)
            replace_once(tc,
                         "        if (existing != null && language.equals(messageObject.messageOwner.translatedToLanguage)) {\n"
                         "            messageObject.updateTranslation(true);\n"
                         "            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslated, messageObject, false);\n"
                         "            return;\n"
                         "        }",
                         "        if (existing != null && language.equals(messageObject.messageOwner.translatedToLanguage)) {\n"
                         "            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.messageTranslated, messageObject, false);\n"
                         "            return;\n"
                         "        }",
                         "bubble: hotfix cached translation repaint", optional=True)
        replace_once(tc,
                     "    public void toggleTranslatingDialog(long dialogId) {",
                     manual_helper + "    public void toggleTranslatingDialog(long dialogId) {",
                     "bubble: manual translation helper")
        replace_once(mo,
                     "            TranslateController.isTranslatable(this) &&\n"
                     "            translateController.isTranslatingDialog(getDialogId()) &&\n"
                     "            !translateController.isTranslateDialogHidden(getDialogId()) &&\n"
                     "            (translatedText != null || messageOwner.translatedPoll != null) &&",
                     "            TranslateController.isTranslatable(this) &&\n"
                     "            (translateController.isMessageManuallyTranslated(getDialogId(), getId()) || translateController.isTranslatingDialog(getDialogId()) && !translateController.isTranslateDialogHidden(getDialogId())) && // [mod] bubble translate\n"
                     "            (translatedText != null || messageOwner.translatedPoll != null) &&",
                     "bubble: MessageObject accepts manual translation")
        replace_once(ca,
                     "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang, toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
                     "                                alert.setDimBehind(false);\n"
                     "                                closeMenu(false);",
                     bubble_call +
                     "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang, toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
                     "                                alert.setDimBehind(false);\n"
                     "                                closeMenu(false);\n"
                     "                                }",
                     "bubble: translate click site 1")
        replace_once(ca,
                     "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang[0], toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
                     "                                alert.setDimBehind(false);\n"
                     "                                closeMenu(false);",
                     bubble_call +
                     "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang[0], toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
                     "                                alert.setDimBehind(false);\n"
                     "                                closeMenu(false);\n"
                     "                                }",
                     "bubble: translate click site 2")
        replace_once(ca,
                     "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, \"und\", toLang, finalMessageText, null, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
                     "                                alert.setDimBehind(false);\n"
                     "                                closeMenu(false);",
                     bubble_call +
                     "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, \"und\", toLang, finalMessageText, null, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
                     "                                alert.setDimBehind(false);\n"
                     "                                closeMenu(false);\n"
                     "                                }",
                     "bubble: translate click site 3")
        # Freeze hotfix for sources patched by an older version of section 7:
        # closeMenu(false) kept the dark scrim alive (the popup used to remove
        # it); without the popup the chat stayed dimmed and unresponsive.
        if file_contains(ca, "toggleManualMessageTranslation(selectedObject);\n                                    closeMenu(false);"):
            replace_all(ca,
                        "                                    getMessagesController().getTranslateController().toggleManualMessageTranslation(selectedObject);\n"
                        "                                    closeMenu(false);",
                        "                                    getMessagesController().getTranslateController().toggleManualMessageTranslation(selectedObject);\n"
                        "                                    closeMenu();",
                        "bubble: hotfix chat freeze after translate")
        # "Show Original" label for a manually translated bubble (both menus).
        replace_all(ca,
                    "                    items.add(LocaleController.getString(R.string.TranslateMessage));",
                    label_new,
                    "bubble: menu label (Show Original)")
        # A translated message returns null from getMessageTextToTranslate, so
        # the Translate option was never added for a translated bubble -> no
        # way to undo. Open the menu entry for manually translated messages.
        replace_once(ca,
                     "                if (selectedObject != null && selectedObject.contentType == 0 && (!TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(groupedMessages, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) {",
                     "                if (selectedObject != null && selectedObject.contentType == 0 && (getMessagesController().getTranslateController().isMessageManuallyTranslated(selectedObject) || !TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(groupedMessages, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) { // [mod] undo option",
                     "bubble: show undo entry site 1")
        replace_once(ca,
                     "                if (selectedObject != null && selectedObject.contentType == 0 && (!TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(selectedObjectGroup, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) {",
                     "                if (selectedObject != null && selectedObject.contentType == 0 && (getMessagesController().getTranslateController().isMessageManuallyTranslated(selectedObject) || !TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(selectedObjectGroup, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) { // [mod] undo option",
                     "bubble: show undo entry site 2")
        # Dedicated undo click branch (the normal translate path relies on
        # getMessageTextToTranslate which is null for a translated message).
        replace_once(ca,
                     "                    if (option == OPTION_TRANSLATE) {",
                     "                    if (option == OPTION_TRANSLATE && selectedObject != null && getMessagesController().getTranslateController().isMessageManuallyTranslated(selectedObject)) { // [mod] undo bubble translation\n"
                     "                        cell.setVisibility(View.VISIBLE);\n"
                     "                        cell.setOnClickListener(e2 -> {\n"
                     "                            if (selectedObject == null || i >= options.size()) {\n"
                     "                                return;\n"
                     "                            }\n"
                     "                            getMessagesController().getTranslateController().toggleManualMessageTranslation(selectedObject);\n"
                     "                            closeMenu();\n"
                     "                        });\n"
                     "                    } else if (option == OPTION_TRANSLATE) {",
                     "bubble: undo click branch")

    if cfg.get("rebrand", True):
        app_name = cfg.get("app_name", "YasTel")
        print("8) Rebrand: app name -> %s, package -> official Telegram" % app_name)
        strings = "TMessagesProj/src/main/res/values/strings.xml"
        # The afat-debug build shows AppNameBeta as the launcher label, so set
        # both AppName and AppNameBeta to keep the name right in every variant.
        replace_once(strings,
                     "<string name=\"AppName\">Telegram</string>",
                     "<string name=\"AppName\">%s</string>" % app_name,
                     "rebrand: AppName")
        replace_once(strings,
                     "<string name=\"AppNameBeta\">Telegram Beta</string>",
                     "<string name=\"AppNameBeta\">%s</string>" % app_name,
                     "rebrand: AppNameBeta")
        # Drop the ".beta" suffix on the debug build type. APP_PACKAGE is already
        # org.telegram.messenger, so the afat-debug package becomes the official
        # one -> installs over / replaces the official Telegram (uninstall the
        # official app first; signatures differ).
        replace_once("TMessagesProj_App/build.gradle",
                     "            applicationIdSuffix \".beta\"",
                     "            // applicationIdSuffix \".beta\" // [mod] YasTel: use official package to install over official Telegram",
                     "rebrand: official package")

    if cfg.get("sleep_inactive_accounts", True):
        print("9) Sleep inactive accounts (only the open account stays connected)")
        cm = "TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java"
        la = "TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java"
        sleep_helpers = (
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
        if not file_contains(cm, "isAccountAwake"):
            replace_once(cm,
                         "    public static void setLangCode(String langCode) {",
                         sleep_helpers + "    public static void setLangCode(String langCode) {",
                         "sleep: helpers in ConnectionsManager")
        else:
            print("  - [sleep: helpers in ConnectionsManager] already present, skipped.")
        # Hotfix for sources patched with the older helper: an account that is
        # being logged in is not selected yet and must NOT be put to sleep.
        replace_once(cm,
                     "        return !sleepInactiveAccounts || account < 0 || account == UserConfig.selectedAccount;\n",
                     "        if (!sleepInactiveAccounts || account < 0 || account == UserConfig.selectedAccount) {\n"
                     "            return true;\n"
                     "        }\n"
                     "        return !UserConfig.getInstance(account).isClientActivated(); // logging-in accounts stay awake\n",
                     "sleep: login-aware isAccountAwake",
                     optional=True)
        replace_once(cm,
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
                     "sleep: gate checkConnection")
        replace_once(cm,
                     "enablePushConnection, ApplicationLoader.isNetworkOnline(), ApplicationLoader.getCurrentNetworkType(), SharedConfig.measureDevicePerformanceClass());",
                     "enablePushConnection, isAccountAwake(currentAccount) && ApplicationLoader.isNetworkOnline(), ApplicationLoader.getCurrentNetworkType(), SharedConfig.measureDevicePerformanceClass());",
                     "sleep: gate init hasNetwork")
        replace_once(la,
                     "        UserConfig.selectedAccount = account;\n"
                     "        UserConfig.getInstance(0).saveConfig(false);",
                     "        UserConfig.selectedAccount = account;\n"
                     "        UserConfig.getInstance(0).saveConfig(false);\n"
                     "        ConnectionsManager.applyAccountSleepStates(); // [mod] sleep inactive accounts",
                     "sleep: hook switchToAccount")

    print("\n=== All modifications applied successfully ===")
    print("Now open the Telegram folder in Android Studio and Build.")


if __name__ == "__main__":
    main()
