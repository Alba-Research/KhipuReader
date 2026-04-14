#!/usr/bin/env python3
"""
coverage_delta_v3.py
====================

Measure the syllabic-coverage delta introduced by the v3 reader
(``translate(..., merged_corpus=...)``) versus the v1 OKR-only pipeline.

For each validated-contribution khipu we run the reader twice — once with
the merged corpus and once without — and compare:

  - number of level-1 STRING cords with any reading
  - number of level-1 STRING cords with a dictionary-confirmed reading
  - number of cords whose knot_sequence contained ``L?`` in v1 but no
    longer does in v3 (= turn counts filled from KFG)
  - distinct vocabulary size

Produces a Markdown table + JSON + scatter PNG, focused on the khipus
where v3 actually unlocks readings.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from khipu_translator.corpus import MergedCorpus, DEFAULT_SQLITE
from khipu_translator.database import KhipuDB
from khipu_translator.translator import translate

VALIDATED_DIR = REPO_ROOT / "contributions" / "validated"


def _has_lq(seq: Optional[str]) -> bool:
    return "L?" in (seq or "")


def _readable_string_cords(result) -> Dict[str, int]:
    l1 = [c for c in result.cords if c.level == 1]
    string_l1 = [c for c in l1 if c.cord_type == "STRING"]
    any_reading = [c for c in string_l1 if c.alba_reading]
    confirmed  = [c for c in string_l1 if c.alba_confirmed]
    with_lq    = [c for c in l1 if _has_lq(c.knot_sequence)]
    vocab      = {c.alba_reading for c in string_l1 if c.alba_reading}
    return {
        "n_level1":       len(l1),
        "n_string":       len(string_l1),
        "n_with_reading": len(any_reading),
        "n_confirmed":    len(confirmed),
        "n_with_lq":      len(with_lq),
        "vocab_size":     len(vocab),
    }


def process_one(okr_id: str, db: KhipuDB, corpus: MergedCorpus) -> Optional[dict]:
    try:
        r_v1 = translate(okr_id, db=db)
        r_v3 = translate(okr_id, db=db, merged_corpus=corpus)
    except Exception as e:
        print(f"  [skip] {okr_id}: {type(e).__name__}: {e}", file=sys.stderr)
        return None

    v1 = _readable_string_cords(r_v1)
    v3 = _readable_string_cords(r_v3)

    kh_id = corpus.resolve_kh_id(okr_id)
    return {
        "okr_id": okr_id,
        "kh_id": kh_id,
        **{f"v1_{k}": v for k, v in v1.items()},
        **{f"v3_{k}": v for k, v in v3.items()},
        "delta_readings":  v3["n_with_reading"] - v1["n_with_reading"],
        "delta_confirmed": v3["n_confirmed"]    - v1["n_confirmed"],
        "delta_lq":        v1["n_with_lq"]      - v3["n_with_lq"],
        "delta_vocab":     v3["vocab_size"]     - v1["vocab_size"],
    }


def plot_delta(rows: List[dict], out_path: Path) -> None:
    gained = [r for r in rows if r["delta_readings"] > 0]
    if not gained:
        print("[!] No khipu gained readings — skipping plot.")
        return
    gained.sort(key=lambda r: -r["delta_readings"])
    top = gained[:25]

    labels = [f"{r['okr_id']}\n({r['kh_id']})" for r in top]
    v1_readings = [r["v1_n_with_reading"] for r in top]
    deltas      = [r["delta_readings"]    for r in top]
    confirmed_d = [r["delta_confirmed"]   for r in top]

    fig, ax = plt.subplots(figsize=(14, 7))
    x = np.arange(len(top))
    ax.bar(x, v1_readings, color="#888", label="v1 readings (OKR only)")
    ax.bar(x, deltas, bottom=v1_readings, color="#2b8cbe",
           label="+ v3 (merged) unlocked")
    ax.bar(x, confirmed_d, bottom=v1_readings, color="#238b45", alpha=0.6,
           label="of which dict-confirmed")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("# level-1 STRING cords with reading")
    ax.set_title("v1 → v3 syllabic coverage delta (top 25 khipus)\n"
                 "Merged OKR × KFG fills L? gaps with KFG-resolved turn counts")
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[✓] plot: {out_path}")


def write_report(rows: List[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gained = [r for r in rows if r["delta_readings"] > 0]
    total_unlocked     = sum(r["delta_readings"]  for r in rows)
    total_confirmed_d  = sum(r["delta_confirmed"] for r in rows)
    total_lq_filled    = sum(r["delta_lq"]        for r in rows)

    L: List[str] = []
    L.append("# KhipuReader v3 — coverage delta (v1 OKR vs v3 merged)")
    L.append("")
    L.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    L.append("")
    L.append("## Aggregate")
    L.append("")
    L.append(f"- Khipus processed:           **{len(rows)}**")
    L.append(f"- Khipus that gained readings: **{len(gained)}**")
    L.append(f"- L? cords filled by KFG:     **{total_lq_filled}**")
    L.append(f"- New readings unlocked:      **{total_unlocked}**")
    L.append(f"- New dict-confirmed readings: **{total_confirmed_d}**")
    L.append("")
    L.append("## Top 20 khipus by readings unlocked")
    L.append("")
    L.append("| OKR | KFG | v1 readings | v3 readings | Δ | v1 vocab | v3 vocab | L? filled |")
    L.append("|-----|-----|------------:|------------:|--:|---------:|---------:|----------:|")
    for r in sorted(rows, key=lambda r: -r["delta_readings"])[:20]:
        L.append(
            f"| {r['okr_id']} | {r['kh_id'] or '—'} | "
            f"{r['v1_n_with_reading']} | {r['v3_n_with_reading']} | "
            f"+{r['delta_readings']} | {r['v1_vocab_size']} | "
            f"{r['v3_vocab_size']} | {r['delta_lq']} |"
        )
    L.append("")
    L.append("## Full table")
    L.append("")
    L.append("| OKR | KFG | v1→v3 reads | v1→v3 confirmed | L? filled | Δ vocab |")
    L.append("|-----|-----|------------:|----------------:|----------:|--------:|")
    for r in sorted(rows, key=lambda r: r["okr_id"]):
        L.append(
            f"| {r['okr_id']} | {r['kh_id'] or '—'} | "
            f"{r['v1_n_with_reading']}→{r['v3_n_with_reading']} | "
            f"{r['v1_n_confirmed']}→{r['v3_n_confirmed']} | "
            f"{r['delta_lq']} | +{r['delta_vocab']} |"
        )
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"[✓] report: {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("khipus", nargs="*", default=None,
                    help="OKR ids (default: every contributions/validated/*.json)")
    ap.add_argument("--output-dir", type=Path,
                    default=REPO_ROOT / "output" / "coverage_delta_v3")
    ap.add_argument("--quiet", action="store_true")
    ns = ap.parse_args()

    if not DEFAULT_SQLITE.exists():
        print("[!] merged corpus not built — run scripts/merge_okr_kfg.py first",
              file=sys.stderr)
        return 2

    if ns.khipus:
        ok_list = list(ns.khipus)
    else:
        ok_list = sorted(p.stem for p in VALIDATED_DIR.glob("*.json"))

    db = KhipuDB()
    corpus = MergedCorpus()
    rows: List[dict] = []
    try:
        for okr_id in ok_list:
            res = process_one(okr_id, db, corpus)
            if res is None:
                continue
            rows.append(res)
            if not ns.quiet:
                print(f"  {okr_id:<8s} / {res['kh_id'] or '—':<7s}  "
                      f"v1 reads={res['v1_n_with_reading']:>3d}  "
                      f"v3 reads={res['v3_n_with_reading']:>3d}  "
                      f"(+{res['delta_readings']})  "
                      f"L? filled={res['delta_lq']}  "
                      f"vocab +{res['delta_vocab']}")
    finally:
        db.close()
        corpus.close()

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    (ns.output_dir / "coverage_delta_v3.json").write_text(
        json.dumps(rows, indent=2, default=str), encoding="utf-8")
    write_report(rows, ns.output_dir / "coverage_delta_v3.md")
    plot_delta(rows, ns.output_dir / "coverage_delta_v3.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
