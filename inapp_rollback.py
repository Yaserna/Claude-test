#!/usr/bin/env python3
# -*- coding: ascii -*-
# inapp_rollback.py
# -----------------
# In-app "go back to the previous build". The app keeps a copy of its own APK;
# whenever you install a newer build, the one you had is kept as "previous".
# A button in Settings > Language reinstalls that previous APK (you confirm the
# install once). Because all YasTel builds share the same version code and
# signature, this reinstalls over the current app WITHOUT losing chats/data.
#
# Two patches (Java only):
#   1) ApplicationLoader.java: on startup, in the background, save the running
#      APK to <externalFiles>/yastel_builds/current.apk and rotate the old
#      current.apk to previous.apk when the build changes.
#   2) LanguageSelectActivity.java: a second top-bar icon opens a "YasTel
#      builds" dialog with a "Reinstall previous build" button (uses Telegram's
#      existing FileProvider + REQUEST_INSTALL_PACKAGES).
#
# Requires ai_translate.py first (for the settings menu). Safe to run multiple
# times (idempotent). Creates one-time .bak18 backups. NORMAL build is enough.

import os
import sys

SKIP_DIRS = {".git", "build", ".cxx", ".gradle", "intermediates", ".idea", "node_modules"}
JAVA = os.path.join("TMessagesProj", "src", "main", "java", "org", "telegram")
AL_REL = os.path.join(JAVA, "messenger", "ApplicationLoader.java")
LSA_REL = os.path.join(JAVA, "ui", "LanguageSelectActivity.java")

applied = 0
skipped = 0
warnings = []

# ---- ApplicationLoader ----
AL_CALL_OLD = "        applicationInited = true;\n"
AL_CALL_NEW = "        applicationInited = true;\n        saveYasTelBuild(); // [mod] keep previous build apk\n"
AL_METHOD_ANCHOR = "    public static void postInitApplication() {\n"
AL_METHOD = (
    "    // [mod] YasTel: keep a copy of the previous build's APK for rollback.\n"
    "    public static void saveYasTelBuild() {\n"
    "        new Thread() {\n"
    "            @Override\n"
    "            public void run() {\n"
    "                try {\n"
    "                    android.content.Context ctx = applicationContext;\n"
    "                    if (ctx == null) {\n"
    "                        return;\n"
    "                    }\n"
    "                    java.io.File base = ctx.getExternalFilesDir(null);\n"
    "                    if (base == null) {\n"
    "                        return;\n"
    "                    }\n"
    "                    java.io.File dir = new java.io.File(base, \"yastel_builds\");\n"
    "                    dir.mkdirs();\n"
    "                    java.io.File curApk = new java.io.File(dir, \"current.apk\");\n"
    "                    java.io.File prevApk = new java.io.File(dir, \"previous.apk\");\n"
    "                    String srcPath = ctx.getApplicationInfo().sourceDir;\n"
    "                    if (srcPath == null) {\n"
    "                        return;\n"
    "                    }\n"
    "                    java.io.File myApk = new java.io.File(srcPath);\n"
    "                    if (!myApk.exists()) {\n"
    "                        return;\n"
    "                    }\n"
    "                    android.content.SharedPreferences p = ctx.getSharedPreferences(\"yastelbuilds\", android.content.Context.MODE_PRIVATE);\n"
    "                    String fp = myApk.length() + \"_\" + myApk.lastModified();\n"
    "                    String savedFp = p.getString(\"current_fp\", \"\");\n"
    "                    if (curApk.exists() && fp.equals(savedFp)) {\n"
    "                        return;\n"
    "                    }\n"
    "                    if (curApk.exists() && !fp.equals(savedFp)) {\n"
    "                        if (prevApk.exists()) {\n"
    "                            prevApk.delete();\n"
    "                        }\n"
    "                        if (curApk.renameTo(prevApk)) {\n"
    "                            p.edit().putString(\"previous_version\", p.getString(\"current_version\", \"\")).apply();\n"
    "                        }\n"
    "                    }\n"
    "                    java.io.FileInputStream in = new java.io.FileInputStream(myApk);\n"
    "                    java.io.FileOutputStream out = new java.io.FileOutputStream(curApk);\n"
    "                    byte[] buf = new byte[65536];\n"
    "                    int r;\n"
    "                    while ((r = in.read(buf)) > 0) {\n"
    "                        out.write(buf, 0, r);\n"
    "                    }\n"
    "                    in.close();\n"
    "                    out.close();\n"
    "                    p.edit().putString(\"current_fp\", fp).putString(\"current_version\", BuildVars.BUILD_VERSION_STRING).apply();\n"
    "                } catch (Throwable e) {\n"
    "                    // best-effort; rollback copy is optional\n"
    "                }\n"
    "            }\n"
    "        }.start();\n"
    "    }\n"
    "\n"
)

# ---- LanguageSelectActivity ----
LSA_MENU_OLD = "        menu.addItem(1001, R.drawable.msg_translate); // [mod] YasTel AI translate settings\n"
LSA_MENU_NEW = LSA_MENU_OLD + "        menu.addItem(1002, R.drawable.ic_ab_other); // [mod] YasTel builds / revert\n"
LSA_CLICK_OLD = (
    "                } else if (id == 1001) { // [mod] YasTel AI translate settings\n"
    "                    showAiTranslateSettings();\n"
    "                }"
)
LSA_CLICK_NEW = (
    "                } else if (id == 1001) { // [mod] YasTel AI translate settings\n"
    "                    showAiTranslateSettings();\n"
    "                } else if (id == 1002) { // [mod] YasTel builds / revert\n"
    "                    yastelRevertToPrevious();\n"
    "                }"
)
LSA_METHOD_ANCHOR = "    @Override\n    public View createView(Context context) {"
LSA_METHOD = (
    "    private void yastelRevertToPrevious() {\n"
    "        android.content.Context context = getParentActivity();\n"
    "        if (context == null) {\n"
    "            return;\n"
    "        }\n"
    "        java.io.File base = context.getExternalFilesDir(null);\n"
    "        java.io.File prevApk = base == null ? null : new java.io.File(new java.io.File(base, \"yastel_builds\"), \"previous.apk\");\n"
    "        android.content.SharedPreferences p = context.getSharedPreferences(\"yastelbuilds\", android.content.Context.MODE_PRIVATE);\n"
    "        String prevVer = p.getString(\"previous_version\", \"\");\n"
    "        AlertDialog.Builder builder = new AlertDialog.Builder(context);\n"
    "        builder.setTitle(\"YasTel builds\");\n"
    "        if (prevApk == null || !prevApk.exists()) {\n"
    "            builder.setMessage(\"No previous build is saved yet. After you build and install a newer version, the current one is kept here so you can roll back to it.\");\n"
    "            builder.setPositiveButton(LocaleController.getString(R.string.OK), null);\n"
    "        } else {\n"
    "            builder.setMessage(\"Reinstall the previous build\" + (prevVer.length() > 0 ? \" (v\" + prevVer + \")\" : \"\") + \"?\\nYour chats and data are kept. Android will ask you to confirm the install.\");\n"
    "            final java.io.File apk = prevApk;\n"
    "            builder.setPositiveButton(\"Reinstall\", (dialog, which) -> {\n"
    "                try {\n"
    "                    android.content.Intent intent = new android.content.Intent(android.content.Intent.ACTION_VIEW);\n"
    "                    intent.setFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION | android.content.Intent.FLAG_ACTIVITY_NEW_TASK);\n"
    "                    android.net.Uri uri = androidx.core.content.FileProvider.getUriForFile(context, org.telegram.messenger.ApplicationLoader.getApplicationId() + \".provider\", apk);\n"
    "                    intent.setDataAndType(uri, \"application/vnd.android.package-archive\");\n"
    "                    context.startActivity(intent);\n"
    "                } catch (Exception e) {\n"
    "                    org.telegram.messenger.FileLog.e(e);\n"
    "                }\n"
    "            });\n"
    "            builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);\n"
    "        }\n"
    "        showDialog(builder.create());\n"
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
            if os.path.isfile(os.path.join(direct, AL_REL)):
                return direct
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.isfile(os.path.join(root, AL_REL)):
                return root
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if not os.path.isfile(path + ".bak18"):
        with open(path + ".bak18", "w", encoding="utf-8") as f:
            f.write(read(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def do(path, old, new, needle, label):
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
    if text.count(old) != 1:
        warnings.append("[%s] anchor found %d times (expected 1)" % (label, text.count(old)))
        print("  !! [%s] anchor not found once, skipped" % label)
        return
    write(path, text.replace(old, new, 1))
    print("  OK [%s]" % label)
    applied += 1


def main():
    print("=== inapp_rollback: locate project ===")
    root = find_project_root()
    if root is None:
        sys.exit("ERROR: Telegram source not found. Put this script next to (or "
                 "inside) the folder that contains TMessagesProj and run again.")
    print("Project root: %s\n" % root)
    al = os.path.join(root, AL_REL)
    lsa = os.path.join(root, LSA_REL)

    print("1) Save/rotate the build APK on startup (ApplicationLoader)")
    do(al, AL_METHOD_ANCHOR, AL_METHOD + AL_METHOD_ANCHOR, "saveYasTelBuild", "AL: method")
    do(al, AL_CALL_OLD, AL_CALL_NEW, "saveYasTelBuild(); // [mod]", "AL: startup call")

    print("\n2) Revert button in Settings > Language (LanguageSelectActivity)")
    if os.path.isfile(lsa) and "showAiTranslateSettings" not in read(lsa):
        warnings.append("run ai_translate.py first (settings menu missing)")
        print("  !! settings menu missing -- run ai_translate.py first")
    else:
        do(lsa, LSA_MENU_OLD, LSA_MENU_NEW, "menu.addItem(1002", "LSA: menu item")
        do(lsa, LSA_CLICK_OLD, LSA_CLICK_NEW, "id == 1002", "LSA: click handler")
        do(lsa, LSA_METHOD_ANCHOR, LSA_METHOD + LSA_METHOD_ANCHOR, "yastelRevertToPrevious", "LSA: revert method")

    print("\n=== RESULT: %d applied, %d already done, %d warnings ===" % (applied, skipped, len(warnings)))
    for w in warnings:
        print("  WARNING: " + w)
    if not warnings:
        print("All good. Build, install. The revert option is Settings > Language >")
        print("the second top-bar icon. A 'previous build' appears after your NEXT build.")


if __name__ == "__main__":
    main()
