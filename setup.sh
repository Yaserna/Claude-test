#!/usr/bin/env bash
# =====================================================================
#  Custom Telegram Fork - Setup for Linux / macOS
#  Downloads the Telegram source and applies our custom modifications.
#  Requires: git and python3
# =====================================================================
set -e

echo "=== Custom Telegram fork setup (Linux/macOS) ==="
echo

command -v git >/dev/null 2>&1 || { echo "[ERROR] git is not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "[ERROR] python3 is not installed."; exit 1; }

cd "$(dirname "$0")"

REPO=$(python3 -c "import json;print(json.load(open('build_config.json'))['upstream_repo'])")
COMMIT=$(python3 -c "import json;print(json.load(open('build_config.json'))['upstream_commit'])")

if [ -d Telegram ]; then
  echo "Telegram folder already exists, skipping clone."
else
  echo "Downloading the Telegram source... (about 1 GB)"
  git clone "$REPO" Telegram
fi

echo "Checking out the pinned commit $COMMIT ..."
git -C Telegram checkout "$COMMIT"

echo "Applying custom modifications..."
python3 apply_mods.py

echo
echo "=== Done! Open the Telegram folder in Android Studio and Build. ==="
