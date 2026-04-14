#!/usr/bin/env python3
"""
ascher_ablation.py
==================

**Controlled ablation** of Ascher erasure-correction capacity.

We take clean (OKR-complete) khipus with varying cascade depths, randomly
mask a fraction of their L-turn counts as ``L?``, and measure how many
Pass 3D recovers by pure sum-arithmetic fixed-point iteration. The
resulting recovery-vs-damage curve is the empirical signature of the
embedded erasure code.

Protocol
--------
For each selected khipu (varied cascade depth), for damage level
N ∈ {5, 10, 15, 20, 25, 30, 40, 50, 60, 70 %}, for K random masks:

  1. copy the knot_sequence of every level-1 cord
  2. randomly replace ``int(N% × total_L_knots)`` of the L-turn tokens
     by ``L?``  (the "erasure")
  3. re-run ``apply_ascher_constraints`` + ``apply_pure_arithmetic_repair``
  4. count
       attempted : cords with exactly one L? after masking
       repaired  : cords where Pass 3D set ``ascher.repaired_turn``
       correct   : cords where ``repaired_turn == original_turn``
  5. restore the original knot_sequence

We plot `correct_recovery` (= # correct / # attempted) vs damage,
one line per khipu, colored by cascade depth.

Predictions
-----------
  * At low damage (N → 0), recovery → 100 % on every khipu with sums.
  * At high damage (N → 100), recovery → 0.
  * **Transition sharpness** should correlate with cascade depth:
    deeper cascades (more redundancy) tolerate more damage before
    collapsing. This is the phase-transition signature of LDPC-style
    erasure codes.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from khipu_translator.ascher import (
    AscherGraph, KFGClient,
    apply_ascher_constraints, apply_pure_arithmetic_repair,
    DEFAULT_CACHE_DIR,
)
from khipu_translator.translator import translate


# Representative khipus spanning the cascade-depth spectrum.
# All are v1-clean (no pre-existing L?) so we control the damage.
DEFAULT_SELECTION = [
    ("UR1145", "KH0161", 6),   # deepest cascade in corpus
    ("UR198",  "KH0436", 4),   # deep
    ("UR022",  "KH0258", 5),   # deep + large
    ("UR1136", "KH0152", 3),   # medium
    ("UR112",  "KH0348", 1),   # shallow
    ("UR052",  "KH0282", 2),   # flagship case
]

DAMAGE_LEVELS = [5, 10, 15, 20, 25, 30, 40, 50, 60, 70]
K_TRIALS = 40

# ---------------------------------------------------------------------------
# Mask application
# ---------------------------------------------------------------------------

def _find_l_turn_tokens(seq: str) -> List[int]:
    """Indices of space-separated tokens that are ``L{N}`` with digit suffix."""
    out = []
    toks = seq.split()
    for i, t in enumerate(toks):
        t = t.strip()
        if t.startswith("L") and t[1:].isdigit():
            out.append(i)
    return out


def _apply_mask(seq: str, mask_indices: List[int]) -> Tuple[str, Dict[int, int]]:
    """Replace L{N} at given indices by L?, return (new_seq, {idx: original_N})."""
    toks = seq.split()
    original: Dict[int, int] = {}
    for i in mask_indices:
        if 0 <= i < len(toks) and toks[i].startswith("L") and toks[i][1:].isdigit():
            original[i] = int(toks[i][1:])
            toks[i] = "L?"
    return " ".join(toks), original


# ---------------------------------------------------------------------------
# Experiment per-khipu
# ---------------------------------------------------------------------------

def run_one_khipu(okr_id: str, kh_id: str, cascade_depth: int,
                  client: KFGClient, rng: random.Random,
                  damage_levels: List[int], k_trials: int,
                  verbose: bool = True) -> List[dict]:
    """Run the ablation on one khipu. Returns list of dicts
    (one per (damage_level, trial))."""
    result = translate(okr_id)
    graph = AscherGraph.from_kfg(kh_id, client=client)

    # Level-1 cords + their original knot_sequence
    l1 = [c for c in result.cords if c.level == 1]
    originals: Dict[int, str] = {id(c): c.knot_sequence for c in l1}

    # We restrict the damage pool to cords that are actually part of a
    # sum relation — FREE cords cannot be repaired by ANY constraint
    # system, so including them in the denominator would only dilute
    # the signal. Annotate once to learn each cord's role.
    apply_ascher_constraints(result, graph)
    involved_cord_indices = {
        ci for ci, c in enumerate(l1)
        if c.ascher is not None and c.ascher.role != "FREE"
    }
    # Reset so repair starts fresh each trial below.
    for c in l1:
        c.ascher = None

    # Build the global damage pool: (cord_index_in_l1, token_index_in_seq)
    # restricted to sum-involved cords.
    damage_pool: List[Tuple[int, int]] = []
    for ci, c in enumerate(l1):
        if ci not in involved_cord_indices:
            continue
        for ti in _find_l_turn_tokens(c.knot_sequence or ""):
            damage_pool.append((ci, ti))

    total_l = len(damage_pool)
    if total_l == 0:
        print(f"  [skip] {okr_id}: no L-knots to mask", file=sys.stderr)
        return []

    # Baseline: are there L? tokens before we mask? If yes, this khipu
    # is not truly clean and results will be noisy — filter out.
    existing_lq = sum(
        1 for c in l1 for t in (c.knot_sequence or "").split() if t.strip() == "L?"
    )
    if existing_lq > 0:
        print(f"  [skip] {okr_id}: already has {existing_lq} L? in OKR — not clean",
              file=sys.stderr)
        return []

    if verbose:
        print(f"  {okr_id}/{kh_id} depth={cascade_depth}  "
              f"l1={len(l1)}  total_L={total_l}  sums={len(graph.relations)}")

    rows: List[dict] = []
    for damage_pct in damage_levels:
        n_mask = int(round((damage_pct / 100.0) * total_l))
        if n_mask == 0:
            continue

        for trial in range(k_trials):
            mask_pairs = rng.sample(damage_pool, n_mask)

            # Group mask_indices by cord
            per_cord: Dict[int, List[int]] = {}
            for ci, ti in mask_pairs:
                per_cord.setdefault(ci, []).append(ti)

            # Apply masks
            restores: Dict[int, Tuple[str, Dict[int, int]]] = {}
            for ci, token_idxs in per_cord.items():
                orig_seq = l1[ci].knot_sequence
                new_seq, originals_map = _apply_mask(orig_seq, token_idxs)
                l1[ci].knot_sequence = new_seq
                restores[ci] = (orig_seq, originals_map)

            # Reset any prior ascher annotations
            for c in l1:
                c.ascher = None
            # reset stats so our repair function can record fresh values
            for key in ("ascher_repaired", "ascher_repair_iterations",
                        "ascher_repair_unresolved"):
                if key in result.stats:
                    del result.stats[key]

            # Run Pass 2 + 3D
            apply_ascher_constraints(result, graph)
            apply_pure_arithmetic_repair(result, graph, max_iter=50)

            # Count metrics
            n_attempted = 0
            n_repaired = 0
            n_correct = 0
            for ci, (_orig_seq, orig_map) in restores.items():
                cord = l1[ci]
                # Was it a single-L? candidate?
                current_toks = cord.knot_sequence.split()
                n_lq = sum(1 for t in current_toks if t == "L?")
                if n_lq == 1:
                    n_attempted += 1
                    if cord.ascher and cord.ascher.repaired_turn is not None:
                        n_repaired += 1
                        # Find the original L-turn for this single L?
                        # It's the only masked index in this cord.
                        ti_masked = list(orig_map.keys())[0]
                        orig_turn = orig_map[ti_masked]
                        if cord.ascher.repaired_turn == orig_turn:
                            n_correct += 1

            # Also count multi-L? cords (they exist if >1 mask fell in a cord)
            n_multi_lq_cords = 0
            for ci in restores:
                n_lq = sum(1 for t in l1[ci].knot_sequence.split() if t == "L?")
                if n_lq > 1:
                    n_multi_lq_cords += 1

            # Restore originals
            for ci, (orig_seq, _) in restores.items():
                l1[ci].knot_sequence = orig_seq

            rows.append({
                "okr_id": okr_id, "kh_id": kh_id,
                "cascade_depth": cascade_depth,
                "damage_pct": damage_pct,
                "trial": trial,
                "n_mask": n_mask,
                "total_L": total_l,
                "n_attempted": n_attempted,       # cords with exactly 1 L? after mask
                "n_repaired": n_repaired,         # Pass 3D produced a value
                "n_correct": n_correct,           # value matches ground truth
                "n_multi_lq_cords": n_multi_lq_cords,
                "iterations": int(result.stats.get("ascher_repair_iterations", 0)),
            })

        # Ensure everything is restored (defensive).
        for c in l1:
            c.knot_sequence = originals[id(c)]
            c.ascher = None

    return rows


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_curves(rows: List[dict], out_path: Path) -> None:
    import pandas as pd
    df = pd.DataFrame(rows)
    if df.empty:
        print("[!] no data to plot", file=sys.stderr)
        return

    # Aggregate per (okr_id, damage_pct): mean & std of correct-recovery rate
    df["recovery"] = df["n_correct"] / df["n_attempted"].replace(0, np.nan)
    agg = df.groupby(["okr_id", "kh_id", "cascade_depth", "damage_pct"]).agg(
        recovery_mean=("recovery", "mean"),
        recovery_std=("recovery", "std"),
        trials=("trial", "count"),
        n_attempted_mean=("n_attempted", "mean"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(10, 7))
    cmap = plt.get_cmap("viridis")
    depths = sorted(agg["cascade_depth"].unique())
    dmin, dmax = min(depths), max(depths)
    for (okr_id, kh_id, depth), sub in agg.groupby(["okr_id", "kh_id", "cascade_depth"]):
        sub = sub.sort_values("damage_pct")
        color = cmap(0.15 + 0.8 * (depth - dmin) / max(dmax - dmin, 1))
        xs = sub["damage_pct"].values
        ys = 100 * sub["recovery_mean"].values
        stds = 100 * sub["recovery_std"].fillna(0).values
        ax.plot(xs, ys, "-o", color=color, linewidth=2,
                markersize=6, label=f"{okr_id} · depth={depth}")
        ax.fill_between(xs, np.maximum(ys - stds, 0),
                        np.minimum(ys + stds, 100),
                        color=color, alpha=0.15)

    ax.axhline(80, color="red", linestyle="--", linewidth=0.8, alpha=0.4,
               label="80 % recovery")
    ax.axhline(50, color="gray", linestyle=":", linewidth=0.8, alpha=0.4)
    ax.set_xlabel("Damage rate: % of L-turns masked to L?")
    ax.set_ylabel("Correct recovery rate on single-L? cords (%)")
    ax.set_title("Ascher Pass 3D — controlled erasure-correction capacity\n"
                 "Strategy A only (iterative fixed-point, pure arithmetic)")
    ax.set_xlim(0, 75)
    ax.set_ylim(-2, 102)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[✓] plot saved: {out_path}")
    return agg


def write_report(rows: List[dict], agg, out_path: Path) -> None:
    import pandas as pd
    if isinstance(agg, type(None)):
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    L: List[str] = []
    L.append("# Ascher Pass 3D — Controlled Ablation Curve")
    L.append("")
    L.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    L.append("")
    L.append("## Protocol")
    L.append("")
    L.append(f"For each khipu × damage level × trial ({K_TRIALS} random masks per point):")
    L.append("")
    L.append("1. Random sample N% of L-turn tokens; replace by `L?`.")
    L.append("2. Run `apply_ascher_constraints` + `apply_pure_arithmetic_repair`.")
    L.append("3. Count ‘correct’ = `repaired_turn == original_turn`.")
    L.append("4. Restore original sequence.")
    L.append("")
    L.append("## Mean recovery per (khipu, damage) bucket")
    L.append("")
    L.append("| OKR | depth | 5% | 10% | 15% | 20% | 25% | 30% | 40% | 50% | 60% | 70% |")
    L.append("|-----|------:|---:|----:|----:|----:|----:|----:|----:|----:|----:|----:|")
    for (okr_id, depth), grp in agg.groupby(["okr_id", "cascade_depth"]):
        row = [f"{okr_id} | {depth}"]
        for lvl in DAMAGE_LEVELS:
            sub = grp[grp["damage_pct"] == lvl]
            if sub.empty or np.isnan(sub["recovery_mean"].iloc[0]):
                row.append("—")
            else:
                row.append(f"{100*sub['recovery_mean'].iloc[0]:.0f}%")
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    L.append("## Damage threshold at 80 % recovery")
    L.append("")
    L.append("For each khipu, the highest damage level where mean recovery ≥ 80 %:")
    L.append("")
    L.append("| OKR | depth | critical damage level |")
    L.append("|-----|------:|---------------------:|")
    for (okr_id, depth), grp in agg.groupby(["okr_id", "cascade_depth"]):
        passing = grp[grp["recovery_mean"] >= 0.80].sort_values("damage_pct")
        if passing.empty:
            threshold = "< 5%"
        else:
            threshold = f"{int(passing['damage_pct'].max())}%"
        L.append(f"| {okr_id} | {depth} | {threshold} |")
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"[✓] {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path,
                    default=REPO_ROOT / "output" / "ascher_ablation")
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    ap.add_argument("--trials", type=int, default=K_TRIALS)
    ap.add_argument("--seed", type=int, default=20260414)
    ns = ap.parse_args()

    client = KFGClient(cache_dir=ns.cache_dir)
    rng = random.Random(ns.seed)

    print(f"[*] Running ablation on {len(DEFAULT_SELECTION)} khipus, "
          f"{len(DAMAGE_LEVELS)} damage levels, {ns.trials} trials each "
          f"({len(DEFAULT_SELECTION) * len(DAMAGE_LEVELS) * ns.trials} runs).")

    all_rows: List[dict] = []
    for okr_id, kh_id, depth in DEFAULT_SELECTION:
        rows = run_one_khipu(okr_id, kh_id, depth, client,
                              rng, DAMAGE_LEVELS, ns.trials, verbose=True)
        all_rows.extend(rows)

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = ns.output_dir / "ablation_raw.json"
    md_path   = ns.output_dir / "ablation_report.md"
    png_path  = ns.output_dir / "ablation_curves.png"
    json_path.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    agg = plot_curves(all_rows, png_path)
    write_report(all_rows, agg, md_path)
    print(f"[✓] raw: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
