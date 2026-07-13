#!/usr/bin/env python3
# -*- coding: ascii -*-
# translate_fixes.py
# ------------------
# Two fixes:
#   1) Compose translate button overlapped the attach (paperclip) button. Move
#      it to the LEFT of the input bar, right next to the emoji button, where
#      there are no dynamic buttons -- so it never overlaps the attach / bot /
#      gift buttons that appear in groups and bots.
#   2) Whole-chat translation used to fire every bubble at once and, on a
#      single slow/rate-limited failure, turn OFF the whole dialog translation
#      and show a "translation failed" popup. Now bubbles are translated ONE AT
#      A TIME; each is applied (and cached in the DB) as soon as it is ready,
#      and a single failure is skipped silently without stopping the rest.
#      (Translations are already stored per message, so re-viewing them costs
#      no tokens and shows instantly.)
#
# Java only, no native recompile. Safe to run multiple times (idempotent).
# Creates one-time .bak15 backups.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
JAVA = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram")
CEV_REL = os.path.join(JAVA, "ui", "Components", "ChatActivityEnterView.java")
TC_REL = os.path.join(JAVA, "messenger", "TranslateController.java")

applied = 0
skipped = 0
warnings = []

# ---- shared onclick used by both old and new button ----
ONCLICK = (
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

# old (top-right) button block to remove
OLD_BUTTON = (
    "        final android.widget.ImageView translateComposeButton = new android.widget.ImageView(context); // [mod] compose translate\n"
    "        translateComposeButton.setImageResource(R.drawable.msg_translate);\n"
    "        translateComposeButton.setScaleType(android.widget.ImageView.ScaleType.CENTER);\n"
    "        translateComposeButton.setColorFilter(new PorterDuffColorFilter(getThemedColor(Theme.key_glass_defaultIcon), PorterDuff.Mode.MULTIPLY));\n"
    "        translateComposeButton.setBackground(Theme.createSelectorDrawable(getThemedColor(Theme.key_listSelector), Theme.RIPPLE_MASK_CIRCLE_20DP, dp(16)));\n"
    "        textFieldContainer.addView(translateComposeButton, LayoutHelper.createFrame(DEFAULT_HEIGHT, DEFAULT_HEIGHT, Gravity.TOP | Gravity.RIGHT, 0, 1, DEFAULT_HEIGHT, 0));\n"
    "        translateComposeButton.setContentDescription(\"Translate typed text\");\n"
    "        ScaleStateListAnimator.apply(translateComposeButton);\n"
    + ONCLICK
)

# new (bottom-left, next to emoji) button block
EMOJI_ANCHOR = "        setEmojiButtonImage(false, false);\n"
NEW_BUTTON = (
    "        final android.widget.ImageView translateComposeButton = new android.widget.ImageView(context); // [mod] compose translate (left)\n"
    "        translateComposeButton.setImageResource(R.drawable.msg_translate);\n"
    "        translateComposeButton.setScaleType(android.widget.ImageView.ScaleType.CENTER);\n"
    "        translateComposeButton.setColorFilter(new PorterDuffColorFilter(getThemedColor(Theme.key_glass_defaultIcon), PorterDuff.Mode.MULTIPLY));\n"
    "        translateComposeButton.setBackground(Theme.createSelectorDrawable(getThemedColor(Theme.key_listSelector), Theme.RIPPLE_MASK_CIRCLE_20DP, dp(16)));\n"
    "        messageEditTextContainer.addView(translateComposeButton, LayoutHelper.createFrame(DEFAULT_HEIGHT, DEFAULT_HEIGHT, Gravity.BOTTOM | Gravity.LEFT, 52, 0, 0, 0));\n"
    "        translateComposeButton.setContentDescription(\"Translate typed text\");\n"
    "        ScaleStateListAnimator.apply(translateComposeButton);\n"
    + ONCLICK
)

MARGIN_OLD = "Gravity.BOTTOM, 52, 0, isChat ? 50 : 2, 1.5f"
MARGIN_NEW = "Gravity.BOTTOM, 96, 0, isChat ? 50 : 2, 1.5f"

# ---- TC sequential translate ----
TC_OLD = (
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
TC_NEW = (
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
    if not os.path.isfile(path + ".bak15"):
        with open(path + ".bak15", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    global applied, skipped
    print("=== translate_fixes: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)
    cev = os.path.join(root, CEV_REL)
    tc = os.path.join(root, TC_REL)

    # ---- 1) move the compose button to the left ----
    print("1) Move compose translate button to the left (no overlap)")
    text = read(cev)
    changed = False
    if "messageEditTextContainer.addView(translateComposeButton" in text:
        print("  -- button already on the left, skipped")
        skipped += 1
    else:
        if OLD_BUTTON in text:
            text = text.replace(OLD_BUTTON, "", 1)
            print("  OK removed old top-right button")
        if EMOJI_ANCHOR in text:
            text = text.replace(EMOJI_ANCHOR, EMOJI_ANCHOR + NEW_BUTTON, 1)
            print("  OK added left button next to emoji")
            changed = True
            applied += 1
        else:
            warnings.append("emoji anchor not found in ChatActivityEnterView")
            print("  !! emoji anchor not found, skipped")
    if MARGIN_NEW in text:
        print("  -- text field margin already shifted, skipped")
    elif text.count(MARGIN_OLD) == 1:
        text = text.replace(MARGIN_OLD, MARGIN_NEW, 1)
        print("  OK shifted text field left margin (52 -> 96)")
        changed = True
    else:
        warnings.append("messageEditText margin anchor not found once")
        print("  !! text field margin anchor not found, skipped")
    if changed:
        write(cev, text)

    # ---- 2) sequential whole-chat translation ----
    print("\n2) Translate whole-chat bubbles one-by-one (no whole-batch failure)")
    ttext = read(tc)
    if "_seqNext" in ttext:
        print("  -- already applied, skipped")
        skipped += 1
    elif ttext.count(TC_OLD) == 1:
        write(tc, ttext.replace(TC_OLD, TC_NEW, 1))
        print("  OK sequential translation applied")
        applied += 1
    else:
        warnings.append("TranslateController whole-chat loop anchor not found once "
                        "(found %d)" % ttext.count(TC_OLD))
        print("  !! whole-chat loop anchor not found, skipped")

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Java-only change: do a NORMAL build in Android Studio.")


if __name__ == "__main__":
    main()
