"""
probe.py - real read-only test (no taps or typing).
Checks the connection and screen reading, and saves output for tuning.

Run (with the phone connected and USB debugging enabled):
    cd ackibot
    python probe.py

Output:
    probe_hierarchy.xml  <- full UI of the current screen
    probe_screen.png     <- screenshot
    and a summary in the terminal (send this summary back)
"""

import time
import xml.etree.ElementTree as ET

import uiautomator2 as u2

import pages
from device import Node


def main():
    print("== connecting to device ==")
    t0 = time.time()
    d = u2.connect()
    info = d.device_info
    w, h = d.window_size()
    print(f"  serial : {info.get('serial')}")
    print(f"  model  : {info.get('model')}  android {info.get('version')}")
    print(f"  screen : {w} x {h}")
    print(f"  current: {d.app_current().get('package')}")
    print(f"  connect+query in {time.time()-t0:.2f}s")

    # measure dump speed (the main advantage of uiautomator2)
    print("\n== screen read speed (3 runs) ==")
    xml = None
    for i in range(3):
        s = time.time()
        xml = d.dump_hierarchy()
        print(f"  dump #{i+1}: {(time.time()-s)*1000:.0f} ms")

    with open("probe_hierarchy.xml", "w", encoding="utf-8") as f:
        f.write(xml)
    try:
        d.screenshot().save("probe_screen.png")
        shot = "probe_screen.png"
    except Exception as e:
        shot = f"(screenshot failed: {e})"

    nodes = [Node(el) for el in ET.fromstring(xml).iter("node")]
    text = "\n".join(n.text for n in nodes)
    page = pages.detect_page(text)

    print("\n== page detection ==")
    print(f"  page = {page}")
    print(f"  files: probe_hierarchy.xml , {shot}")

    print("\n== visible texts on screen ==")
    for n in nodes:
        if n.text.strip():
            print(f"   [{n.cls.split('.')[-1]:<10}] '{n.text}'  bounds={n.bounds}")

    # help tuning the gear/checkbox: clickable buttons and their positions
    print("\n== clickable buttons (for gear/checkbox tuning) ==")
    for n in nodes:
        if n.clickable and n.center:
            rx = n.center[0] / w
            ry = n.center[1] / h
            print(f"   {n.cls.split('.')[-1]:<10} text='{n.text}' "
                  f"center={n.center} ratio=({rx:.2f},{ry:.2f})")


if __name__ == "__main__":
    main()
