#!/usr/bin/env python3
# -*- coding: ascii -*-
# fix_bidi.py
# -----------
# Fixes scrambled mixed RTL/LTR translated text (e.g. a Persian line that
# contains English words, numbers, @usernames or links). It adds directional
# Unicode marks to the translation result so it displays in the right order:
#   * each line gets a leading RLM (U+200F) to force an RTL base direction,
#   * each run of Latin/number/symbol text is wrapped in an isolate
#     (LRI U+2066 ... PDI U+2069) so it stays a single left-to-right unit.
# Only applied when the target language is right-to-left (fa, ar, he, ur, ...);
# left-to-right targets are left unchanged.
#
# Patches TranslateAlert2.java (both the AI path and the Google path). Safe to
# run multiple times (idempotent). Creates one-time .bak13 backups.
# Java-only change: a NORMAL Gradle build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
TA2_REL = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram",
                       "ui", "Components", "TranslateAlert2.java")

applied = 0
skipped = 0
warnings = []

FIXBIDI_METHOD = (
    "    // [mod] fix bidi: keep mixed RTL/LTR translated text from scrambling.\n"
    "    public static String fixBidi(String text, String toLng) {\n"
    "        if (text == null || text.length() == 0) {\n"
    "            return text;\n"
    "        }\n"
    "        String lng = toLng == null ? \"\" : toLng.toLowerCase();\n"
    "        boolean rtl = lng.startsWith(\"fa\") || lng.startsWith(\"ar\") || lng.startsWith(\"he\") || lng.startsWith(\"iw\") || lng.startsWith(\"ur\") || lng.startsWith(\"ps\") || lng.startsWith(\"ckb\") || lng.startsWith(\"sd\") || lng.startsWith(\"ug\") || lng.startsWith(\"yi\") || lng.startsWith(\"dv\");\n"
    "        if (!rtl) {\n"
    "            return text;\n"
    "        }\n"
    "        final char RLM = '\\u200F';\n"
    "        final char LRI = '\\u2066';\n"
    "        final char PDI = '\\u2069';\n"
    "        String[] lines = text.split(\"\\n\", -1);\n"
    "        StringBuilder out = new StringBuilder();\n"
    "        for (int li = 0; li < lines.length; li++) {\n"
    "            if (li > 0) {\n"
    "                out.append('\\n');\n"
    "            }\n"
    "            String line = lines[li];\n"
    "            out.append(RLM);\n"
    "            int i = 0, n = line.length();\n"
    "            while (i < n) {\n"
    "                char c = line.charAt(i);\n"
    "                if (c >= 0x20 && c <= 0x7E) {\n"
    "                    int j = i;\n"
    "                    boolean alnum = false;\n"
    "                    while (j < n && line.charAt(j) >= 0x20 && line.charAt(j) <= 0x7E) {\n"
    "                        char cj = line.charAt(j);\n"
    "                        if ((cj >= 'A' && cj <= 'Z') || (cj >= 'a' && cj <= 'z') || (cj >= '0' && cj <= '9')) {\n"
    "                            alnum = true;\n"
    "                        }\n"
    "                        j++;\n"
    "                    }\n"
    "                    String run = line.substring(i, j);\n"
    "                    if (alnum) {\n"
    "                        out.append(LRI).append(run).append(PDI);\n"
    "                    } else {\n"
    "                        out.append(run);\n"
    "                    }\n"
    "                    i = j;\n"
    "                } else {\n"
    "                    out.append(c);\n"
    "                    i++;\n"
    "                }\n"
    "            }\n"
    "        }\n"
    "        return out.toString();\n"
    "    }\n"
    "\n"
)
METHOD_ANCHOR = "    public static void alternativeTranslate(String text, String fromLng, String toLng, Utilities.Callback2<String, Boolean> done) {"

AI_OLD = '                    String out = resp.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content").trim();\n'
AI_NEW = AI_OLD + '                    out = fixBidi(out, toLng);\n'

GOOGLE_OLD = ("                    if (text.length() > 0 && text.charAt(0) == '\\n')\n"
              "                        result = \"\\n\" + result;\n"
              "                    final String finalResult = result;")
GOOGLE_NEW = ("                    if (text.length() > 0 && text.charAt(0) == '\\n')\n"
              "                        result = \"\\n\" + result;\n"
              "                    result = fixBidi(result, toLng);\n"
              "                    final String finalResult = result;")


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
    if not os.path.isfile(path + ".bak13"):
        with open(path + ".bak13", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def do(text, old, new, needle, label):
    global applied, skipped
    if needle in text:
        print("  -- [%s] already applied, skipped" % label)
        skipped += 1
        return text
    count = text.count(old)
    if count != 1:
        warnings.append("[%s] anchor found %d times (expected 1)" % (label, count))
        print("  !! [%s] anchor found %d times, skipped" % (label, count))
        return text
    print("  OK [%s]" % label)
    applied += 1
    return text.replace(old, new, 1)


def main():
    print("=== fix_bidi: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    path = os.path.join(root, TA2_REL)
    print("Project root: %s\n" % root)

    text = read(path)
    print("1) fixBidi helper")
    text = do(text, METHOD_ANCHOR, FIXBIDI_METHOD + METHOD_ANCHOR,
              "public static String fixBidi(", "fixBidi helper")
    print("\n2) apply to AI translation output")
    if "String out = resp.getJSONArray(\"choices\")" in text:
        text = do(text, AI_OLD, AI_NEW, "out = fixBidi(out, toLng);", "AI output")
    else:
        print("  -- AI path not present (run ai_translate first if you want AI); skipped")
    print("\n3) apply to Google translation output")
    text = do(text, GOOGLE_OLD, GOOGLE_NEW, "result = fixBidi(result, toLng);", "Google output")

    write(path, text)
    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Java-only change: do a NORMAL build in Android Studio.")


if __name__ == "__main__":
    main()
