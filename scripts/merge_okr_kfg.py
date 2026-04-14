#!/usr/bin/env python3
"""
merge_okr_kfg.py
================

Build the merged OKR × KFG corpus — the unified source of truth for the
KhipuReader v3.

For every KH_ID from KH0001 to KH0702 we:

  1. Load the KFG xlsx if cached (structure + full knot data).
  2. Resolve the OKR alias (UR039, AS030, ...) from the xlsx ``Aliases`` field.
  3. Translate the OKR khipu if the alias exists in the OKR SQLite DB.
  4. Align level-1 cords by pendant number (``p{N}`` ↔ ``global_ordinal``).
  5. Merge per-cord data with a quality tag:
        AGREED          both sources identical
        KFG_RESOLVED    OKR had L? / missing, KFG supplies the value
        KFG_CORRECTED   values differ, we log both, KFG wins by default
        OKR_ONLY        no KFG twin
        KFG_ONLY        no OKR twin
        DIVERGENT       values differ by more than the tolerance
        ASCHER_VALIDATED resolved via a pendant-pendant sum constraint
  6. Emit ``data/merged/KH{NNNN}.json`` per khipu + ``merged_corpus.sqlite`` +
     ``merge_report.md`` + ``divergences.csv``.

Originals (OKR and KFG source values) are always preserved inside each
cord record — the merger never destroys information.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from khipu_translator.ascher import (
    KFGClient, parse_khipu_xlsx, parse_sums_html, parse_knots,
    DEFAULT_CACHE_DIR,
)
from khipu_translator.database import KhipuDB
from khipu_translator.translator import translate

DATA_DIR   = REPO_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "merged"

KH_RANGE = (1, 702)
LOCKE_TOLERANCE = 1   # values differing by ≤ this are considered "AGREED"


# ---------------------------------------------------------------------------
# OKR helpers
# ---------------------------------------------------------------------------

def okr_cord_to_dict(cord) -> dict:
    """Extract the OKR-side fields we care about for a given CordTranslation."""
    return {
        "cord_id": int(cord.cord_id),
        "level": int(cord.level),
        "global_ordinal": int(cord.global_ordinal),
        "color": str(cord.color or ""),
        "knot_sequence": str(cord.knot_sequence or ""),
        "locke_value": cord.locke_value,     # may be None for STRING
        "has_l_unknown": "L?" in (cord.knot_sequence or ""),
        "cord_type": str(cord.cord_type),
        "parent_cord_id": cord.parent_cord_id,
    }


def locke_from_knot_seq(seq: str) -> Optional[int]:
    """Compute Locke value from a knot_sequence string ('L4 S30 E' etc.).

    Returns None if the sequence contains L? (any unreadable turn).
    """
    if "L?" in (seq or ""):
        return None
    total = 0
    for tok in (seq or "").split():
        t = tok.strip()
        if t == "E":
            total += 1
        elif t.startswith("L") and t[1:].isdigit():
            total += int(t[1:])
        elif t.startswith("S") and t[1:].isdigit():
            total += int(t[1:])
    return total


# ---------------------------------------------------------------------------
# KFG helpers
# ---------------------------------------------------------------------------

def kfg_cord_row_to_dict(row) -> Optional[dict]:
    """Extract KFG fields from a Cords-sheet row.

    Returns ``None`` when the KFG row contains no knot data
    (empty ``Knots`` string) — that is a structural placeholder in KFG's
    own sheet, not genuine source data. Treating it as "KFG knows about
    this cord but has 0 value" would otherwise create thousands of spurious
    DIVERGENT labels against the OKR's real knot data.
    """
    knots_raw = str(row.get("Knots") or "").strip()
    if not knots_raw:
        return None
    cp = parse_knots(knots_raw)
    return {
        "cord_name": str(row.get("Cord_Name") or ""),
        "color": str(row.get("Color") or ""),
        "knots_raw": knots_raw,
        "value": row.get("Value"),       # the pre-computed Locke total from KFG
        "long_turns": list(cp.long_turns),
        "n_eight": int(cp.n_eight),
        "n_simple": int(cp.n_simple),
        "s_value_total": int(cp.s_value_total),
        "cord_type": str(cp.cord_type),
    }


# ---------------------------------------------------------------------------
# Per-khipu merge
# ---------------------------------------------------------------------------

def merge_cord(okr: Optional[dict], kfg: Optional[dict]) -> dict:
    """Merge one cord from OKR + KFG. Returns a dict ready for JSON export."""
    out: dict = {}
    if okr is not None:
        out["okr"] = okr
    if kfg is not None:
        out["kfg"] = kfg

    # --- Colour
    if okr and kfg:
        out["color"] = {
            "okr": okr["color"], "kfg": kfg["color"],
            "agreed": okr["color"] == kfg["color"],
        }
    elif okr:
        out["color"] = {"okr": okr["color"], "agreed": None}
    elif kfg:
        out["color"] = {"kfg": kfg["color"], "agreed": None}

    # --- Locke value
    okr_val = okr["locke_value"] if okr else None
    # Fallback: compute from knot_sequence if OKR didn't provide a value.
    if okr and okr_val is None and not okr.get("has_l_unknown"):
        okr_val = locke_from_knot_seq(okr.get("knot_sequence", ""))
    kfg_val = None
    if kfg:
        try:
            kfg_val = float(kfg.get("value")) if kfg.get("value") is not None else None
        except (TypeError, ValueError):
            kfg_val = None

    merged_val = None
    merge_source = None
    agreed = False
    if okr_val is not None and kfg_val is not None:
        if abs(float(okr_val) - kfg_val) <= LOCKE_TOLERANCE:
            merged_val = kfg_val     # KFG tends to be more precise on units
            merge_source = "agreed"
            agreed = True
        else:
            merged_val = kfg_val
            merge_source = "kfg"
    elif kfg_val is not None:
        merged_val = kfg_val
        merge_source = "kfg"
    elif okr_val is not None:
        merged_val = okr_val
        merge_source = "okr"

    out["locke_value"] = {
        "okr": okr_val, "kfg": kfg_val,
        "merged": merged_val, "merge_source": merge_source,
        "agreed": agreed,
    }

    # --- Quality label
    quality = _compute_quality(okr, kfg, out["locke_value"])
    out["quality"] = quality

    # Carry a few convenience fields at top level
    if kfg:
        out["long_knot_turns"] = kfg["long_turns"]
        out["figure_eight_count"] = kfg["n_eight"]
        out["simple_knot_total"] = kfg["s_value_total"]
        out["classification"] = kfg["cord_type"]
    elif okr:
        out["classification"] = okr["cord_type"]

    return out


def _compute_quality(okr, kfg, locke_block) -> str:
    if kfg is None:
        return "OKR_ONLY"
    if okr is None:
        return "KFG_ONLY"
    okr_has_lq = bool(okr.get("has_l_unknown"))
    l_block = locke_block or {}
    if okr_has_lq and l_block.get("kfg") is not None:
        return "KFG_RESOLVED"
    if l_block.get("agreed"):
        return "AGREED"
    if l_block.get("okr") is None and l_block.get("kfg") is not None:
        return "KFG_RESOLVED"
    if l_block.get("okr") is not None and l_block.get("kfg") is not None:
        diff = abs(float(l_block["okr"]) - float(l_block["kfg"]))
        if diff <= LOCKE_TOLERANCE:
            return "AGREED"
        return "DIVERGENT"
    return "AGREED"


def _ascher_validate(merged_cords: List[dict],
                     kfg_data, kfg_sums: list) -> None:
    """Resolve DIVERGENT cords using KFG sum constraints (in-place).

    For each (g, p) pair referenced in a sum we know the KFG-declared value.
    If a merged cord at the corresponding pendant is DIVERGENT and either
    OKR or KFG matches the KFG-declared summand value, promote that side
    and tag the cord ``ASCHER_VALIDATED``.
    """
    # Build KFG-declared value lookup per pendant name, from the sum HTML
    # (which always carries values even when the xlsx row is ambiguous).
    declared: Dict[str, float] = {}
    for s in kfg_sums:
        # Sum-cord
        key = _pendant_name(kfg_data, s.sum_group, s.sum_pos)
        if key:
            declared.setdefault(key, float(s.sum_value))
        for g, p, v in s.summands:
            key = _pendant_name(kfg_data, g, p)
            if key:
                declared.setdefault(key, float(v))
    if not declared:
        return

    for c in merged_cords:
        if c.get("quality") != "DIVERGENT":
            continue
        kfg_id = c.get("kfg_id")
        if kfg_id not in declared:
            continue
        lv = c.get("locke_value", {}) or {}
        okr_v = lv.get("okr"); kfg_v = lv.get("kfg")
        target = declared[kfg_id]
        okr_ok = okr_v is not None and abs(float(okr_v) - target) < 1e-9
        kfg_ok = kfg_v is not None and abs(float(kfg_v) - target) < 1e-9
        if kfg_ok and not okr_ok:
            lv["merged"] = kfg_v
            lv["merge_source"] = "kfg (ascher)"
            c["quality"] = "ASCHER_VALIDATED"
        elif okr_ok and not kfg_ok:
            lv["merged"] = okr_v
            lv["merge_source"] = "okr (ascher)"
            c["quality"] = "ASCHER_VALIDATED"


def _pendant_name(kfg_data, g: int, p: int) -> Optional[str]:
    """(group, within-group-position) -> 'p{N}' using KFG group map."""
    rng = kfg_data.groups.get(g) if kfg_data else None
    if not rng:
        return None
    start, end = rng
    pn = start + p - 1
    if pn > end:
        return None
    return f"p{pn}"


def merge_khipu(kh_id: str, client: KFGClient,
                okr_db: KhipuDB,
                okr_index: Dict[str, int],
                ) -> Optional[dict]:
    """Produce the merged record for one KH_ID.

    Returns ``None`` if both OKR and KFG are absent (true corpus gap).
    """
    # --- KFG xlsx
    kfg_data = None
    kfg_sums = []
    xlsx_path = client.cache_dir / f"{kh_id}.xlsx"
    if xlsx_path.exists() and xlsx_path.stat().st_size > 0:
        try:
            kfg_data = parse_khipu_xlsx(xlsx_path, kh_id)
        except Exception as e:
            kfg_data = None
            print(f"  [warn] {kh_id} xlsx parse failed: {e}", file=sys.stderr)
    # Sum pages
    sums_path = client.cache_dir / f"{kh_id}_sums.html"
    if kfg_data is not None and sums_path.exists() and sums_path.stat().st_size > 0:
        try:
            kfg_sums = parse_sums_html(sums_path.read_text(encoding="utf-8",
                                                             errors="replace"),
                                        kh_id)
        except Exception:
            kfg_sums = []

    # --- OKR
    okr_result = None
    aliases: List[str] = []
    if kfg_data and kfg_data.alias:
        for alias in kfg_data.alias.replace("/", ",").split(","):
            alias = alias.strip()
            if not alias:
                continue
            aliases.append(alias)
            if okr_result is None and alias in okr_index:
                try:
                    okr_result = translate(alias, db=okr_db)
                except Exception as e:
                    print(f"  [warn] {kh_id}/{alias} OKR translate failed: {e}",
                          file=sys.stderr)

    # --- Nothing on either side
    if kfg_data is None and okr_result is None:
        return None
    # Skip khipus whose xlsx has no cord data (structural stubs in KFG).
    if kfg_data is not None and (kfg_data.cords.empty or
                                  "Knots" not in kfg_data.cords.columns or
                                  kfg_data.cords["Knots"].fillna("").str.strip().eq("").all()):
        if okr_result is None:
            return None

    # --- Build alignment (level-1 cords only; subsidiaries are attached verbatim)
    okr_l1_by_ord: Dict[int, dict] = {}
    okr_sub: List[dict] = []
    if okr_result is not None:
        for c in okr_result.cords:
            d = okr_cord_to_dict(c)
            if c.level == 1:
                okr_l1_by_ord.setdefault(c.global_ordinal, d)
            else:
                okr_sub.append(d)

    kfg_l1_by_pn: Dict[int, dict] = {}
    if kfg_data is not None:
        for _, row in kfg_data.cords.iterrows():
            name = row.get("Cord_Name")
            if not isinstance(name, str):
                continue
            if name.startswith("p") and name[1:].isdigit():
                d = kfg_cord_row_to_dict(row)
                if d is not None:
                    kfg_l1_by_pn[int(name[1:])] = d

    all_pns = sorted(set(okr_l1_by_ord) | set(kfg_l1_by_pn))
    merged_cords = [
        {
            "cord_num": pn,
            "kfg_id": f"p{pn}",
            **merge_cord(okr_l1_by_ord.get(pn), kfg_l1_by_pn.get(pn)),
        }
        for pn in all_pns
    ]

    # --- Subsidiaries (OKR-only for now; KFG naming varies and is rarely used)
    for d in okr_sub:
        merged_cords.append({
            "cord_num": f"L{d['level']}_{d['cord_id']}",
            "kfg_id": None,
            "okr": d,
            "quality": "OKR_ONLY",
            "classification": d["cord_type"],
        })

    # --- Ascher sums
    sums_block = []
    for s in kfg_sums:
        sums_block.append({
            "hand": s.hand,
            "sum_cord": f"g{s.sum_group}p{s.sum_pos}",
            "sum_value": s.sum_value,
            "summands": [{"g": g, "p": p, "value": v} for g, p, v in s.summands],
        })

    # --- Ascher cross-validation of DIVERGENT cords
    # Strategy: for each DIVERGENT cord that is a summand of a sum, check
    # whether picking OKR or KFG makes the sum close. If one side makes the
    # sum close (and the other doesn't), promote that side and flag the cord
    # as ASCHER_VALIDATED. Requires KFG cord-name mapping.
    if kfg_data is not None and kfg_sums:
        _ascher_validate(merged_cords, kfg_data, kfg_sums)

    # --- Agreement metric
    comparable = [c for c in merged_cords
                  if c.get("quality") in {"AGREED", "KFG_RESOLVED",
                                            "KFG_CORRECTED", "DIVERGENT",
                                            "ASCHER_VALIDATED"}]
    agreed = sum(1 for c in comparable if c["quality"] in {"AGREED",
                                                             "ASCHER_VALIDATED"})
    agreement_ratio = agreed / len(comparable) if comparable else None

    return {
        "kh_id": kh_id,
        "aliases": aliases,
        "sources": {
            "okr": okr_result is not None,
            "kfg": kfg_data is not None,
            "okr_kfg_agreement": agreement_ratio,
        },
        "khipu_meta": {
            "okr_provenance": okr_result.khipu.provenance if okr_result else None,
            "okr_museum":     okr_result.khipu.museum_name if okr_result else None,
            "kfg_alias_raw": kfg_data.alias if kfg_data else None,
        },
        "groups": [
            {"group_num": g, "cord_range": list(rng)}
            for g, rng in (kfg_data.groups.items() if kfg_data else [])
        ],
        "cords": merged_cords,
        "ascher_sums": sums_block,
    }


# ---------------------------------------------------------------------------
# Export: SQLite + divergences.csv
# ---------------------------------------------------------------------------

def write_sqlite(records: List[dict], path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE khipus (
            kh_id TEXT PRIMARY KEY,
            aliases TEXT,
            has_okr INTEGER,
            has_kfg INTEGER,
            agreement_ratio REAL,
            n_cords INTEGER,
            n_sums INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE cords (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            kh_id TEXT,
            cord_num TEXT,
            kfg_id TEXT,
            quality TEXT,
            classification TEXT,
            merged_locke REAL,
            okr_locke REAL,
            kfg_locke REAL,
            color_okr TEXT,
            color_kfg TEXT,
            knot_seq_okr TEXT,
            knots_raw_kfg TEXT
        )
    """)
    cur.execute("CREATE INDEX idx_cords_kh ON cords(kh_id)")
    cur.execute("CREATE INDEX idx_cords_num ON cords(kh_id, cord_num)")
    for r in records:
        cur.execute(
            "INSERT INTO khipus VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r["kh_id"], ",".join(r.get("aliases", [])),
             1 if r["sources"]["okr"] else 0,
             1 if r["sources"]["kfg"] else 0,
             r["sources"]["okr_kfg_agreement"],
             len(r["cords"]), len(r["ascher_sums"])),
        )
        for c in r["cords"]:
            lv = c.get("locke_value", {}) or {}
            col = c.get("color", {}) or {}
            cur.execute(
                "INSERT INTO cords "
                "(kh_id, cord_num, kfg_id, quality, classification, "
                " merged_locke, okr_locke, kfg_locke, color_okr, color_kfg, "
                " knot_seq_okr, knots_raw_kfg) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r["kh_id"], str(c.get("cord_num")), c.get("kfg_id"),
                 c.get("quality"), c.get("classification"),
                 lv.get("merged"), lv.get("okr"), lv.get("kfg"),
                 col.get("okr") if isinstance(col, dict) else None,
                 col.get("kfg") if isinstance(col, dict) else None,
                 (c.get("okr") or {}).get("knot_sequence"),
                 (c.get("kfg") or {}).get("knots_raw")),
            )
    conn.commit()
    conn.close()


def write_divergences(records: List[dict], path: Path) -> None:
    rows = []
    for r in records:
        for c in r["cords"]:
            if c.get("quality") == "DIVERGENT":
                lv = c.get("locke_value", {}) or {}
                rows.append([
                    r["kh_id"], ",".join(r.get("aliases", [])),
                    c.get("cord_num"), c.get("kfg_id"),
                    lv.get("okr"), lv.get("kfg"),
                    (c.get("okr") or {}).get("knot_sequence"),
                    (c.get("kfg") or {}).get("knots_raw"),
                ])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kh_id", "aliases", "cord_num", "kfg_id",
                    "locke_okr", "locke_kfg", "knots_okr", "knots_kfg"])
        w.writerows(rows)


def write_report(records: List[dict], path: Path, elapsed_s: float) -> None:
    n = len(records)
    with_okr = sum(1 for r in records if r["sources"]["okr"])
    with_kfg = sum(1 for r in records if r["sources"]["kfg"])
    twinned = sum(1 for r in records if r["sources"]["okr"] and r["sources"]["kfg"])

    quality_counter: Counter = Counter()
    total_cords = 0
    for r in records:
        for c in r["cords"]:
            q = c.get("quality") or "UNKNOWN"
            quality_counter[q] += 1
            total_cords += 1

    L: List[str] = []
    L.append("# OKR × KFG merge report")
    L.append("")
    L.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')} — elapsed {elapsed_s:.1f}s_")
    L.append("")
    L.append("## Corpus")
    L.append("")
    L.append(f"- KH IDs emitted:     **{n}**")
    L.append(f"- With OKR data:      {with_okr}")
    L.append(f"- With KFG data:      {with_kfg}")
    L.append(f"- Twinned (both):     **{twinned}**")
    L.append(f"- OKR-only:           {with_okr - twinned}")
    L.append(f"- KFG-only:           {with_kfg - twinned}")
    L.append("")
    L.append("## Cord quality distribution")
    L.append("")
    L.append(f"- Total cord rows:    {total_cords}")
    L.append("")
    L.append("| Quality | count | % |")
    L.append("|---------|------:|--:|")
    for q, cnt in quality_counter.most_common():
        L.append(f"| {q} | {cnt} | {100 * cnt / max(total_cords, 1):.1f}% |")
    L.append("")

    # Top divergent khipus
    div_by_kh = sorted(
        [(r["kh_id"], sum(1 for c in r["cords"] if c.get("quality") == "DIVERGENT"))
         for r in records],
        key=lambda t: -t[1],
    )
    top_div = [t for t in div_by_kh if t[1] > 0][:15]
    if top_div:
        L.append("## Khipus with most divergent cords")
        L.append("")
        L.append("| kh_id | n_divergent |")
        L.append("|-------|------------:|")
        for kh, nd in top_div:
            L.append(f"| {kh} | {nd} |")
        L.append("")

    # Credits
    L.append("## Credits")
    L.append("")
    L.append("- **OKR** (Open Khipu Repository): Brezine, Clindaniel, Ghezzi, Hyland, Medrano, Splitstoser, FitzPatrick — https://github.com/khipulab/open-khipu-repository")
    L.append("- **KFG** (Khipu Field Guide): Ashok Khosla, Manuel Medrano — https://www.khipufieldguide.com/")
    L.append("- **Primary sources**: Ascher & Ascher (1980 databook); Gary Urton; Kylie Quave; Hugo Pereyra")

    path.write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    ap.add_argument("--start", type=int, default=KH_RANGE[0])
    ap.add_argument("--stop", type=int, default=KH_RANGE[1])
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-json", action="store_true",
                    help="Skip per-khipu JSON output (keep only sqlite + reports).")
    ns = ap.parse_args()

    client = KFGClient(cache_dir=ns.cache_dir)
    okr_db = KhipuDB()
    okr_list = okr_db.list_khipus()
    okr_index = {str(row["INVESTIGATOR_NUM"]).strip(): i
                 for i, row in okr_list.iterrows()
                 if isinstance(row.get("INVESTIGATOR_NUM"), str)}

    print(f"[*] OKR khipus indexed: {len(okr_index)}")

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    records: List[dict] = []
    t0 = time.time()

    for n in range(ns.start, ns.stop + 1):
        kh = f"KH{n:04d}"
        try:
            rec = merge_khipu(kh, client, okr_db, okr_index)
        except Exception as e:
            print(f"  [skip] {kh}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        if rec is None:
            continue
        records.append(rec)
        if not ns.no_json:
            (ns.output_dir / f"{kh}.json").write_text(
                json.dumps(rec, indent=2, default=str), encoding="utf-8")
        if not ns.quiet and n % 50 == 0:
            agrees = sum(1 for c in rec["cords"] if c.get("quality") == "AGREED")
            print(f"  {kh}  aliases={rec['aliases']}  cords={len(rec['cords'])}  "
                  f"agreed={agrees}")

    # --- Fallback pass: OKR khipus with no KFG twin (OKR-only).
    # These would otherwise be dropped since we iterate the KH_ID range
    # starting from KFG availability. We synthesize a merged record
    # using only OKR data so the merged corpus is a true superset.
    seen_aliases: "set[str]" = set()
    for r in records:
        for a in r.get("aliases", []):
            seen_aliases.add(a)
    okr_only_count = 0
    for inv_num in okr_index:
        if inv_num in seen_aliases:
            continue
        try:
            res = translate(inv_num, db=okr_db)
        except Exception:
            continue
        # Build a minimal "OKR-only" record
        cords_out = []
        for c in res.cords:
            d = okr_cord_to_dict(c)
            cords_out.append({
                "cord_num": d["global_ordinal"] if d["level"] == 1 else
                            f"L{d['level']}_{d['cord_id']}",
                "kfg_id": None,
                "okr": d,
                "classification": d["cord_type"],
                "quality": "OKR_ONLY",
                "locke_value": {"okr": d["locke_value"], "kfg": None,
                                 "merged": d["locke_value"], "merge_source": "okr",
                                 "agreed": False},
                "color": {"okr": d["color"], "agreed": None},
            })
        safe_inv = inv_num.replace("/", "-").replace(" ", "_")
        rec = {
            "kh_id": f"OKR_{safe_inv}",   # synthetic KH id
            "aliases": [inv_num],
            "sources": {"okr": True, "kfg": False, "okr_kfg_agreement": None},
            "khipu_meta": {
                "okr_provenance": res.khipu.provenance,
                "okr_museum":     res.khipu.museum_name,
                "kfg_alias_raw":  None,
            },
            "groups": [],
            "cords": cords_out,
            "ascher_sums": [],
        }
        records.append(rec)
        okr_only_count += 1
        if not ns.no_json:
            (ns.output_dir / f"OKR_{safe_inv}.json").write_text(
                json.dumps(rec, indent=2, default=str), encoding="utf-8")
    if okr_only_count:
        print(f"[*] Added {okr_only_count} OKR-only khipus (no KFG twin)")

    elapsed = time.time() - t0
    print(f"[*] Merged {len(records)} khipus in {elapsed:.1f}s")

    okr_db.close()

    sqlite_path = ns.output_dir / "merged_corpus.sqlite"
    md_path     = ns.output_dir / "merge_report.md"
    csv_path    = ns.output_dir / "divergences.csv"
    write_sqlite(records, sqlite_path)
    write_divergences(records, csv_path)
    write_report(records, md_path, elapsed)
    print(f"[✓] {sqlite_path}")
    print(f"[✓] {csv_path}")
    print(f"[✓] {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
