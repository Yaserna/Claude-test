# CLAUDE.md — Working Agreement

## Token-saving rules (always apply)

- **No summaries at turn start.** Never recap what was done in a previous turn. Jump straight to the work.
- **No "I'll now..." narration.** Run the tool; don't announce it first.
- **Responses in the language of the user's message.** Persian message → Persian reply; English message → English reply.
- **Code comments only when the WHY is non-obvious.** No docstrings, no "this function does X" comments.
- **No mid-task check-ins.** Complete the task, then give one short summary of what changed.

## Project: Acki Nacki miner — `yasan1`

| Item | Value |
|------|-------|
| Server path | `/root/miner_server/` |
| Run command | `bash run_smart.sh yasan1` |
| Log | `smart_log_yasan1.txt` |
| State file | `epoch_state_yasan1.json` |
| Quick status | `bash /root/miner_server/status.sh` |

### Miner strategy

- `START_FRAC=0.60` — waits for the last 40% of each epoch (low competition)
- `TARGET_BASKETS=90` — reward saturates here; anything beyond is wasted CPU
- `RESTART_EVERY=20` — anti-fatigue: restarts process every 20 baskets, resumes via state file

### Key files in repo (`miner/`)

| File | Purpose |
|------|---------|
| `mine_smart.mjs` | Smart Miner v2 (main logic) |
| `bee_sdk.mjs` | WASM glue layer (wasm-bindgen 0.2.106) — still compatible with mainnet v0.16.3 |
| `bee_sdk_bg.wasm` | Compiled WASM binary |
| `proxy_pool.mjs` | Free-proxy scraper/validator (paused — single wallet, not needed yet) |
| `run_smart.sh` | Infinite restart wrapper |
| `status.sh` | 3-day health check script |

### Proxy work

Paused. Resume when scaling beyond one wallet. Uses `undici` (`npm install undici`).

## Review cadence

Every 3 days: run `bash /root/miner_server/status.sh` and paste output here.
