#!/usr/bin/env bash
cd "$(dirname "$0")"
NAME="${1:-yasan1}"
LOG="smart_log_${NAME}.txt"
echo "▶ ماینر زنده؟"; pgrep -f "mine_smart.mjs $NAME" >/dev/null && echo "  YES ✅" || echo "  NO ❌"
echo; echo "▶ ریوارد هر epoch:"; grep -E "EPOCH [0-9]+ DONE" "$LOG" | tail -8
echo; echo "▶ رشد موجودی (startLocked):"; grep -E "EPOCH [0-9]+ START" "$LOG" | tail -8
echo; echo "▶ تعداد خطای stale در ۲۴ساعت اخیر:"; grep "Cancel stale" "$LOG" | grep "$(date -u +%Y-%m-%d)" | wc -l
echo; echo "▶ الان:"; tail -1 "$LOG"
