"""
File management: names / taken / wallets / password / state
Writes are atomic (tmp + os.replace) so a crash cannot corrupt a file.
"""

import os
import re
import json


class Storage:
    def __init__(self, files):
        self.names = files["names"]
        self.taken = files["taken"]
        self.wallets = files["wallets"]
        self.password_file = files["password"]
        self.state_file = files["state"]
        # per-Telegram-account storage: <wallets_dir>/<account>.txt
        self._default_wallets = self.wallets
        self.wallets_dir = files.get("wallets_dir")

    def set_account(self, account_id):
        """Switches the active wallets file to the account's own file.
        Empty account_id -> back to the default file. Numbering is
        independent per file."""
        if not account_id:
            self.wallets = self._default_wallets
            return self.wallets
        d = self.wallets_dir or os.path.dirname(self._default_wallets) or "."
        os.makedirs(d, exist_ok=True)
        self.wallets = os.path.join(d, f"{account_id}.txt")
        return self.wallets

    # ---------- password ----------
    def password(self):
        with open(self.password_file, encoding="utf-8") as f:
            return f.read().strip()

    # ---------- names ----------
    def next_name(self):
        if not os.path.exists(self.names):
            return None
        with open(self.names, encoding="utf-8") as f:
            for line in f:
                n = line.strip()
                if n:
                    return n
        return None

    def remove_name(self, name):
        if not name or not os.path.exists(self.names):
            return
        with open(self.names, encoding="utf-8") as f:
            lines = f.readlines()
        kept, removed = [], False
        for line in lines:
            if not removed and line.strip() == name:
                removed = True
                continue
            kept.append(line)
        self._atomic_write(self.names, "".join(kept))

    def add_taken(self, name):
        with open(self.taken, "a", encoding="utf-8") as f:
            f.write(name + "\n")

    # ---------- wallets ----------
    def wallet_exists(self, name):
        if not name or not os.path.exists(self.wallets):
            return False
        pat = re.compile(r"^\s*\d+\.\s+" + re.escape(name) + r"\s*$")
        with open(self.wallets, encoding="utf-8") as f:
            for line in f:
                if pat.match(line.rstrip("\n")):
                    return True
        return False

    def next_index(self):
        mx = 0
        if os.path.exists(self.wallets):
            pat = re.compile(r"^\s*(\d+)\.\s+")
            with open(self.wallets, encoding="utf-8") as f:
                for line in f:
                    m = pat.match(line)
                    if m:
                        mx = max(mx, int(m.group(1)))
        return mx + 1

    def save_wallet(self, name, seed):
        if not name or not name.strip():
            return None
        idx = self.next_index()
        with open(self.wallets, "a", encoding="utf-8") as f:
            f.write(f"{idx}. {name}\n\n{seed}\n\n")
        return idx

    # ---------- state ----------
    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_state(self, state):
        self._atomic_write(self.state_file,
                           json.dumps(state, ensure_ascii=False, indent=2))

    # ---------- util ----------
    @staticmethod
    def _atomic_write(path, content):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
