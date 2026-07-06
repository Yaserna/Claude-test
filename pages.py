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
# Bot-chat structure confirmed from a real XML dump (2026-07-06):
# - each incoming message node's text contains the message body plus its
#   HH:MM timestamp (the surrounding words are localized, so only the
#   digits are matched)
# - the status-bar clock (current device time) is a TextView in the top
#   strip of the screen, e.g. "14:27"

_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_ACCT_ROW = re.compile(r"^(\d{7,15})\s+#(\d+)\s*$")


def read_status_clock(nodes):
    """Current device time from the status-bar clock, as minutes since
    midnight. The clock is the top-strip TextView whose whole text is HH:MM."""
    for n in nodes:
        if n.cls.endswith("TextView") and n.bounds and n.bounds[1] < 110:
            m = _TIME.fullmatch(n.text.strip())
            if m:
                return int(m.group(1)) * 60 + int(m.group(2))
    return None


def read_tg_last_login_time(nodes, marker):
    """Timestamp (minutes since midnight) of the bottom-most login-success
    message in the bot chat, or None if no such message is visible."""
    best = None
    for n in nodes:
        if marker in n.text and n.bounds:
            if best is None or n.bounds[1] > best.bounds[1]:
                best = n
    if not best:
        return None
    m = _TIME.search(best.text)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def find_tg_profile_tab(nodes, w, h):
    """Profile tab in the bottom bar of the Telegram main page (confirmed by a
    real dump: 4 tab items in the bottom strip; profile is the right-most).
    Found structurally - no dependency on the localized label text.
    Long-pressing it opens the account switcher."""
    best = None
    for n in nodes:
        if n.clickable and n.cls == "android.widget.FrameLayout" and n.bounds:
            x1, y1, x2, y2 = n.bounds
            if y1 > h * 0.85 and (y2 - y1) < h * 0.1 and (x2 - x1) < w * 0.3:
                if best is None or n.center[0] > best.center[0]:
                    best = n
    return best


def read_tg_switcher_accounts(nodes):
    """Account rows of the switcher popup (opened by long-pressing the
    profile tab). Confirmed by a real dump:
    - each row is a clickable LinearLayout containing a TextView like
      '9035505150  #1' (phone, then #row-number)
    - the ACTIVE account's avatar is drawn with a selection ring, which
      makes its inner avatar View a few pixels smaller than the others
    Returns dicts sorted by row number:
    {phone, row, item (tappable Node), avatar_w, selected}."""
    items = [n for n in nodes
             if n.clickable and n.cls == "android.widget.LinearLayout" and n.bounds]
    out = []
    for n in nodes:
        m = _ACCT_ROW.match(n.text.strip()) if n.text else None
        if not m or not n.bounds:
            continue
        t = n.bounds
        item = next((it for it in items
                     if it.bounds[0] <= t[0] and it.bounds[1] <= t[1] and
                        it.bounds[2] >= t[2] and it.bounds[3] >= t[3]), None)
        if not item:
            continue
        # smallest square View on the left edge of the row = inner avatar view
        avatar_w = None
        for v in nodes:
            if v.cls == "android.view.View" and v.bounds:
                vb = v.bounds
                if (item.bounds[0] <= vb[0] and vb[2] <= item.bounds[0] + 200 and
                        item.bounds[1] <= vb[1] and vb[3] <= item.bounds[3]):
                    w = vb[2] - vb[0]
                    if avatar_w is None or w < avatar_w:
                        avatar_w = w
        out.append({"phone": m.group(1), "row": int(m.group(2)),
                    "item": item, "avatar_w": avatar_w})
    out.sort(key=lambda a: a["row"])
    widths = [a["avatar_w"] for a in out if a["avatar_w"]]
    ringed = min(widths) if widths and min(widths) < max(widths) - 4 else None
    for a in out:
        a["selected"] = (ringed is not None and a["avatar_w"] == ringed)
    return out
