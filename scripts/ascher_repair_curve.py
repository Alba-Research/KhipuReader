#!/usr/bin/env python3
"""
ascher_repair_curve.py
======================

Measure the **erasure-correction capacity** of the Ascher checksum system
across the full KFG-twinned validated corpus.

For each khipu, we compute:

  - damage_rate  = fraction of level-1 cords whose OKR knot_sequence
                   contains an L? (unreadable long-knot turn count)
  - recovery_rate = fraction of single-L? damaged cords repaired by
                   iterative fixed-point Strategy A (pure arithmetic,
                   no external cord-total source)
  - max_cascade_depth : depth of the sum-DAG

Output: scatter plot (damage × recovery, color = cascade depth) and a
Markdown report identifying the "sweet spot" — the damage-rate window
where Strategy A recovers > 80 % of damaged cords.

Usage
-----
    python3 scripts/ascher_repair_curve.py
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

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from khipu_translator.ascher import (
    AscherGraph, KFGClient,
    apply_ascher_constraints, apply_pure_arithmetic_repair,
    parse_kh_index, parse_khipu_xlsx, DEFAULT_CACHE_DIR,
)
from khipu_translator.translator import translate


VALIDATED_DIR = REPO_ROOT / "contributions" / "validated"


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
            xlsx = client.fetch_xlsx(kh)
            kd = parse_khipu_xlsx(xlsx, kh)
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


def _count_l_unknowns(seq: Optional[str]) -> int:
    return sum(1 for t in (seq or "").split() if t.strip() == "L?")


def process_one(okr_id: str, kh_id: str,
                client: KFGClient) -> Optional[dict]:
    """Run pipeline + repair, return per-khipu metrics (or None on error)."""
    try:
        result = translate(okr_id)
        graph = AscherGraph.from_kfg(kh_id, client=client)
        apply_ascher_constraints(result, graph)
        apply_pure_arithmetic_repair(result, graph, max_iter=50)
    except Exception as e:
        print(f"  [skip] {okr_id}/{kh_id}: {type(e).__name__}: {e}",
              file=sys.stderr)
        return None

    l1 = [c for c in result.cords if c.level == 1]
    # n_damaged counts cords with at least 1 L? (we'll differentiate
    # single-L? vs multi-L? for the "repairable in principle" denominator).
    damaged = [c for c in l1 if _count_l_unknowns(c.knot_sequence) > 0]
    single_lq = [c for c in l1 if _count_l_unknowns(c.knot_sequence) == 1]
    repaired = [c for c in l1
                if c.ascher is not None and c.ascher.repaired_turn is not None]

    n_l1 = len(l1)
    n_damaged = len(damaged)
    n_single = len(single_lq)
    n_repaired = len(repaired)

    return {
        "okr_id": okr_id,
        "kh_id": kh_id,
        "n_cords_level1": n_l1,
        "n_damaged": n_damaged,
        "n_single_lq": n_single,
        "n_repaired": n_repaired,
        "damage_rate": n_damaged / max(n_l1, 1),
        "recovery_rate_single": n_repaired / max(n_single, 1),
        "recovery_rate_overall": n_repaired / max(n_damaged, 1),
        "max_cascade_depth": graph.max_cascade_depth(),
        "n_sums": len(graph.relations),
        "n_iterations": int(result.stats.get("ascher_repair_iterations", 0)),
    }


def plot_curve(rows: List[dict], out_path: Path) -> None:
    """Scatter: x = damage rate, y = recovery rate on single-L? cords,
    size = number of damaged cords, color = max cascade depth.

    Only khipus with >= 1 single-L? cord are plotted (otherwise recovery
    is undefined).
    """
    plotted = [r for r in rows if r["n_single_lq"] > 0]
    if not plotted:
        print("[!] no data to plot", file=sys.stderr)
        return

    xs = np.array([100 * r["damage_rate"] for r in plotted])
    ys = np.array([100 * r["recovery_rate_single"] for r in plotted])
    sizes = np.array([25 + 3 * r["n_damaged"] for r in plotted])
    colors = np.array([r["max_cascade_depth"] for r in plotted])

    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(xs, ys, s=sizes, c=colors, cmap="viridis",
                    alpha=0.85, edgecolors="white", linewidths=0.8)

    # Annotate each point with OKR id
    for x, y, r in zip(xs, ys, plotted):
        ax.annotate(r["okr_id"], (x, y),
                    xytext=(5, 3), textcoords="offset points",
                    fontsize=7, color="#333")

    # Reference lines
    ax.axhline(80, color="red", linestyle="--", linewidth=0.8, alpha=0.4,
               label="80 % recovery threshold")
    ax.axvline(20, color="gray", linestyle=":",  linewidth=0.8, alpha=0.4)
    ax.axvline(50, color="gray", linestyle=":",  linewidth=0.8, alpha=0.4)

    ax.set_xlabel("Damage rate (% of level-1 cords with at least one L?)")
    ax.set_ylabel("Recovery rate on single-L? cords (%)")
    ax.set_title("Ascher Strategy A — iterative erasure-correction capacity\n"
                 "KhipuReader v2 · pure-checksum repair, no external totals")
    ax.set_xlim(-2, 102)
    ax.set_ylim(-2, 102)
    ax.grid(alpha=0.25)

    cbar = plt.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label("Max cascade depth (Merkle levels)")

    ax.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(f"[✓] plot saved: {out_path}")


def write_report(rows: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_ok = [r for r in rows if r is not None]
    rows_with_damage = [r for r in rows_ok if r["n_single_lq"] > 0]

    L: List[str] = []
    L.append("# Ascher Strategy A — Iterative Repair Curve")
    L.append("")
    L.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    L.append("")
    L.append("## Method")
    L.append("")
    L.append("For each KFG-twinned khipu in `contributions/validated/`:")
    L.append("")
    L.append("1. Translate via v1 pipeline (`translate`).")
    L.append("2. Build the KFG AscherGraph (sum relations + DAG).")
    L.append("3. Annotate cords with role / cascade depth.")
    L.append("4. Run **Pass 3D** — iterative fixed-point repair using **only**")
    L.append("   Ascher sum constraints (Strategy A, no external cord totals).")
    L.append("5. Count `n_single_lq` (level-1 cords with exactly one L?) and")
    L.append("   `n_repaired` (cords where Pass 3D recovered an L-turn).")
    L.append("")

    if rows_with_damage:
        damage  = np.array([100 * r["damage_rate"] for r in rows_with_damage])
        recov   = np.array([100 * r["recovery_rate_single"] for r in rows_with_damage])
        depth   = np.array([r["max_cascade_depth"] for r in rows_with_damage])
        L.append("## Aggregate")
        L.append("")
        L.append(f"- Khipus with ≥1 single-L? cord: **{len(rows_with_damage)}**")
        L.append(f"- Mean damage rate:    {damage.mean():.1f}% "
                 f"(median {np.median(damage):.1f}%, range {damage.min():.1f}–{damage.max():.1f}%)")
        L.append(f"- Mean recovery rate:  {recov.mean():.1f}% "
                 f"(median {np.median(recov):.1f}%)")
        L.append(f"- Total single-L? cords: {sum(r['n_single_lq'] for r in rows_with_damage)}")
        L.append(f"- Total repaired:        {sum(r['n_repaired'] for r in rows_with_damage)}")
        L.append("")

        # Sweet-spot detection: buckets of damage, mean recovery in each.
        edges = [0, 5, 10, 20, 30, 50, 75, 100]
        L.append("## Damage-bucket summary")
        L.append("")
        L.append("| damage bucket | khipus | mean recovery | mean cascade depth |")
        L.append("|--------------:|-------:|--------------:|-------------------:|")
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (damage >= lo) & (damage < hi)
            n = int(mask.sum())
            if n == 0:
                L.append(f"| {lo}–{hi}% | 0 | — | — |")
                continue
            L.append(
                f"| {lo}–{hi}% | {n} | "
                f"{recov[mask].mean():.1f}% | "
                f"{depth[mask].mean():.1f} |"
            )
        L.append("")

        # Sweet-spot identified: lowest damage bucket where recovery >= 80%
        L.append("## Sweet spot")
        L.append("")
        sweet_found = False
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (damage >= lo) & (damage < hi)
            if mask.sum() == 0:
                continue
            if recov[mask].mean() >= 80:
                L.append(f"Strategy A recovers ≥ 80 % of single-L? cords in the "
                         f"**{lo}–{hi}%** damage bucket ({int(mask.sum())} khipus).")
                sweet_found = True
                break
        if not sweet_found:
            # Fall back to best bucket
            best_lo, best_hi, best_mean = None, None, -1.0
            for lo, hi in zip(edges[:-1], edges[1:]):
                mask = (damage >= lo) & (damage < hi)
                if mask.sum() == 0:
                    continue
                m = recov[mask].mean()
                if m > best_mean:
                    best_mean, best_lo, best_hi = m, lo, hi
            if best_lo is not None:
                L.append(f"No bucket reaches 80 % recovery. Best: "
                         f"**{best_lo}–{best_hi}%** damage → "
                         f"{best_mean:.1f}% recovery.")

        L.append("")

    # Per-khipu table
    L.append("## Per-khipu detail")
    L.append("")
    L.append("| OKR | KFG | n_l1 | damaged | single-L? | repaired | "
             "damage% | recovery% | depth | iters |")
    L.append("|-----|-----|-----:|--------:|----------:|---------:|"
             "--------:|----------:|------:|------:|")
    for r in sorted(rows_ok, key=lambda r: -r["damage_rate"]):
        L.append(
            f"| {r['okr_id']} | {r['kh_id']} | {r['n_cords_level1']} | "
            f"{r['n_damaged']} | {r['n_single_lq']} | {r['n_repaired']} | "
            f"{100*r['damage_rate']:.1f}% | "
            f"{100*r['recovery_rate_single']:.1f}% | "
            f"{r['max_cascade_depth']} | {r['n_iterations']} |"
        )
    path.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path,
                    default=REPO_ROOT / "output" / "ascher_repair_curve")
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    ap.add_argument("--quiet", action="store_true")
    ns = ap.parse_args()

    ok_list = _list_validated_okr_ids()
    client = KFGClient(cache_dir=ns.cache_dir)
    print(f"[*] Building OKR→KFG mapping ...")
    index = _build_okr_to_kh_index(client)
    print(f"    {len(index)} aliases indexed")

    rows: List[dict] = []
    for okr_id in ok_list:
        kh_id = index.get(okr_id)
        if not kh_id:
            continue
        res = process_one(okr_id, kh_id, client)
        if res is None:
            continue
        rows.append(res)
        if not ns.quiet:
            print(
                f"  {okr_id:<8s} / {kh_id:<7s}  "
                f"l1={res['n_cords_level1']:>3d}  dmg={100*res['damage_rate']:>5.1f}%  "
                f"single-L?={res['n_single_lq']:>3d}  repaired={res['n_repaired']:>3d}  "
                f"recov={100*res['recovery_rate_single']:>5.1f}%  "
                f"depth={res['max_cascade_depth']}  iters={res['n_iterations']}"
            )

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = ns.output_dir / "repair_curve.json"
    md_path = ns.output_dir / "repair_curve.md"
    png_path = ns.output_dir / "repair_curve.png"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_report(rows, md_path)
    plot_curve(rows, png_path)
    print(f"[✓] {json_path}")
    print(f"[✓] {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
