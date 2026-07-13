#!/usr/bin/env python3
# -*- coding: ascii -*-
# compose_translate.py
# --------------------
# Adds a "translate what I typed" button to the message input bar. Tapping it
# translates the current draft (the text you are typing) into your chosen
# compose-target language and replaces the text in place. It uses the same
# engine as message translation (AI if enabled in Settings > Language, else
# Google) and the same RTL/LTR fix.
#
# Two patches (Java only, no native recompile):
#   1) ChatActivityEnterView.java: a translate icon next to the AI-editor icon
#      at the top-right of the text field; on click it translates the draft.
#   2) LanguageSelectActivity.java: the "YasTel AI Translate" dialog gets an
#      extra field "Compose translate target" (ISO code, e.g. en) so you can
#      choose the language the compose button translates into.
#
# Requires ai_translate.py to have been run first (for the settings dialog and
# the translate engine). Safe to run multiple times (idempotent). Creates
# one-time .bak14 backups.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
JAVA = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram")
CEV_REL = os.path.join(JAVA, "ui", "Components", "ChatActivityEnterView.java")
LSA_REL = os.path.join(JAVA, "ui", "LanguageSelectActivity.java")

applied = 0
skipped = 0
warnings = []

# ---- 1) the button in the input bar (left side, next to the emoji button, so
#         it never overlaps the dynamic attach / bot / gift buttons) -----------
CEV_ANCHOR = "        setEmojiButtonImage(false, false);\n"
CEV_BUTTON = (
    "        final android.widget.ImageView translateComposeButton = new android.widget.ImageView(context); // [mod] compose translate (left)\n"
    "        translateComposeButton.setImageResource(R.drawable.msg_translate);\n"
    "        translateComposeButton.setScaleType(android.widget.ImageView.ScaleType.CENTER);\n"
    "        translateComposeButton.setColorFilter(new PorterDuffColorFilter(getThemedColor(Theme.key_glass_defaultIcon), PorterDuff.Mode.MULTIPLY));\n"
    "        translateComposeButton.setBackground(Theme.createSelectorDrawable(getThemedColor(Theme.key_listSelector), Theme.RIPPLE_MASK_CIRCLE_20DP, dp(16)));\n"
    "        messageEditTextContainer.addView(translateComposeButton, LayoutHelper.createFrame(DEFAULT_HEIGHT, DEFAULT_HEIGHT, Gravity.BOTTOM | Gravity.LEFT, 52, 0, 0, 0));\n"
    "        translateComposeButton.setContentDescription(\"Translate typed text\");\n"
    "        ScaleStateListAnimator.apply(translateComposeButton);\n"
    "        translateComposeButton.setOnClickListener(v -> {\n"
    "            if (messageEditText == null) return;\n"
    "            CharSequence cs = messageEditText.getText();\n"
    "            if (cs == null || cs.length() == 0) return;\n"
    "            String toLng = MessagesController.getGlobalMainSettings().getString(\"compose_translate_to\", \"en\");\n"
    "            final String src = cs.toString();\n"
    "            org.telegram.messenger.Utilities.Callback2<String, Boolean> cb = (res, rl) -> {\n"
    "                if (res != null && messageEditText != null) {\n"
    "                    messageEditText.setText(res);\n"
    "                    try { messageEditText.setSelection(messageEditText.length()); } catch (Exception ignore) {}\n"
    "                }\n"
    "            };\n"
    "            TranslateAlert2.alternativeTranslate(src, null, toLng, cb);\n"
    "        });\n"
)
CEV_MARGIN_OLD = "Gravity.BOTTOM, 52, 0, isChat ? 50 : 2, 1.5f"
CEV_MARGIN_NEW = "Gravity.BOTTOM, 96, 0, isChat ? 50 : 2, 1.5f"

# ---- 2) compose-target field in the settings dialog --------------------------
# Anchor on ll.addView(modelEdit) only (NOT the model default string, which
# varies with when ai_translate was run), so the field is always inserted.
LSA_FIELD_ANCHOR = "        ll.addView(modelEdit);\n"
LSA_FIELD_NEW = LSA_FIELD_ANCHOR + (
    "        final EditText composeEdit = new EditText(context);\n"
    "        composeEdit.setHint(\"Compose translate target (e.g. en)\");\n"
    "        composeEdit.setSingleLine(true);\n"
    "        composeEdit.setText(prefs.getString(\"compose_translate_to\", \"en\"));\n"
    "        ll.addView(composeEdit);\n"
)
LSA_SAVE_ANCHOR = (
    '                .putString("ai_translate_model", modelEdit.getText().toString().trim())\n'
    "                .apply();"
)
LSA_SAVE_NEW = (
    '                .putString("ai_translate_model", modelEdit.getText().toString().trim())\n'
    '                .putString("compose_translate_to", composeEdit.getText().toString().trim())\n'
    "                .apply();"
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
            if os.path.isfile(os.path.join(direct, CEV_REL)):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, CEV_REL)):
                return root
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if not os.path.isfile(path + ".bak14"):
        with open(path + ".bak14", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def patch(path, old, new, needle, label):
    global applied, skipped
    if not os.path.isfile(path):
        warnings.append("[%s] file not found" % label)
        print("  !! [%s] FILE NOT FOUND" % label)
        return
    text = read(path)
    if needle in text:
        print("  -- [%s] already applied, skipped" % label)
        skipped += 1
        return
    count = text.count(old)
    if count != 1:
        warnings.append("[%s] anchor found %d times (expected 1)" % (label, count))
        print("  !! [%s] anchor found %d times, skipped" % (label, count))
        return
    write(path, text.replace(old, new, 1))
    print("  OK [%s]" % label)
    applied += 1


def main():
    print("=== compose_translate: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)
    cev = os.path.join(root, CEV_REL)
    lsa = os.path.join(root, LSA_REL)

    print("1) Translate button in the message input bar (left side)")
    patch(cev, CEV_ANCHOR, CEV_ANCHOR + CEV_BUTTON,
          "translateComposeButton", "compose button")
    patch(cev, CEV_MARGIN_OLD, CEV_MARGIN_NEW,
          "Gravity.BOTTOM, 96, 0, isChat", "compose button: text margin")

    print("\n2) Compose-target field in the settings dialog")
    if not os.path.isfile(lsa) or "showAiTranslateSettings" not in read(lsa):
        warnings.append("settings dialog not found; run ai_translate.py first")
        print("  !! settings dialog not found -- run ai_translate.py first")
    else:
        patch(lsa, LSA_FIELD_ANCHOR, LSA_FIELD_NEW, "EditText composeEdit", "settings field")
        patch(lsa, LSA_SAVE_ANCHOR, LSA_SAVE_NEW,
              'putString("compose_translate_to", composeEdit', "settings save")

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Build normally. Type some text in a chat and tap the")
        print("translate icon at the top-right of the input bar.")


if __name__ == "__main__":
    main()
