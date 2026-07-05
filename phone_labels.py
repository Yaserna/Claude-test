#!/usr/bin/env python3
# -*- coding: ascii -*-
# phone_labels.py
# ---------------
# Shows each logged-in account by its PHONE NUMBER (without the country code)
# instead of the display name -- ONLY in our own account-management places:
#   - the account switcher (long press on the avatar)
#   - the drawer account list
#   - the "send as" account select sheet
#   - your own profile page header
#   - the Settings screen header
#   - the accounts list inside Settings
# The number keeps the #N login-order tag: e.g. "#1 912 345 6789".
# Names inside chats, groups and contacts are NOT touched.
# If an account somehow has no phone number, the name is kept as fallback.
#
# Safe to run multiple times (idempotent). Creates one-time .bak6 backups.
# Java-only changes: a NORMAL Gradle build is enough.

import os
import sys

JAVA_BASE = os.path.join("TMessagesProj", "src", "main", "java")

FILES = {
    "UserConfig":        os.path.join("org", "telegram", "messenger", "UserConfig.java"),
    "MainTabsActivity":  os.path.join("org", "telegram", "ui", "MainTabsActivity.java"),
    "DialogsActivity":   os.path.join("org", "telegram", "ui", "DialogsActivity.java"),
    "AccountSelectCell": os.path.join("org", "telegram", "ui", "Cells", "AccountSelectCell.java"),
    "ProfileActivity":   os.path.join("org", "telegram", "ui", "ProfileActivity.java"),
    "SettingsActivity":  os.path.join("org", "telegram", "ui", "SettingsActivity.java"),
}

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}

applied = 0
skipped = 0
warnings = []


def find_project_root():
    probe = os.path.join("TMessagesProj", "src", "main", "java", "org",
                         "telegram", "messenger", "UserConfig.java")
    candidates = []
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
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
    if not os.path.isfile(path + ".bak6"):
        with open(path + ".bak6", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def patch_first(root, file_key, pairs, needle, label):
    """Idempotent multi-state replacement: if `needle` is already in the file
    the patch is done; otherwise the first (old, new) pair whose old text
    occurs exactly once is applied. Handles sources in different patch
    states (with or without the earlier number-tag patches)."""
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
    for old, new in pairs:
        count = text.count(old)
        if count == 1:
            write(path, text.replace(old, new, 1))
            print("  OK [%s]" % label)
            applied += 1
            return
        if count > 1:
            warnings.append("[%s] anchor found %d times in %s; patch not applied"
                            % (label, count, FILES[file_key]))
            print("  !! [%s] anchor found %d times, skipped" % (label, count))
            return
    warnings.append("[%s] no known anchor found in %s (source differs; "
                    "patch not applied)" % (label, FILES[file_key]))
    print("  !! [%s] anchor NOT FOUND, skipped" % label)


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

PHONE_HELPER = (
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


def main():
    print("=== phone_labels: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)

    print("0) Helpers in UserConfig")
    patch_first(root, "UserConfig",
                [("    public static int getActivatedAccountsCount() {",
                  TAG_HELPER + "\n    public static int getActivatedAccountsCount() {")],
                "getAccountTagNumber",
                "helper: login-order tag number")
    patch_first(root, "UserConfig",
                [("    public static int getActivatedAccountsCount() {",
                  PHONE_HELPER + "\n    public static int getActivatedAccountsCount() {")],
                "getAccountLabel",
                "helper: phone label")
    # Hotfix for sources patched with the older helper version: strip spaces
    # from the number and move the #N tag to the end (two spaces before it).
    # On a fresh insert these are already in PHONE_HELPER and get skipped.
    patch_first(root, "UserConfig",
                [("                    local = local.trim();\n",
                  '                    local = local.replace(" ", "").replace("-", "");\n')],
                'local.replace(" ", "")',
                "label format: no spaces in number")
    patch_first(root, "UserConfig",
                [('        return "#" + getAccountTagNumber(account) + " " + label;',
                  '        return label + "  #" + getAccountTagNumber(account);')],
                'return label + "  #" + getAccountTagNumber(account);',
                "label format: tag at end")

    print("\n1) Account switcher / drawer / send-as")
    patch_first(root, "MainTabsActivity",
                [('textView.setText("#" + UserConfig.getAccountTagNumber(account) + " " + UserObject.getUserName(user));',
                  'textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user)));'),
                 ('textView.setText(UserObject.getUserName(user));',
                  'textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user)));')],
                "UserConfig.getAccountLabel(account, UserObject.getUserName(user))",
                "phone label: main switcher list")
    patch_first(root, "DialogsActivity",
                [('textView.setText("#" + UserConfig.getAccountTagNumber(account) + " " + UserObject.getUserName(user));',
                  'textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user)));'),
                 ('textView.setText(UserObject.getUserName(user));',
                  'textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user)));')],
                "UserConfig.getAccountLabel(account, UserObject.getUserName(user))",
                "phone label: dialogs drawer switcher")
    patch_first(root, "AccountSelectCell",
                [('textView.setText("#" + UserConfig.getAccountTagNumber(accountNumber) + " " + ContactsController.formatName(user.first_name, user.last_name));',
                  'textView.setText(UserConfig.getAccountLabel(accountNumber, ContactsController.formatName(user.first_name, user.last_name)));'),
                 ('textView.setText(ContactsController.formatName(user.first_name, user.last_name));',
                  'textView.setText(UserConfig.getAccountLabel(accountNumber, ContactsController.formatName(user.first_name, user.last_name)));')],
                "UserConfig.getAccountLabel(accountNumber, ContactsController.formatName(user.first_name, user.last_name))",
                "phone label: send-as account select")

    print("\n2) Own profile / Settings headers -> real name + #N tag")
    # These two places show the REAL NAME with the #N tag after it (user's
    # choice); the phone-number label stays everywhere else.
    profile_name_tag = '            if (user.id == getUserConfig().getClientUserId()) { newString = newString.toString() + "  #" + UserConfig.getAccountTagNumber(currentAccount); } // [mod] account name tag (own profile)'
    settings_name_tag = '        titleView.setText(UserObject.getUserName(user) + "  #" + UserConfig.getAccountTagNumber(currentAccount)); // [mod] account name tag (settings header)'
    patch_first(root, "ProfileActivity",
                [('            if (user.id == getUserConfig().getClientUserId()) { newString = UserConfig.getAccountLabel(currentAccount, newString.toString()); } // [mod] account phone label (own profile)',
                  profile_name_tag),
                 ('            if (user.id == getUserConfig().getClientUserId()) { newString = "#" + UserConfig.getAccountTagNumber(currentAccount) + " " + newString; } // [mod] account number tag (own profile)',
                  profile_name_tag),
                 ("            CharSequence newString = UserObject.getUserName(user);\n            String newString2;",
                  "            CharSequence newString = UserObject.getUserName(user);\n"
                  + profile_name_tag + "\n"
                  "            String newString2;")],
                "account name tag (own profile)",
                "name tag: own profile header")
    patch_first(root, "SettingsActivity",
                [('        titleView.setText(UserConfig.getAccountLabel(currentAccount, UserObject.getUserName(user))); // [mod] account phone label (settings header)',
                  settings_name_tag),
                 ('        titleView.setText("#" + UserConfig.getAccountTagNumber(currentAccount) + " " + UserObject.getUserName(user)); // [mod] account number tag (settings header)',
                  settings_name_tag),
                 ('        titleView.setText(UserObject.getUserName(user));',
                  settings_name_tag)],
                "account name tag (settings header)",
                "name tag: settings header")
    patch_first(root, "SettingsActivity",
                [('            textView.setText("#" + UserConfig.getAccountTagNumber(account) + " " + UserObject.getUserName(user)); // [mod] account number tag (settings accounts list)',
                  '            textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user))); // [mod] account phone label (settings accounts list)'),
                 ('            textView.setText(UserObject.getUserName(user));',
                  '            textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user))); // [mod] account phone label (settings accounts list)')],
                "textView.setText(UserConfig.getAccountLabel(account, UserObject.getUserName(user)))",
                "phone label: settings accounts list")

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Java-only changes: do a NORMAL build in Android Studio,")
        print("then reinstall the app.")


if __name__ == "__main__":
    main()
