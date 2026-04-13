#!/usr/bin/env python3
"""
Cross-validation of the top-3 brute-force candidate mappings on held-out
khipus UR050 and UR055.

Reproduces paper Section 2.5 line 28:
    "Cross-validation on two additional khipus (UR050 and UR055, not
     used in derivation) confirms the ranking: the L3=ma, L4=ka mapping
     yields 137 combined hits versus 128 and 121 for the second and third
     alternatives."

Method
------
1. Take the top 3 four-letter mappings produced by brute_force_derivation.py
   on UR039 (D1 Quechua):
     #1  L3=ma, L4=ka, L5=ta, L6=pa  (19/19 types, 64 hits on UR039)
     #2  L3=ma, L4=ka, L5=ta, L6=wa  (18/19 types, 63 hits)
     #3  L3=na, L4=ya, L5=ku, L6=si  (18/19 types, 62 hits)
2. Extract STRING cord sequences from UR050 and UR055 via the same knot
   decoding pipeline as the derivation script.
3. For each mapping, translate every STRING cord on UR050+UR055.
   Cords containing L-values outside {3,4,5,6} yield no translation and
   are excluded. Remaining cords are scored against the same 1,750-entry
   Quechua dictionary used in the derivation.
4. Report combined hits per mapping. The primary mapping is expected to
   lead by a meaningful margin.

This is a purely confirmatory test: UR050 and UR055 played no role in
selecting any of the three mappings, so the ranking on them is
independent evidence.

Usage
-----
    python reproducibility/cross_validation.py

Requirements
------------
    pip install -e .   (khipu_translator.database for OKR access)
"""

from __future__ import annotations

import os
import re
import sys
from typing import Iterable

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khipu_translator.database import KhipuDB


# -----------------------------------------------------------------------------
# Quechua dictionary — MUST match brute_force_derivation.py exactly.
# -----------------------------------------------------------------------------

QUECHUA_ROOTS_2SYL: set[str] = {
    'mama','papa','tata','kaka','wawa','paya','yaya','nana','tura','pana',
    'yaku','mayu','rumi','sara','kuka','muyu','puyu','turu','nina','pata','waru',
    'maki','simi','siki','wira','puma','kuru','runa','mita','suyu','tawa','kipu',
    'waka','kuya','wasi','tampu','yana','puka','yura','kusi',
    'kama','taki','taka','kata','paka','tiya','yapa','riku','rima','tuku','tupu',
    'miku','puri','saya','raki','paki','kuti','tupa','muna','wata','kaya','maka',
    'tapa','qara','qura','siku','muru','suti','suwa','yuri','yupa','ruqa','sura',
    'waya','napa','laya','tumi','tika','sipa',
    'mana','kuna','masi','sami','mapa','kiru','puku','rupa','katu','tama','raya',
    'riti','wiku','nuna','kuku','pupu','pipi','sasa','nini',
}

QUECHUA_CV_SUFFIXES: list[str] = [
    'pa','ta','pi','qa','ri','na','ku','mu','ya','si',
    'chi','cha','mi','pu','ra','ka','ma',
]

QUECHUA_3SYL_ROOTS: set[str] = {
    'kuraka','yupana','kamana','tikana','papaya','wanaku','puriri','kutiri',
    'rimana','takiri','tukuri','tapara','kamari','wakana','tamari','rapaki',
    'tupana','pakana','munana','tiyapa',
}


def build_quechua_dictionary() -> set[str]:
    extended = set(QUECHUA_ROOTS_2SYL)
    for root in QUECHUA_ROOTS_2SYL:
        if len(root) == 4:
            for suf in QUECHUA_CV_SUFFIXES:
                extended.add(root + suf)
    extended |= QUECHUA_3SYL_ROOTS
    return extended


# -----------------------------------------------------------------------------
# Top-3 mappings from D1 Quechua brute-force on UR039.
# Keys are the 4 active letter codes (e.g. 'L5s'), values are CV syllables.
# The letter suffix 's' encodes DIRECTION=S ('z' = Z); both share the same
# turn-count interpretation. We match on turn count only, ignoring the
# direction suffix, to stay consistent with the derivation script.
# -----------------------------------------------------------------------------

CANDIDATE_MAPPINGS: list[tuple[str, dict[int, str]]] = [
    ("#1  L3=ma, L4=ka, L5=ta, L6=pa  (primary)",
     {3: 'ma', 4: 'ka', 5: 'ta', 6: 'pa'}),
    ("#2  L3=ma, L4=ka, L5=ta, L6=wa",
     {3: 'ma', 4: 'ka', 5: 'ta', 6: 'wa'}),
    ("#3  L3=na, L4=ya, L5=ku, L6=si",
     {3: 'na', 4: 'ya', 5: 'ku', 6: 'si'}),
]


# -----------------------------------------------------------------------------
# STRING-cord extraction — identical to brute_force_derivation.py
# -----------------------------------------------------------------------------

def extract_string_words(khipu_id_name: str, cord_all: pd.DataFrame,
                         knot_all: pd.DataFrame, khipu_df: pd.DataFrame
                         ) -> list[list[int]]:
    """Return a list of STRING words, each as a list of integer turn counts."""
    row = khipu_df[khipu_df['INVESTIGATOR_NUM'] == khipu_id_name]
    if row.empty:
        sys.exit(f"ERROR: khipu {khipu_id_name} not found in OKR.")
    kid = int(row.iloc[0]['KHIPU_ID'])

    cords = cord_all[cord_all['KHIPU_ID'] == kid].sort_values('CORD_ORDINAL')
    knots = knot_all[knot_all['CORD_ID'].isin(cords['CORD_ID'])]

    words: list[list[int]] = []
    for _, cord in cords.iterrows():
        ck = knots[knots['CORD_ID'] == cord['CORD_ID']]
        ck = ck.sort_values(['CLUSTER_ORDINAL', 'KNOT_ORDINAL'])
        l_knots = ck[ck['TYPE_CODE'] == 'L']
        if len(l_knots) < 2:
            continue
        turns: list[int] = []
        for _, k in l_knots.iterrows():
            t = int(k['NUM_TURNS']) if not pd.isna(k['NUM_TURNS']) and k['NUM_TURNS'] > 0 else 0
            turns.append(t)
        words.append(turns)
    return words


def score_words(words: Iterable[list[int]], mapping: dict[int, str],
                dic: set[str]) -> tuple[int, int, int]:
    """Translate each word under the mapping; count hits / translatable / total.

    - 'total':        number of STRING words in input
    - 'translatable': number that resolve fully under the 4-letter mapping
                      (i.e. every turn count is in the mapping's keyset)
    - 'hits':         translatable words whose translation is in `dic`
    """
    total = translatable = hits = 0
    for w in words:
        total += 1
        if all(t in mapping for t in w):
            translatable += 1
            translation = ''.join(mapping[t] for t in w)
            if translation in dic:
                hits += 1
    return hits, translatable, total


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("ALBA Cross-Validation — UR050 + UR055 (held out from derivation)")
    print("=" * 70)

    qu_dict = build_quechua_dictionary()
    print(f"Quechua dictionary: {len(qu_dict):,} entries (same as derivation)")

    db = KhipuDB()
    cord_all = pd.read_sql('SELECT * FROM cord', db.connection)
    knot_all = pd.read_sql('SELECT * FROM knot', db.connection)
    khipu_df = pd.read_sql('SELECT KHIPU_ID, INVESTIGATOR_NUM FROM khipu_main',
                            db.connection)
    db.close()

    ur050 = extract_string_words('UR050', cord_all, knot_all, khipu_df)
    ur055 = extract_string_words('UR055', cord_all, knot_all, khipu_df)
    print(f"UR050 STRING cords: {len(ur050):,}")
    print(f"UR055 STRING cords: {len(ur055):,}")
    print(f"Combined:           {len(ur050) + len(ur055):,}")

    print(f"\n{'Mapping':<46} {'UR050':>10} {'UR055':>10} {'Combined':>10}")
    print("-" * 78)
    combined_hits: list[int] = []
    for label, mapping in CANDIDATE_MAPPINGS:
        h50, _, _ = score_words(ur050, mapping, qu_dict)
        h55, _, _ = score_words(ur055, mapping, qu_dict)
        combined = h50 + h55
        combined_hits.append(combined)
        print(f"{label:<46} {h50:>10} {h55:>10} {combined:>10}")

    print("\n" + "=" * 70)
    print("RESULT — combined hits across UR050 + UR055")
    print("=" * 70)
    for (label, _), h in zip(CANDIDATE_MAPPINGS, combined_hits):
        print(f"  {h:>5}  {label}")

    ranking = sorted(range(3), key=lambda i: -combined_hits[i])
    if ranking[0] == 0:
        print("\nPrimary mapping (L3=ma, L4=ka, L5=ta, L6=pa) leads on held-out khipus.")
    else:
        print(f"\nNote: primary mapping is not the leader on held-out set "
              f"(rank {ranking.index(0) + 1}/3).")


if __name__ == '__main__':
    main()
