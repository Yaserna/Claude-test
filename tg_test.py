"""
tg_test.py - safe, isolated test of the Telegram parts only.
Does NOT create wallets and does NOT start the endless loop.

What it does:
  1. reads config.yaml
  2. restarts Telegram
  3. long-presses the bottom-bar profile tab to open the account switcher
  4. reads and prints all accounts + which one is currently active
  5. (optional) with 'switch', taps the NEXT account to verify switching works

Run:
    python tg_test.py          # read only, no tap on accounts
    python tg_test.py switch   # also switch to the next account
"""

import os
import sys
import time
import yaml

from bot import Bot
import pages


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    bot = Bot(cfg, base)
    do_switch = len(sys.argv) > 1 and sys.argv[1].lower() == "switch"

    pkg = bot.tg.get("package", "org.telegram.messenger")
    print(f"\n>>> restarting Telegram ({pkg}) ...")
    bot.dev.app_restart(pkg)
    time.sleep(bot.waits.get("tg_render", 2))

    print(">>> long-pressing the profile tab to open the account switcher ...")
    if not bot._tg_open_account_switcher():
        print("!! could not find/open the profile tab. Send the probe dump of "
              "the Telegram main page.")
        return

    accounts = pages.read_tg_switcher_accounts(bot.dev.dump_nodes())
    print(f"\n=== {len(accounts)} accounts found ===")
    for a in accounts:
        mark = "  <== ACTIVE (ring)" if a["selected"] else ""
        print(f"   row #{a['row']:<2} phone={a['phone']}  "
              f"avatar_w={a['avatar_w']}  tap={a['item'].center}{mark}")

    if not accounts:
        print("!! no accounts parsed. Send the probe dump of the open switcher.")
        return

    cur = next((i for i, a in enumerate(accounts) if a["selected"]), None)
    if cur is None:
        print("\n!! active account (blue ring) not detected.")
    else:
        nxt = (cur + 1) % min(len(accounts), int(bot.tg.get("max_accounts", 10)))
        print(f"\n>>> active = {accounts[cur]['phone']} (row #{accounts[cur]['row']})")
        print(f">>> next   = {accounts[nxt]['phone']} (row #{accounts[nxt]['row']})")
        print(f">>> output file would be: {accounts[cur]['phone']}.txt")

        if do_switch:
            print(f"\n>>> switching to {accounts[nxt]['phone']} ...")
            bot.dev.tap_node(accounts[nxt]["item"])
            time.sleep(bot.waits.get("tg_switch_wait", 3))
            print(">>> tapped. Re-open the switcher and run again to confirm the "
                  "ring moved to the new account.")

    print("\n(done. no wallet was created.)")


if __name__ == "__main__":
    main()
