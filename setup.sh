#!/usr/bin/env bash
# =====================================================================
#  Custom Telegram Fork - Setup for Linux / macOS
#  سورس تلگرام را دانلود و تغییرات اختصاصی را اعمال می‌کند.
#  پیش‌نیاز: git و python3
# =====================================================================
set -e

echo "=== راه‌اندازی فورک اختصاصی تلگرام (Linux/macOS) ==="
echo

command -v git >/dev/null 2>&1 || { echo "[خطا] git نصب نیست."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "[خطا] python3 نصب نیست."; exit 1; }

cd "$(dirname "$0")"

REPO=$(python3 -c "import json;print(json.load(open('build_config.json'))['upstream_repo'])")
COMMIT=$(python3 -c "import json;print(json.load(open('build_config.json'))['upstream_commit'])")

if [ -d Telegram ]; then
  echo "پوشه Telegram از قبل وجود دارد، از کلون رد می‌شویم."
else
  echo "در حال دانلود سورس تلگرام... (حدود ۱ گیگابایت)"
  git clone "$REPO" Telegram
fi

echo "در حال تنظیم روی نسخه‌ی ثابت‌شده $COMMIT ..."
git -C Telegram checkout "$COMMIT"

echo "در حال اعمال تغییرات اختصاصی..."
python3 apply_mods.py

echo
echo "=== تمام شد! پوشه‌ی Telegram را در Android Studio باز کن و Build بزن. ==="
