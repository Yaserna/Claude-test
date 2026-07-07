"""
Acki Nacki Wallet Bot - Python + uiautomator2

Run:
    python bot.py                # reads config.yaml next to this file
    python bot.py myconfig.yaml  # custom config

Clean stop: create stop.txt, or press Ctrl+C.
"""

import os
import re
import sys
import time
import logging
from logging.handlers import RotatingFileHandler

import yaml

from device import Device
from storage import Storage
import pages


class Bot:
    def __init__(self, cfg, base_dir):
        self.cfg = cfg
        self.base = base_dir
        self.waits = cfg["waits"]
        self.tuning = cfg["tuning"]

        # make file paths absolute relative to the config location
        files = {k: self._abs(v) for k, v in cfg["files"].items()}
        self.stop_file = files["stop"]
        self.storage = Storage(files)

        self.log = self._setup_logging(cfg["logging"])
        self.dev = Device(
            serial=cfg["device"]["serial"],
            package=cfg["device"]["package"],
            action_delay=self.waits["action_delay"],
        )

        # current state + stats (for recovery and logging)
        st = self.storage.load_state()
        self.stats = st.get("stats", {"created": 0, "taken": 0, "errors": 0})
        self.wallet_name = None
        self.pw_tries = 0
        self.unknown_since = None
        self._last_stats_log = 0.0

        # --- Telegram: successful-login counting + account rotation ---
        self.tg = cfg.get("telegram", {})
        self.tg_login_count = st.get("tg_login_count", 0)
        self.account_index = st.get("account_index", 0)
        self.current_account = st.get("current_account")
        # HH:MM (minutes) of the last success message we already counted, plus
        # how many same-minute success bubbles were present then, so a stale
        # message is never recounted AND two logins in the same minute are told
        # apart (the same-minute bubble count increases)
        self.tg_last_login_min = st.get("tg_last_login_min")
        self.tg_last_min_count = st.get("tg_last_min_count", 0)
        if self.current_account:
            self.storage.set_account(self.current_account)

        # page -> handler map (used by the main loop and the step tool)
        self.dispatch = {
            "WELCOME": self.handle_welcome,
            "LOGIN": self.handle_login,
            "NAME": self.handle_name,
            "PASSWORD_CREATE": self.handle_pw_create,
            "DEPLOY": self.handle_deploy,
            "READY": self.handle_ready,
            "HOME": self.handle_home,
            "PASSWORD_GATE": self.handle_pw_gate,
            "SEED": self.handle_seed,
            "SETTINGS": self.handle_settings,
            "LOGOUT_CONFIRM": self.handle_logout_confirm,
        }

    # ===================== infrastructure =====================
    def _abs(self, p):
        return p if os.path.isabs(p) else os.path.join(self.base, p)

    def _setup_logging(self, lc):
        log_dir = self._abs(lc["dir"])
        os.makedirs(log_dir, exist_ok=True)
        logger = logging.getLogger("ackibot")
        logger.setLevel(getattr(logging, lc["level"].upper(), logging.INFO))
        logger.handlers.clear()
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        fh = RotatingFileHandler(os.path.join(log_dir, "bot.log"),
                                 maxBytes=2_000_000, backupCount=5, encoding="utf-8")
        fh.setFormatter(fmt)
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger

    def _persist(self):
        self.storage.save_state({
            "stats": self.stats,
            "wallet_name": self.wallet_name,
            "tg_login_count": self.tg_login_count,
            "tg_last_login_min": self.tg_last_login_min,
            "tg_last_min_count": self.tg_last_min_count,
            "account_index": self.account_index,
            "current_account": self.current_account,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def _print_status(self):
        """Live one-line terminal status (updates in place) so the login
        progress of the current account is always visible."""
        limit = self.tg.get("logins_per_account", 400)
        s = self.stats
        line = (f"[account {self.current_account or '-'}] "
                f"logins {self.tg_login_count}/{limit} | "
                f"created {s['created']} taken {s['taken']} errors {s['errors']}")
        try:
            print("\r" + line + "        ", end="", flush=True)
        except Exception:
            pass

    def _maybe_log_stats(self):
        every = self.cfg["logging"]["stats_every"]
        now = time.time()
        if every and now - self._last_stats_log >= every:
            self._last_stats_log = now
            s = self.stats
            self.log.info("STATS created=%d taken=%d errors=%d remaining=%s",
                          s["created"], s["taken"], s["errors"],
                          self._remaining_names())

    def _remaining_names(self):
        path = self.storage.names
        if not os.path.exists(path):
            return 0
        with open(path, encoding="utf-8") as f:
            return sum(1 for ln in f if ln.strip())

    def wait_for_page(self, target, timeout):
        end = time.time() + timeout
        while time.time() < end:
            if pages.detect_page(self.dev.all_text(self.dev.dump_nodes())) == target:
                return True
            time.sleep(0.8)
        return False

    def restart_app(self, why):
        self.log.warning("restart app: %s", why)
        if not self.dev.healthy():
            self.log.warning("device offline -> reconnecting before restart")
            if not self.dev.ensure_connected(self.cfg["device"]["serial"]):
                self.log.error("reconnect failed; will retry next loop")
                return
        self.dev.app_restart()

    # ===================== handlers =====================
    def _switch_due(self):
        return self.tg_login_count >= self.tg.get("logins_per_account", 400)

    def handle_welcome(self, nodes):
        # Limit already reached and no wallet is in progress yet -> switch
        # NOW instead of starting a new wallet on a capped account.
        if self._switch_due():
            self.switch_telegram_account()
            return
        if not self.storage.next_name():
            self.log.info("WELCOME: names empty; waiting %ss", self.waits["empty_poll"])
            time.sleep(self.waits["empty_poll"])
            return
        self.wallet_name = None
        self.pw_tries = 0          # start of a new wallet cycle
        # customization: tap the create-wallet button immediately, no pause
        self.dev.tap_text(nodes, "Create new wallet", pause=False)
        self.log.info("WELCOME -> Create new wallet (no delay)")

    def handle_login(self, nodes):
        # Limit already reached BEFORE passing ZK login -> do not attempt a
        # new login on this (possibly daily-capped) account: switch NOW.
        # This breaks the deadlock where a capped account can no longer log
        # in, so no wallet gets saved and the post-save switch never runs.
        if self._switch_due():
            self.switch_telegram_account()
            return
        # tap Telegram ZK Login immediately, no fixed pause
        tapped = self.dev.tap_text(nodes, "Telegram ZK Login", contains=True, pause=False)
        self.log.info("LOGIN -> Telegram ZK Login tapped=%s", tapped)

        # Count the login by OBSERVING the fresh success message in Telegram.
        # _tg_after_login polls until the message appears (or its timeout),
        # so there is no fixed delay here. It also rotates the account when
        # the per-account limit is reached.
        try:
            self._tg_after_login()
        except Exception:
            self.log.exception("TG: post-login handling failed")

        # relaunch the wallet app, then poll the page until we OBSERVE that we
        # left the ZK/LOGIN screen (no fixed delay). If it is still LOGIN after
        # login_recheck seconds, restart from scratch.
        self.log.info("relaunching wallet app")
        self.dev.app_start()
        timeout = self.waits.get("login_recheck", 20)
        end = time.time() + timeout
        while time.time() < end:
            page, _ = self.peek()
            if page != "LOGIN":
                self.log.info("left ZK login -> now on %s", page)
                return
            time.sleep(0.5)
        self.log.warning("still on ZK/LOGIN after %ss -> restart from scratch", timeout)
        self.restart_app("stuck on ZK login")

    def _name_status(self, nodes):
        """Returns the status text under the name field ('' if none)."""
        edit = self.dev.find_edit(nodes)
        if not edit or not edit.bounds:
            return ""
        ebottom = edit.bounds[3]
        best = None
        for n in nodes:
            if n.cls.endswith("TextView") and n.text.strip() and n.bounds:
                top = n.bounds[1]
                if ebottom - 20 <= top <= ebottom + 220:
                    if best is None or top < best.bounds[1]:
                        best = n
        return best.text.strip() if best else ""

    def handle_name(self, nodes):
        gap = self.tuning["name_poll_gap"]
        no_text_timeout = self.waits.get("name_no_text", 10)
        stuck_timeout = self.waits.get("name_stuck_timeout", 120)

        # outer loop: try names one by one until one is available
        while True:
            if os.path.exists(self.stop_file):
                return
            name = self.storage.next_name()
            if not name:
                self.log.info("NAME: names.txt empty")
                return
            if not self.dev.set_edit_text(name):
                self.log.info("NAME: could not set text for '%s'", name)
                return
            self.log.info("NAME: typed '%s'", name)

            # inner loop: wait for the status text under the field
            last_text = time.time()
            name_start = time.time()
            next_name = False
            while not next_name:
                if os.path.exists(self.stop_file):
                    return
                # overall guard: a non-empty but unresolved status (e.g. a
                # persistent 'Request failed', or 'available' whose button
                # never enables) must not hang the loop forever
                if time.time() - name_start > stuck_timeout:
                    self.log.warning("NAME: stuck on '%s' for %ss -> restart",
                                     name, stuck_timeout)
                    self.restart_app("NAME stuck (status never resolved)")
                    return
                time.sleep(gap)
                n2 = self.dev.dump_nodes()
                status = self._name_status(n2)

                if status:
                    last_text = time.time()
                    if "already taken" in status:
                        self.log.info("NAME: '%s' taken -> next name", name)
                        self.storage.add_taken(name)
                        self.storage.remove_name(name)
                        self.stats["taken"] += 1
                        next_name = True          # move to the next name
                    elif "cannot be changed" in status:
                        sel = self.dev.find(n2, "Select name")
                        if sel and sel.enabled:
                            self.dev.tap_node(sel)
                            self.wallet_name = name
                            self.pw_tries = 0      # entering password stage for this wallet
                            self.log.info("NAME: '%s' available -> Select name", name)
                            return
                        # name is free but the button is not enabled yet -> wait
                    elif "Request failed" in status:
                        # transient server error -> wait until it clears
                        pass
                    else:
                        # any other message -> restart immediately
                        self.log.warning("NAME: unexpected message -> restart: %s",
                                         status[:100].replace("\n", " "))
                        self.restart_app("NAME unexpected message")
                        return
                else:
                    # no text under the field -> no-text timer
                    if time.time() - last_text > no_text_timeout:
                        self.log.warning("NAME: no status text for %ss -> restart",
                                         no_text_timeout)
                        self.restart_app("NAME stuck (no status text)")
                        return

    def _find_continue(self, nodes):
        """Looks for the continue button among Buttons only
        (so it is not confused with the page title)."""
        for n in nodes:
            if n.cls.endswith("Button") and n.text:
                for lbl in ("Continue", "Confirm", "Next", "Done"):
                    if lbl in n.text:
                        return n
        return None

    def handle_pw_create(self, nodes):
        # count every entry to this page; repeated returns = wallet creation failing
        self.pw_tries += 1
        if self.pw_tries > 4:               # 1 initial + more than 3 returns
            self.log.warning("PW_CREATE: returned more than 3 times -> restart app")
            self.pw_tries = 0
            self.restart_app("PW_CREATE returned >3 times")
            return

        flds = self.dev.pw_fields(nodes)
        if len(flds) < 2:
            self.log.info("PW_CREATE: fewer than 2 fields -> waiting")
            self.pw_tries -= 1              # don't count a half-rendered page
            time.sleep(0.8)
            return

        pw = self.storage.password()
        # fill both fields top to bottom (set_text; the keyboard never opens)
        self.dev.set_edit_text(pw, instance=0)
        time.sleep(0.3)
        self.dev.set_edit_text(pw, instance=1)
        time.sleep(0.3)
        # note: no keyboard was opened, so no Back press - Back inside the
        # WebView would navigate back to the NAME page

        # wait for Continue to become enabled, then tap
        deadline = time.time() + 6
        while time.time() < deadline:
            n3 = self.dev.dump_nodes()
            cont = self._find_continue(n3)
            if cont and cont.enabled:
                self.dev.tap_node(cont)
                self.log.info("PW_CREATE: filled + continue tapped (entry %d) -> creating wallet",
                              self.pw_tries)
                return
            time.sleep(0.3)
        self.log.info("PW_CREATE: continue not enabled within timeout (entry %d)", self.pw_tries)

    def handle_deploy(self, nodes):
        # Wait until we leave DEPLOY; if it lasts longer than deploy_timeout -> restart.
        # If it goes back to PASSWORD_CREATE, the main loop handles and counts it again.
        timeout = self.waits.get("deploy_timeout", 60)
        deadline = time.time() + timeout
        while time.time() < deadline:
            page, _ = self.peek()
            if page != "DEPLOY":
                self.log.info("DEPLOY -> moved to %s", page)
                return
            time.sleep(1)
        self.log.warning("DEPLOY: stuck >%ss -> restart", timeout)
        self.restart_app("DEPLOY timeout")

    def handle_ready(self, nodes):
        # customization: tap Not now immediately, no pause
        self.dev.tap_text(nodes, "Not now", pause=False)
        self.log.info("READY -> Not now (no delay)")

    def handle_home(self, nodes):
        wn = pages.read_wallet_name(nodes) or self.storage.next_name()
        self.wallet_name = wn
        if self.storage.wallet_exists(wn):
            # wallet already saved -> go to settings to log out
            if wn and wn == self.storage.next_name():
                self.storage.remove_name(wn)
            gear = self._find_gear(nodes)
            if not self.dev.tap_node(gear):
                self.log.info("HOME: '%s' already saved but gear not found", wn)
        else:
            # customization: tap the "Save your seed phrase" card immediately
            tapped = self.dev.tap_text(nodes, "Save your seed phrase", contains=True, pause=False)
            self.log.info("HOME: '%s' -> Save your seed phrase (no delay) tapped=%s", wn, tapped)

    def handle_pw_gate(self, nodes):
        # lock modal over the SEED page: type the password, then tap Continue
        pw = self.storage.password()
        if not self.dev.set_edit_text(pw, instance=0):
            self.log.info("PASSWORD_GATE: password field not found")
            return
        self.log.info("PASSWORD_GATE: password typed")
        time.sleep(0.3)
        deadline = time.time() + 6
        while time.time() < deadline:
            n2 = self.dev.dump_nodes()
            cont = self._find_continue(n2)
            if cont and cont.enabled:
                self.dev.tap_node(cont)
                self.log.info("PASSWORD_GATE -> continue tapped")
                return
            time.sleep(0.3)
        self.log.info("PASSWORD_GATE: continue not enabled within timeout")

    def handle_seed(self, nodes):
        seed = pages.read_seed(nodes) or pages.read_seed(self.dev.dump_nodes())
        if not seed:
            self.dev.back()
            return
        wn = self.wallet_name or pages.read_wallet_name(nodes) or self.storage.next_name()
        if not wn:
            self.log.warning("SEED: no wallet name resolved -> not saving")
            self.dev.back()
            return
        if not self.storage.wallet_exists(wn):
            idx = self.storage.save_wallet(wn, seed)
            if idx:
                self.stats["created"] += 1
                self.log.info("SAVED row %d - '%s'", idx, wn)
        self.storage.remove_name(wn)
        self.dev.back()
        time.sleep(self.waits["render"])
        # The wallet is now fully created and saved. If the per-account login
        # limit was reached during this cycle, stop here and switch the
        # Telegram account before any new wallet is started.
        if self._switch_due():
            self.switch_telegram_account()

    def handle_settings(self, nodes):
        for s in range(6):
            n = self.dev.dump_nodes()
            lo = self.dev.find(n, "Log out", contains=True)
            if lo and self.dev.tap_node(lo):
                self.log.info("SETTINGS: tapped Log out")
                return
            self.log.info("SETTINGS: strong scroll to bottom (try %d)", s)
            # fast, strong scroll to the bottom (near full-screen flick, short duration)
            self.dev.swipe(self.dev.w // 2, int(self.dev.h * 0.88),
                           self.dev.w // 2, int(self.dev.h * 0.12), 0.05)
            time.sleep(0.5)
        self.log.warning("SETTINGS: could not reach a tappable 'Log out'")

    def handle_logout_confirm(self, nodes):
        offset = int(self.dev.w * self.tuning["checkbox_offset_ratio"])

        def is_option(o):
            return (o.cls.endswith("Button") and o.topleft and
                    (o.text.startswith("I understand") or o.text.startswith("I stored my seed")))

        # tap each option only once (a second tap toggles it back)
        tapped = set()
        deadline = time.time() + 8
        while time.time() < deadline:
            n = self.dev.dump_nodes()
            btn = self.dev.find(n, "Log out from wallet")
            if btn and btn.enabled:
                self.dev.tap_node(btn, pause=False)
                self.log.info("LOGOUT_CONFIRM: all confirmed -> logging out")
                self._wait_logout_done()
                return
            for o in n:
                if is_option(o) and o.text not in tapped:
                    self.dev.tap(o.topleft[0] + offset, o.center[1], pause=False)
                    tapped.add(o.text)
            time.sleep(0.2)
        self.log.warning("LOGOUT_CONFIRM: logout button never enabled")

    def _wait_logout_done(self):
        # logging out takes a while; wait for WELCOME, then restart once
        wait = self.waits.get("logout_wait", 60)
        self.log.info("LOGOUT_CONFIRM: waiting up to %ss for WELCOME...", wait)
        end = time.time() + wait
        while time.time() < end:
            page, _ = self.peek()
            if page == "WELCOME":
                self.log.info("LOGOUT_CONFIRM: WELCOME reached -> logout done, restart app")
                self.restart_app("post-logout")
                return
            time.sleep(1)
        self.log.warning("LOGOUT_CONFIRM: WELCOME not reached in %ss -> restart anyway", wait)
        self.restart_app("logout timeout")

    def _find_gear(self, nodes):
        """Gear icon on the HOME page; ratio-based (resolution independent)."""
        x0, y0, x1, y1 = self.tuning["gear_region"]
        xmin, xmax = self.dev.w * x0, self.dev.w * x1
        ymin, ymax = self.dev.h * y0, self.dev.h * y1
        for n in nodes:
            if n.clickable and n.cls == "android.widget.Button" and n.center:
                cx, cy = n.center
                if xmin <= cx <= xmax and ymin <= cy <= ymax:
                    return n
        return None

    # ===================== Telegram: login counting + account rotation =====================
    # TODO: markers/ratios will be tuned with real Telegram XML dumps.

    @staticmethod
    def _normalize_account(phone_text, strip_cc=""):
        """'+98 903 550-51-55' -> '9035505155' (with strip_country_code from config)."""
        digits = re.sub(r"\D", "", phone_text or "")
        if strip_cc and digits.startswith(strip_cc):
            digits = digits[len(strip_cc):]
        return digits or None

    def _tg_after_login(self):
        """Wait (by OBSERVING the screen) until a genuinely NEW login-success
        message appears in the Telegram bot chat, then count it. 'New' means:
        the bottom-most success message is FRESH (its HH:MM is within
        fresh_window_minutes of the status-bar clock) AND its timestamp differs
        from the last message we already counted -- so a stale message left in
        the chat from the previous login is never mistaken for this one.
        This is what makes the flow wait for the login instead of relaunching
        the wallet too early."""
        marker = self.tg.get("login_ok_marker",
                             "You have successfully logged into Acki Nacki")
        window = self.tg.get("fresh_window_minutes", 2)
        deadline = time.time() + self.waits.get("tg_login_ok_timeout", 30)

        msg_time = clock = None
        while time.time() < deadline:
            nodes = self.dev.dump_nodes()
            msg_time, cnt = pages.read_tg_login_info(nodes, marker)
            clock = pages.read_status_clock(nodes)
            if msg_time is not None and clock is not None:
                # signed minute difference (clock - message), wrapped to
                # [-720, 720). Fresh = the message is at most `window` minutes
                # old, or up to 1 minute AHEAD of the device clock (covers the
                # minute-boundary / server-vs-device skew that would otherwise
                # drop a login).
                diff = (clock - msg_time + 720) % (24 * 60) - 720
                is_fresh = -1 <= diff <= window
                # new = a different minute, OR the same minute but more
                # same-minute bubbles than last time (a 2nd login this minute)
                is_new = (msg_time != self.tg_last_login_min or
                          cnt > self.tg_last_min_count)
                if is_fresh and is_new:
                    self.tg_last_login_min = msg_time
                    self.tg_last_min_count = cnt
                    self.tg_login_count += 1
                    limit = self.tg.get("logins_per_account", 400)
                    self.log.info("TG: NEW login message at %02d:%02d (x%d) -> "
                                  "count %d/%d (account=%s)",
                                  msg_time // 60, msg_time % 60, cnt,
                                  self.tg_login_count, limit, self.current_account)
                    if self.tg_login_count >= limit:
                        # do NOT switch here: the wallet currently in progress
                        # must be created and saved first. The switch runs in
                        # handle_seed right after the wallet is saved.
                        self.log.info("TG: limit reached -> account switch is "
                                      "scheduled after the current wallet is saved")
                    self._persist()
                    return
            time.sleep(1.0)

        self.log.info("TG: no NEW login-success message within timeout "
                      "(last_seen=%s counted_min=%s clock=%s) -> not counted",
                      msg_time, self.tg_last_login_min, clock)

    def switch_telegram_account(self):
        """Rotate to the next account in the Telegram side-menu list.
        Flow (as specified): close the wallet app, restart Telegram once so it
        lands on its main page, switch the account there, then reopen the
        wallet. On success the counter resets and the output file changes."""
        pkg = self.tg.get("package", "org.telegram.messenger")
        self.log.info("TG: switching account (logins=%d, index=%d)",
                      self.tg_login_count, self.account_index)
        self.dev.app_stop()          # close the wallet app
        self.dev.app_restart(pkg)    # restart Telegram -> its main page
        time.sleep(self.waits.get("tg_render", 2))

        ok = self._do_account_switch()
        self.dev.app_start()         # back to the wallet app either way
        if not ok:
            # counter stays >= limit, so the switch is retried after the
            # next wallet is saved
            self.log.error("TG: account switch failed -> will retry after "
                           "the next wallet")
        return ok

    def _do_account_switch(self):
        # step 1 (confirmed by a real dump): long-press (~300ms) the profile
        # tab in the bottom bar of the Telegram main page -> account switcher
        if not self._tg_open_account_switcher():
            return False

        # step 2 (confirmed by a real dump): rows look like '9035505150  #1';
        # the active account is the one whose avatar has the selection ring
        accounts = pages.read_tg_switcher_accounts(self.dev.dump_nodes())
        if len(accounts) < 2:
            self.log.error("TG: fewer than 2 accounts in switcher: %s",
                           [(a["phone"], a["row"]) for a in accounts])
            return False

        # rotation is capped at max_accounts rows (default 10): after the
        # 10th account (or the last one, if fewer) it wraps back to row #1
        cap = max(2, int(self.tg.get("max_accounts", 10)))
        n = min(len(accounts), cap)
        cur = self._current_switcher_index(accounts)
        if cur >= n:
            cur = n - 1
        nxt = (cur + 1) % n
        target = accounts[nxt]
        self.log.info("TG: switching account %s (row #%d) -> %s (row #%d)",
                      accounts[cur]["phone"], accounts[cur]["row"],
                      target["phone"], target["row"])
        self.dev.tap_node(target["item"])
        time.sleep(self.waits.get("tg_switch_wait", 3))

        # the output file name is the phone number ONLY (no row number)
        acct = self._normalize_account(target["phone"],
                                       self.tg.get("strip_country_code", ""))
        self.current_account = acct
        self.account_index = nxt
        self.storage.set_account(acct)
        self.tg_login_count = 0
        self.tg_last_login_min = None
        self.tg_last_min_count = 0
        self._persist()
        self.log.info("TG: switched to account '%s' -> wallets file %s",
                      acct, self.storage.wallets)
        return True

    def _current_switcher_index(self, accounts):
        """Index of the active account in the switcher list: the ring-marked
        row; falls back to the stored phone, then the stored index."""
        for i, a in enumerate(accounts):
            if a["selected"]:
                return i
        if self.current_account:
            for i, a in enumerate(accounts):
                if a["phone"] == self.current_account:
                    return i
        return self.account_index % len(accounts)

    def _tg_wait_main_page(self):
        """Block until the Telegram bottom bar (profile tab) is actually
        rendered, so we never act before the app has finished loading.
        Returns the profile-tab node, or None on timeout."""
        timeout = self.waits.get("tg_main_ready_timeout", 30)
        end = time.time() + timeout
        while time.time() < end:
            tab = pages.find_tg_profile_tab(self.dev.dump_nodes(),
                                            self.dev.w, self.dev.h)
            if tab:
                return tab
            time.sleep(0.5)
        return None

    def _tg_open_account_switcher(self):
        """On the Telegram main page: wait for the bottom-bar profile tab to be
        loaded, then long-press it (~300ms) to open the account switcher."""
        tab = self._tg_wait_main_page()
        if not tab:
            self.log.error("TG: bottom bar / profile tab did not load in time")
            return False
        dur = self.tg.get("profile_longpress_ms", 300) / 1000.0
        self.log.info("TG: long-pressing profile tab at %s for %.0fms",
                      tab.center, dur * 1000)
        self.dev.long_tap(*tab.center, duration=dur)
        time.sleep(self.waits.get("tg_render", 2))
        return True

    def _tg_detect_current_account(self):
        """At startup: keep restarting Telegram until the active (ring-marked)
        account is read, so the output file is correct from the very first
        wallet. Retries forever (with a short pause) until it succeeds."""
        pkg = self.tg.get("package", "org.telegram.messenger")
        attempt = 0
        while True:
            if os.path.exists(self.stop_file):
                return
            attempt += 1
            self.log.info("TG: startup account detection attempt %d", attempt)
            self.dev.app_restart(pkg)
            time.sleep(self.waits.get("tg_render", 2))
            if self._tg_detect_once():
                self.dev.back()          # close the switcher popup
                self.dev.app_start()     # back to the wallet app
                return
            self.log.warning("TG: could not read active account -> restarting "
                             "Telegram and retrying")
            time.sleep(self.waits.get("tg_detect_retry", 2))

    def _tg_detect_once(self):
        """One attempt to read the active account from the switcher.
        Returns True on success (account read + bound), False otherwise."""
        if not self._tg_open_account_switcher():
            return False
        accounts = pages.read_tg_switcher_accounts(self.dev.dump_nodes())
        sel = next((i for i, a in enumerate(accounts) if a["selected"]), None)
        if sel is None:
            self.log.warning("TG: ring-marked account not found (%d rows read)",
                             len(accounts))
            return False
        acct = self._normalize_account(accounts[sel]["phone"],
                                       self.tg.get("strip_country_code", ""))
        if not acct:
            return False
        if self.current_account and acct != self.current_account:
            # active account changed since the last run (e.g. manually)
            # -> the stored counter belongs to the old account
            self.log.info("TG: active account changed '%s' -> '%s' -> counter reset",
                          self.current_account, acct)
            self.tg_login_count = 0
            self.tg_last_login_min = None
            self.tg_last_min_count = 0
        else:
            self.log.info("TG: resuming login counter at %d", self.tg_login_count)
        self.current_account = acct
        self.account_index = sel
        self.storage.set_account(acct)
        self._persist()
        self.log.info("TG: current account detected: '%s' (row #%d)",
                      acct, accounts[sel]["row"])
        return True

    # ===================== main loop =====================
    def peek(self):
        """Read-only: returns (page, nodes) without any action."""
        nodes = self.dev.dump_nodes()
        page = pages.detect_page(self.dev.all_text(nodes))
        return page, nodes

    def handle_page(self, page, nodes):
        if page != "UNKNOWN":
            self.unknown_since = None
        handler = self.dispatch.get(page)
        if handler:
            handler(nodes)
        else:
            self._handle_unknown()

    def step(self):
        """One iteration: detect + handle. Shared by the full loop and step mode."""
        if not self.dev.healthy():
            self.log.warning("device unhealthy -> reconnecting (with backoff)")
            self.dev.ensure_connected(self.cfg["device"]["serial"])
            time.sleep(2)
            return None
        page, nodes = self.peek()
        self.handle_page(page, nodes)
        self._persist()
        return page

    def run(self):
        self.log.info("=============== bot start ===============")
        # ALWAYS at startup: restart Telegram once, read the ring-marked
        # account, bind the output file to it, then launch the wallet and
        # continue the loop (the login counter is restored from state.json)
        if self.tg.get("detect_account_on_start", True):
            try:
                self._tg_detect_current_account()
            except Exception:
                self.log.exception("TG: startup account detection failed")
        while True:
            if os.path.exists(self.stop_file):
                self.log.info("stop.txt found -> exiting")
                break
            try:
                self.step()
                self._maybe_log_stats()
                self._print_status()
                if self.waits["scan_interval"]:
                    time.sleep(self.waits["scan_interval"])
            except KeyboardInterrupt:
                self.log.info("KeyboardInterrupt -> exiting")
                break
            except Exception:
                self.stats["errors"] += 1
                self.log.exception("loop error")
                time.sleep(2)

        self._persist()
        self.log.info("=============== bot stopped ===============")

    def _handle_unknown(self):
        if self.unknown_since is None:
            self.unknown_since = time.time()
            self.log.info("UNKNOWN page -> recovery timer started (%ss)",
                          self.waits["unknown_timeout"])
        elif time.time() - self.unknown_since >= self.waits["unknown_timeout"]:
            self.restart_app("stuck on UNKNOWN")
            self.unknown_since = None
        time.sleep(2)


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    Bot(cfg, os.path.dirname(os.path.abspath(cfg_path))).run()


if __name__ == "__main__":
    main()
