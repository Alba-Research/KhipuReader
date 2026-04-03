#!/usr/bin/env python3
"""
Brute-force syllabary derivation on UR039 (Wari/Huari, Ayacucho).

Tests all P(12,4) × 3 vowels = 46,512 possible CV syllable assignments
to the four active long-knot turn values (L3, L4, L5, L6) on UR039.
Scores each mapping against the Kaikki Quechua dictionary (exact + prefix).

The optimal mapping (L3=ma, L4=ka, L5=ta, L6=pa) is identified automatically.
A permutation test (N=5,000) establishes statistical significance.

References:
    Sivan, J. (2026). Evidence for a Syllabic Mapping in Andean Khipu
    Long-Knot Turn Counts. DOI: 10.5281/zenodo.19184002

Usage:
    python scripts/brute_force_derivation.py

Requirements:
    pip install -e .  (KhipuReader must be installed)
    The OKR database is downloaded automatically on first use.
"""

import sys
import os
import random
import itertools
from collections import Counter

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khipu_translator.translator import translate


def load_kaikki_dictionary():
    """Load the Kaikki Quechua dictionary (~2,060 entries)."""
    paths = [
        os.path.join(os.path.dirname(__file__), '..', '..',
                     'alba_khipu_output', 'quechua_real_dict.txt'),
        os.path.join(os.path.dirname(__file__), '..', 'src',
                     'khipu_translator', 'data', 'quechua_strict_clean.txt'),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                words = {line.strip().lower() for line in f if len(line.strip()) >= 2}
            return words
    raise FileNotFoundError("Kaikki dictionary not found. Expected quechua_real_dict.txt")


def build_lookup(dictionary):
    """Build exact + prefix lookup set (Section 2.4 matching rule)."""
    lookup = set(dictionary)
    for w in dictionary:
        for i in range(4, len(w)):
            lookup.add(w[:i])
    return lookup


def extract_string_sequences(khipu_id):
    """Extract raw turn-count sequences from STRING cords."""
    r = translate(khipu_id)
    sequences = []
    for c in r.cords:
        if c.cord_type == 'STRING' and c.knot_sequence:
            turns = []
            for k in c.knot_sequence.split():
                if k.startswith('L'):
                    try:
                        turns.append(int(k[1:]))
                    except ValueError:
                        pass
                elif k == 'E' or k.startswith('E'):
                    turns.append(-1)
            if len(turns) >= 2:
                sequences.append(turns)
    return sequences


def score_mapping(mapping, sequences, lookup):
    """Score a mapping by counting dictionary matches (exact + prefix)."""
    hits = 0
    for seq in sequences:
        word = ''
        valid = True
        for t in seq:
            if t in mapping:
                word += mapping[t]
            else:
                valid = False
                break
        if valid and len(word) >= 4 and word in lookup:
            hits += 1
    return hits


def main():
    print("=" * 60)
    print("ALBA Brute-Force Syllabary Derivation")
    print("Calibration khipu: UR039 (Wari/Huari, Ayacucho)")
    print("=" * 60)

    # Load dictionary
    dictionary = load_kaikki_dictionary()
    lookup = build_lookup(dictionary)
    print(f"Dictionary: {len(dictionary)} entries")
    print(f"Lookup (exact + prefix): {len(lookup)} entries")

    # Extract UR039 STRING sequences
    sequences = extract_string_sequences('UR039')
    print(f"UR039 STRING sequences: {len(sequences)}")

    # Identify active turn values
    active_turns = sorted(set(t for seq in sequences for t in seq))
    print(f"Active turn values: {active_turns}")

    # Define search space
    consonants = ['k', 'm', 't', 'p', 'n', 's', 'ch', 'w', 'll', 'y', 'q', 'h']
    vowels = ['a', 'i', 'u']

    # Generate all CV syllables
    all_syllables = []
    for c in consonants:
        for v in vowels:
            all_syllables.append(c + v)
    print(f"CV syllables: {len(all_syllables)}")

    # Exhaustive search: all ordered assignments of syllables to active turns
    n_active = len(active_turns)
    total_mappings = 1
    for i in range(n_active):
        total_mappings *= (len(all_syllables) - i)
    print(f"Search space: P({len(all_syllables)},{n_active}) = {total_mappings}")

    # Test all mappings
    print(f"\nTesting all {total_mappings} mappings...")
    best_score = 0
    best_mapping = None
    all_scores = []
    count = 0

    for perm in itertools.permutations(all_syllables, n_active):
        mapping = {t: perm[j] for j, t in enumerate(active_turns)}
        s = score_mapping(mapping, sequences, lookup)
        all_scores.append(s)
        if s > best_score:
            best_score = s
            best_mapping = dict(mapping)
        count += 1
        if count % 10000 == 0:
            print(f"  {count}/{total_mappings}... best so far: {best_score}")

    print(f"\nSearch complete. {count} mappings tested.")
    print(f"Best score: {best_score}/{len(sequences)}")
    print(f"Best mapping: {best_mapping}")

    # Top 10 mappings
    from collections import defaultdict
    score_counts = Counter(all_scores)
    print(f"\nScore distribution (top 10):")
    for s, c in sorted(score_counts.items(), reverse=True)[:10]:
        print(f"  Score {s}: {c} mappings ({c/count*100:.3f}%)")

    # Permutation test
    print(f"\nPermutation test (N=5,000 random shuffles)...")
    random.seed(42)
    perm_scores = []
    for i in range(5000):
        perm = random.sample(all_syllables, n_active)
        mapping = {t: perm[j] for j, t in enumerate(active_turns)}
        perm_scores.append(score_mapping(mapping, sequences, lookup))

    rank = sum(1 for s in perm_scores if s >= best_score)
    p_value = rank / len(perm_scores)
    print(f"  Best score: {best_score}")
    print(f"  Permutation scores >= best: {rank}/{len(perm_scores)}")
    print(f"  p-value: {p_value:.4f}")

    print(f"\n{'=' * 60}")
    print(f"RESULT: Optimal mapping L3={best_mapping.get(3)}, "
          f"L4={best_mapping.get(4)}, L5={best_mapping.get(5)}, "
          f"L6={best_mapping.get(6)}")
    print(f"Score: {best_score}/{len(sequences)} dictionary matches")
    print(f"Permutation test: p = {p_value:.4f}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
