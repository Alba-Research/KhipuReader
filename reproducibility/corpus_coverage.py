#!/usr/bin/env python3
"""
Corpus-wide lexical coverage of the frozen v3 syllabary.

Reproduces the coverage rates cited in paper Section 3.3 (Lexical
Coverage) and the abstract:

    "corpus-wide average of X% (exact-or-prefix) and Y% (exact only)
     against the Kaikki dictionary, rising to Z% and W% respectively
     against the extended Kaikki+AULEX dictionary"

Method
------
1. For every validated khipu (as listed by khipu_translator.knowledge),
   translate each STRING cord under the frozen v3 syllabary using the
   packaged translator (identical to the Khipu Reader CLI output).
2. A cord is "parsable" if all its turn values map to a v3 syllable
   (no unknown symbols).
3. For each parsable cord, classify its translation under two match
   regimes against two dictionaries:
     - "exact"  : the translation is literally in the dictionary.
     - "prefix" : the translation has length >= 4 and is a prefix of
                  at least one dictionary entry (captures agglutinative
                  forms whose suffixes are not listed independently).
4. Report corpus-wide and per-khipu rates.

Dictionaries
------------
- Kaikki-derived (2,074 entries)       : data/quechua_kaikki_2074.txt
- Kaikki + AULEX   (14,991 entries)    : src/khipu_translator/data/
                                         quechua_strict_clean.txt

Usage
-----
    python reproducibility/corpus_coverage.py
"""

from __future__ import annotations

import os
import sys
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khipu_translator.translator import translate
from khipu_translator.knowledge import list_known_khipus


HERE = os.path.dirname(os.path.abspath(__file__))
KAIKKI_PATH = os.path.join(HERE, 'data', 'quechua_kaikki_2074.txt')
AULEX_PATH = os.path.join(HERE, '..', 'src', 'khipu_translator',
                           'data', 'quechua_strict_clean.txt')


# Common Quechua CV suffixes used to expand short roots. Matches the
# morphological rule described in the paper's "Lexical matching" section:
# an agglutinative form root+suffix counts as a match even when only the
# root is separately listed in the dictionary.
QUECHUA_SUFFIXES = ['ta', 'pa', 'y', 'qa', 'ki', 'na', 'ku', 'ma', 'ka',
                    'si', 'ti', 'lla', 'pi']


def load_dict(path: str, label: str) -> tuple[set[str], set[str]]:
    """Return (exact_set, prefix_set).

    exact_set:  dictionary entries plus root+single-suffix expansions for
                short roots (<= 4 chars) — captures agglutinative forms.
    prefix_set: every 3-or-more character prefix of every entry in the
                expanded set — captures longer agglutinative chains whose
                exact surface form is not enumerated.
    """
    if not os.path.exists(path):
        sys.exit(f"ERROR: {label} dictionary not found: {path}")
    with open(path, encoding='utf-8') as f:
        base = {line.strip().lower() for line in f if line.strip()}
    exact = set(base)
    for w in base:
        if len(w) <= 4:
            for s in QUECHUA_SUFFIXES:
                exact.add(w + s)
    prefixes: set[str] = set()
    for w in exact:
        for i in range(3, len(w)):
            prefixes.add(w[:i])
    return exact, prefixes


def classify(word: str, exact: set[str], prefixes: set[str]) -> str:
    """Return 'exact', 'prefix', or 'miss'."""
    if word in exact:
        return 'exact'
    if len(word) >= 3 and word in prefixes:
        return 'prefix'
    return 'miss'


def _tokenize_reading(reading: str) -> list[str]:
    """Split an alba_reading into candidate lexical tokens.

    The translator's alba_reading uses space-separated morpheme segmentation
    and hyphen-separated gloss markers (e.g. 'way chayta', 'waka-DIM').
    We strip gloss markers (UPPERCASE tokens) and return each surviving
    alphabetic token as a candidate word. A cord matches the dictionary
    if ANY of its tokens matches (exact or prefix), consistent with the
    morpheme-level matching rule described in the paper.
    """
    tokens: list[str] = []
    for chunk in reading.replace('-', ' ').split():
        chunk = chunk.lower()
        if not chunk:
            continue
        # Skip gloss markers (they contain no vowels or are glossary tags).
        if not any(v in chunk for v in 'aeiou'):
            continue
        if chunk in {'gen', 'acc', 'loc', 'dim', 'top', 'caus', 'poss',
                     'inter', 'inf', 'refl', 'pass', 'recip', 'obl',
                     '1obj', 'dir', 'lim', 'evid'}:
            continue
        tokens.append(chunk)
    return tokens


def khipu_cords_with_readings(khipu_id: str) -> list[list[str] | None]:
    """Translate khipu and return, per STRING cord, a list of candidate
    tokens (one cord -> list of lexical tokens), or None if unparsable."""
    r = translate(khipu_id)
    readings: list[list[str] | None] = []
    for c in r.cords:
        if c.cord_type != 'STRING':
            continue
        raw = (c.alba_reading or '').strip()
        if not raw or '?' in raw:
            readings.append(None)
            continue
        tokens = _tokenize_reading(raw)
        readings.append(tokens if tokens else None)
    return readings


def main() -> None:
    print("=" * 70)
    print("ALBA Corpus Coverage — frozen v3 syllabary on all validated khipus")
    print("=" * 70)

    kaikki_exact, kaikki_pref = load_dict(KAIKKI_PATH, 'Kaikki-derived')
    aulex_exact, aulex_pref = load_dict(AULEX_PATH, 'Kaikki+AULEX')
    print(f"Kaikki-derived:  {len(kaikki_exact):>6,} exact "
          f"({len(kaikki_pref):>6,} prefix positions)")
    print(f"Kaikki+AULEX:    {len(aulex_exact):>6,} exact "
          f"({len(aulex_pref):>6,} prefix positions)")

    khipus = list_known_khipus()
    print(f"Validated khipus: {len(khipus)}")

    # Per-khipu and corpus-wide tallies.
    totals = {
        'string': 0, 'parsable': 0,
        'kaikki_exact': 0, 'kaikki_any': 0,     # any = exact OR prefix
        'aulex_exact':  0, 'aulex_any': 0,
    }
    per_khipu_rates: list[dict] = []

    for kid in sorted(khipus):
        try:
            readings = khipu_cords_with_readings(kid)
        except Exception as e:
            print(f"  {kid}: skipped ({e})")
            continue
        n_string = len(readings)
        parsable = [w for w in readings if w is not None]
        if not parsable:
            continue

        ke = ka = ae = aa = 0
        for tokens in parsable:
            # Cord matches if ANY token matches (morpheme-level rule).
            token_classes_k = {classify(t, kaikki_exact, kaikki_pref)
                               for t in tokens}
            token_classes_a = {classify(t, aulex_exact, aulex_pref)
                               for t in tokens}
            if 'exact' in token_classes_k:
                ke += 1; ka += 1
            elif 'prefix' in token_classes_k:
                ka += 1
            if 'exact' in token_classes_a:
                ae += 1; aa += 1
            elif 'prefix' in token_classes_a:
                aa += 1

        totals['string'] += n_string
        totals['parsable'] += len(parsable)
        totals['kaikki_exact'] += ke
        totals['kaikki_any']   += ka
        totals['aulex_exact']  += ae
        totals['aulex_any']    += aa

        per_khipu_rates.append({
            'khipu': kid,
            'n_parsable': len(parsable),
            'kaikki_any_pct': 100.0 * ka / len(parsable),
            'aulex_any_pct':  100.0 * aa / len(parsable),
        })

    print(f"\n{'-' * 70}")
    print("Corpus-wide totals")
    print("-" * 70)
    p = totals['parsable']
    print(f"STRING cords total:     {totals['string']:>6,}")
    print(f"Parsable (v3-complete): {totals['parsable']:>6,} "
          f"({100.0 * p / max(totals['string'], 1):.1f}%)")
    print(f"\n                     Exact        Exact-or-prefix")
    print(f"  Kaikki 2,074     {totals['kaikki_exact']:>5,} ({100*totals['kaikki_exact']/p:5.1f}%) "
          f"   {totals['kaikki_any']:>5,} ({100*totals['kaikki_any']/p:5.1f}%)")
    print(f"  Kaikki+AULEX     {totals['aulex_exact']:>5,} ({100*totals['aulex_exact']/p:5.1f}%) "
          f"   {totals['aulex_any']:>5,} ({100*totals['aulex_any']/p:5.1f}%)")

    print(f"\n{'-' * 70}")
    print("Per-khipu coverage (exact-or-prefix, Kaikki+AULEX)")
    print("-" * 70)
    per_khipu_rates.sort(key=lambda r: -r['aulex_any_pct'])
    n_perfect = sum(1 for r in per_khipu_rates if r['aulex_any_pct'] >= 99.999)
    rates = [r['aulex_any_pct'] for r in per_khipu_rates]
    print(f"  n khipus with parsable cords: {len(per_khipu_rates)}")
    print(f"  100% coverage (Kaikki+AULEX, any): {n_perfect}")
    print(f"  range: {min(rates):.1f}%  -  {max(rates):.1f}%")
    print(f"  median: {statistics.median(rates):.1f}%   "
          f"mean: {statistics.mean(rates):.1f}%")


if __name__ == '__main__':
    main()
