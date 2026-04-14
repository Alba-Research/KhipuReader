#!/usr/bin/env python3
"""
ascher_density_predictor.py
===========================

Find the structural variable that best predicts a khipu's erasure-correction
capacity.

Protocol
--------
1. Scan all KFG-twinned validated khipus; keep only those that are
   "clean" (0 pre-existing L? in OKR knot_sequence) AND have at least
   one pendant-pendant sum.
2. For each clean khipu, compute structural metrics:
     - cascade_depth            : longest DAG path (already computed)
     - n_sums                   : number of sum relations
     - n_involved_cords         : cords in at least one sum
     - covering_ratio           : n_involved / n_level1_cords
     - sums_per_cord            : n_sums / n_involved_cords
     - mean_refs_per_cord       : sum(|referenced_by|) / n_involved_cords
     - mean_summand_degree      : for DATA/BOTH cords, mean number of
                                   sums that reference them
3. Ablate (N ∈ {5,10,20,30,40,50}%, K trials) and compute 80%-recovery
   threshold: the largest damage level where mean recovery ≥ 80%.
4. Correlate threshold against each metric (Spearman ρ + p).
5. Plot: scatter of threshold vs best predictor, colored by cascade
   depth, with trend line and R² annotation.

Usage
-----
    python3 scripts/ascher_density_predictor.py
    python3 scripts/ascher_density_predictor.py --trials 30
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as sst

from khipu_translator.ascher import (
    AscherGraph, KFGClient,
    apply_ascher_constraints, apply_pure_arithmetic_repair,
    parse_kh_index, parse_khipu_xlsx, DEFAULT_CACHE_DIR,
)
from khipu_translator.translator import translate


VALIDATED_DIR = REPO_ROOT / "contributions" / "validated"
DAMAGE_LEVELS = [5, 10, 20, 30, 40, 50]   # cap at 50 to keep runs manageable
K_TRIALS = 20


# ---------------------------------------------------------------------------
# OKR ↔ KFG index
# ---------------------------------------------------------------------------

def _build_okr_to_kh_index(client: KFGClient) -> Dict[str, str]:
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


def _list_validated_okr_ids() -> List[str]:
    if not VALIDATED_DIR.is_dir():
        return []
    return sorted(p.stem for p in VALIDATED_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Per-khipu metrics + ablation
# ---------------------------------------------------------------------------

def _find_l_turn_tokens(seq: str) -> List[int]:
    out = []
    for i, t in enumerate(seq.split()):
        t = t.strip()
        if t.startswith("L") and t[1:].isdigit():
            out.append(i)
    return out


def _apply_mask(seq: str, idxs: List[int]) -> Tuple[str, Dict[int, int]]:
    toks = seq.split()
    original: Dict[int, int] = {}
    for i in idxs:
        if 0 <= i < len(toks) and toks[i].startswith("L") and toks[i][1:].isdigit():
            original[i] = int(toks[i][1:])
            toks[i] = "L?"
    return " ".join(toks), original


def compute_density_metrics(graph: AscherGraph, n_level1: int) -> Dict[str, float]:
    """Structural density metrics computed once from the graph."""
    involved = set()
    for rel in graph.relations:
        involved.add(rel.sum_cord)
        involved.update(rel.summands)
    # Reference count for each involved cord
    ref_count: Dict[str, int] = {}
    for c in involved:
        ref_count[c] = len(graph.get_sums_referencing(c))
    data_refs = [n for c, n in ref_count.items() if n > 0]

    n_sums = len(graph.relations)
    n_inv = len(involved)

    return {
        "n_sums": n_sums,
        "n_involved_cords": n_inv,
        "covering_ratio": n_inv / max(n_level1, 1),
        "sums_per_cord": n_sums / max(n_inv, 1),
        "mean_refs_per_cord": (sum(ref_count.values()) / max(n_inv, 1)),
        "mean_summand_degree": (sum(data_refs) / max(len(data_refs), 1))
                                if data_refs else 0.0,
        "max_refs": max(ref_count.values(), default=0),
    }


def ablate_one(result, graph: AscherGraph, damage_levels: List[int],
               k_trials: int, rng: random.Random) -> Dict[int, float]:
    """Return {damage_pct: mean correct-recovery rate} over K trials.

    Skips cords with pre-existing L?.
    """
    l1 = [c for c in result.cords if c.level == 1]
    for c in l1:
        if "L?" in (c.knot_sequence or ""):
            return {}   # khipu not clean — skip

    # Build damage pool on sum-involved cords only
    apply_ascher_constraints(result, graph)
    involved_idxs = {
        i for i, c in enumerate(l1)
        if c.ascher is not None and c.ascher.role != "FREE"
    }
    for c in l1:
        c.ascher = None

    damage_pool: List[Tuple[int, int]] = []
    for ci, c in enumerate(l1):
        if ci not in involved_idxs:
            continue
        for ti in _find_l_turn_tokens(c.knot_sequence or ""):
            damage_pool.append((ci, ti))
    if not damage_pool:
        return {}

    originals = {id(c): c.knot_sequence for c in l1}
    out: Dict[int, float] = {}
    for damage_pct in damage_levels:
        n_mask = max(1, int(round(damage_pct / 100.0 * len(damage_pool))))
        rates: List[float] = []
        for _ in range(k_trials):
            pairs = rng.sample(damage_pool, min(n_mask, len(damage_pool)))
            per_cord: Dict[int, List[int]] = {}
            for ci, ti in pairs:
                per_cord.setdefault(ci, []).append(ti)
            restores: Dict[int, Tuple[str, Dict[int, int]]] = {}
            for ci, tis in per_cord.items():
                seq = l1[ci].knot_sequence
                new_seq, om = _apply_mask(seq, tis)
                l1[ci].knot_sequence = new_seq
                restores[ci] = (seq, om)
            for c in l1:
                c.ascher = None
            apply_ascher_constraints(result, graph)
            apply_pure_arithmetic_repair(result, graph, max_iter=50)
            n_att = n_correct = 0
            for ci, (_, om) in restores.items():
                toks = l1[ci].knot_sequence.split()
                if sum(1 for t in toks if t == "L?") != 1:
                    continue
                n_att += 1
                cord = l1[ci]
                if cord.ascher and cord.ascher.repaired_turn is not None:
                    ti_masked = list(om.keys())[0]
                    if cord.ascher.repaired_turn == om[ti_masked]:
                        n_correct += 1
            for ci, (seq, _) in restores.items():
                l1[ci].knot_sequence = seq
            if n_att:
                rates.append(n_correct / n_att)
        out[damage_pct] = float(np.mean(rates)) if rates else float("nan")

    for c in l1:
        c.knot_sequence = originals[id(c)]
        c.ascher = None
    return out


def threshold_80(recovery_by_damage: Dict[int, float]) -> float:
    """Largest damage level where mean recovery ≥ 0.80 (0.0 if none)."""
    best = 0.0
    for d, r in sorted(recovery_by_damage.items()):
        if np.isnan(r):
            continue
        if r >= 0.80:
            best = float(d)
    return best


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path,
                    default=REPO_ROOT / "output" / "ascher_density")
    ap.add_argument("--trials", type=int, default=K_TRIALS)
    ap.add_argument("--seed", type=int, default=20260414)
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    ns = ap.parse_args()

    client = KFGClient(cache_dir=ns.cache_dir)
    rng = random.Random(ns.seed)

    print(f"[*] Indexing OKR ↔ KFG ...")
    index = _build_okr_to_kh_index(client)

    ok_list = [o for o in _list_validated_okr_ids() if o in index]
    print(f"[*] KFG-twinned validated khipus: {len(ok_list)}")

    rows: List[dict] = []
    for okr_id in ok_list:
        kh_id = index[okr_id]
        try:
            result = translate(okr_id)
            graph = AscherGraph.from_kfg(kh_id, client=client)
        except Exception as e:
            print(f"  [skip] {okr_id}/{kh_id}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            continue

        n_l1 = sum(1 for c in result.cords if c.level == 1)
        if len(graph.relations) == 0:
            continue

        # Compute density metrics (don't require ablation yet)
        metrics = compute_density_metrics(graph, n_l1)
        metrics["cascade_depth"] = graph.max_cascade_depth()

        # Ablate
        rec = ablate_one(result, graph, DAMAGE_LEVELS, ns.trials, rng)
        if not rec:
            print(f"  [skip] {okr_id}: not clean or no ablation pool",
                  file=sys.stderr)
            continue
        thr = threshold_80(rec)

        row = {"okr_id": okr_id, "kh_id": kh_id,
               "n_level1": n_l1, **metrics,
               "recovery": {str(k): v for k, v in rec.items()},
               "threshold_80": thr}
        rows.append(row)
        print(
            f"  {okr_id:<8s} / {kh_id:<7s}  depth={metrics['cascade_depth']}  "
            f"sums={metrics['n_sums']:>3d}  "
            f"refs/cord={metrics['mean_refs_per_cord']:>4.2f}  "
            f"thr80={thr:>4.0f}%"
        )

    if not rows:
        print("[!] no data", file=sys.stderr)
        return 1

    # Correlation analysis
    predictors = [
        "cascade_depth", "n_sums", "n_involved_cords",
        "covering_ratio", "sums_per_cord",
        "mean_refs_per_cord", "mean_summand_degree", "max_refs",
    ]
    y = np.array([r["threshold_80"] for r in rows])
    corr: List[Tuple[str, float, float]] = []
    for pred in predictors:
        x = np.array([r[pred] for r in rows], dtype=float)
        rho, p = sst.spearmanr(x, y)
        corr.append((pred, float(rho), float(p)))
    corr.sort(key=lambda t: -abs(t[1]))

    # --- Plot: threshold vs best predictor ---
    best = corr[0][0]
    x_best = np.array([r[best] for r in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(10, 7))
    depths = np.array([r["cascade_depth"] for r in rows])
    sc = ax.scatter(x_best, y, c=depths, cmap="viridis", s=100,
                    alpha=0.85, edgecolors="white", linewidths=0.8)
    for r in rows:
        ax.annotate(r["okr_id"], (r[best], r["threshold_80"]),
                    xytext=(5, 3), textcoords="offset points",
                    fontsize=7, color="#333")
    # Trend line (Spearman already has rho; fit a linear OLS for visual)
    if len(rows) >= 3:
        slope, intercept, r_val, p_val, _ = sst.linregress(x_best, y)
        xs = np.linspace(x_best.min(), x_best.max(), 100)
        ax.plot(xs, slope * xs + intercept, "--", color="red", alpha=0.5,
                label=f"OLS trend  R²={r_val**2:.2f}  (Spearman ρ={corr[0][1]:.2f}, p={corr[0][2]:.1e})")
    cbar = plt.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label("Cascade depth")
    ax.set_xlabel(best)
    ax.set_ylabel("Critical damage at 80 % recovery (%)")
    ax.set_title("Ascher erasure capacity — best predictor\n"
                 f"Across {len(rows)} KFG-twinned clean khipus")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    out_dir = ns.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "threshold_vs_best.png", dpi=180)
    plt.close(fig)

    # --- Plot grid: threshold vs each predictor ---
    fig2, axes = plt.subplots(2, 4, figsize=(18, 9))
    for ax_, (pred, rho, p) in zip(axes.flat, corr):
        x_vals = np.array([r[pred] for r in rows], dtype=float)
        ax_.scatter(x_vals, y, c=depths, cmap="viridis", s=60,
                    alpha=0.8, edgecolors="white", linewidths=0.6)
        ax_.set_xlabel(pred)
        ax_.set_ylabel("threshold 80% (%)")
        ax_.set_title(f"{pred}\nρ={rho:+.2f}  p={p:.1e}")
        ax_.grid(alpha=0.25)
    fig2.suptitle("Threshold vs structural predictors — Spearman correlations",
                  fontsize=12)
    fig2.tight_layout()
    fig2.savefig(out_dir / "threshold_vs_all.png", dpi=180)
    plt.close(fig2)

    # --- JSON + Markdown ---
    (out_dir / "density_results.json").write_text(
        json.dumps({"rows": rows,
                    "correlations": [{"predictor": c[0], "rho": c[1], "p": c[2]}
                                      for c in corr]},
                   indent=2, default=str),
        encoding="utf-8",
    )

    L = []
    L.append("# Ascher erasure capacity — density predictor analysis")
    L.append("")
    L.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    L.append("")
    L.append(f"## Corpus: {len(rows)} clean KFG-twinned khipus")
    L.append("")
    L.append("## Spearman correlations: structural predictors × 80%-recovery threshold")
    L.append("")
    L.append("| predictor | ρ | p |")
    L.append("|-----------|--:|--:|")
    for pred, rho, pv in corr:
        L.append(f"| {pred} | {rho:+.3f} | {pv:.2e} |")
    L.append("")
    L.append(f"**Best predictor**: `{corr[0][0]}` (ρ={corr[0][1]:+.3f}, p={corr[0][2]:.2e}).")
    L.append("")
    L.append("## Per-khipu detail")
    L.append("")
    L.append("| OKR | KFG | depth | n_sums | refs/cord | covering | thr80% |")
    L.append("|-----|-----|------:|-------:|----------:|---------:|-------:|")
    for r in sorted(rows, key=lambda r: -r["threshold_80"]):
        L.append(
            f"| {r['okr_id']} | {r['kh_id']} | {r['cascade_depth']} | "
            f"{r['n_sums']} | {r['mean_refs_per_cord']:.2f} | "
            f"{r['covering_ratio']:.2f} | {r['threshold_80']:.0f}% |"
        )
    L.append("")
    (out_dir / "density_report.md").write_text("\n".join(L), encoding="utf-8")

    print(f"[✓] {out_dir/'density_results.json'}")
    print(f"[✓] {out_dir/'density_report.md'}")
    print(f"[✓] {out_dir/'threshold_vs_best.png'}")
    print(f"[✓] {out_dir/'threshold_vs_all.png'}")
    print()
    print("Top-3 predictors (Spearman |ρ|):")
    for pred, rho, p in corr[:3]:
        print(f"  {pred:<22s}  ρ={rho:+.3f}  p={p:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
