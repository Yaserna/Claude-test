#!/usr/bin/env python3
# -*- coding: ascii -*-
# ai_server_url.py
# ----------------
# Adds a "Server URL" field to the YasTel AI Translate settings dialog so you
# can point the app at any OpenAI-compatible endpoint (OpenRouter, Groq,
# OpenAI, a LiteLLM proxy, ...), not just OpenRouter. The translate code
# already reads this URL (pref "ai_translate_url"); this only adds the UI.
#
# Example endpoints:
#   OpenRouter : https://openrouter.ai/api/v1/chat/completions   (default)
#   Groq       : https://api.groq.com/openai/v1/chat/completions
#   OpenAI     : https://api.openai.com/v1/chat/completions
#
# Requires ai_translate.py to have been run first. Safe to run multiple times
# (idempotent). Creates one-time .bak17 backups. Java-only change.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
LSA_REL = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram",
                       "ui", "LanguageSelectActivity.java")

applied = 0
warnings = []

FIELD_ANCHOR = "        ll.addView(modelEdit);\n"
FIELD_NEW = FIELD_ANCHOR + (
    "        final EditText urlEdit = new EditText(context);\n"
    "        urlEdit.setHint(\"Server URL (OpenAI-compatible)\");\n"
    "        urlEdit.setSingleLine(true);\n"
    "        urlEdit.setText(prefs.getString(\"ai_translate_url\", \"https://openrouter.ai/api/v1/chat/completions\"));\n"
    "        ll.addView(urlEdit);\n"
)
SAVE_ANCHOR = '                .putString("ai_translate_model", modelEdit.getText().toString().trim())\n'
SAVE_NEW = SAVE_ANCHOR + (
    '                .putString("ai_translate_url", urlEdit.getText().toString().trim())\n'
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
            if os.path.isfile(os.path.join(direct, LSA_REL)):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, LSA_REL)):
                return root
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if not os.path.isfile(path + ".bak17"):
        with open(path + ".bak17", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def do(text, old, new, needle, label):
    global applied
    if needle in text:
        print("  -- [%s] already applied, skipped" % label)
        return text
    if text.count(old) != 1:
        warnings.append("[%s] anchor found %d times (expected 1)" % (label, text.count(old)))
        print("  !! [%s] anchor not found once, skipped" % label)
        return text
    print("  OK [%s]" % label)
    applied += 1
    return text.replace(old, new, 1)


def main():
    print("=== ai_server_url: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    path = os.path.join(root, LSA_REL)
    print("Project root: %s\n" % root)
    text = read(path)
    if "showAiTranslateSettings" not in text:
        sys.exit("ERROR: settings dialog not found. Run ai_translate.py first.")

    print("1) Add Server URL field")
    text = do(text, FIELD_ANCHOR, FIELD_NEW, "EditText urlEdit", "url field")
    print("\n2) Save the Server URL")
    text = do(text, SAVE_ANCHOR, SAVE_NEW,
              'putString("ai_translate_url", urlEdit', "url save")

    write(path, text)
    print("\n=== RESULT: %d applied, %d warnings ===" % (applied, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Build, then in Settings > Language > translate icon you can")
        print("set the Server URL (e.g. Groq) + its key + a model of that service.")


if __name__ == "__main__":
    main()
