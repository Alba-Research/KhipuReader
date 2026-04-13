#!/usr/bin/env python3
"""
Symbol-extension analyses cited in paper Section 2.6.

Two experiments:

1. L9 reassignment (q -> pi)
   Paper line 32:
     "L9 was changed from 'q' to 'pi' after systematic testing ...
     81 dictionary matches gained, 3 lost."
   Test: score all corpus STRING cords containing L9 under two baselines
   identical except for the L9 syllable. Count net cord-level hits.

2. Positional polyphony (L2, L7, L8)
   Paper line 35:
     "L2 reads 'chi' in onset and 'ki' in coda (+75 cords gained, 0 lost);
      L7 reads 'wa' in onset and 'y' in coda (+94 gained, 0 lost);
      L8 reads 'cha' in onset and 'na' in coda (+60 gained, 0 lost)."
   Test: for each of L2/L7/L8, score all corpus STRING cords containing
   the letter under two regimes:
     - uniform  = single CV reading (coda form) in every position
     - polyphonic = V3 onset form if first position, V2 coda form if last
   Count gained cords (polyphonic matches, uniform doesn't) and lost
   cords (the converse).

Dictionary: the Kaikki-derived lexicon (2,074 entries) produced by
build_kaikki_dictionary.py — the same reference dictionary used in the
paper's lexical-coverage and replication claims.

Usage
-----
    python reproducibility/extension_analysis.py

Requirements
------------
    pip install -e .
"""

from __future__ import annotations

import os
import sys
from typing import Iterable

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khipu_translator.database import KhipuDB


HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, 'data', 'quechua_kaikki_2074.txt')


# V2 = pre-polyphony syllabary (uniform reading for every turn value).
# V3 = post-polyphony syllabary (onset form for the three polyphonic
# letters: L2=chi, L7=wa, L8=cha).
V2 = {0: 'lla', 2: 'ki',  3: 'ma', 4: 'ka', 5: 'ta', 6: 'pa',
      7: 'y',   8: 'na',  9: 'pi', 10: 'si', 11: 'ti', 12: 'ku', -1: 'qa'}

V3_ONSET = {0: 'lla', 2: 'chi', 3: 'ma', 4: 'ka', 5: 'ta', 6: 'pa',
            7: 'wa',  8: 'cha', 9: 'pi', 10: 'si', 11: 'ti', 12: 'ku', -1: 'qa'}


def load_dictionary() -> set[str]:
    if not os.path.exists(DICT_PATH):
        sys.exit(
            f"ERROR: dictionary not found: {DICT_PATH}\n"
            f"Run `python reproducibility/build_kaikki_dictionary.py` first."
        )
    with open(DICT_PATH, encoding='utf-8') as f:
        return {line.strip().lower() for line in f if line.strip()}


def extract_string_cords(db: KhipuDB) -> list[list[int]]:
    """Return every STRING cord in the OKR as a list of turn counts.

    A STRING cord here is any cord carrying >= 2 L knots (figure-eight
    knots encoded as -1). This matches the derivation's classification.
    """
    cord_all = pd.read_sql('SELECT CORD_ID, KHIPU_ID, CORD_ORDINAL FROM cord',
                            db.connection)
    knot_all = pd.read_sql(
        'SELECT CORD_ID, TYPE_CODE, NUM_TURNS, CLUSTER_ORDINAL, KNOT_ORDINAL '
        'FROM knot WHERE TYPE_CODE IN ("L", "E")',
        db.connection)

    cords: list[list[int]] = []
    for cid, g in knot_all.groupby('CORD_ID', sort=False):
        g = g.sort_values(['CLUSTER_ORDINAL', 'KNOT_ORDINAL'])
        seq: list[int] = []
        for _, k in g.iterrows():
            if k['TYPE_CODE'] == 'E':
                seq.append(-1)
            elif pd.notna(k['NUM_TURNS']) and k['NUM_TURNS'] >= 0:
                seq.append(int(k['NUM_TURNS']))
        if len(seq) >= 2:
            cords.append(seq)
    return cords


def translate(seq: list[int], mapping: dict[int, str]) -> str | None:
    if not all(t in mapping for t in seq):
        return None
    return ''.join(mapping[t] for t in seq)


def translate_polyphonic(seq: list[int],
                         onset_map: dict[int, str],
                         coda_map: dict[int, str]) -> str | None:
    """First position -> onset_map, last -> coda_map, middle -> coda_map."""
    if not all(t in coda_map and t in onset_map for t in seq):
        return None
    if len(seq) == 1:
        return onset_map[seq[0]]
    parts = [onset_map[seq[0]]]
    parts += [coda_map[t] for t in seq[1:]]
    return ''.join(parts)


def gain_loss(cords: Iterable[list[int]],
              base_translator, new_translator,
              dictionary: set[str],
              filter_contains: int | None = None) -> tuple[int, int, int, int]:
    """Count gains/losses/shared/denominator between two translation functions."""
    gained = lost = shared = n = 0
    for seq in cords:
        if filter_contains is not None and filter_contains not in seq:
            continue
        n += 1
        b = base_translator(seq)
        x = new_translator(seq)
        b_hit = b is not None and b in dictionary
        x_hit = x is not None and x in dictionary
        if b_hit and x_hit:
            shared += 1
        elif x_hit and not b_hit:
            gained += 1
        elif b_hit and not x_hit:
            lost += 1
    return gained, lost, shared, n


def main() -> None:
    print("=" * 70)
    print("ALBA Extension Analyses — L9 reassignment + positional polyphony")
    print("=" * 70)

    dictionary = load_dictionary()
    print(f"Dictionary: {len(dictionary):,} entries (Kaikki-derived)")

    db = KhipuDB()
    cords = extract_string_cords(db)
    db.close()
    print(f"Corpus STRING cords (>=2 L/E knots): {len(cords):,}")

    # -------------------------------------------------------------------------
    # 1. L9 reassignment  q -> pi
    # -------------------------------------------------------------------------
    print(f"\n{'-' * 70}")
    print("1. L9 reassignment  (q -> pi)")
    print("-" * 70)

    V_L9_q = dict(V2);  V_L9_q[9] = 'q'
    V_L9_pi = dict(V2);  V_L9_pi[9] = 'pi'

    gained, lost, shared, n = gain_loss(
        cords,
        lambda s: translate(s, V_L9_q),
        lambda s: translate(s, V_L9_pi),
        dictionary,
        filter_contains=9,
    )
    print(f"Cords containing L9:      {n}")
    print(f"Dictionary matches gained: {gained}")
    print(f"Dictionary matches lost:   {lost}")
    print(f"Shared (hit in both):      {shared}")
    if lost:
        print(f"Ratio gained:lost:         {gained / lost:.2f} : 1")
    else:
        print(f"Ratio gained:lost:         {gained} : 0  (infinite)")

    # -------------------------------------------------------------------------
    # 2. Positional polyphony
    #    baseline = uniform V2 reading
    #    polyphonic = V3 onset at position 0, V2 coda elsewhere
    # -------------------------------------------------------------------------
    print(f"\n{'-' * 70}")
    print("2. Positional polyphony  (V2 uniform  vs  V3 onset / V2 coda)")
    print("-" * 70)

    for turn_val, label in [(2, 'L2 (chi/ki)'),
                            (7, 'L7 (wa/y)'),
                            (8, 'L8 (cha/na)')]:
        gained, lost, shared, n = gain_loss(
            cords,
            lambda s: translate(s, V2),
            lambda s: translate_polyphonic(s, V3_ONSET, V2),
            dictionary,
            filter_contains=turn_val,
        )
        print(f"{label:<18}  n={n:4d}   +{gained} gained   -{lost} lost   "
              f"(shared={shared})")


if __name__ == '__main__':
    main()
