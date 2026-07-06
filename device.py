"""
Device layer: all uiautomator2 interaction is encapsulated here.
- Connect once to the warm on-device server; queries take ~50-200ms.
- Select elements by text/class instead of fixed coordinates -> resolution independent.
"""

import re
import time
import xml.etree.ElementTree as ET

import uiautomator2 as u2

_BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


class Node:
    """A lightweight node from dump_hierarchy output."""

    __slots__ = ("text", "desc", "cls", "enabled", "clickable", "password", "bounds")

    def __init__(self, el):
        self.text = el.get("text") or ""
        self.desc = el.get("content-desc") or ""
        self.cls = el.get("class") or ""
        self.enabled = el.get("enabled") == "true"
        self.clickable = el.get("clickable") == "true"
        self.password = el.get("password") == "true"
        m = _BOUNDS.match(el.get("bounds") or "")
        self.bounds = tuple(map(int, m.groups())) if m else None

    @property
    def center(self):
        if not self.bounds:
            return None
        x1, y1, x2, y2 = self.bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def topleft(self):
        return (self.bounds[0], self.bounds[1]) if self.bounds else None


class Device:
    def __init__(self, serial=None, package=None, action_delay=0.3):
        self.d = u2.connect(serial) if serial else u2.connect()
        self.pkg = package
        self.action_delay = action_delay
        self.w, self.h = self.d.window_size()

    # ---------- reading the screen ----------
    def dump_nodes(self):
        """Fetches the whole hierarchy in one fast round-trip and converts it to Nodes."""
        try:
            xml = self.d.dump_hierarchy()
            root = ET.fromstring(xml)
        except Exception:
            return []
        return [Node(el) for el in root.iter("node")]

    @staticmethod
    def all_text(nodes):
        return "\n".join(n.text for n in nodes)

    @staticmethod
    def find(nodes, text, contains=False):
        for n in nodes:
            if (text in n.text) if contains else (n.text == text):
                return n
        return None

    @staticmethod
    def find_desc(nodes, desc, contains=False):
        """Search by content-desc (many Telegram buttons only have a desc)."""
        for n in nodes:
            if (desc in n.desc) if contains else (n.desc == desc):
                return n
        return None

    @staticmethod
    def find_edit(nodes):
        for n in nodes:
            if n.cls == "android.widget.EditText":
                return n
        return None

    @staticmethod
    def pw_fields(nodes):
        r = [n for n in nodes
             if (n.password or n.cls == "android.widget.EditText") and n.topleft]
        return sorted(r, key=lambda n: n.topleft[1])

    # ---------- actions ----------
    def _pause(self):
        if self.action_delay:
            time.sleep(self.action_delay)

    def tap(self, x, y, pause=True):
        self.d.click(x, y)
        if pause:
            self._pause()

    def tap_node(self, n, pause=True):
        if n and n.center and n.center != (0, 0):
            self.tap(*n.center, pause=pause)
            return True
        return False

    def long_tap(self, x, y, duration=0.3, pause=True):
        """Long press at (x, y) for the given duration in seconds."""
        self.d.long_click(x, y, duration)
        if pause:
            self._pause()

    def long_tap_node(self, n, duration=0.3, pause=True):
        if n and n.center and n.center != (0, 0):
            self.long_tap(*n.center, duration=duration, pause=pause)
            return True
        return False

    def tap_text(self, nodes, text, contains=False, pause=True):
        return self.tap_node(self.find(nodes, text, contains), pause=pause)

    def set_edit_text(self, value, instance=0):
        """Replaces the text of an EditText (internal clear+type, no IME needed)."""
        try:
            self.d(className="android.widget.EditText", instance=instance).set_text(value)
            self._pause()
            return True
        except Exception:
            return False

    def back(self):
        self.d.press("back")
        self._pause()

    def enter(self):
        self.d.press("enter")
        self._pause()

    def swipe(self, sx, sy, ex, ey, dur=0.1):
        self.d.swipe(sx, sy, ex, ey, dur)

    def screenshot(self):
        try:
            return self.d.screenshot()  # PIL.Image
        except Exception:
            return None

    # ---------- app management ----------
    # pkg=None means the default (wallet) app; pass Telegram's package explicitly.
    def app_start(self, pkg=None):
        self.d.app_start(pkg or self.pkg, stop=False)

    def app_stop(self, pkg=None):
        self.d.app_stop(pkg or self.pkg)

    def app_restart(self, pkg=None):
        # tolerant of momentary connection drops
        pkg = pkg or self.pkg
        try:
            self.d.app_stop(pkg)
        except Exception:
            pass
        time.sleep(2)
        try:
            self.d.app_start(pkg)
        except Exception:
            pass
        time.sleep(4)

    def current_pkg(self):
        try:
            return self.d.app_current().get("package")
        except Exception:
            return None

    def healthy(self):
        try:
            self.d.window_size()
            return True
        except Exception:
            return False

    def reconnect(self, serial=None):
        self.d = u2.connect(serial) if serial else u2.connect()
        self.w, self.h = self.d.window_size()

    def ensure_connected(self, serial=None, retries=6):
        """Reconnects with exponential backoff if the phone goes offline."""
        for i in range(retries):
            try:
                self.d = u2.connect(serial) if serial else u2.connect()
                self.w, self.h = self.d.window_size()
                return True
            except Exception:
                time.sleep(min(2 ** i, 16))
        return False
