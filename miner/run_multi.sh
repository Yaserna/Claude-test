#!/usr/bin/env bash
# Fleet launcher: starts the proxy pool + one smart miner per wallet in fleet.txt.
# Safe to re-run any time — skips whatever is already running.
cd "$(dirname "$0")"
if ! pgrep -f "proxy_pool.mjs" >/dev/null; then
  nohup node proxy_pool.mjs > proxy.log 2>&1 &
  echo "proxy_pool: started"
else
  echo "proxy_pool: already running"
fi
while IFS= read -r n; do
  n="${n%%#*}"; n="$(echo "$n" | tr -d '[:space:]')"
  [ -z "$n" ] && continue
  if pgrep -f "mine_smart.mjs $n" >/dev/null; then
    echo "miner $n: already running"
  else
    nohup bash run_smart.sh "$n" > /dev/null 2>&1 &
    echo "miner $n: started"
  fi
done < fleet.txt
