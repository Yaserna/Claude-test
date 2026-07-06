"""
Page detection + information extraction (seed and wallet name) from Nodes.
This module is pure (no state) so it stays easy to test and change.
"""

import re

# Order matters: the first match wins.
_PAGE_MARKERS = [
    ("WELCOME",         "Create new wallet"),
    ("LOGIN",           "Telegram ZK Login"),
    ("NAME",            "Name your wallet"),
    ("PASSWORD_CREATE", "Create password"),
    ("DEPLOY",          "deploying your wallet"),
    ("READY",           "Your Wallet is ready"),
    ("PASSWORD_GATE",   "to access your Acki Nacki"),
    ("SEED",            "Write down all 24 words"),
    ("LOGOUT_CONFIRM",  "Before logging out"),
    ("SETTINGS",        "Biometrics access"),
]

_WORD = re.compile(r"^[a-z]{2,}$")


def detect_page(text):
    if not text:
        return "UNKNOWN"
    for page, marker in _PAGE_MARKERS:
        if marker in text:
            return page
    if "Swap" in text and "Receive" in text:
        return "HOME"
    return "UNKNOWN"


def read_seed(nodes):
    """Reads the 24 words by matching numbers (1..24) with the word to their right."""
    nums = {}
    words = []
    for n in nodes:
        t = n.text
        if t.isdigit():
            v = int(t)
            if 1 <= v <= 24 and n.topleft:
                nums[v] = n.topleft
        elif _WORD.match(t) and n.topleft:
            words.append((t, n.topleft[0], n.topleft[1]))
    if len(nums) < 24:
        return None
    out = []
    for i in range(1, 25):
        np = nums.get(i)
        if not np:
            return None
        cands = [w for w in words if abs(w[2] - np[1]) <= 100 and w[1] > np[0]]
        if not cands:
            return None
        # closest row first, then leftmost word (disambiguates nearby rows)
        cands.sort(key=lambda w: (abs(w[2] - np[1]), w[1]))
        out.append(cands[0][0])
    return " ".join(out)


def read_wallet_name(nodes):
    """Wallet name = first non-empty text before the 'Copy' button."""
    for i, n in enumerate(nodes):
        if n.text == "Copy":
            for j in range(i - 1, -1, -1):
                t = nodes[j].text
                if t and t.strip():
                    return t.strip()
    return None


def is_green(img, cx, cy):
    """Is the area around (cx,cy) green? (checked checkbox)"""
    if img is None:
        return False
    w, h = img.size
    green = total = 0
    for dx in range(-18, 19, 4):
        for dy in range(-18, 19, 4):
            px, py = cx + dx, cy + dy
            if 0 <= px < w and 0 <= py < h:
                p = img.getpixel((px, py))
                r, g, b = p[0], p[1], p[2]
                total += 1
                if g > 90 and g > r + 25 and g > b + 25:
                    green += 1
    return total > 0 and (green / total) >= 0.25


# ===================== Telegram =====================
# TODO: markers and structure will be tuned once real Telegram XML dumps arrive.

_PHONE = re.compile(r"^\+?\d[\d\s\-]{7,}$")


def is_tg_drawer(text):
    """Is the Telegram side menu open? (based on fixed menu items)"""
    if not text:
        return False
    return "Settings" in text and ("Contacts" in text or "Saved Messages" in text)


def read_tg_current_phone(nodes):
    """Current account's phone in the drawer header (first phone-like text)."""
    for n in nodes:
        t = n.text.strip()
        if t and _PHONE.match(t):
            return t
    return None


def read_tg_accounts(nodes):
    """Account items in the expanded drawer: texts between the header phone
    and the 'Add Account' item, sorted top to bottom.
    Returns a list of Nodes (so they can be tapped directly)."""
    phone = add = None
    for n in nodes:
        t = n.text.strip()
        if phone is None and t and _PHONE.match(t) and n.bounds:
            phone = n
        if t == "Add Account" and n.bounds:
            add = n
    if not add:
        return []
    top = phone.bounds[3] if phone else 0
    out = []
    for n in nodes:
        t = n.text.strip()
        if not t or not n.bounds or n is phone or n is add:
            continue
        if top <= n.bounds[1] < add.bounds[1] and not _PHONE.match(t):
            out.append(n)
    out.sort(key=lambda n: n.bounds[1])
    return out
