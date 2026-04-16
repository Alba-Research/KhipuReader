#!/usr/bin/env python3
"""
ascher_bidirectional_overlap.py
===============================

Strong test of Paper 2's T3 bidirectionality claim.

The weak form of T3 only asks "does this khipu have both right-handed and
left-handed Ascher sums?" That is true of 82% of the corpus, but does not
distinguish:
    (a) two independent totals for two different sections, vs
    (b) two independent totals over the **same** set of summand cords -
        i.e. a genuine double verification.

Only (b) is truly discriminant between pure bookkeeping and a structured
checksum layer. This script measures it directly via summand-set overlap.

Method
------
For each KFG-twinned validated khipu that contains at least one right sum
and at least one left sum:

1. For every (R_sum, L_sum) pair, compute
       Jaccard(R, L) = |S_R intersect S_L| / |S_R union S_L|
   where S_R and S_L are the summand cord-name sets.
2. Per khipu, keep:
      max_jaccard   -- the best double-verification pair on the khipu
      mean_jaccard  -- the overall tendency to double-verify
      pairs_ge_0.5  -- count of pairs with Jaccard >= 0.5
3. Null baseline: per khipu, shuffle the R/L labels across the existing
   sums (preserving the total number of R and L) 100 times and recompute
   max_jaccard for each permutation. The empirical p-value is
   (# null >= observed + 1) / (# null + 1).

Decision rule (see brief)
-------------------------
    mean max_jaccard > 0.5 AND p < 0.01  -> T3 strong: double verification
    mean max_jaccard in [0.2, 0.5]       -> T3 partial: moderate overlap
    mean max_jaccard < 0.2               -> T3 weak: complementary coverage

Outputs
-------
    output/ascher_bidirectional/overlap_analysis.csv
    output/ascher_bidirectional/overlap_report.md
    stdout : six-line summary plus the decision.

Usage
-----
    python scripts/ascher_bidirectional_overlap.py [--n-perms 100] [--seed N]
"""

from __future__ import annotations

import argparse
import random
import sys
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from khipu_translator.ascher import (  # noqa: E402
    AscherGraph, KFGClient, DEFAULT_CACHE_DIR,
    parse_kh_index, parse_khipu_xlsx,
)


VALIDATED_DIR = REPO_ROOT / "contributions" / "validated"
OUTPUT_DIR = REPO_ROOT / "output" / "ascher_bidirectional"


# ---------------------------------------------------------------------------
# OKR <-> KFG twinning (same recipe as ascher_null_model.py)
# ---------------------------------------------------------------------------

def build_okr_to_kh_index(client: KFGClient) -> Dict[str, str]:
    try:
        kh_list = parse_kh_index(client.fetch_index())
    except Exception:
        return {}
    mapping: Dict[str, str] = {}
    for kh in kh_list:
        if not kh.startswith("KH"):
            continue
        try:
            kd = parse_khipu_xlsx(client.fetch_xlsx(kh), kh)
        except Exception:
            continue
        for token in (kd.alias or "").replace("/", ",").split(","):
            t = token.strip()
            if t:
                mapping.setdefault(t, kh)
    return mapping


def list_validated_okr_ids() -> List[str]:
    if not VALIDATED_DIR.is_dir():
        return []
    return sorted(p.stem for p in VALIDATED_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def analyze(relations) -> Optional[dict]:
    """Compute Jaccard stats for one khipu's relations list.

    Returns None if the khipu has no R sums or no L sums (test inapplicable).
    """
    r_rels = [(i, r) for i, r in enumerate(relations) if r.hand == "right"]
    l_rels = [(i, r) for i, r in enumerate(relations) if r.hand == "left"]
    if not r_rels or not l_rels:
        return None

    pairs = []
    for (ri, r), (li, l) in product(r_rels, l_rels):
        sr = set(r.summands)
        sl = set(l.summands)
        j = jaccard(sr, sl)
        pairs.append({
            "r_sum_cord": r.sum_cord,
            "l_sum_cord": l.sum_cord,
            "jaccard":   j,
            "shared":    len(sr & sl),
            "union":     len(sr | sl),
        })

    jaccards = [p["jaccard"] for p in pairs]
    best = max(pairs, key=lambda p: p["jaccard"])
    return {
        "n_r_sums":     len(r_rels),
        "n_l_sums":     len(l_rels),
        "n_pairs":      len(pairs),
        "max_jaccard":  max(jaccards),
        "mean_jaccard": float(np.mean(jaccards)),
        "pairs_ge_0.5": sum(1 for j in jaccards if j >= 0.5),
        "best_pair":    best,
    }


def null_distribution(relations, n_perms: int, rng: random.Random
                      ) -> List[float]:
    """Shuffle hand labels and recompute max_jaccard. Returns list of
    max_jaccard values under the null (skipping permutations that happen
    to collapse one direction to zero, which cannot produce any pair)."""
    hands = [r.hand for r in relations]
    null_max: List[float] = []
    for _ in range(n_perms):
        shuffled = hands[:]
        rng.shuffle(shuffled)
        # Build shadow relations with only the `hand` and `summands` fields
        # that analyze() needs.
        shadow = [
            _FakeRel(hand=h, summands=r.summands, sum_cord=r.sum_cord)
            for h, r in zip(shuffled, relations)
        ]
        res = analyze(shadow)
        if res is not None:
            null_max.append(res["max_jaccard"])
    return null_max


class _FakeRel:
    __slots__ = ("hand", "summands", "sum_cord")

    def __init__(self, hand: str, summands: List[str], sum_cord: str):
        self.hand = hand
        self.summands = summands
        self.sum_cord = sum_cord


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-perms", type=int, default=100)
    ap.add_argument("--seed",    type=int, default=20260416)
    ap.add_argument("--cache-dir",  type=Path, default=DEFAULT_CACHE_DIR)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    ns = ap.parse_args()

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(ns.seed)

    client = KFGClient(cache_dir=ns.cache_dir)

    print("[*] Indexing OKR <-> KFG ...")
    index = build_okr_to_kh_index(client)
    okr_ids = [o for o in list_validated_okr_ids() if o in index]
    print(f"[*] Validated khipus with KFG twin: {len(okr_ids)}")

    rows: List[dict] = []
    skipped_no_sums = skipped_one_direction = 0

    for okr_id in okr_ids:
        kh_id = index[okr_id]
        try:
            graph = AscherGraph.from_kfg(kh_id, client=client)
        except Exception as e:
            print(f"  [skip] {okr_id}/{kh_id}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            continue
        if not graph.relations:
            skipped_no_sums += 1
            continue

        obs = analyze(graph.relations)
        if obs is None:
            skipped_one_direction += 1
            continue

        null_dist = null_distribution(graph.relations, ns.n_perms, rng)
        if null_dist:
            # Empirical right-tail p (observed >= null) with +1 smoothing.
            ge = sum(1 for x in null_dist if x >= obs["max_jaccard"])
            p_emp = (ge + 1) / (len(null_dist) + 1)
        else:
            p_emp = None

        rows.append({
            "okr_id":        okr_id,
            "kh_id":         kh_id,
            "n_sums":        len(graph.relations),
            "n_r":           obs["n_r_sums"],
            "n_l":           obs["n_l_sums"],
            "n_pairs":       obs["n_pairs"],
            "max_jaccard":   obs["max_jaccard"],
            "mean_jaccard":  obs["mean_jaccard"],
            "pairs_ge_0.5":  obs["pairs_ge_0.5"],
            "best_r_cord":   obs["best_pair"]["r_sum_cord"],
            "best_l_cord":   obs["best_pair"]["l_sum_cord"],
            "best_shared":   obs["best_pair"]["shared"],
            "best_union":    obs["best_pair"]["union"],
            "p_empirical":   p_emp,
            "n_null_valid":  len(null_dist),
        })

    df = pd.DataFrame(rows)
    csv_path = ns.output_dir / "overlap_analysis.csv"
    df.to_csv(csv_path, index=False)
    print(f"[+] wrote {csv_path} ({len(df)} rows)")
    print(f"    skipped: {skipped_no_sums} with no Ascher sums, "
          f"{skipped_one_direction} with only one direction")

    if df.empty:
        print("[!] No khipus with both R and L sums; nothing to report.")
        return 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    mean_max = df["max_jaccard"].mean()
    median_max = df["max_jaccard"].median()
    ge05_n = int((df["max_jaccard"] >= 0.5).sum())
    ge05_pct = 100.0 * ge05_n / len(df)
    ge08_n = int((df["max_jaccard"] >= 0.8).sum())
    ge08_pct = 100.0 * ge08_n / len(df)
    pmask = df["p_empirical"].notna()
    sig_n = int(((df["p_empirical"] < 0.01) & pmask).sum())
    mean_p = df.loc[pmask, "p_empirical"].mean() if pmask.any() else float("nan")

    if mean_max > 0.5 and sig_n >= max(1, int(0.5 * len(df))):
        decision = ("T3 STRONG: the double-verification reading is supported. "
                    "Most khipus pair a right sum with a left sum that "
                    "covers the same summand set.")
    elif mean_max >= 0.2:
        decision = ("T3 PARTIAL: directions partially overlap. Report T3 as "
                    "'moderate overlap between directions' with explicit "
                    "numeric spread.")
    else:
        decision = ("T3 WEAK: directions typically cover different summand "
                    "sets. Reformulate T3 as 'complementary coverage' rather "
                    "than 'double verification'.")

    # ------------------------------------------------------------------
    # Stdout
    # ------------------------------------------------------------------
    print()
    print("=" * 70)
    print("BIDIRECTIONAL OVERLAP ANALYSIS")
    print("=" * 70)
    print(f"Khipus with both R and L sums             : {len(df)}")
    print(f"Mean   of max_jaccard per khipu           : {mean_max:.3f}")
    print(f"Median of max_jaccard per khipu           : {median_max:.3f}")
    print(f"Khipus with max_jaccard >= 0.5            : {ge05_n}/{len(df)}"
          f" ({ge05_pct:.0f}%)")
    print(f"Khipus with max_jaccard >= 0.8            : {ge08_n}/{len(df)}"
          f" ({ge08_pct:.0f}%)")
    print(f"Khipus with p_empirical < 0.01            : {sig_n}/{len(df)}")
    print(f"Mean p_empirical                          : "
          f"{'n/a' if np.isnan(mean_p) else f'{mean_p:.3f}'}")
    print()
    print(f"Decision: {decision}")

    # ------------------------------------------------------------------
    # Markdown report
    # ------------------------------------------------------------------
    lines = []
    lines.append("# Bidirectional Overlap Analysis (Paper 2, T3 strong)")
    lines.append("")
    lines.append(
        "Test whether right-handed and left-handed Ascher sums on the same "
        "khipu total the **same cord sets** (genuine double verification) or "
        "**disjoint cord sets** (complementary coverage of different sections)."
    )
    lines.append("")
    lines.append(f"## Corpus: {len(df)} khipus with both R and L sums")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Mean max_jaccard (per khipu) | {mean_max:.3f} |")
    lines.append(f"| Median max_jaccard | {median_max:.3f} |")
    lines.append(
        f"| Khipus with at least one pair at Jaccard >= 0.5 "
        f"| {ge05_n} / {len(df)} ({ge05_pct:.0f}%) |"
    )
    lines.append(
        f"| Khipus with at least one pair at Jaccard >= 0.8 "
        f"| {ge08_n} / {len(df)} ({ge08_pct:.0f}%) |"
    )
    lines.append(
        f"| Khipus with p_empirical < 0.01 "
        f"(vs label-shuffle null, N={ns.n_perms}) | {sig_n} / {len(df)} |"
    )
    lines.append(
        f"| Mean p_empirical | "
        f"{'n/a' if np.isnan(mean_p) else f'{mean_p:.3f}'} |"
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(decision)
    lines.append("")
    lines.append("## Skipped khipus")
    lines.append("")
    lines.append(
        f"- {skipped_no_sums} khipus with no Ascher sums at all."
    )
    lines.append(
        f"- {skipped_one_direction} khipus with only one direction of sums "
        f"(R-only or L-only); the overlap test is not applicable to them."
    )

    report_path = ns.output_dir / "overlap_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[+] wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
