#!/usr/bin/env python3
"""
run_ascher_enhanced.py
======================

Run the v2 Ascher-enhanced reader on every validated-contribution khipu
and produce a Merkle-structure report (not a syllabic-coverage report):

  - number of pendant-pendant sums found
  - number (and fraction) of checksums that verify against the reader
  - maximum and mean cascade depth in the Merkle DAG
  - new readings unlocked via Pass 3A reclassification
  - exactly-one-unknown constraints solved via Pass 3C
  - fraction of sum-cords that are STRING (the "hybrid" zone where both
    arithmetic and syllabic channels operate)

Usage
-----
    python3 scripts/run_ascher_enhanced.py                           # all validated
    python3 scripts/run_ascher_enhanced.py UR052 UR120               # explicit list
    python3 scripts/run_ascher_enhanced.py --output-dir output/...   # custom dir
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from khipu_translator.ascher import (
    AscherGraph, KFGClient,
    apply_ascher_constraints, apply_reclassification, apply_constraint_propagation,
    parse_kh_index, parse_khipu_xlsx, DEFAULT_CACHE_DIR,
)
from khipu_translator.translator import translate

VALIDATED_DIR = REPO_ROOT / "contributions" / "validated"


# ---------------------------------------------------------------------------
# OKR ↔ KFG index
# ---------------------------------------------------------------------------

def _build_okr_to_kh_index(client: KFGClient) -> Dict[str, str]:
    """Scan the KFG sums index, build {okr_alias: kh_id}."""
    try:
        kh_list = parse_kh_index(client.fetch_index())
    except Exception as e:
        print(f"[warn] cannot fetch KFG index: {e}", file=sys.stderr)
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
        alias = (kd.alias or "").strip()
        if not alias:
            continue
        for token in alias.replace("/", ",").split(","):
            t = token.strip()
            if t:
                mapping.setdefault(t, kh)
    return mapping


def _list_validated_okr_ids() -> List[str]:
    """Return the OKR id of every *.json file under contributions/validated/."""
    if not VALIDATED_DIR.is_dir():
        return []
    return sorted(p.stem for p in VALIDATED_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Per-khipu processing
# ---------------------------------------------------------------------------

def _merkle_stats(result, graph: AscherGraph) -> Dict[str, object]:
    """Compute the Merkle-structure view of an annotated TranslationResult."""
    sum_cord_names = [rel.sum_cord for rel in graph.relations]
    annotated = [c for c in result.cords if c.ascher is not None]
    headers   = [c for c in annotated if c.ascher.role in ("HEADER", "BOTH")]
    data      = [c for c in annotated if c.ascher.role in ("DATA",   "BOTH")]
    verified  = [c for c in headers if c.ascher.verified is True]

    # Per-node depths (exclude 0-depth leaves to get meaningful mean)
    depths = [c.ascher.cascade_depth for c in annotated]
    mean_depth = mean(depths) if depths else 0.0
    max_depth  = graph.max_cascade_depth()

    # STRING fraction of sum-cords (the "hybrid" zone)
    n_string_headers = sum(1 for c in headers if c.cord_type == "STRING")

    return {
        "n_sums": len(graph.relations),
        "n_sum_cords": len(headers),
        "n_sum_cords_string": n_string_headers,
        "sum_string_frac": (n_string_headers / len(headers)) if headers else 0.0,
        "n_verified": len(verified),
        "verified_frac": (len(verified) / len(headers)) if headers else 0.0,
        "n_data_cords": len(data),
        "max_cascade_depth": max_depth,
        "mean_cascade_depth": round(mean_depth, 2),
        "n_reclassified": int(result.stats.get("ascher_reclassified", 0)),
        "n_propagated": int(result.stats.get("ascher_propagated", 0)),
    }


def process_one(okr_id: str, kh_id: Optional[str],
                client: KFGClient) -> Dict[str, object]:
    t0 = time.time()
    try:
        result = translate(okr_id)
    except Exception as e:
        return {"okr_id": okr_id, "status": f"translate_failed:{e}"}

    # Baseline info — always useful alongside the Merkle view.
    n_cords = len(result.cords)
    n_string = sum(1 for c in result.cords if c.cord_type == "STRING")

    if not kh_id:
        return {
            "okr_id": okr_id, "kh_id": None, "status": "no_kfg_twin",
            "n_cords": n_cords, "n_string": n_string,
            "elapsed_s": round(time.time() - t0, 2),
        }

    try:
        graph = AscherGraph.from_kfg(kh_id, client=client)
        apply_ascher_constraints(result, graph)
        apply_reclassification(result, graph)
        apply_constraint_propagation(result, graph)
    except Exception as e:
        return {
            "okr_id": okr_id, "kh_id": kh_id, "status": f"ascher_failed:{e}",
            "n_cords": n_cords, "n_string": n_string,
        }

    merkle = _merkle_stats(result, graph)
    return {
        "okr_id": okr_id, "kh_id": kh_id, "status": "ok",
        "n_cords": n_cords, "n_string": n_string,
        "elapsed_s": round(time.time() - t0, 2),
        **merkle,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [r for r in rows if r["status"] == "ok"]
    skipped = [r for r in rows if r["status"] != "ok"]

    L: List[str] = []
    L.append("# KhipuReader v2 — Merkle-structure report")
    L.append("")
    L.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    L.append("")

    # --- Aggregate headline ---
    if ok_rows:
        total_sums     = sum(r["n_sums"] for r in ok_rows)
        total_sumcords = sum(r["n_sum_cords"] for r in ok_rows)
        total_verified = sum(r["n_verified"] for r in ok_rows)
        total_recl     = sum(r["n_reclassified"] for r in ok_rows)
        total_prop     = sum(r["n_propagated"] for r in ok_rows)
        deepest        = max(r["max_cascade_depth"] for r in ok_rows)
        cascaded       = [r for r in ok_rows if r["max_cascade_depth"] >= 2]
        L.append("## Headline")
        L.append("")
        L.append(f"- Khipus attempted: **{len(rows)}**  (with KFG twin: **{len(ok_rows)}**, skipped: {len(skipped)})")
        L.append(f"- Pendant-pendant sums parsed: **{total_sums}**")
        L.append(f"- Sum-cords verified: **{total_verified} / {total_sumcords}** "
                 f"(**{100*total_verified/max(total_sumcords,1):.1f}%**)")
        L.append(f"- Khipus with cascading (depth ≥ 2): **{len(cascaded)} / {len(ok_rows)}**")
        L.append(f"- Deepest Merkle cascade: **{deepest}**")
        L.append(f"- Readings unlocked (Pass 3A): **{total_recl}**")
        L.append(f"- Constraints solved (Pass 3C): **{total_prop}**")
        L.append("")

    # --- Per-khipu Merkle view ---
    L.append("## Per-khipu Merkle structure")
    L.append("")
    L.append(
        "| OKR | KFG | cords | sums | sum-cords "
        "STRING% | verified | cascade max | mean | new reads | solved |"
    )
    L.append(
        "|-----|-----|------:|-----:|---------:|---------:|"
        "-------:|-----:|----------:|-------:|"
    )
    for r in sorted(rows, key=lambda x: -x.get("max_cascade_depth", -1)):
        if r["status"] != "ok":
            L.append(
                f"| {r['okr_id']} | {r.get('kh_id') or '—'} | "
                f"{r.get('n_cords','?')} | — | — | — | — | — | — | — |"
                f"  _({r['status']})_"
            )
            continue
        L.append(
            f"| {r['okr_id']} | {r['kh_id']} | "
            f"{r['n_cords']} | {r['n_sums']} | "
            f"{100*r['sum_string_frac']:>5.1f}% | "
            f"{r['n_verified']}/{r['n_sum_cords']} | "
            f"{r['max_cascade_depth']} | {r['mean_cascade_depth']:.1f} | "
            f"{r['n_reclassified']} | {r['n_propagated']} |"
        )
    L.append("")

    # --- Cascades: distribution + top-10 deepest
    if ok_rows:
        depths = [r["max_cascade_depth"] for r in ok_rows]
        bucket: Dict[int, int] = {}
        for d in depths:
            bucket[d] = bucket.get(d, 0) + 1
        L.append("## Cascade-depth distribution")
        L.append("")
        L.append("| depth | khipus |")
        L.append("|------:|-------:|")
        for d in sorted(bucket):
            L.append(f"| {d} | {bucket[d]} |")
        L.append("")
        L.append("## Deepest cascades (top 10)")
        L.append("")
        L.append("| OKR | KFG | max depth | verified/sums | new reads |")
        L.append("|-----|-----|----------:|--------------:|----------:|")
        top = sorted(ok_rows, key=lambda r: -r["max_cascade_depth"])[:10]
        for r in top:
            L.append(
                f"| {r['okr_id']} | {r['kh_id']} | "
                f"{r['max_cascade_depth']} | "
                f"{r['n_verified']}/{r['n_sum_cords']} | "
                f"{r['n_reclassified']} |"
            )
        L.append("")

    # --- Where reclassification helped
    if ok_rows:
        recl_rows = sorted(
            [r for r in ok_rows if r["n_reclassified"] > 0],
            key=lambda r: -r["n_reclassified"],
        )
        if recl_rows:
            L.append("## Khipus where Pass 3A unlocked readings")
            L.append("")
            L.append("| OKR | KFG | new readings | STRING% sum-cords |")
            L.append("|-----|-----|-------------:|------------------:|")
            for r in recl_rows:
                L.append(
                    f"| {r['okr_id']} | {r['kh_id']} | "
                    f"{r['n_reclassified']} | "
                    f"{100*r['sum_string_frac']:.0f}% |"
                )
            L.append("")

    # --- Skipped
    if skipped:
        L.append("## Skipped khipus")
        L.append("")
        L.append("| OKR | reason |")
        L.append("|-----|--------|")
        for r in skipped:
            L.append(f"| {r['okr_id']} | {r['status']} |")
        L.append("")

    path.write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("khipus", nargs="*", default=None,
                    help="OKR IDs to process (default: every contributions/validated/*.json)")
    ap.add_argument("--output-dir", type=Path,
                    default=REPO_ROOT / "output" / "ascher_enhanced")
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    ap.add_argument("--quiet", action="store_true")
    ns = ap.parse_args()

    if ns.khipus:
        ok_list = list(ns.khipus)
    else:
        ok_list = _list_validated_okr_ids()
        if not ok_list:
            print(f"[!] No validated contributions under {VALIDATED_DIR}",
                  file=sys.stderr)
            return 1

    client = KFGClient(cache_dir=ns.cache_dir)
    print(f"[*] {len(ok_list)} khipus to process")
    print(f"[*] Building OKR→KFG mapping from {ns.cache_dir} ...")
    index = _build_okr_to_kh_index(client)
    print(f"    {len(index)} OKR aliases indexed")

    rows: List[Dict[str, object]] = []
    for okr_id in ok_list:
        kh_id = index.get(okr_id)
        result = process_one(okr_id, kh_id, client)
        rows.append(result)
        if not ns.quiet:
            if result["status"] == "ok":
                print(
                    f"  {okr_id:<8s} / {kh_id or '—':<7s}  "
                    f"sums={result['n_sums']:>3d}  "
                    f"verif={result['n_verified']:>3d}/{result['n_sum_cords']:<3d}  "
                    f"depth={result['max_cascade_depth']}  "
                    f"recl={result['n_reclassified']:>2d}  prop={result['n_propagated']}"
                )
            else:
                print(f"  {okr_id:<8s} / {kh_id or '—':<7s}  {result['status']}")

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = ns.output_dir / "ascher_enhanced_stats.json"
    md_path = ns.output_dir / "ascher_enhanced_report.md"
    json_path.write_text(json.dumps(rows, indent=2, default=str),
                         encoding="utf-8")
    write_report(rows, md_path)
    print(f"[✓] {json_path}")
    print(f"[✓] {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
