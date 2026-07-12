#!/usr/bin/env python3
# -*- coding: ascii -*-
# ai_translate.py
# ---------------
# Upgrades translation to an AI model (OpenAI-compatible chat API, e.g.
# OpenRouter free models) AND lets you set the API key/model INSIDE the app --
# no rebuild needed to change the key later.
#
# What it does (Java only, no native recompile):
#   1) TranslateAlert2.java: adds aiTranslate() which POSTs to the AI endpoint,
#      reading the key/model from the app's own settings (SharedPreferences).
#      Both whole-chat and single-bubble translation route through it when the
#      key is set and AI is enabled; otherwise it falls back to Google.
#   2) LanguageSelectActivity.java (Settings > Language): adds a translate icon
#      in the top bar that opens a "YasTel AI Translate" dialog where you turn
#      it on/off and paste your API key + model id.
#
# In the app: Settings > Language > tap the translate icon (top-right) ->
# enable, paste your free OpenRouter key (openrouter.ai -> Keys), Save.
#
# Safe to run multiple times (idempotent). Migrates the older baked-key version
# of this script automatically (via its .bak12 backup). Creates one-time .bak12
# backups. Java-only change: a NORMAL Gradle build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

JAVA = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram")
TA2_REL = os.path.join(JAVA, "ui", "Components", "TranslateAlert2.java")
LSA_REL = os.path.join(JAVA, "ui", "LanguageSelectActivity.java")

applied = 0
skipped = 0
warnings = []

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

# ---- TranslateAlert2: AI method (reads key/model from app settings) ----------
AI_METHOD = (
    "    // [mod] AI translation: key/model come from the app settings\n"
    "    // (Settings > Language > translate icon). Falls back to Google if off.\n"
    "    public static boolean isAiTranslateEnabled() {\n"
    "        android.content.SharedPreferences p = org.telegram.messenger.MessagesController.getGlobalMainSettings();\n"
    "        return p.getBoolean(\"ai_translate_enabled\", false) && p.getString(\"ai_translate_key\", \"\").length() > 0;\n"
    "    }\n"
    "\n"
    "    public static void aiTranslate(String text, String toLng, Utilities.Callback2<String, Boolean> done) {\n"
    "        if (done == null) return;\n"
    "        new Thread() {\n"
    "            @Override\n"
    "            public void run() {\n"
    "                HttpURLConnection connection = null;\n"
    "                try {\n"
    "                    android.content.SharedPreferences p = org.telegram.messenger.MessagesController.getGlobalMainSettings();\n"
    "                    String apiKey = p.getString(\"ai_translate_key\", \"\");\n"
    "                    String model = p.getString(\"ai_translate_model\", \"" + DEFAULT_MODEL + "\");\n"
    "                    String baseUrl = p.getString(\"ai_translate_url\", \"https://openrouter.ai/api/v1/chat/completions\");\n"
    "                    String target = (toLng == null || toLng.length() == 0) ? \"en\" : toLng;\n"
    "                    org.json.JSONObject sys = new org.json.JSONObject();\n"
    "                    sys.put(\"role\", \"system\");\n"
    "                    sys.put(\"content\", \"You are a professional translation engine. Translate the user's message into the language with ISO 639-1 code \\\"\" + target + \"\\\". Output only the translation itself, with no quotes and no extra words. Preserve line breaks, emojis, @mentions, #hashtags and links exactly.\");\n"
    "                    org.json.JSONObject usr = new org.json.JSONObject();\n"
    "                    usr.put(\"role\", \"user\");\n"
    "                    usr.put(\"content\", text);\n"
    "                    org.json.JSONArray messages = new org.json.JSONArray();\n"
    "                    messages.put(sys);\n"
    "                    messages.put(usr);\n"
    "                    org.json.JSONObject bodyJson = new org.json.JSONObject();\n"
    "                    bodyJson.put(\"model\", model);\n"
    "                    bodyJson.put(\"messages\", messages);\n"
    "                    bodyJson.put(\"temperature\", 0.2);\n"
    "                    byte[] payload = bodyJson.toString().getBytes(\"UTF-8\");\n"
    "\n"
    "                    connection = (HttpURLConnection) new URI(baseUrl).toURL().openConnection();\n"
    "                    connection.setRequestMethod(\"POST\");\n"
    "                    connection.setRequestProperty(\"Content-Type\", \"application/json\");\n"
    "                    connection.setRequestProperty(\"Authorization\", \"Bearer \" + apiKey);\n"
    "                    connection.setConnectTimeout(15000);\n"
    "                    connection.setReadTimeout(40000);\n"
    "                    connection.setDoOutput(true);\n"
    "                    java.io.OutputStream os = connection.getOutputStream();\n"
    "                    os.write(payload);\n"
    "                    os.close();\n"
    "\n"
    "                    int status = connection.getResponseCode();\n"
    "                    java.io.InputStream is = (status >= 200 && status < 300) ? connection.getInputStream() : connection.getErrorStream();\n"
    "                    StringBuilder sb = new StringBuilder();\n"
    "                    if (is != null) {\n"
    "                        Reader reader = new BufferedReader(new InputStreamReader(is, Charsets.UTF_8));\n"
    "                        int c;\n"
    "                        while ((c = reader.read()) != -1) {\n"
    "                            sb.append((char) c);\n"
    "                        }\n"
    "                        reader.close();\n"
    "                    }\n"
    "                    if (status < 200 || status >= 300) {\n"
    "                        throw new Exception(\"AI HTTP \" + status);\n"
    "                    }\n"
    "                    org.json.JSONObject resp = new org.json.JSONObject(sb.toString());\n"
    "                    String out = resp.getJSONArray(\"choices\").getJSONObject(0).getJSONObject(\"message\").getString(\"content\").trim();\n"
    "                    final String finalOut = out;\n"
    "                    AndroidUtilities.runOnUIThread(() -> {\n"
    "                        if (done != null) done.run(finalOut, false);\n"
    "                    });\n"
    "                } catch (Exception e) {\n"
    "                    AndroidUtilities.runOnUIThread(() -> {\n"
    "                        if (done != null) done.run(null, false);\n"
    "                    });\n"
    "                } finally {\n"
    "                    if (connection != null) {\n"
    "                        try { connection.disconnect(); } catch (Exception ignore) {}\n"
    "                    }\n"
    "                }\n"
    "            }\n"
    "        }.start();\n"
    "    }\n"
    "\n"
)
TA2_ANCHOR = "    public static void alternativeTranslate(String text, String fromLng, String toLng, Utilities.Callback2<String, Boolean> done) {"
TA2_ROUTE_OLD = ("        if (done == null) return;\n"
                 "        if (fromLng == null) {")
TA2_ROUTE_NEW = ("        if (done == null) return;\n"
                 "        if (isAiTranslateEnabled()) { aiTranslate(text, toLng, done); return; } // [mod] AI translation engine\n"
                 "        if (fromLng == null) {")

# ---- LanguageSelectActivity: settings dialog ---------------------------------
LSA_METHOD = (
    "    private void showAiTranslateSettings() {\n"
    "        android.content.Context context = getParentActivity();\n"
    "        if (context == null) {\n"
    "            return;\n"
    "        }\n"
    "        final android.content.SharedPreferences prefs = MessagesController.getGlobalMainSettings();\n"
    "        android.widget.LinearLayout ll = new android.widget.LinearLayout(context);\n"
    "        ll.setOrientation(android.widget.LinearLayout.VERTICAL);\n"
    "        int pad = org.telegram.messenger.AndroidUtilities.dp(22);\n"
    "        ll.setPadding(pad, org.telegram.messenger.AndroidUtilities.dp(8), pad, 0);\n"
    "        final android.widget.CheckBox enableBox = new android.widget.CheckBox(context);\n"
    "        enableBox.setText(\"Use AI translation (off = Google)\");\n"
    "        enableBox.setChecked(prefs.getBoolean(\"ai_translate_enabled\", false));\n"
    "        ll.addView(enableBox);\n"
    "        final EditText keyEdit = new EditText(context);\n"
    "        keyEdit.setHint(\"API key (sk-or-v1-...)\");\n"
    "        keyEdit.setSingleLine(true);\n"
    "        keyEdit.setText(prefs.getString(\"ai_translate_key\", \"\"));\n"
    "        ll.addView(keyEdit);\n"
    "        final EditText modelEdit = new EditText(context);\n"
    "        modelEdit.setHint(\"Model id\");\n"
    "        modelEdit.setSingleLine(true);\n"
    "        modelEdit.setText(prefs.getString(\"ai_translate_model\", \"" + DEFAULT_MODEL + "\"));\n"
    "        ll.addView(modelEdit);\n"
    "        AlertDialog.Builder builder = new AlertDialog.Builder(context);\n"
    "        builder.setTitle(\"YasTel AI Translate\");\n"
    "        builder.setView(ll);\n"
    "        builder.setPositiveButton(LocaleController.getString(R.string.Save), (dialog, which) -> {\n"
    "            prefs.edit()\n"
    "                .putBoolean(\"ai_translate_enabled\", enableBox.isChecked())\n"
    "                .putString(\"ai_translate_key\", keyEdit.getText().toString().trim())\n"
    "                .putString(\"ai_translate_model\", modelEdit.getText().toString().trim())\n"
    "                .apply();\n"
    "        });\n"
    "        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);\n"
    "        showDialog(builder.create());\n"
    "    }\n"
    "\n"
)
LSA_MENU_OLD = "        ActionBarMenu menu = actionBar.createMenu();\n"
LSA_MENU_NEW = ("        ActionBarMenu menu = actionBar.createMenu();\n"
                "        menu.addItem(1001, R.drawable.msg_translate); // [mod] YasTel AI translate settings\n")
LSA_CLICK_OLD = ("                if (id == -1) {\n"
                 "                    finishFragment();\n"
                 "                }")
LSA_CLICK_NEW = ("                if (id == -1) {\n"
                 "                    finishFragment();\n"
                 "                } else if (id == 1001) { // [mod] YasTel AI translate settings\n"
                 "                    showAiTranslateSettings();\n"
                 "                }")
LSA_ANCHOR = "    @Override\n    public View createView(Context context) {"


def find_project_root():
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    candidates = []
    for base in (cwd, here):
        if base not in candidates:
            candidates.append(base)
    for base in candidates:
        for direct in (base, os.path.join(base, "Telegram")):
            if os.path.isfile(os.path.join(direct, TA2_REL)):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, TA2_REL)):
                return root
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if not os.path.isfile(path + ".bak12"):
        with open(path + ".bak12", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def replace_once(text, old, new, label):
    global applied
    count = text.count(old)
    if count != 1:
        warnings.append("[%s] anchor found %d times (expected 1)" % (label, count))
        print("  !! [%s] anchor found %d times, skipped" % (label, count))
        return text, False
    print("  OK [%s]" % label)
    applied += 1
    return text.replace(old, new, 1), True


def patch_ta2(root):
    global skipped
    path = os.path.join(root, TA2_REL)
    text = read(path)
    # migrate the older baked-key version of this script, if present
    if "AI_API_KEY" in text and "ai_translate_key" not in text:
        bak = path + ".bak12"
        if os.path.isfile(bak):
            print("  .. migrating older baked-key AI version (restoring .bak12)")
            text = read(bak)
        else:
            warnings.append("old baked-key AI version found but no .bak12 to "
                            "restore; revert TranslateAlert2.java manually first")
            print("  !! old AI version present, cannot migrate (no backup)")
            return
    changed = False
    if "ai_translate_key" in text and "isAiTranslateEnabled" in text:
        print("  -- [ta2: AI method] already applied, skipped")
        skipped += 1
    else:
        if text.count(TA2_ANCHOR) != 1:
            warnings.append("[ta2: AI method] anchor not found once")
            print("  !! [ta2: AI method] anchor not found, skipped")
            return
        text = text.replace(TA2_ANCHOR, AI_METHOD + TA2_ANCHOR, 1)
        print("  OK [ta2: AI method]")
        changed = True
    if "aiTranslate(text, toLng, done); return; } // [mod] AI translation engine" in text:
        print("  -- [ta2: routing] already applied, skipped")
        skipped += 1
    else:
        text, ok = replace_once(text, TA2_ROUTE_OLD, TA2_ROUTE_NEW, "ta2: routing")
        changed = changed or ok
    if changed or True:
        write(path, text)


def patch_lsa(root):
    global skipped
    path = os.path.join(root, LSA_REL)
    if not os.path.isfile(path):
        warnings.append("LanguageSelectActivity.java not found")
        print("  !! LanguageSelectActivity.java NOT FOUND")
        return
    text = read(path)
    if "showAiTranslateSettings" in text:
        print("  -- [settings UI] already applied, skipped")
        skipped += 1
        return
    text, _ = replace_once(text, LSA_MENU_OLD, LSA_MENU_NEW, "lsa: menu item")
    text, _ = replace_once(text, LSA_CLICK_OLD, LSA_CLICK_NEW, "lsa: click handler")
    if text.count(LSA_ANCHOR) == 1:
        text = text.replace(LSA_ANCHOR, LSA_METHOD + LSA_ANCHOR, 1)
        print("  OK [lsa: settings method]")
        global applied
        applied += 1
    else:
        warnings.append("[lsa: settings method] createView anchor not found once")
        print("  !! [lsa: settings method] anchor not found, skipped")
    write(path, text)


def main():
    print("=== ai_translate: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    print("1) AI translate engine in TranslateAlert2")
    patch_ta2(root)
    print("\n2) In-app settings in Settings > Language")
    patch_lsa(root)

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Build normally, then in the app open")
        print("Settings > Language > tap the translate icon (top bar) to set your key.")


if __name__ == "__main__":
    main()
