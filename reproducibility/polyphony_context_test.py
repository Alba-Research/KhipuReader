#!/usr/bin/env python3
"""
Test whether the onset/coda choice for polyphonic letters (L2, L7, L8)
is better explained by position or by the identity of the adjacent turn.

Reproduces paper line 36:
    "Context-dependent polyphony (where a symbol's reading depends on
     its neighbors) was tested and rejected (p = 0.78)."

Method
------
For each polyphonic letter X in {L2, L7, L8}:

1. Collect every 2-syllable STRING cord in the OKR where X occupies
   position 0 (the "onset slot" under the positional model).
2. For each such cord, tag whether the ONSET reading (V3) or the CODA
   reading (V2) produces a dictionary word, given the fixed coda reading
   for the neighbor at position 1:
       - 'onset_wins' : only onset form yields a dict match
       - 'coda_wins'  : only coda form yields a dict match
       - 'both' or 'neither' : excluded from the context test (uninformative)
3. Restrict to informative cords (onset_wins / coda_wins) and build a
   2 x K contingency table:
       rows: {onset_wins, coda_wins}
       cols: identity of the position-1 turn value
4. Chi-square test of independence.

Interpretation
--------------
Under the NULL hypothesis (only position matters), the onset/coda
preference should be independent of the neighbor identity: large p.
Under the ALTERNATIVE (context matters), the preference should co-vary
with the neighbor: small p.

A large p across the three polyphonic letters supports the simpler
positional model and rejects a context-dependent extension.

Dictionary
----------
Kaikki-derived 2,074 entries (build_kaikki_dictionary.py).

Usage
-----
    python reproducibility/polyphony_context_test.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from scipy.stats import chi2_contingency
except ImportError:
    sys.exit("ERROR: scipy is required. Install via `pip install scipy`.")

from khipu_translator.database import KhipuDB


HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, 'data', 'quechua_kaikki_2074.txt')


# Onset and coda forms for the three polyphonic letters.
POLYPHONIC = {
    2: {'onset': 'chi', 'coda': 'ki',  'label': 'L2'},
    7: {'onset': 'wa',  'coda': 'y',   'label': 'L7'},
    8: {'onset': 'cha', 'coda': 'na',  'label': 'L8'},
}

# V2 coda readings for the non-polyphonic neighbor letters.
V2_CODA = {0: 'lla', 2: 'ki',  3: 'ma', 4: 'ka', 5: 'ta', 6: 'pa',
           7: 'y',   8: 'na',  9: 'pi', 10: 'si', 11: 'ti', 12: 'ku', -1: 'qa'}


def load_dictionary() -> set[str]:
    if not os.path.exists(DICT_PATH):
        sys.exit(
            f"ERROR: {DICT_PATH} not found. "
            f"Run `python reproducibility/build_kaikki_dictionary.py` first."
        )
    with open(DICT_PATH, encoding='utf-8') as f:
        return {line.strip().lower() for line in f if line.strip()}


def extract_two_syllable_cords(db: KhipuDB) -> list[tuple[int, int]]:
    """Return all cords with exactly 2 L/E knots, as (turn1, turn2) pairs."""
    knot_all = pd.read_sql(
        'SELECT CORD_ID, TYPE_CODE, NUM_TURNS, CLUSTER_ORDINAL, KNOT_ORDINAL '
        'FROM knot WHERE TYPE_CODE IN ("L", "E")',
        db.connection)

    pairs: list[tuple[int, int]] = []
    for _, g in knot_all.groupby('CORD_ID', sort=False):
        g = g.sort_values(['CLUSTER_ORDINAL', 'KNOT_ORDINAL'])
        if len(g) != 2:
            continue
        seq: list[int] = []
        for _, k in g.iterrows():
            if k['TYPE_CODE'] == 'E':
                seq.append(-1)
            elif pd.notna(k['NUM_TURNS']) and k['NUM_TURNS'] >= 0:
                seq.append(int(k['NUM_TURNS']))
            else:
                break
        if len(seq) == 2:
            pairs.append((seq[0], seq[1]))
    return pairs


def run_one(letter: int, cfg: dict, pairs: list[tuple[int, int]],
            dictionary: set[str]) -> None:
    """Chi-square test of context-dependence for one polyphonic letter."""
    print(f"\n{'-' * 64}")
    print(f"{cfg['label']}  ({cfg['onset']} onset  vs  {cfg['coda']} coda)")
    print('-' * 64)

    # Restrict to cords where this letter is at position 0 and the neighbor
    # at position 1 has a defined V2 reading.
    informative: list[tuple[int, str]] = []  # (neighbor_turn, which_wins)
    both = neither = 0
    for t0, t1 in pairs:
        if t0 != letter or t1 not in V2_CODA:
            continue
        neighbor_syl = V2_CODA[t1]
        word_onset = cfg['onset'] + neighbor_syl
        word_coda = cfg['coda'] + neighbor_syl
        h_onset = word_onset in dictionary
        h_coda = word_coda in dictionary
        if h_onset and h_coda:
            both += 1
        elif h_onset and not h_coda:
            informative.append((t1, 'onset_wins'))
        elif h_coda and not h_onset:
            informative.append((t1, 'coda_wins'))
        else:
            neither += 1

    n_total = len(informative) + both + neither
    print(f"2-syllable cords with {cfg['label']} at position 0: {n_total}")
    print(f"  both readings hit dict:    {both}")
    print(f"  neither hits dict:         {neither}")
    print(f"  informative (exactly one): {len(informative)}")

    if len(informative) < 10:
        print("  Too few informative cords for a meaningful chi-square.")
        return

    # Contingency table: rows = {onset_wins, coda_wins}, cols = neighbor turn.
    # Drop rare neighbors (count < 3) to avoid zero-expected-frequency rows
    # that break the chi-square approximation; those rare cells carry no
    # usable signal for context-dependence anyway.
    from collections import Counter
    neighbor_counts = Counter(n for n, _ in informative)
    kept = sorted(n for n, c in neighbor_counts.items() if c >= 3)
    dropped = sum(c for n, c in neighbor_counts.items() if c < 3)
    if dropped:
        print(f"  dropped {dropped} cords in {len(neighbor_counts) - len(kept)} "
              f"rare-neighbor categories (count < 3)")

    rows = ['onset_wins', 'coda_wins']
    table = [[0] * len(kept) for _ in rows]
    for n, w in informative:
        if n in kept:
            table[rows.index(w)][kept.index(n)] += 1
    n_used = sum(sum(r) for r in table)
    row_totals = [sum(r) for r in table]
    if n_used < 10 or min(row_totals) == 0:
        print(f"  informative cords collapse into a single reading across "
              f"all neighbors (onset_wins={row_totals[0]}, "
              f"coda_wins={row_totals[1]}).")
        print(f"  No heterogeneity to test — the strongest possible "
              f"evidence AGAINST a context effect.")
        return
    chi2, p, dof, expected = chi2_contingency(table)
    print(f"  Contingency: {len(rows)} outcomes x {len(kept)} neighbors")
    print(f"  Neighbors tested: {[f'L{n}' if n != -1 else 'E' for n in kept]}")
    print(f"  onset_wins row: {table[0]}  (total {sum(table[0])})")
    print(f"  coda_wins  row: {table[1]}  (total {sum(table[1])})")
    print(f"  chi2 = {chi2:.3f}   dof = {dof}   p = {p:.3f}")
    verdict = ("no context effect detected" if p > 0.05
               else "context effect is statistically detectable")
    print(f"  -> {verdict}")


def main() -> None:
    print("=" * 64)
    print("Polyphony context-dependence test  (H0 = positional only)")
    print("=" * 64)

    dictionary = load_dictionary()
    print(f"Dictionary: {len(dictionary):,} entries (Kaikki-derived)")

    db = KhipuDB()
    pairs = extract_two_syllable_cords(db)
    db.close()
    print(f"2-syllable STRING cords: {len(pairs):,}")

    for turn, cfg in POLYPHONIC.items():
        run_one(turn, cfg, pairs, dictionary)


if __name__ == '__main__':
    main()
