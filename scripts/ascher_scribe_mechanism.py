#!/usr/bin/env python3
"""
ascher_scribe_mechanism.py
==========================

Test the "scribe gesture" / checksum hypothesis for Ascher pendant-pendant sums:

    The khipukamayuq first knots the textual label (long knots, syllabic channel),
    then pads the cord with simple knots (numerical channel) so the Locke total
    matches a section sum. The Ascher sum is a tamper-detection checksum, not
    the scribe's primary intent.

Seven tests on the OKR corpus:
  T1. S-knot padding surplus     (Mann-Whitney U, sum-cords vs summands, STRING)
  T2. Topological separation     (sum-cord in a different group from its summands)
  T3. Directional asymmetry      (right = header BEFORE data; left = AFTER)
  T4. Color role-marking          (sum-cord color != majority summand color)
  T5. Syllabic complexity         (sum-cord more L-knots than summand)
  T6. Cascade depth vs khipu size (Merkle tree — Spearman correlation)
  T7. Summand criticality         (high-degree summands = kinship/governance)

Author : Julien Sivan (ALBA Project)
Date   : 2026-04-14

Usage : python3 ascher_scribe_mechanism.py [--limit N] [--khipus KH0001 ...]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Set

import numpy as np
import pandas as pd
from scipy import stats as sst

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

# Structural KFG parsing is shared with the reader (and the V1 crossref
# script). Only the research-facing syllabary + lexical categories and
# the 7 statistical tests live in this script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from khipu_translator.ascher import (  # noqa: E402
    CordParse, parse_knots,
    KFGClient, AscherSum, parse_kh_index, parse_sums_html,
    KhipuData, parse_khipu_xlsx, resolve_cord,
)

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

REPO_ROOT  = Path(__file__).resolve().parents[1]
CACHE_DIR  = REPO_ROOT / "data" / "kfg_cache"
OUTPUT_DIR = REPO_ROOT / "output" / "ascher_scribe"

# ---------------------------------------------------------------------------
# ALBA Syllabary v3 (frozen for this analysis; duplicate of syllabary.py
# production values kept local so the paper's p-values stay reproducible
# even if the main syllabary is later revised)
# ---------------------------------------------------------------------------

SYLLABARY: Dict[int, str] = {
    0: "lla", 2: "ki", 3: "ma", 4: "ka", 5: "ta", 6: "pa",
    7: "y",   8: "na", 9: "q", 10: "si", 11: "ti", 12: "ku",
}
ONSET_SYLLABARY = dict(SYLLABARY)
ONSET_SYLLABARY.update({2: "chi", 7: "wa", 8: "cha"})
FIGURE_EIGHT = "qa"

LEXICAL_CATEGORIES: Dict[str, List[str]] = {
    "KINSHIP":    ["mama", "tata", "papa", "nana", "kaka", "tayka", "pana",
                   "panaka", "chichi", "chacha"],
    "ACTION":     ["taka", "kama", "kamay", "takay", "taki", "chaki", "maki",
                   "paka", "naka", "chaku", "naku", "waka"],
    "NATURE":     ["qaqa", "pata", "waqa", "chaqa", "kaqa", "paqa", "taqa",
                   "qata", "piqa", "sipa", "wasi", "chapa"],
    "GOVERNANCE": ["qapaq", "qama", "wapa", "wapapa", "qaki", "qampa"],
    "TEMPORAL":   ["wata", "kuti", "kuska", "killa", "chay", "chayka"],
    "DEICTIC":    ["kay", "pay", "chay", "kaypi", "chayp"],
    "INTERROG":   ["pi", "piy", "pita", "piqa", "pim"],
    "INTENSIF":   ["kiki"],
}
_WORD_TO_CATEGORY: Dict[str, str] = {}
for cat, words in LEXICAL_CATEGORIES.items():
    for w in words:
        _WORD_TO_CATEGORY.setdefault(w, cat)


def word_category(word: str) -> str:
    if not word:
        return "UNKNOWN"
    return _WORD_TO_CATEGORY.get(word, "UNKNOWN")


def apply_syllabary(cp: CordParse) -> Tuple[str, str]:
    """Apply the frozen research syllabary to a structural :class:`CordParse`.

    Returns ``(reading, category)`` for STRING cords, ``('', 'UNKNOWN')`` otherwise.
    """
    if cp.cord_type != "STRING":
        return "", "UNKNOWN"
    parts: List[str] = []
    for i, t in enumerate(cp.long_turns):
        tbl = ONSET_SYLLABARY if i == 0 else SYLLABARY
        parts.append(tbl.get(t, f"[L{t}?]"))
    parts.extend([FIGURE_EIGHT] * cp.n_eight)
    reading = "".join(parts)
    return reading, word_category(reading)


# ---------------------------------------------------------------------------
# Per-sum record
# ---------------------------------------------------------------------------

@dataclass
class SumObs:
    kh_id: str
    alias: str
    hand: str
    sum_cord_name: str
    sum_group: int
    sum_index: int
    sum_value: float
    sum_color: str
    sum_type: str
    sum_reading: str
    sum_category: str
    sum_n_long: int
    sum_s_value: int
    sum_l_value: int

    n_summands: int
    summand_names: List[str]
    summand_groups: List[int]
    summand_indexes: List[int]
    summand_colors: List[str]
    summand_types: List[str]
    summand_readings: List[str]
    summand_categories: List[str]
    summand_n_longs: List[int]
    summand_s_values: List[int]
    summand_l_values: List[int]


def build_sum_observations(kd: KhipuData, sums: List[AscherSum]) -> List[SumObs]:
    obs: List[SumObs] = []
    for s in sums:
        srow = resolve_cord(kd, s.sum_group, s.sum_pos)
        if srow is None:
            continue
        scp = parse_knots(str(srow.get("Knots") or ""))
        sum_color = str(srow.get("Color") or "")
        # Summands
        names, groups_, indexes, colors = [], [], [], []
        types, readings, cats, n_longs, s_vals, l_vals = [], [], [], [], [], []
        for g, p, _v in s.summands:
            r = resolve_cord(kd, g, p)
            if r is None:
                names.append(f"g{g}p{p}"); groups_.append(g); indexes.append(-1)
                colors.append(""); types.append("MISSING"); readings.append("")
                cats.append("UNKNOWN"); n_longs.append(0)
                s_vals.append(0); l_vals.append(0)
                continue
            cp = parse_knots(str(r.get("Knots") or ""))
            cp_reading, cp_category = apply_syllabary(cp)
            names.append(str(r["_cord_name"]))
            groups_.append(int(r["_group"]))
            indexes.append(int(r["_index"]))
            colors.append(str(r.get("Color") or ""))
            types.append(cp.cord_type)
            readings.append(cp_reading)
            cats.append(cp_category)
            n_longs.append(cp.n_long)
            s_vals.append(cp.s_value_total)
            l_vals.append(cp.l_value_total)

        scp_reading, scp_category = apply_syllabary(scp)
        obs.append(SumObs(
            kh_id=kd.kh_id, alias=kd.alias, hand=s.hand,
            sum_cord_name=str(srow["_cord_name"]),
            sum_group=int(srow["_group"]),
            sum_index=int(srow["_index"]),
            sum_value=s.sum_value,
            sum_color=sum_color,
            sum_type=scp.cord_type,
            sum_reading=scp_reading,
            sum_category=scp_category,
            sum_n_long=scp.n_long,
            sum_s_value=scp.s_value_total,
            sum_l_value=scp.l_value_total,
            n_summands=len(s.summands),
            summand_names=names, summand_groups=groups_, summand_indexes=indexes,
            summand_colors=colors, summand_types=types, summand_readings=readings,
            summand_categories=cats, summand_n_longs=n_longs,
            summand_s_values=s_vals, summand_l_values=l_vals,
        ))
    return obs


# ---------------------------------------------------------------------------
# The 7 tests
# ---------------------------------------------------------------------------

def test_1_s_surplus(obs: List[SumObs]) -> dict:
    """Do STRING sum-cords carry more S-knot padding than STRING summand cords?

    De-duplicated by (kh_id, cord_name): a cord that acts as summand in N
    distinct sum relations is counted once. A cord that is both a sum-cord
    AND a summand (cascade intermediate) is counted once on each side.
    """
    sum_vals: Dict[Tuple[str, str], int] = {}
    summ_vals: Dict[Tuple[str, str], int] = {}
    for o in obs:
        if o.sum_type == "STRING":
            sum_vals.setdefault((o.kh_id, o.sum_cord_name), o.sum_s_value)
        for name, t, sv in zip(o.summand_names, o.summand_types, o.summand_s_values):
            if t == "STRING":
                summ_vals.setdefault((o.kh_id, name), sv)
    sum_arr  = list(sum_vals.values())
    summ_arr = list(summ_vals.values())
    if not sum_arr or not summ_arr:
        return {"p_value": float("nan"), "n_sum": len(sum_arr), "n_summ": len(summ_arr)}
    u, p = sst.mannwhitneyu(sum_arr, summ_arr, alternative="greater")
    return {
        "median_sum": float(np.median(sum_arr)),
        "median_summ": float(np.median(summ_arr)),
        "mean_sum": float(np.mean(sum_arr)),
        "mean_summ": float(np.mean(summ_arr)),
        "n_sum": len(sum_arr), "n_summ": len(summ_arr),
        "U": float(u), "p_value": float(p),
    }


def test_2_topological_separation(obs: List[SumObs]) -> dict:
    """Is the sum-cord in a different cord-group than all its summands?"""
    total = 0
    fully_separated = 0
    any_separated = 0
    for o in obs:
        if not o.summand_groups:
            continue
        total += 1
        diffs = [sg != o.sum_group for sg in o.summand_groups]
        if all(diffs):
            fully_separated += 1
        if any(diffs):
            any_separated += 1
    return {
        "n_total": total,
        "fully_separated": fully_separated,
        "frac_fully": fully_separated / max(total, 1),
        "any_separated": any_separated,
        "frac_any": any_separated / max(total, 1),
    }


def test_3_direction(obs: List[SumObs]) -> dict:
    """Right-handed: sum-cord index < mean(summand index).
       Left-handed : sum-cord index > mean(summand index)."""
    right_deltas, left_deltas = [], []
    right_match, right_total = 0, 0
    left_match,  left_total  = 0, 0
    for o in obs:
        idxs = [i for i in o.summand_indexes if i >= 0]
        if not idxs or o.sum_index < 0:
            continue
        mean_summ = float(np.mean(idxs))
        delta = o.sum_index - mean_summ
        if o.hand == "right":
            right_total += 1
            right_deltas.append(delta)
            if delta < 0:
                right_match += 1
        else:
            left_total += 1
            left_deltas.append(delta)
            if delta > 0:
                left_match += 1
    return {
        "right_total": right_total,
        "right_match": right_match,
        "right_frac": right_match / max(right_total, 1),
        "right_mean_delta": float(np.mean(right_deltas)) if right_deltas else float("nan"),
        "left_total": left_total,
        "left_match": left_match,
        "left_frac": left_match / max(left_total, 1),
        "left_mean_delta": float(np.mean(left_deltas)) if left_deltas else float("nan"),
    }


def test_4_color(obs: List[SumObs], khipu_colors_pool: Dict[str, List[str]],
                 n_perm: int = 5000, seed: int = 20260414) -> dict:
    """Is the sum-cord color systematically different from its summands' colors?

    Null model: for each khipu, shuffle colors among cords involved in sums
    and recompute the mismatch rate.
    """
    rng = np.random.default_rng(seed)

    # Observed
    obs_total = 0
    obs_mismatch = 0
    for o in obs:
        summ_colors = [c for c in o.summand_colors if c]
        if not summ_colors or not o.sum_color:
            continue
        obs_total += 1
        maj = Counter(summ_colors).most_common(1)[0][0]
        if o.sum_color != maj:
            obs_mismatch += 1
    if obs_total == 0:
        return {"p_value": float("nan"), "n_total": 0, "mismatch": 0, "frac": float("nan")}

    # Null: per khipu, shuffle the color pool across sum-involved cord slots
    # Approach: group obs by khipu, build a list of (is_sum, color) per khipu,
    # shuffle colors, recount mismatches.
    by_kh: Dict[str, List[SumObs]] = defaultdict(list)
    for o in obs:
        by_kh[o.kh_id].append(o)

    null_scores = np.empty(n_perm, dtype=np.int64)
    for k in range(n_perm):
        total_mismatch = 0
        for kh, olist in by_kh.items():
            # Collect all colored cord slots for this khipu's sums
            all_slots: List[str] = []
            struct: List[Tuple[int, int]] = []  # (sum_idx, n_summands) slices
            for o in olist:
                summ_colors = [c for c in o.summand_colors if c]
                if not summ_colors or not o.sum_color:
                    continue
                start = len(all_slots)
                all_slots.append(o.sum_color)         # slot 0 = sum
                all_slots.extend(summ_colors)         # slots 1+ = summands
                struct.append((start, len(summ_colors)))
            if not struct:
                continue
            shuffled = np.array(all_slots, dtype=object)
            rng.shuffle(shuffled)
            for start, n_s in struct:
                new_sum_color = shuffled[start]
                new_summ_colors = list(shuffled[start + 1: start + 1 + n_s])
                maj = Counter(new_summ_colors).most_common(1)[0][0]
                if new_sum_color != maj:
                    total_mismatch += 1
        null_scores[k] = total_mismatch

    # Two-sided: is observed far from null?
    p_high = (np.sum(null_scores >= obs_mismatch) + 1) / (n_perm + 1)
    p_low  = (np.sum(null_scores <= obs_mismatch) + 1) / (n_perm + 1)
    return {
        "n_total": obs_total,
        "mismatch": obs_mismatch,
        "frac": obs_mismatch / obs_total,
        "null_mean": float(null_scores.mean()),
        "null_std": float(null_scores.std(ddof=1)),
        "p_value_higher": float(p_high),
        "p_value_lower": float(p_low),
        "n_perm": n_perm,
    }


def test_5_syllabic_complexity(obs: List[SumObs]) -> dict:
    """Do STRING sum-cords have more L-knots (syllables) than STRING summands?

    De-duplicated by (kh_id, cord_name) — see T1 docstring.
    """
    sum_n: Dict[Tuple[str, str], int] = {}
    summ_n: Dict[Tuple[str, str], int] = {}
    for o in obs:
        if o.sum_type == "STRING":
            sum_n.setdefault((o.kh_id, o.sum_cord_name), o.sum_n_long)
        for name, t, n in zip(o.summand_names, o.summand_types, o.summand_n_longs):
            if t == "STRING":
                summ_n.setdefault((o.kh_id, name), n)
    sum_arr  = list(sum_n.values())
    summ_arr = list(summ_n.values())
    if not sum_arr or not summ_arr:
        return {"p_value": float("nan"), "n_sum": len(sum_arr), "n_summ": len(summ_arr)}
    u, p = sst.mannwhitneyu(sum_arr, summ_arr, alternative="greater")
    return {
        "median_sum": float(np.median(sum_arr)),
        "median_summ": float(np.median(summ_arr)),
        "mean_sum": float(np.mean(sum_arr)),
        "mean_summ": float(np.mean(summ_arr)),
        "n_sum": len(sum_arr), "n_summ": len(summ_arr),
        "U": float(u), "p_value": float(p),
    }


def _build_sum_graph(obs: List[SumObs]):
    """Per-khipu DAG: edge from each summand cord -> sum cord."""
    if not HAS_NX:
        return None, None
    graphs: Dict[str, "nx.DiGraph"] = {}
    for o in obs:
        G = graphs.setdefault(o.kh_id, nx.DiGraph())
        sc = (o.kh_id, o.sum_cord_name)
        G.add_node(sc)
        for name in o.summand_names:
            sd = (o.kh_id, name)
            G.add_edge(sd, sc)
    return graphs, None


def test_6_cascade_depth(obs: List[SumObs], summaries: Dict[str, int]) -> dict:
    """Does cascade depth grow with khipu size (Spearman)?

    If a khipu's sum graph contains a cycle (should not happen per KFG spec),
    we DROP that khipu from the correlation (rather than silently reporting
    depth=0, which would pull rho toward zero) and log it.
    """
    if not HAS_NX:
        return {"p_value": float("nan"), "note": "networkx not installed"}
    graphs, _ = _build_sum_graph(obs)
    depths: List[int] = []
    sizes:  List[int] = []
    per_kh: List[Tuple[str, int, int]] = []
    cyclic: List[str] = []
    for kh, G in graphs.items():
        if len(G) == 0:
            continue
        if not nx.is_directed_acyclic_graph(G):
            cyclic.append(kh)
            continue
        depth = nx.dag_longest_path_length(G)
        size = summaries.get(kh, 0)
        depths.append(depth)
        sizes.append(size)
        per_kh.append((kh, depth, size))
    if len(depths) < 3:
        return {"p_value": float("nan"), "n": len(depths), "cyclic": cyclic}
    rho, p = sst.spearmanr(sizes, depths)
    per_kh.sort(key=lambda t: -t[1])
    return {
        "n": len(depths),
        "max_depth": int(max(depths)),
        "mean_depth": float(np.mean(depths)),
        "rho": float(rho), "p_value": float(p),
        "top_depth_khipus": per_kh[:10],
        "cyclic_khipus_dropped": cyclic,
        "n_cyclic_dropped": len(cyclic),
    }


def test_7_criticality(obs: List[SumObs]) -> dict:
    """High-degree summands are more often KINSHIP/GOVERNANCE than low-degree."""
    # Degree = number of distinct sums a cord is a summand of (per khipu).
    degree: Dict[Tuple[str, str], int] = Counter()
    category: Dict[Tuple[str, str], str] = {}
    cord_type: Dict[Tuple[str, str], str] = {}
    for o in obs:
        for name, cat, t in zip(o.summand_names, o.summand_categories, o.summand_types):
            key = (o.kh_id, name)
            degree[key] += 1
            category[key] = cat
            cord_type[key] = t

    high_cat = Counter()
    low_cat  = Counter()
    for key, d in degree.items():
        if cord_type.get(key) != "STRING":
            continue
        if d >= 3:
            high_cat[category[key]] += 1
        elif d == 1:
            low_cat[category[key]] += 1

    def _kg(counter: Counter) -> Tuple[int, int]:
        kg = counter.get("KINSHIP", 0) + counter.get("GOVERNANCE", 0)
        return kg, sum(counter.values())

    hi_kg, hi_tot = _kg(high_cat)
    lo_kg, lo_tot = _kg(low_cat)
    # Fisher exact
    try:
        _, p = sst.fisher_exact([[hi_kg, hi_tot - hi_kg],
                                 [lo_kg, lo_tot - lo_kg]],
                                alternative="greater")
    except Exception:
        p = float("nan")
    return {
        "hi_degree_n": hi_tot, "hi_degree_kg": hi_kg,
        "hi_frac": hi_kg / max(hi_tot, 1),
        "lo_degree_n": lo_tot, "lo_degree_kg": lo_kg,
        "lo_frac": lo_kg / max(lo_tot, 1),
        "p_value": float(p),
        "high_dist": dict(high_cat),
        "low_dist": dict(low_cat),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_csv(obs: List[SumObs], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "kh_id", "alias", "hand",
            "sum_cord", "sum_group", "sum_index", "sum_value", "sum_color",
            "sum_type", "sum_reading", "sum_category",
            "sum_n_long", "sum_s_value", "sum_l_value",
            "n_summands",
            "summand_names", "summand_groups", "summand_colors", "summand_types",
            "summand_readings", "summand_n_longs", "summand_s_values",
        ])
        for o in obs:
            w.writerow([
                o.kh_id, o.alias, o.hand,
                o.sum_cord_name, o.sum_group, o.sum_index, o.sum_value, o.sum_color,
                o.sum_type, o.sum_reading, o.sum_category,
                o.sum_n_long, o.sum_s_value, o.sum_l_value,
                o.n_summands,
                "|".join(o.summand_names),
                "|".join(map(str, o.summand_groups)),
                "|".join(o.summand_colors),
                "|".join(o.summand_types),
                "|".join(o.summand_readings),
                "|".join(map(str, o.summand_n_longs)),
                "|".join(map(str, o.summand_s_values)),
            ])


def write_report(obs: List[SumObs], khipu_summaries: Dict[str, dict],
                 t1: dict, t2: dict, t3: dict, t4: dict, t5: dict,
                 t6: dict, t7: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    L: List[str] = []
    L.append("# Le Geste du Scribe — Tests Mécaniques sur les Sommes d'Ascher")
    L.append("")
    L.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    L.append("")
    L.append("## Corpus")
    n_kh = len(khipu_summaries)
    n_sum = len(obs)
    n_right = sum(1 for o in obs if o.hand == "right")
    n_left  = sum(1 for o in obs if o.hand == "left")
    n_sum_S = sum(1 for o in obs if o.sum_type == "STRING")
    n_summ_S = sum(1 for o in obs for t in o.summand_types if t == "STRING")
    n_summ_total = sum(len(o.summand_types) for o in obs)
    L.append(f"- Khipus analysés : **{n_kh}**")
    L.append(f"- Relations de somme : **{n_sum}**  ({n_right} droites, {n_left} gauches)")
    L.append(f"- Cordes-sommes STRING : {n_sum_S} / {n_sum} ({100*n_sum_S/max(n_sum,1):.1f}%)")
    L.append(f"- Sommands STRING : {n_summ_S} / {n_summ_total} ({100*n_summ_S/max(n_summ_total,1):.1f}%)")
    L.append("")

    # T1
    L.append("## Test 1 — Bourrage S-knot (la signature du scribe)")
    L.append("")
    L.append("Hypothèse : cordes-sommes STRING portent **plus de nœuds simples** que les sommands STRING.")
    if t1.get("n_sum", 0) and t1.get("n_summ", 0):
        L.append(f"- S-surplus **médian** — cordes-sommes : {t1['median_sum']:.1f}")
        L.append(f"- S-surplus **médian** — sommands : {t1['median_summ']:.1f}")
        L.append(f"- S-surplus **moyen**  — cordes-sommes : {t1['mean_sum']:.1f}")
        L.append(f"- S-surplus **moyen**  — sommands : {t1['mean_summ']:.1f}")
        L.append(f"- N (cordes-sommes / sommands) : {t1['n_sum']} / {t1['n_summ']}")
        L.append(f"- Mann-Whitney U (one-sided, greater) : U={t1['U']:.0f}, **p = {t1['p_value']:.4g}**")
    else:
        L.append("- _Pas assez de cordes STRING pour tester._")
    L.append("")

    # T2
    L.append("## Test 2 — Séparation topologique (header vs données)")
    L.append("")
    L.append("Hypothèse : la corde-somme est dans un **groupe (canuto) différent** de ses sommands.")
    L.append(f"- Sommes testées : {t2['n_total']}")
    L.append(f"- **100 % séparées** (sum-cord hors de tous les groupes de ses sommands) : "
             f"{t2['fully_separated']} / {t2['n_total']}  ({100*t2['frac_fully']:.1f}%)")
    L.append(f"- Au moins partiellement séparées : "
             f"{t2['any_separated']} / {t2['n_total']}  ({100*t2['frac_any']:.1f}%)")
    L.append("")

    # T3
    L.append("## Test 3 — Asymétrie directionnelle")
    L.append("")
    L.append("Sommes droites → corde-somme **avant** les sommands (delta < 0).  Sommes gauches → **après** (delta > 0).")
    L.append(f"- Droites : {t3['right_match']} / {t3['right_total']} "
             f"({100*t3['right_frac']:.1f}%) delta_moyen = {t3['right_mean_delta']:.2f}")
    L.append(f"- Gauches : {t3['left_match']} / {t3['left_total']} "
             f"({100*t3['left_frac']:.1f}%) delta_moyen = {t3['left_mean_delta']:.2f}")
    L.append("")

    # T4
    L.append("## Test 4 — Mismatch de couleur (couleur = rôle structurel)")
    L.append("")
    if t4.get("n_total"):
        L.append(f"- Sommes testées : {t4['n_total']}")
        L.append(f"- Mismatch observé : {t4['mismatch']} ({100*t4['frac']:.1f}%)")
        L.append(f"- Null (shuffle intra-khipu) : {t4['null_mean']:.1f} ± {t4['null_std']:.1f}  (n_perm={t4['n_perm']})")
        L.append(f"- **p (observé > null) = {t4['p_value_higher']:.4g}**  "
                 f"| p (observé < null) = {t4['p_value_lower']:.4g}")
    L.append("")

    # T5
    L.append("## Test 5 — Complexité syllabique (nb de L-knots)")
    L.append("")
    if t5.get("n_sum", 0) and t5.get("n_summ", 0):
        L.append(f"- Médiane cordes-sommes : {t5['median_sum']:.1f} syllabes")
        L.append(f"- Médiane sommands : {t5['median_summ']:.1f} syllabes")
        L.append(f"- N : {t5['n_sum']} / {t5['n_summ']}")
        L.append(f"- Mann-Whitney U (greater) : U={t5['U']:.0f}, **p = {t5['p_value']:.4g}**")
    L.append("")

    # T6
    L.append("## Test 6 — Profondeur de cascade (arbre de Merkle)")
    L.append("")
    if "p_value" in t6 and not np.isnan(t6.get("p_value", float("nan"))):
        L.append(f"- Khipus avec sommes : {t6.get('n', 0)}  |  profondeur max observée : {t6.get('max_depth', 0)}")
        L.append(f"- Profondeur moyenne : {t6.get('mean_depth', 0):.2f}")
        L.append(f"- Spearman (taille khipu ↔ profondeur cascade) : ρ = {t6['rho']:.3f}, **p = {t6['p_value']:.4g}**")
        L.append("")
        L.append("Top 10 par profondeur de cascade :")
        L.append("")
        L.append("| KH | depth | n_cords |")
        L.append("|----|------:|--------:|")
        for kh, d, n in t6.get("top_depth_khipus", [])[:10]:
            L.append(f"| {kh} | {d} | {n} |")
    else:
        L.append("- _networkx non installé ou pas assez de données._")
    L.append("")

    # T7
    L.append("## Test 7 — Criticité des sommands (données protégées)")
    L.append("")
    L.append("Les sommands référencés par ≥3 sommes portent-ils plus souvent des termes KINSHIP/GOVERNANCE ?")
    L.append(f"- Haut degré (≥3 sommes) : {t7['hi_degree_kg']}/{t7['hi_degree_n']} "
             f"KIN+GOV ({100*t7['hi_frac']:.1f}%)")
    L.append(f"- Bas degré (=1 somme) : {t7['lo_degree_kg']}/{t7['lo_degree_n']} "
             f"KIN+GOV ({100*t7['lo_frac']:.1f}%)")
    L.append(f"- Fisher exact (hi > lo) : **p = {t7['p_value']:.4g}**")
    if t7.get("high_dist"):
        L.append("")
        L.append(f"- Distribution catégorielle haut degré : {t7['high_dist']}")
        L.append(f"- Distribution catégorielle bas degré : {t7['low_dist']}")
    L.append("")

    # Headline
    L.append("## Synthèse")
    L.append("")
    # Binomial test on T3 (direction) — H0: 50% match, one-sided.
    t3_right_p = float("nan")
    t3_left_p  = float("nan")
    if t3["right_total"] > 0:
        t3_right_p = sst.binomtest(t3["right_match"], t3["right_total"], p=0.5,
                                   alternative="greater").pvalue
    if t3["left_total"] > 0:
        t3_left_p = sst.binomtest(t3["left_match"], t3["left_total"], p=0.5,
                                  alternative="greater").pvalue
    # Binomial on T2 (fully separated) — H0: random if sum-cord could land anywhere.
    # Conservative: use H0=0.5 (not rigorous but gives a lower bound on significance).
    t2_p = float("nan")
    if t2["n_total"] > 0:
        t2_p = sst.binomtest(t2["fully_separated"], t2["n_total"], p=0.5,
                             alternative="greater").pvalue

    sig_rows: List[Tuple[str, str, str]] = []
    def _row(name: str, stat: str, pv: float) -> None:
        if pv is not None and not np.isnan(pv):
            mark = "✓" if pv < 0.05 else "✗"
            sig_rows.append((mark, name, f"p = {pv:.3g}  |  {stat}"))

    _row("T1 S-surplus (scribe padding)",
         f"mean sum={t1.get('mean_sum','—')} vs summ={t1.get('mean_summ','—')}",
         t1.get("p_value", float("nan")))
    _row("T2 topological separation",
         f"{t2['fully_separated']}/{t2['n_total']} fully separated ({100*t2['frac_fully']:.1f}%)",
         t2_p)
    _row("T3 direction (right: header before data)",
         f"right {100*t3['right_frac']:.1f}% | left {100*t3['left_frac']:.1f}%",
         min(t3_right_p, t3_left_p) if not (np.isnan(t3_right_p) or np.isnan(t3_left_p)) else float("nan"))
    _row("T4 color role-marking",
         f"mismatch {t4.get('frac', 0)*100:.1f}% vs null",
         t4.get("p_value_higher", float("nan")))
    _row("T5 syllabic complexity",
         f"sum-cord median {t5.get('median_sum','—')} L vs summ {t5.get('median_summ','—')} L",
         t5.get("p_value", float("nan")))
    _row("T6 cascade depth (Merkle tree)",
         f"max depth {t6.get('max_depth','—')}, ρ={t6.get('rho','—')}",
         t6.get("p_value", float("nan")))
    _row("T7 summand criticality",
         f"hi {t7.get('hi_frac', 0)*100:.1f}% vs lo {t7.get('lo_frac', 0)*100:.1f}% KIN+GOV",
         t7.get("p_value", float("nan")))

    L.append("| ✓/✗ | Test | Effect |")
    L.append("|---|---|---|")
    for mark, name, detail in sig_rows:
        L.append(f"| {mark} | **{name}** | {detail} |")
    L.append("")
    n_sig = sum(1 for m, _, _ in sig_rows if m == "✓")
    L.append(f"**{n_sig} / {len(sig_rows)} tests significatifs (p < 0.05).**")
    L.append("")

    path.write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=9999)
    ap.add_argument("--khipus", nargs="*", default=None)
    ap.add_argument("--n-perm", type=int, default=5000)
    ap.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    ap.add_argument("--quiet", action="store_true")
    ns = ap.parse_args()

    client = KFGClient(cache_dir=ns.cache_dir)

    if ns.khipus:
        kh_list = list(ns.khipus)
    else:
        print("[*] Fetching KFG sums index ...")
        idx_html = client.fetch_index()
        kh_list = [k for k in parse_kh_index(idx_html) if re.fullmatch(r"KH\d{4}", k)]
        kh_list = kh_list[: ns.limit]
    print(f"[*] Processing {len(kh_list)} khipus")

    all_obs: List[SumObs] = []
    khipu_summaries: Dict[str, int] = {}

    for kh in kh_list:
        try:
            xlsx = client.fetch_xlsx(kh)
            html = client.fetch_sums_html(kh)
            kd = parse_khipu_xlsx(xlsx, kh)
            sums = parse_sums_html(html, kh)
            obs = build_sum_observations(kd, sums)
            all_obs.extend(obs)
            khipu_summaries[kh] = int(len(kd.cords))
            if not ns.quiet:
                n_S = sum(1 for o in obs if o.sum_type == "STRING")
                print(f"  {kh}/{kd.alias:<18s} cords={len(kd.cords):>4d} sums={len(obs):>3d} sum_S={n_S:>3d}")
        except Exception as e:
            print(f"  [skip] {kh}: {type(e).__name__}: {e}", file=sys.stderr)

    if not all_obs:
        print("[!] No observations collected — aborting.", file=sys.stderr)
        return 1

    print(f"[*] Running 7 tests on {len(all_obs)} sum relations ...")
    t1 = test_1_s_surplus(all_obs)
    print(f"    T1 S-surplus        : p={t1.get('p_value', float('nan')):.4g}  "
          f"(med_sum={t1.get('median_sum','—')}, med_summ={t1.get('median_summ','—')})")
    t2 = test_2_topological_separation(all_obs)
    print(f"    T2 separation       : fully={t2['frac_fully']*100:.1f}%  any={t2['frac_any']*100:.1f}%")
    t3 = test_3_direction(all_obs)
    print(f"    T3 direction        : right {t3['right_frac']*100:.1f}%  left {t3['left_frac']*100:.1f}%")
    t4 = test_4_color(all_obs, khipu_colors_pool={}, n_perm=ns.n_perm)
    print(f"    T4 color mismatch   : obs={t4.get('mismatch',0)} ({100*t4.get('frac',0):.1f}%) "
          f"null={t4.get('null_mean','—')}  p_high={t4.get('p_value_higher', float('nan')):.4g}")
    t5 = test_5_syllabic_complexity(all_obs)
    print(f"    T5 syllabic         : p={t5.get('p_value', float('nan')):.4g}")
    t6 = test_6_cascade_depth(all_obs, khipu_summaries)
    print(f"    T6 cascade depth    : max={t6.get('max_depth','—')}  p={t6.get('p_value', float('nan')):.4g}")
    t7 = test_7_criticality(all_obs)
    print(f"    T7 criticality      : hi={t7.get('hi_frac',0)*100:.1f}% lo={t7.get('lo_frac',0)*100:.1f}% "
          f"p={t7.get('p_value', float('nan')):.4g}")

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = ns.output_dir / "ascher_scribe_mechanism_data.csv"
    json_path = ns.output_dir / "ascher_scribe_mechanism_stats.json"
    md_path = ns.output_dir / "ascher_scribe_mechanism_report.md"

    write_csv(all_obs, csv_path)
    json_path.write_text(json.dumps({
        "corpus": {"n_khipus": len(khipu_summaries), "n_sums": len(all_obs)},
        "t1_s_surplus": t1, "t2_topology": t2, "t3_direction": t3,
        "t4_color": t4, "t5_syllabic": t5, "t6_cascade": {k: v for k, v in t6.items() if k != "top_depth_khipus"},
        "t7_criticality": t7,
    }, indent=2, default=str), encoding="utf-8")
    write_report(all_obs, khipu_summaries, t1, t2, t3, t4, t5, t6, t7, md_path)

    print(f"[✓] CSV  : {csv_path}")
    print(f"[✓] JSON : {json_path}")
    print(f"[✓] MD   : {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
