"""
record_ui_text.py - record every text template the app shows, tab by tab, for pipeline/seed_translations.py.

Runs the app headless (Streamlit AppTest) with services/i18n.py in RECORD mode, opens each navbar tab,
presses every keyed button once, and merges what it saw into scratch/i18n_seen.json.

Run from the repo root:  python pipeline/record_ui_text.py
"""

import json
import os
import sys
import warnings

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
warnings.filterwarnings("ignore")

from services import i18n  # noqa: E402

i18n.RECORD = True
i18n.finish_run = lambda: None          # record only, never translate here

from streamlit.testing.v1 import AppTest  # noqa: E402

SKIP = {"aa_live_loc", "aa_auto_loc"}


def main():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=600)
    at.run()
    nav_key = next(k for k in at.session_state.filtered_state if str(k).startswith("aa_nav_"))
    labels = [t.label for t in at.tabs][:13]
    for i, lab in enumerate(labels):
        at.session_state[nav_key] = lab
        at.session_state["aa_nav_idx"] = i
        at.run()
        for k in [b.key for b in at.button if b.key and b.key not in SKIP]:
            try:
                at.session_state[nav_key] = lab
                at.run()
                if any(b.key == k for b in at.button):
                    at.button(key=k).click().run()
            except Exception:
                pass
        print(f"tab {i:2d} {lab[:24]:24s} templates so far {len(i18n.SEEN)}", flush=True)
    out = os.path.join(ROOT, "scratch", "i18n_seen.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    old = set(json.load(open(out, encoding="utf-8"))) if os.path.exists(out) else set()
    merged = sorted(old | i18n.SEEN)
    json.dump(merged, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"saved {len(merged)} templates ({len(i18n.SEEN - old)} new) -> {out}")


if __name__ == "__main__":
    main()
