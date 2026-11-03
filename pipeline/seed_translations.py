"""
seed_translations.py - pre-translate the app's UI text so every language loads instantly and offline.

Input:  scratch/i18n_seen.json (every text template the app showed during a full click-through, recorded by
        services/i18n.py with RECORD=True) or, if missing, the templates already in data/i18n/mr.json.
Output: data/i18n/<code>.json for each language.

Run from the repo root:  python pipeline/seed_translations.py [mr hi te ...]
"""

import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from services import i18n  # noqa: E402


def main(codes):
    src = os.path.join(ROOT, "scratch", "i18n_seen.json")
    if os.path.exists(src):
        templates = json.load(open(src, encoding="utf-8"))
    else:
        templates = list(i18n._load("mr").keys())
    print(f"{len(templates)} templates", flush=True)
    i18n.QUOTA_WAIT_S = 180.0          # offline: wait out per-minute rate limits instead of skipping chunks
    for code in codes:
        dropped = i18n.purge_wrong_script(code)
        if dropped:
            print(f"{code}: dropped {dropped} translations in the wrong script", flush=True)
        t = time.time()
        n = i18n.seed(code, templates)
        print(f"{code}: +{n} in {time.time() - t:.0f}s, cache {len(i18n._load(code))}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(i18n.LANGS.keys()))
