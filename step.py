"""
step.py - controlled page-by-page stepping.

  python step.py        <- look only: shows the current page and its content (no taps)
  python step.py go     <- executes just that one step (current page's handler) and reports

Workflow: first run without arguments to see the page and its content,
tune config/code if needed; then run with 'go' to execute that single step.
"""

import os
import sys
import yaml

from bot import Bot


def show(bot):
    page, nodes = bot.peek()
    print(f"\n=== current page: {page} ===")
    print("-- visible texts --")
    for n in nodes:
        if n.text.strip():
            print(f"   [{n.cls.split('.')[-1]:<10}] '{n.text}'  bounds={n.bounds}"
                  f"{'  [edit]' if n.cls.endswith('EditText') else ''}"
                  f"{'  [pw]' if n.password else ''}")
    print("-- clickable elements --")
    for n in nodes:
        if n.clickable and n.center:
            print(f"   {n.cls.split('.')[-1]:<10} '{n.text}' center={n.center}")
    return page


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    bot = Bot(cfg, base)

    go = len(sys.argv) > 1 and sys.argv[1].lower() == "go"
    page = show(bot)

    if go:
        print(f"\n>>> running handler for '{page}' ...")
        bot.handle_page(page, bot.peek()[1])
        print(">>> done. waiting 1.5s and reading the result...")
        import time
        time.sleep(1.5)
        new_page, _ = bot.peek()
        print(f">>> page after execution: {new_page}")
    else:
        print("\n(view only. to execute this step: python step.py go)")


if __name__ == "__main__":
    main()
