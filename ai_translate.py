#!/usr/bin/env python3
# -*- coding: ascii -*-
# ai_translate.py
# ---------------
# Upgrades the translation engine from Google's basic word-by-word service to
# an AI model (OpenAI-compatible chat API, e.g. OpenRouter free models, OpenAI,
# Groq, Together, ...). Both whole-chat translation and single-bubble
# translation go through TranslateAlert2.alternativeTranslate(), so wiring the
# AI there upgrades BOTH at once.
#
# How to use:
#   1) Make a free API key (e.g. https://openrouter.ai -> Keys). Free models
#      exist (their id ends with ":free"); the key itself is free (no card).
#   2) Run this script (double-click the .bat). It asks for your API key, the
#      model id, and the base URL. Press Enter to keep the shown default.
#   3) Build normally in Android Studio and reinstall.
#
# The key is written ONLY into your local source (never committed anywhere).
# If the key is left empty, the app keeps using Google (safe fallback).
# Re-run any time to change the key/model. Creates one-time .bak12 backups.
# Java-only change: a NORMAL Gradle build is enough.

import os
import re
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

TA2_REL = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram",
                       "ui", "Components", "TranslateAlert2.java")

DEFAULT_BASE = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

ANCHOR_METHOD = "    public static void alternativeTranslate(String text, String fromLng, String toLng, Utilities.Callback2<String, Boolean> done) {"
ROUTE_OLD = ("        if (done == null) return;\n"
             "        if (fromLng == null) {")
ROUTE_NEW = ("        if (done == null) return;\n"
             "        if (isAiTranslateEnabled()) { aiTranslate(text, toLng, done); return; } // [mod] AI translation engine\n"
             "        if (fromLng == null) {")

AI_BLOCK = (
    "    // [mod] AI translation config (set by the ai_translate script)\n"
    "    public static String AI_BASE_URL = \"__BASE__\";\n"
    "    public static String AI_MODEL = \"__MODEL__\";\n"
    "    public static String AI_API_KEY = \"__KEY__\";\n"
    "\n"
    "    public static boolean isAiTranslateEnabled() {\n"
    "        return AI_API_KEY != null && AI_API_KEY.length() > 0;\n"
    "    }\n"
    "\n"
    "    public static void aiTranslate(String text, String toLng, Utilities.Callback2<String, Boolean> done) {\n"
    "        if (done == null) return;\n"
    "        new Thread() {\n"
    "            @Override\n"
    "            public void run() {\n"
    "                HttpURLConnection connection = null;\n"
    "                try {\n"
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
    "                    bodyJson.put(\"model\", AI_MODEL);\n"
    "                    bodyJson.put(\"messages\", messages);\n"
    "                    bodyJson.put(\"temperature\", 0.2);\n"
    "                    byte[] payload = bodyJson.toString().getBytes(\"UTF-8\");\n"
    "\n"
    "                    connection = (HttpURLConnection) new URI(AI_BASE_URL).toURL().openConnection();\n"
    "                    connection.setRequestMethod(\"POST\");\n"
    "                    connection.setRequestProperty(\"Content-Type\", \"application/json\");\n"
    "                    connection.setRequestProperty(\"Authorization\", \"Bearer \" + AI_API_KEY);\n"
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


def set_const(text, name, value):
    # replace  public static String NAME = "...";  keeping the value ASCII-safe
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    pat = r'(public static String %s = ")(.*?)(";)' % re.escape(name)
    return re.sub(pat, lambda m: m.group(1) + value + m.group(3), text, count=1)


def ask(prompt, current, default):
    shown = current if current else default
    try:
        val = raw_input("%s [%s]: " % (prompt, shown))  # py2
    except NameError:
        val = input("%s [%s]: " % (prompt, shown))
    val = val.strip()
    if not val:
        return current if current else default
    return val


def main():
    print("=== ai_translate: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    path = os.path.join(root, TA2_REL)
    print("Project root: %s\n" % root)

    text = read(path)

    # 1) inject the AI method + config block once
    if "isAiTranslateEnabled" not in text:
        if text.count(ANCHOR_METHOD) != 1:
            sys.exit("ERROR: alternativeTranslate anchor not found once (source differs).")
        block = AI_BLOCK.replace("__BASE__", DEFAULT_BASE).replace("__MODEL__", DEFAULT_MODEL).replace("__KEY__", "")
        text = text.replace(ANCHOR_METHOD, block + ANCHOR_METHOD, 1)
        print("  OK  AI translate method injected")
    else:
        print("  --  AI translate method already present")

    # 2) route alternativeTranslate through AI when a key is set
    if "aiTranslate(text, toLng, done); return; } // [mod] AI translation engine" not in text:
        if text.count(ROUTE_OLD) != 1:
            sys.exit("ERROR: routing anchor not found once (source differs).")
        text = text.replace(ROUTE_OLD, ROUTE_NEW, 1)
        print("  OK  routing added (AI when key set, else Google)")
    else:
        print("  --  routing already present")

    # read current values back
    def cur(name):
        m = re.search(r'public static String %s = "(.*?)";' % name, text)
        return m.group(1) if m else ""

    print("\nEnter your AI settings (press Enter to keep the shown value):")
    key = ask("  API key", cur("AI_API_KEY"), "")
    model = ask("  Model id", cur("AI_MODEL"), DEFAULT_MODEL)
    base = ask("  Base URL", cur("AI_BASE_URL"), DEFAULT_BASE)

    text = set_const(text, "AI_API_KEY", key)
    text = set_const(text, "AI_MODEL", model)
    text = set_const(text, "AI_BASE_URL", base)

    write(path, text)

    print("\n=== Saved ===")
    print("  key set  : %s" % ("YES" if key else "NO (app will use Google)"))
    print("  model    : %s" % model)
    print("  base URL : %s" % base)
    print("\nBuild normally in Android Studio and reinstall.")


if __name__ == "__main__":
    main()
