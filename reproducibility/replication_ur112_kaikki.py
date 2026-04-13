#!/usr/bin/env python3
"""
Independent replication on UR112 — scored against the Kaikki-derived
dictionary (2,074 entries) rather than the small ALBA glossary.

This is the Kaikki counterpart of replication_ur112.py. It reproduces the
claim in paper Section 3.2 / Figure 3 caption:

    "Among these 154,440 mappings tested against the Kaikki dictionary,
    N produce more raw dictionary hits than the v3 mapping."

The ALBA glossary version (replication_ur112.py) uses a curated 112-root
lexicon expanded with suffixes and 4-char prefixes — a permissive lookup
designed to reward morphologically plausible forms. The Kaikki version
below uses the Kaikki Quechua extract (2,074 entries, frozen 2026-03-20,
see build_kaikki_dictionary.py) with light morphological expansion
(root + single CV suffix for roots <= 4 chars) and strict exact-match
scoring. This matches the methodology used in the original derivation
script (alba_replication_final.py) and yields the "raw dictionary hits"
number cited in the paper.

Method
------
1. Load data/quechua_kaikki_2074.txt.
2. Extend with the 13 most common Quechua CV suffixes
   (ta, pa, y, qa, ki, na, ku, ma, ka, si, ti, lla, pi) applied to roots
   of length <= 4 — this captures agglutinative forms not independently
   listed in Kaikki.
3. Extract UR112 STRING sequences via the KhipuReader translator.
4. Score the frozen v3 syllabary as an exact-match count against the
   extended Kaikki lookup.
5. Enumerate all P(13, 5) = 154,440 ordered syllable assignments over the
   5 active turn values on UR112, score each, and rank v3 against them.
6. Report the number of mappings strictly higher (the paper's central
   Kaikki-based statistic), the rank-based p-value, and the score
   distribution.

Output
------
Prints a complete audit block to stdout. No side-effect files.

Usage
-----
    python reproducibility/replication_ur112_kaikki.py

References
----------
    Sivan, J. (2026). Evidence for a Syllabic Mapping in Andean Khipu
    Long-Knot Turn Counts. Section 3.2, Figure 3.
"""

from __future__ import annotations

import os
import sys
import statistics
from itertools import permutations
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khipu_translator.translator import translate


HERE = os.path.dirname(os.path.abspath(__file__))
KAIKKI_PATH = os.path.join(HERE, 'data', 'quechua_kaikki_2074.txt')

# Frozen v3 syllabary (identical to replication_ur112.py, syllabary.json, paper Table 2).
V3 = {
    0: 'lla',  2: 'chi', 3: 'ma',  4: 'ka',  5: 'ta',
    6: 'pa',   7: 'wa',  8: 'cha', 9: 'pi',  10: 'si',
    11: 'ti',  12: 'ku', -1: 'qa',
}

ALL_SYLLABLES = [
    'ma', 'ka', 'ta', 'pa', 'wa', 'cha', 'pi', 'si',
    'lla', 'chi', 'ti', 'ku', 'qa',
]

def load_kaikki_lookup() -> set[str]:
    """Load Kaikki 2,074 as-is. Exact-match only, no morphological expansion.

    The paper's Figure 3 caption refers to "raw dictionary hits" — we
    deliberately do not apply suffix expansion here to avoid inflating the
    hit rate and saturating the distribution.
    """
    if not os.path.exists(KAIKKI_PATH):
        sys.exit(
            f"ERROR: {KAIKKI_PATH} not found. "
            f"Run `python reproducibility/build_kaikki_dictionary.py` first."
        )
    with open(KAIKKI_PATH, encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}


def extract_sequences(khipu_id: str) -> list[list[int]]:
    """Extract STRING cord turn sequences via the translator."""
    r = translate(khipu_id)
    seqs: list[list[int]] = []
    for c in r.cords:
        if c.cord_type == 'STRING' and c.knot_sequence:
            turns: list[int] = []
            for tok in c.knot_sequence.split():
                if tok.startswith('L'):
                    try:
                        turns.append(int(tok[1:]))
                    except ValueError:
                        pass
                elif tok == 'E' or tok.startswith('E'):
                    turns.append(-1)
            if len(turns) >= 2:
                seqs.append(turns)
    return seqs


def score(mapping: dict[int, str], sequences: list[list[int]],
          lookup: set[str]) -> int:
    """Exact-match hit count against the Kaikki extended lookup."""
    hits = 0
    for seq in sequences:
        parts = [mapping.get(t) for t in seq]
        if any(p is None for p in parts):
            continue
        word = ''.join(parts)
        if word in lookup:
            hits += 1
    return hits


def main() -> None:
    print("=" * 64)
    print("ALBA Independent Replication on UR112 — Kaikki 2,074")
    print("(syllabary frozen before test)")
    print("=" * 64)

    lookup = load_kaikki_lookup()
    sequences = extract_sequences('UR112')
    active_turns = sorted({t for s in sequences for t in s})
    n_active = len(active_turns)

    print(f"Kaikki lookup (exact, no morphology): {len(lookup):,} entries")
    print(f"UR112 STRING sequences:          {len(sequences):,}")
    print(f"Active turn values:              {active_turns}")

    v3_score = score(V3, sequences, lookup)
    print(f"V3 score:                        {v3_score}/{len(sequences)}")

    total = 1
    for i in range(n_active):
        total *= (len(ALL_SYLLABLES) - i)
    print(f"\nExhaustive enumeration: P({len(ALL_SYLLABLES)},{n_active}) = {total:,} mappings")

    all_scores: list[int] = []
    for count, perm in enumerate(permutations(ALL_SYLLABLES, n_active), start=1):
        mapping = {t: perm[j] for j, t in enumerate(active_turns)}
        all_scores.append(score(mapping, sequences, lookup))
        if count % 50000 == 0:
            print(f"  {count:,}/{total:,}...")
    print(f"Enumeration complete: {len(all_scores):,} mappings tested")

    rank_strict = sum(1 for s in all_scores if s > v3_score)
    rank_equal = sum(1 for s in all_scores if s == v3_score)
    p_strict = rank_strict / total
    mean_score = statistics.mean(all_scores)
    std_score = statistics.stdev(all_scores)

    print(f"\n{'=' * 64}")
    print("RESULTS — Kaikki 2,074")
    print("=" * 64)
    print(f"V3 score:                        {v3_score}/{len(sequences)}")
    print(f"Random mean (std):               {mean_score:.2f} ({std_score:.2f})")
    print(f"Max random score:                {max(all_scores)}")
    print(f"Mappings scoring strictly higher:{rank_strict:>6} / {total:,}")
    print(f"Mappings scoring equal:          {rank_equal:>6} / {total:,}")
    print(f"Rank-based p (strict):           {p_strict:.6f}")
    print(f"p < 0.001:                       {'YES' if p_strict < 0.001 else 'NO'}")

    dist = Counter(all_scores)
    print("\nScore distribution (top 10):")
    for s in sorted(dist.keys(), reverse=True)[:10]:
        marker = "  <-- V3" if s == v3_score else ""
        print(f"  score={s:3d}: {dist[s]:6,} mappings "
              f"({dist[s]/total*100:5.2f}%){marker}")


if __name__ == '__main__':
    main()
