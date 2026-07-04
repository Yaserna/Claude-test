#!/usr/bin/env python3
# -*- coding: ascii -*-
# bubble_translate_and_tags.py
# ----------------------------
# Run this on your local Telegram source (same folder layout as before).
# It applies three groups of changes:
#
#   A) Account number tag (#1, #2, ...) in MORE places:
#      - your own profile page header (ProfileActivity)
#      - the Settings screen header (SettingsActivity)
#      - the accounts list inside Settings (SettingsActivity.AccountCell)
#
#   B) Translate bar at the top of EVERY chat/group:
#      - no premium needed, no Google-ML language detection needed
#        (language detection is blocked on devices without Google services,
#        which is why the bar never appeared before)
#      - tap the bar -> whole chat translates inline in the bubbles
#      - the small menu (customize icon) works for everyone
#
#   C) In-bubble translation for a SINGLE message:
#      - long press a message -> Translate -> the bubble itself is translated
#        (no popup window anymore)
#      - long press the translated message again -> "Show Original" restores
#        the original text
#
# Safe to run multiple times (idempotent). Creates one-time .bak5 backups.
# Java-only changes: a NORMAL Gradle build is enough (no .cxx/build cleanup).

import os
import sys

JAVA_BASE = os.path.join("TMessagesProj", "src", "main", "java")

FILES = {
    "UserConfig":          os.path.join("org", "telegram", "messenger", "UserConfig.java"),
    "TranslateController": os.path.join("org", "telegram", "messenger", "TranslateController.java"),
    "MessageObject":       os.path.join("org", "telegram", "messenger", "MessageObject.java"),
    "ChatActivity":        os.path.join("org", "telegram", "ui", "ChatActivity.java"),
    "TranslateButton":     os.path.join("org", "telegram", "ui", "Components", "TranslateButton.java"),
    "ProfileActivity":     os.path.join("org", "telegram", "ui", "ProfileActivity.java"),
    "SettingsActivity":    os.path.join("org", "telegram", "ui", "SettingsActivity.java"),
}

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

applied = 0
skipped = 0
warnings = []


def find_project_root():
    """Find the folder that contains TMessagesProj/src/main/java/..., while
    ignoring build copies (build/.cxx/intermediates/.gradle)."""
    probe = os.path.join("TMessagesProj", "src", "main", "java", "org",
                         "telegram", "messenger", "UserConfig.java")
    candidates = []
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    for base in (cwd, here):
        if base not in candidates:
            candidates.append(base)
    for base in candidates:
        # direct hit first (script placed next to the Telegram folder or inside it)
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
    if not os.path.isfile(path + ".bak5"):
        with open(path + ".bak5", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def patch(root, file_key, old, new, label, optional=False):
    """Idempotent single replacement. Never stops the script: unexpected
    situations are collected as warnings and printed in the final report.
    optional=True: absence of the old text is normal (hotfix for a previous
    script version) and is not even reported as a warning."""
    global applied, skipped
    path = os.path.join(root, JAVA_BASE, FILES[file_key])
    if not os.path.isfile(path):
        warnings.append("[%s] file not found: %s" % (label, path))
        print("  !! [%s] FILE NOT FOUND" % label)
        return
    text = read(path)
    if new in text:
        print("  -- [%s] already applied, skipped" % label)
        skipped += 1
        return
    count = text.count(old)
    if count == 0:
        if optional:
            print("  -- [%s] not needed on this copy" % label)
            skipped += 1
            return
        warnings.append("[%s] original text not found in %s "
                        "(source differs; patch not applied)" % (label, FILES[file_key]))
        print("  !! [%s] original text NOT FOUND, skipped" % label)
        return
    if count > 1:
        warnings.append("[%s] original text found %d times in %s "
                        "(expected 1; patch not applied)" % (label, count, FILES[file_key]))
        print("  !! [%s] found %d times, skipped" % (label, count))
        return
    write(path, text.replace(old, new, 1))
    print("  OK [%s]" % label)
    applied += 1


def patch_multi(root, file_key, old, new, label):
    """Idempotent replacement of EVERY occurrence (used when the same text
    appears at several places on purpose)."""
    global applied, skipped
    path = os.path.join(root, JAVA_BASE, FILES[file_key])
    if not os.path.isfile(path):
        warnings.append("[%s] file not found: %s" % (label, path))
        print("  !! [%s] FILE NOT FOUND" % label)
        return
    text = read(path)
    count = text.count(old)
    if count == 0:
        if new in text:
            print("  -- [%s] already applied, skipped" % label)
            skipped += 1
        else:
            print("  -- [%s] not needed on this copy" % label)
            skipped += 1
        return
    write(path, text.replace(old, new))
    print("  OK [%s] (%d places)" % (label, count))
    applied += 1


def contains(root, file_key, needle):
    path = os.path.join(root, JAVA_BASE, FILES[file_key])
    return os.path.isfile(path) and needle in read(path)


TAG_HELPER = (
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

MANUAL_TRANSLATION_HELPER = (
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


def main():
    print("=== bubble_translate_and_tags: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    # ------------------------------------------------------------------
    # 0) Prerequisites (in case an earlier script was not run on this copy)
    # ------------------------------------------------------------------
    print("0) Prerequisites")
    if not contains(root, "UserConfig", "getAccountTagNumber"):
        patch(root, "UserConfig",
              "    public static int getActivatedAccountsCount() {",
              TAG_HELPER + "\n    public static int getActivatedAccountsCount() {",
              "pre: login-order tag helper in UserConfig")
    else:
        print("  -- [pre: login-order tag helper in UserConfig] already present")

    patch(root, "TranslateController",
          "    public boolean isFeatureAvailable() {\n"
          "        return isChatTranslateEnabled() && UserConfig.getInstance(currentAccount).isPremium();\n"
          "    }",
          "    public boolean isFeatureAvailable() {\n"
          "        return isChatTranslateEnabled();\n"
          "    }",
          "pre: chat translate feature for all")
    patch(root, "TranslateController",
          "        final TLRPC.Chat chat = getMessagesController().getChat(-dialogId);\n"
          "        return (\n"
          "            UserConfig.getInstance(currentAccount).isPremium() ||\n"
          "            chat != null && chat.autotranslation\n"
          "        );",
          "        return true; // [mod] chat/group translate enabled for everyone",
          "pre: per-dialog translate feature for all")

    # ------------------------------------------------------------------
    # A) Account number tag in more places
    # ------------------------------------------------------------------
    print("\nA) Account number tag in more places")
    patch(root, "ProfileActivity",
          "            CharSequence newString = UserObject.getUserName(user);\n"
          "            String newString2;",
          "            CharSequence newString = UserObject.getUserName(user);\n"
          "            if (user.id == getUserConfig().getClientUserId()) { newString = \"#\" + UserConfig.getAccountTagNumber(currentAccount) + \" \" + newString; } // [mod] account number tag (own profile)\n"
          "            String newString2;",
          "tag: own profile header")
    patch(root, "SettingsActivity",
          "        titleView.setText(UserObject.getUserName(user));",
          "        titleView.setText(\"#\" + UserConfig.getAccountTagNumber(currentAccount) + \" \" + UserObject.getUserName(user)); // [mod] account number tag (settings header)",
          "tag: settings header")
    patch(root, "SettingsActivity",
          "            textView.setText(UserObject.getUserName(user));",
          "            textView.setText(\"#\" + UserConfig.getAccountTagNumber(account) + \" \" + UserObject.getUserName(user)); // [mod] account number tag (settings accounts list)",
          "tag: settings accounts list")

    # ------------------------------------------------------------------
    # B) Translate bar at the top of every chat/group
    # ------------------------------------------------------------------
    print("\nB) Translate bar on top of every chat")
    # The bar used to require Google-ML language detection to mark a dialog as
    # translatable; that never completes on devices without Google services.
    patch(root, "TranslateController",
          "        return (\n"
          "            translatableDialogs.contains(dialogId) &&\n"
          "            isFeatureAvailable(dialogId) &&",
          "        return (\n"
          "            isFeatureAvailable(dialogId) && // [mod] translate bar in all chats (no language detection needed)",
          "bar: isDialogTranslatable without detection")
    patch(root, "ChatActivity",
          "        boolean showTranslate = (\n"
          "            getUserConfig().isPremium() || currentChat != null && currentChat.autotranslation ?\n"
          "                getMessagesController().getTranslateController().isDialogTranslatable(getDialogId()) && !getMessagesController().getTranslateController().isTranslateDialogHidden(getDialogId()) :\n"
          "                !getMessagesController().premiumFeaturesBlocked() && preferences.getInt(\"dialog_show_translate_count\" + did, 5) <= 0\n"
          "        ) || DEBUG_TOP_PANELS;",
          "        boolean showTranslate = (\n"
          "            getMessagesController().getTranslateController().isDialogTranslatable(getDialogId()) && !getMessagesController().getTranslateController().isTranslateDialogHidden(getDialogId()) // [mod] translate bar for everyone\n"
          "        ) || DEBUG_TOP_PANELS;",
          "bar: show condition without premium")
    patch(root, "ChatActivity",
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
          "bar: button toggles translation (no premium sheet)")
    patch(root, "TranslateButton",
          "            if (UserConfig.getInstance(currentAccount).isPremium() || chat != null && chat.autotranslation) {\n"
          "                onMenuClick();",
          "            if (true) { // [mod] translate settings menu for everyone\n"
          "                onMenuClick();",
          "bar: settings menu for everyone")
    patch(root, "TranslateButton",
          "        menuView.setImageResource(UserConfig.getInstance(currentAccount).isPremium() || chat != null && chat.autotranslation ? R.drawable.msg_mini_customize : R.drawable.msg_close);",
          "        menuView.setImageResource(R.drawable.msg_mini_customize); // [mod] translate settings menu for everyone",
          "bar: customize icon for everyone")
    patch(root, "TranslateButton",
          "        if (UserConfig.getInstance(currentAccount).isPremium() && detectedLanguageNameAccusative != null) {",
          "        if (detectedLanguageNameAccusative != null) { // [mod] no premium",
          "bar: do-not-translate option for everyone")

    # ------------------------------------------------------------------
    # C) In-bubble translation for a single message (+ Show Original)
    # ------------------------------------------------------------------
    print("\nC) In-bubble single message translation")
    # Hotfixes for the previous version of this script: the helper used to call
    # updateTranslation(true) itself, which consumed the state change so the
    # chat screen never repainted the bubble (undo / re-translate looked dead),
    # and a failed translation left the message flagged so the next tap did
    # nothing. Applied BEFORE the insert so an old helper is repaired in place.
    patch(root, "TranslateController",
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
    patch(root, "TranslateController",
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
    patch(root, "TranslateController",
          "    public void toggleTranslatingDialog(long dialogId) {",
          MANUAL_TRANSLATION_HELPER +
          "    public void toggleTranslatingDialog(long dialogId) {",
          "bubble: manual translation helper in TranslateController")
    patch(root, "MessageObject",
          "            TranslateController.isTranslatable(this) &&\n"
          "            translateController.isTranslatingDialog(getDialogId()) &&\n"
          "            !translateController.isTranslateDialogHidden(getDialogId()) &&\n"
          "            (translatedText != null || messageOwner.translatedPoll != null) &&",
          "            TranslateController.isTranslatable(this) &&\n"
          "            (translateController.isMessageManuallyTranslated(getDialogId(), getId()) || translateController.isTranslatingDialog(getDialogId()) && !translateController.isTranslateDialogHidden(getDialogId())) && // [mod] bubble translate\n"
          "            (translatedText != null || messageOwner.translatedPoll != null) &&",
          "bubble: MessageObject accepts manual translation")

    # Freeze hotfix for the previous script version: closeMenu(false) keeps the
    # dark scrim behind the popup menu alive (the popup window used to remove
    # it on dismiss); without the popup the chat stayed dimmed and unresponsive
    # until reopened. closeMenu() removes the scrim itself.
    patch_multi(root, "ChatActivity",
                "                                    getMessagesController().getTranslateController().toggleManualMessageTranslation(selectedObject);\n"
                "                                    closeMenu(false);",
                "                                    getMessagesController().getTranslateController().toggleManualMessageTranslation(selectedObject);\n"
                "                                    closeMenu();",
                "bubble: hotfix chat freeze after translate")

    bubble_call = (
        "                                if (TranslateController.isTranslatable(selectedObject)) { // [mod] bubble translate\n"
        "                                    getMessagesController().getTranslateController().toggleManualMessageTranslation(selectedObject);\n"
        "                                    closeMenu();\n"
        "                                } else {\n"
    )
    patch(root, "ChatActivity",
          "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang, toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
          "                                alert.setDimBehind(false);\n"
          "                                closeMenu(false);",
          bubble_call +
          "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang, toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
          "                                alert.setDimBehind(false);\n"
          "                                closeMenu(false);\n"
          "                                }",
          "bubble: translate click site 1 (known language)")
    patch(root, "ChatActivity",
          "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang[0], toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
          "                                alert.setDimBehind(false);\n"
          "                                closeMenu(false);",
          bubble_call +
          "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, fromLang[0], toLangValue, finalMessageText, entities, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
          "                                alert.setDimBehind(false);\n"
          "                                closeMenu(false);\n"
          "                                }",
          "bubble: translate click site 2 (detected language)")
    patch(root, "ChatActivity",
          "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, \"und\", toLang, finalMessageText, null, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
          "                                alert.setDimBehind(false);\n"
          "                                closeMenu(false);",
          bubble_call +
          "                                TranslateAlert2 alert = TranslateAlert2.showAlert(getParentActivity(), this, currentAccount, inputPeer, messageIdToTranslate[0], selectedObject.summarized, \"und\", toLang, finalMessageText, null, noforwardsOrPaidMedia, onLinkPress, () -> dimBehindView(false));\n"
          "                                alert.setDimBehind(false);\n"
          "                                closeMenu(false);\n"
          "                                }",
          "bubble: translate click site 3 (no detector)")

    # "Show Original" label for a manually translated bubble.
    label_new = "                    items.add(LocaleController.getString(getMessagesController().getTranslateController().isMessageManuallyTranslated(selectedObject) && selectedObject.translated ? R.string.ShowOriginalButton : R.string.TranslateMessage)); // [mod] bubble translate label"
    patch_multi(root, "ChatActivity",
                "                    items.add(LocaleController.getString(R.string.TranslateMessage));",
                label_new,
                "bubble: menu label (Show Original)")

    # A translated message returns null from getMessageTextToTranslate, so the
    # Translate option was never even ADDED to the menu for a translated bubble
    # -> there was no way to undo. The manual-translation state must open the
    # menu entry too (both menu variants).
    patch(root, "ChatActivity",
          "                if (selectedObject != null && selectedObject.contentType == 0 && (!TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(groupedMessages, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) {",
          "                if (selectedObject != null && selectedObject.contentType == 0 && (getMessagesController().getTranslateController().isMessageManuallyTranslated(selectedObject) || !TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(groupedMessages, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) { // [mod] undo option",
          "bubble: show undo entry site 1")
    patch(root, "ChatActivity",
          "                if (selectedObject != null && selectedObject.contentType == 0 && (!TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(selectedObjectGroup, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) {",
          "                if (selectedObject != null && selectedObject.contentType == 0 && (getMessagesController().getTranslateController().isMessageManuallyTranslated(selectedObject) || !TextUtils.isEmpty(selectedObject.getMessageTextToTranslate(selectedObjectGroup, null)) && !selectedObject.isAnimatedEmoji() && !selectedObject.isDice())) { // [mod] undo option",
          "bubble: show undo entry site 2")

    # The click handler for a manually translated bubble must not go through
    # the normal translate path (getMessageTextToTranslate is null there and
    # the language checks could hide the option) -> dedicated undo branch.
    patch(root, "ChatActivity",
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

    # ------------------------------------------------------------------
    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Java-only changes: do a NORMAL build in Android Studio")
        print("(no need to delete .cxx/build), then reinstall the app.")


if __name__ == "__main__":
    main()
