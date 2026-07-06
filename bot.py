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


class StopBot(Exception):
    """Raised from handlers to stop the whole script cleanly
    (e.g. too many consecutive restarts)."""
    pass


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
        if self.current_account:
            self.storage.set_account(self.current_account)

        # Counter of consecutive ZK-login restarts; reset on every wallet
        # successfully created. When it reaches max_consecutive_restarts,
        # the whole script stops with a "Telegram Full" message.
        self.consecutive_restarts = 0
        self.max_restarts = self.tuning.get("max_consecutive_restarts", 10)

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
            "account_index": self.account_index,
            "current_account": self.current_account,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

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

    def restart_app(self, why, count=False):
        # Only ZK-login restarts are counted (count=True from handle_login).
        # Other restarts (NAME, DEPLOY, PW_CREATE, UNKNOWN, logout, ...) are not.
        # Too many consecutive counted restarts -> stop the whole script.
        if count:
            self.consecutive_restarts += 1
            if self.consecutive_restarts >= self.max_restarts:
                self.log.error("Telegram Full - %d consecutive restarts without "
                               "success; stopping script", self.consecutive_restarts)
                raise StopBot("Telegram Full")
            self.log.warning("restart app (%d/%d): %s",
                             self.consecutive_restarts, self.max_restarts, why)
        else:
            self.log.warning("restart app: %s", why)

        if not self.dev.healthy():
            self.log.warning("device offline -> reconnecting before restart")
            if not self.dev.ensure_connected(self.cfg["device"]["serial"]):
                self.log.error("reconnect failed; will retry next loop")
                return
        self.dev.app_restart()

    # ===================== handlers =====================
    def handle_welcome(self, nodes):
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
        # customization: tap Telegram ZK Login immediately, no pause
        tapped = self.dev.tap_text(nodes, "Telegram ZK Login", contains=True, pause=False)
        self.log.info("LOGIN -> Telegram ZK Login (no delay) tapped=%s, waiting %ss",
                      tapped, self.waits["telegram"])
        time.sleep(self.waits["telegram"])

        # Telegram interaction: count successful logins and rotate the
        # account when the per-account limit is reached
        try:
            self._tg_after_login()
        except StopBot:
            raise
        except Exception:
            self.log.exception("TG: post-login handling failed")

        self.log.info("relaunching wallet app")
        self.dev.app_start()

        # customization: wait, then verify we actually left the ZK/LOGIN page;
        # if still there, restart the app and start over
        recheck = self.waits.get("login_recheck", 20)
        self.log.info("waiting %ss after relaunch, then verifying we left ZK", recheck)
        time.sleep(recheck)
        page, _ = self.peek()
        if page == "LOGIN":
            self.log.warning("still on ZK/LOGIN after relaunch -> restart from scratch")
            self.restart_app("stuck on ZK login", count=True)
        else:
            self.log.info("left ZK login -> now on %s", page)

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
            next_name = False
            while not next_name:
                if os.path.exists(self.stop_file):
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
                # real success -> reset the ZK-login restart counter
                self.consecutive_restarts = 0
                self.log.info("SAVED row %d - '%s'", idx, wn)
        self.storage.remove_name(wn)
        self.dev.back()
        time.sleep(self.waits["render"])

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
                # normal part of the flow; don't count it as a stuck restart
                self.restart_app("post-logout", count=False)
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
        """Called after every ZK round-trip to Telegram: if the success message
        is on screen, count it; at the limit, rotate the account."""
        marker = self.tg.get("login_ok_marker")
        if not marker or marker == "CHANGE_ME":
            return  # real marker not configured yet (waiting for XML)
        nodes = self.dev.dump_nodes()
        if marker not in self.dev.all_text(nodes):
            return
        self.tg_login_count += 1
        limit = self.tg.get("logins_per_account", 400)
        self.log.info("TG: login success %d/%d (account=%s)",
                      self.tg_login_count, limit, self.current_account)
        if self.tg_login_count >= limit:
            # counter is not reset until the switch succeeds -> retried next login
            self.switch_telegram_account()
        self._persist()

    def switch_telegram_account(self):
        """Rotate to the next account in the Telegram side-menu list.
        On success the counter resets and the output file changes."""
        pkg = self.tg.get("package", "org.telegram.messenger")
        self.log.info("TG: switching account (logins=%d, index=%d)",
                      self.tg_login_count, self.account_index)
        self.dev.app_start(pkg)
        time.sleep(self.waits.get("tg_render", 2))

        if not self._tg_open_drawer():
            self.log.error("TG: drawer did not open -> keeping current account")
            return False
        if not self._tg_expand_accounts():
            self.log.error("TG: accounts list did not expand")
            return False

        nodes = self.dev.dump_nodes()
        accounts = pages.read_tg_accounts(nodes)
        if len(accounts) < 2:
            self.log.error("TG: fewer than 2 accounts found: %s",
                           [a.text for a in accounts])
            return False

        self.account_index = (self.account_index + 1) % len(accounts)
        target = accounts[self.account_index]
        self.log.info("TG: tapping account #%d '%s'", self.account_index, target.text)
        self.dev.tap_node(target)
        time.sleep(self.waits.get("tg_switch_wait", 3))

        # read the new account's phone from the drawer header -> output file name
        phone = self._tg_read_header_phone()
        acct = self._normalize_account(phone, self.tg.get("strip_country_code", ""))
        if not acct:
            self.log.error("TG: could not read new account phone -> keeping old file")
            return False

        self.current_account = acct
        self.storage.set_account(acct)
        self.tg_login_count = 0
        self._persist()
        self.log.info("TG: switched to account '%s' -> wallets file %s",
                      acct, self.storage.wallets)
        return True

    def _tg_detect_current_account(self):
        """At startup: read the active Telegram account so the output file
        is correct from the very first wallet."""
        pkg = self.tg.get("package", "org.telegram.messenger")
        self.dev.app_start(pkg)
        time.sleep(self.waits.get("tg_render", 2))
        if not self._tg_open_drawer():
            self.log.warning("TG: could not open drawer to detect current account")
            self.dev.app_start()
            return
        phone = self._tg_read_header_phone()
        acct = self._normalize_account(phone, self.tg.get("strip_country_code", ""))
        if acct:
            self.current_account = acct
            self.storage.set_account(acct)
            self._persist()
            self.log.info("TG: current account detected: '%s'", acct)
        else:
            self.log.warning("TG: current account phone not found in drawer")
        self.dev.back()          # close the drawer
        self.dev.app_start()     # back to the wallet app

    def _tg_read_header_phone(self):
        """Phone number in the drawer header; opens the drawer if it is closed."""
        for _ in range(2):
            nodes = self.dev.dump_nodes()
            phone = pages.read_tg_current_phone(nodes)
            if phone:
                return phone
            if not self._tg_open_drawer():
                break
        return None

    def _tg_open_drawer(self):
        """Open the Telegram side menu: try content-desc first, then a ratio tap."""
        for _ in range(3):
            nodes = self.dev.dump_nodes()
            if pages.is_tg_drawer(self.dev.all_text(nodes)):
                return True
            btn = self.dev.find_desc(
                nodes, self.tg.get("drawer_open_desc", "Open navigation menu"))
            if not self.dev.tap_node(btn):
                rx, ry = self.tg.get("drawer_open_ratio", [0.06, 0.045])
                self.dev.tap(int(self.dev.w * rx), int(self.dev.h * ry))
            time.sleep(1)
        return pages.is_tg_drawer(self.dev.all_text(self.dev.dump_nodes()))

    def _tg_expand_accounts(self):
        """Expand the accounts list in the drawer header
        ('Add Account' visible = expanded)."""
        for _ in range(3):
            nodes = self.dev.dump_nodes()
            if self.dev.find(nodes, "Add Account"):
                return True
            rx, ry = self.tg.get("accounts_toggle_ratio", [0.88, 0.17])
            self.dev.tap(int(self.dev.w * rx), int(self.dev.h * ry))
            time.sleep(1)
        return bool(self.dev.find(self.dev.dump_nodes(), "Add Account"))

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
        if self.tg.get("detect_account_on_start") and not self.current_account:
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
                if self.waits["scan_interval"]:
                    time.sleep(self.waits["scan_interval"])
            except KeyboardInterrupt:
                self.log.info("KeyboardInterrupt -> exiting")
                break
            except StopBot as e:
                # consecutive-restart cap reached -> full stop with Telegram Full
                self.log.error("Telegram Full -> stopping script (%s)", e)
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
