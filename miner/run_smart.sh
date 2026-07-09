#!/usr/bin/env bash
# Infinite restart wrapper. mine_smart.mjs exits ON PURPOSE every RESTART_EVERY
# baskets (anti-fatigue) and resumes from epoch_state_<name>.json — so just relaunch.
cd "$(dirname "$0")"
NAME="${1:-yasan1}"
while true; do
  node mine_smart.mjs "$NAME"
  echo "[run_smart] node exited ($?) — restart in 5s" >> "smart_log_${NAME}.txt"
  sleep 5
done
