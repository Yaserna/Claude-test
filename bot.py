"""
Acki Nacki Wallet Bot — نسخه‌ی Python + uiautomator2

اجرا:
    python bot.py                # از config.yaml کنار همین فایل می‌خواند
    python bot.py myconfig.yaml  # کانفیگ دلخواه

توقف تمیز: فایل stop.txt را بساز، یا Ctrl+C بزن.
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler

import yaml

from device import Device
from storage import Storage
import pages


class StopBot(Exception):
    """برای توقفِ تمیزِ کل اسکریپت از داخل هندلرها (مثلاً ریستارت‌های پی‌درپی)."""
    pass


class Bot:
    def __init__(self, cfg, base_dir):
        self.cfg = cfg
        self.base = base_dir
        self.waits = cfg["waits"]
        self.tuning = cfg["tuning"]

        # مسیر فایل‌ها را نسبت به محل کانفیگ مطلق می‌کنیم
        files = {k: self._abs(v) for k, v in cfg["files"].items()}
        self.stop_file = files["stop"]
        self.storage = Storage(files)

        self.log = self._setup_logging(cfg["logging"])
        self.dev = Device(
            serial=cfg["device"]["serial"],
            package=cfg["device"]["package"],
            action_delay=self.waits["action_delay"],
        )

        # وضعیت جاری + آمار (برای بازیابی و لاگ)
        st = self.storage.load_state()
        self.stats = st.get("stats", {"created": 0, "taken": 0, "errors": 0})
        self.wallet_name = None
        self.pw_tries = 0
        self.unknown_since = None
        self._last_stats_log = 0.0

        # شمارنده‌ی ریستارت‌های پشت‌سرهم؛ با هر موفقیت (ساخت کیف‌پول) صفر می‌شود.
        # وقتی به max_consecutive_restarts برسد، کل اسکریپت با پیام Telegram Full می‌ایستد.
        self.consecutive_restarts = 0
        self.max_restarts = self.tuning.get("max_consecutive_restarts", 10)

        # نگاشت صفحه -> هندلر (هم در حلقه‌ی کامل، هم در حالت تک‌قدمی استفاده می‌شود)
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

    # ===================== زیرساخت =====================
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

    def restart_app(self, why, count=True):
        # ریستارت‌های «گیرکردنی» را می‌شماریم؛ اگر بیش از حد پشت‌سرهم شد، کل اسکریپت می‌ایستد.
        # ریستارت‌های عادیِ بخشی از روند (مثل بعدِ logout) با count=False شمرده نمی‌شوند.
        if count:
            self.consecutive_restarts += 1
            if self.consecutive_restarts >= self.max_restarts:
                self.log.error("Telegram Full — %d ریستارت پشت‌سرهم بدون موفقیت؛ توقف اسکریپت",
                               self.consecutive_restarts)
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

    # ===================== هندلرها =====================
    def handle_welcome(self, nodes):
        if not self.storage.next_name():
            self.log.info("WELCOME: names empty; waiting %ss", self.waits["empty_poll"])
            time.sleep(self.waits["empty_poll"])
            return
        self.wallet_name = None
        self.pw_tries = 0          # شروع چرخه‌ی یک کیف‌پول جدید
        # شخصی‌سازی: کلیک فوری و بدون هیچ مکثی روی دکمه‌ی ساخت کیف‌پول
        self.dev.tap_text(nodes, "Create new wallet", pause=False)
        self.log.info("WELCOME -> Create new wallet (no delay)")

    def handle_login(self, nodes):
        # شخصی‌سازی: کلیک فوری (بی‌تأخیر) روی Telegram ZK Login
        tapped = self.dev.tap_text(nodes, "Telegram ZK Login", contains=True, pause=False)
        self.log.info("LOGIN -> Telegram ZK Login (no delay) tapped=%s, waiting %ss",
                      tapped, self.waits["telegram"])
        time.sleep(self.waits["telegram"])
        self.log.info("relaunching wallet app")
        self.dev.app_start()

        # شخصی‌سازی: ۲۰ ثانیه صبر؛ اگر هنوز روی صفحه‌ی ZK/LOGIN بودیم، اپ را ریستارت و از اول
        recheck = self.waits.get("login_recheck", 20)
        self.log.info("waiting %ss after relaunch, then verifying we left ZK", recheck)
        time.sleep(recheck)
        page, _ = self.peek()
        if page == "LOGIN":
            self.log.warning("still on ZK/LOGIN after relaunch -> restart from scratch")
            self.restart_app("stuck on ZK login")
        else:
            self.log.info("left ZK login -> now on %s", page)

    def _name_status(self, nodes):
        """متنِ وضعیتِ زیرِ فیلدِ نام را برمی‌گرداند (یا '' اگر چیزی نبود)."""
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

        # حلقه‌ی بیرونی: نام‌ها را یکی‌یکی امتحان می‌کند تا یکی آزاد باشد
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

            # حلقه‌ی داخلی: منتظر وضعیتِ زیر فیلد می‌ماند
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
                        next_name = True          # برو سراغ نام بعدی
                    elif "cannot be changed" in status:
                        sel = self.dev.find(n2, "Select name")
                        if sel and sel.enabled:
                            self.dev.tap_node(sel)
                            self.wallet_name = name
                            self.pw_tries = 0      # ورود به مرحله‌ی پسورد برای این کیف‌پول
                            self.log.info("NAME: '%s' available -> Select name", name)
                            return
                        # آزاد است ولی دکمه هنوز فعال نشده -> صبر
                    elif "Request failed" in status:
                        # خطای موقتیِ سرور -> منتظر بمان تا حل شود
                        pass
                    else:
                        # هر پیغام دیگری غیر از موارد مشخص‌شده -> ریستارت فوری
                        self.log.warning("NAME: unexpected message -> restart: %s",
                                         status[:100].replace("\n", " "))
                        self.restart_app("NAME unexpected message")
                        return
                else:
                    # هیچ متنی زیر فیلد نیست -> تایمر بی‌متنی
                    if time.time() - last_text > no_text_timeout:
                        self.log.warning("NAME: no status text for %ss -> restart",
                                         no_text_timeout)
                        self.restart_app("NAME stuck (no status text)")
                        return

    def _find_continue(self, nodes):
        """دکمه‌ی ادامه را فقط بین Buttonها می‌گردد (تا با عنوانِ صفحه اشتباه نشود)."""
        for n in nodes:
            if n.cls.endswith("Button") and n.text:
                for lbl in ("Continue", "Confirm", "Next", "Done"):
                    if lbl in n.text:
                        return n
        return None

    def handle_pw_create(self, nodes):
        # هر ورود به این صفحه را می‌شماریم؛ برگشت‌های مکرر = ساخت کیف‌پول ناموفق
        self.pw_tries += 1
        if self.pw_tries > 4:               # ۱ بار اولیه + بیش از ۳ برگشت
            self.log.warning("PW_CREATE: returned more than 3 times -> restart app")
            self.pw_tries = 0
            self.restart_app("PW_CREATE returned >3 times")
            return

        flds = self.dev.pw_fields(nodes)
        if len(flds) < 2:
            self.log.info("PW_CREATE: fewer than 2 fields -> waiting")
            self.pw_tries -= 1              # صفحه‌ی نیمه‌رندر را به حساب نیاور
            time.sleep(0.8)
            return

        pw = self.storage.password()
        # پر کردن دو فیلد از بالا به پایین (با set_text؛ کیبرد اصلاً باز نمی‌شود)
        self.dev.set_edit_text(pw, instance=0)
        time.sleep(0.3)
        self.dev.set_edit_text(pw, instance=1)
        time.sleep(0.3)
        # توجه: چون کیبردی باز نشده، Back نمی‌زنیم — Back در WebView به صفحه‌ی NAME برمی‌گرداند

        # منتظر فعال‌شدن Continue و سپس کلیک
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
        # منتظر می‌مانیم تا از DEPLOY خارج شویم؛ اگر بیش از deploy_timeout ماند -> ریستارت.
        # اگر به PASSWORD_CREATE برگشت، حلقه‌ی اصلی دوباره آن را هندل و شمارش می‌کند.
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
        # شخصی‌سازی: کلیک فوری و بی‌تأخیر روی Not now
        self.dev.tap_text(nodes, "Not now", pause=False)
        self.log.info("READY -> Not now (no delay)")

    def handle_home(self, nodes):
        wn = pages.read_wallet_name(nodes) or self.storage.next_name()
        self.wallet_name = wn
        if self.storage.wallet_exists(wn):
            # کیف‌پول قبلاً ذخیره شده -> برو تنظیمات برای خروج
            if wn and wn == self.storage.next_name():
                self.storage.remove_name(wn)
            gear = self._find_gear(nodes)
            if not self.dev.tap_node(gear):
                self.log.info("HOME: '%s' already saved but gear not found", wn)
        else:
            # شخصی‌سازی: کلیک فوری روی کادرِ Save your seed phrase
            tapped = self.dev.tap_text(nodes, "Save your seed phrase", contains=True, pause=False)
            self.log.info("HOME: '%s' -> Save your seed phrase (no delay) tapped=%s", wn, tapped)

    def handle_pw_gate(self, nodes):
        # مودالِ قفل روی صفحه‌ی SEED: پسورد را تایپ و سپس Continue را بزن
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
                # موفقیتِ واقعی -> شمارنده‌ی ریستارت‌های پشت‌سرهم را صفر کن
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
            # اسکرول سریع و قوی به انتهای صفحه (فلیکِ تقریباً تمام‌صفحه با مدت کوتاه)
            self.dev.swipe(self.dev.w // 2, int(self.dev.h * 0.88),
                           self.dev.w // 2, int(self.dev.h * 0.12), 0.05)
            time.sleep(0.5)
        self.log.warning("SETTINGS: could not reach a tappable 'Log out'")

    def handle_logout_confirm(self, nodes):
        offset = int(self.dev.w * self.tuning["checkbox_offset_ratio"])

        def is_option(o):
            return (o.cls.endswith("Button") and o.topleft and
                    (o.text.startswith("I understand") or o.text.startswith("I stored my seed")))

        # هر گزینه را فقط یک‌بار تیک می‌زنیم (تپ دوباره آن را برعکس می‌کند)
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
        # خروج کمی طول می‌کشد؛ تا رسیدن به WELCOME صبر کن، سپس یک‌بار ریستارت
        wait = self.waits.get("logout_wait", 60)
        self.log.info("LOGOUT_CONFIRM: waiting up to %ss for WELCOME...", wait)
        end = time.time() + wait
        while time.time() < end:
            page, _ = self.peek()
            if page == "WELCOME":
                self.log.info("LOGOUT_CONFIRM: WELCOME reached -> logout done, restart app")
                # ریستارتِ عادیِ بخشی از روند است؛ آن را در شمارنده‌ی گیرکردن حساب نکن
                self.restart_app("post-logout", count=False)
                return
            time.sleep(1)
        self.log.warning("LOGOUT_CONFIRM: WELCOME not reached in %ss -> restart anyway", wait)
        self.restart_app("logout timeout")

    def _find_gear(self, nodes):
        """آیکن چرخ‌دنده‌ی صفحه‌ی HOME؛ نسبت‌محور (مستقل از رزولوشن)."""
        x0, y0, x1, y1 = self.tuning["gear_region"]
        xmin, xmax = self.dev.w * x0, self.dev.w * x1
        ymin, ymax = self.dev.h * y0, self.dev.h * y1
        for n in nodes:
            if n.clickable and n.cls == "android.widget.Button" and n.center:
                cx, cy = n.center
                if xmin <= cx <= xmax and ymin <= cy <= ymax:
                    return n
        return None

    # ===================== حلقه‌ی اصلی =====================
    def peek(self):
        """فقط می‌خواند: (page, nodes) را برمی‌گرداند بدون هیچ اکشنی."""
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
        """یک تکرار: detect + handle. در حلقه‌ی کامل و حالت تک‌قدمی مشترک است."""
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
                # ریستارت‌های پی‌درپی به سقف رسید -> توقف کامل با پیام Telegram Full
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
