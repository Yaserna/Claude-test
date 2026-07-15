"""
snap.py - rapid screen capture to catch a short-lived UI state (e.g. the
loading circle shown while a wallet name is being checked).

It saves a burst of dumps into the snaps/ folder, each numbered with its
time offset, so at least one snapshot lands on the transient state.

Run:
    python snap.py            # 20 dumps, ~0.5s apart (about 10s)
    python snap.py 40 0.3     # 40 dumps, ~0.3s apart

Usage for the NAME loading circle:
    1. On the phone, get to the NAME page and type/submit a name so the
       little loading circle appears in the text field.
    2. IMMEDIATELY run this script (or start it just before submitting).
    3. Send the snaps/ files - or just tell me which numbered snap shows
       the circle and send that one.
"""

import os
import sys
import time

import uiautomator2 as u2


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    gap = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    base = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(base, "snaps")
    os.makedirs(out, exist_ok=True)

    d = u2.connect()
    print(f"capturing {count} dumps, ~{gap}s apart -> {out}")
    t0 = time.time()
    for i in range(count):
        ms = int((time.time() - t0) * 1000)
        try:
            xml = d.dump_hierarchy()
        except Exception as e:
            xml = f"<error>{e}</error>"
        path = os.path.join(out, f"snap_{i:02d}_{ms:05d}ms.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"  {os.path.basename(path)}")
        time.sleep(gap)
    print("done. send the snaps that show the loading circle.")


if __name__ == "__main__":
    main()
