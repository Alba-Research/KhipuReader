#!/usr/bin/env python3
"""
download_kfg_corpus.py
======================

Download every KFG xlsx (KH0001..KH0702) into ``data/kfg_cache/``.

- Re-uses anything already cached; skips existing non-empty files.
- 1 s rate limit between network calls; retries once on 5xx.
- Logs per-KH outcome so we know which IDs are 404 (gaps).
- Also fetches the pendant-pendant sum HTML page when it exists.

Usage
-----
    python3 scripts/download_kfg_corpus.py
    python3 scripts/download_kfg_corpus.py --start 200 --stop 300   # test range
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import requests
from khipu_translator.ascher import KFGClient, DEFAULT_CACHE_DIR


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--stop", type=int, default=702)
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--sums-too", action="store_true",
                    help="Also fetch the pendant-pendant-sum HTML pages")
    ns = ap.parse_args()

    client = KFGClient(cache_dir=ns.cache_dir)
    outcomes = {"xlsx_cached": 0, "xlsx_downloaded": 0, "xlsx_missing": 0,
                "sums_cached": 0, "sums_downloaded": 0, "sums_missing": 0}
    gaps: List[str] = []
    t0 = time.time()

    for n in range(ns.start, ns.stop + 1):
        kh = f"KH{n:04d}"
        xlsx_path = ns.cache_dir / f"{kh}.xlsx"

        # --- xlsx ---
        if xlsx_path.exists() and xlsx_path.stat().st_size > 0:
            outcomes["xlsx_cached"] += 1
            if not ns.quiet and n % 50 == 0:
                print(f"  [cached] {kh}")
        else:
            try:
                client.fetch_xlsx(kh)
                outcomes["xlsx_downloaded"] += 1
                if not ns.quiet:
                    print(f"  [fetch ] {kh}.xlsx")
            except requests.HTTPError as e:
                code = e.response.status_code
                if code == 404:
                    outcomes["xlsx_missing"] += 1
                    gaps.append(kh)
                else:
                    print(f"  [!] {kh}.xlsx HTTP {code}", file=sys.stderr)
            except Exception as e:
                print(f"  [!] {kh}.xlsx {type(e).__name__}: {e}", file=sys.stderr)

        # --- sums html (optional) ---
        if ns.sums_too:
            sums_path = ns.cache_dir / f"{kh}_sums.html"
            if sums_path.exists() and sums_path.stat().st_size > 0:
                outcomes["sums_cached"] += 1
            else:
                try:
                    client.fetch_sums_html(kh)
                    outcomes["sums_downloaded"] += 1
                except requests.HTTPError as e:
                    if e.response.status_code == 404:
                        outcomes["sums_missing"] += 1
                    else:
                        print(f"  [!] {kh}_sums.html HTTP "
                              f"{e.response.status_code}", file=sys.stderr)
                except Exception as e:
                    print(f"  [!] {kh}_sums.html {type(e).__name__}: {e}",
                          file=sys.stderr)

    elapsed = time.time() - t0
    print()
    print(f"=== Download summary ({elapsed:.0f}s) ===")
    for k, v in outcomes.items():
        print(f"  {k:<20s}  {v}")
    if gaps:
        print(f"\nGaps (HTTP 404): {', '.join(gaps[:30])}"
              f"{' …' if len(gaps) > 30 else ''}  ({len(gaps)} total)")

    report = ns.cache_dir / "download_report.json"
    report.write_text(json.dumps({
        "outcomes": outcomes,
        "gaps": gaps,
        "elapsed_s": round(elapsed, 1),
    }, indent=2), encoding="utf-8")
    print(f"\n[✓] {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
