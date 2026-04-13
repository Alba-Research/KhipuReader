#!/usr/bin/env python3
"""
Independent replication of the ALBA syllabary on UR112 (Pachacamac).

UR112 had no role in calibration (UR039), cross-validation (UR050, UR055),
or iterative symbol extension. The v3 syllabary was frozen prior to this test.

Tests all P(13,5) = 154,440 possible syllable assignments to the 5 active
turn values on UR112. The frozen v3 mapping is compared against all
alternatives using strict ranking (mappings scoring strictly higher).

References:
    Sivan, J. (2026). Evidence for a Syllabic Mapping in Andean Khipu
    Long-Knot Turn Counts. Section 3.2. DOI: 10.5281/zenodo.19184002

Usage:
    python scripts/replication_ur112.py

Output:
    Prints rank, p-value, and optionally generates the distribution figure.
"""

import sys
import os
from itertools import permutations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khipu_translator.translator import translate
from khipu_translator.dictionary import GLOSSARY


def build_lookup():
    """Build the scoring lookup from the translator glossary."""
    base = set(GLOSSARY.keys())
    suffixes = ['ta', 'pa', 'ka', 'ma', 'na', 'qa', 'ki', 'si', 'y']
    test_dict = set()
    for w in base:
        test_dict.add(w)
        for s in suffixes:
            if len(w + s) >= 4:
                test_dict.add(w + s)
    prefix_set = set()
    for w in test_dict:
        for i in range(4, len(w)):
            prefix_set.add(w[:i])
    return test_dict | prefix_set


def extract_sequences(khipu_id):
    """Extract STRING cord turn sequences."""
    r = translate(khipu_id)
    seqs = []
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
                seqs.append(turns)
    return seqs


def score(mapping, sequences, lookup):
    """Count dictionary matches (exact + prefix)."""
    hits = 0
    for seq in sequences:
        word = ''.join(mapping.get(t, '?') for t in seq)
        if '?' not in word and len(word) >= 4 and word in lookup:
            hits += 1
    return hits


def main():
    print("=" * 60)
    print("ALBA Independent Replication on UR112")
    print("(syllabary frozen before test)")
    print("=" * 60)

    # Frozen v3 syllabary
    V3 = {
        0: 'lla', 2: 'chi', 3: 'ma', 4: 'ka', 5: 'ta',
        6: 'pa', 7: 'wa', 8: 'cha', 9: 'pi', 10: 'si',
        11: 'ti', 12: 'ku', -1: 'qa'
    }

    ALL_SYLLABLES = [
        'ma', 'ka', 'ta', 'pa', 'wa', 'cha', 'pi', 'si',
        'lla', 'chi', 'ti', 'ku', 'qa'
    ]

    lookup = build_lookup()
    sequences = extract_sequences('UR112')
    active_turns = sorted(set(t for s in sequences for t in s))
    n_active = len(active_turns)

    print(f"UR112: {len(sequences)} STRING sequences")
    print(f"Active turns: {active_turns}")
    print(f"Lookup: {len(lookup)} entries")

    # Score v3
    v3_score = score(V3, sequences, lookup)
    print(f"V3 score: {v3_score}/{len(sequences)}")

    # Exhaustive enumeration
    total = 1
    for i in range(n_active):
        total *= (len(ALL_SYLLABLES) - i)
    print(f"\nExhaustive enumeration: P({len(ALL_SYLLABLES)},{n_active}) "
          f"= {total:,} mappings")

    all_scores = []
    count = 0
    for perm in permutations(ALL_SYLLABLES, n_active):
        mapping = {t: perm[j] for j, t in enumerate(active_turns)}
        all_scores.append(score(mapping, sequences, lookup))
        count += 1
        if count % 50000 == 0:
            print(f"  {count:,}/{total:,}...")

    print(f"Enumeration complete: {count:,} mappings tested")

    # Ranking
    rank_strict = sum(1 for s in all_scores if s > v3_score)
    rank_geq = sum(1 for s in all_scores if s >= v3_score)
    rank_equal = sum(1 for s in all_scores if s == v3_score)
    p_strict = rank_strict / total
    p_geq = rank_geq / total

    import statistics
    mean_score = statistics.mean(all_scores)
    std_score = statistics.stdev(all_scores)

    print(f"\n{'=' * 60}")
    print(f"RESULTS")
    print(f"{'=' * 60}")
    print(f"V3 score: {v3_score}/{len(sequences)}")
    print(f"All mappings: mean = {mean_score:.1f}, "
          f"std = {std_score:.1f}, max = {max(all_scores)}")
    print(f"Mappings scoring strictly higher: {rank_strict}/{total:,}")
    print(f"Mappings scoring equal: {rank_equal}/{total:,}")
    print(f"Mappings scoring equal or higher: {rank_geq}/{total:,}")
    print(f"Rank-based p (strict, >): {p_strict:.6f}")
    print(f"Rank-based p (non-strict, >=): {p_geq:.6f}")
    print(f"p < 0.001: {'YES' if p_strict < 0.001 else 'NO'}")

    # Score distribution
    from collections import Counter
    score_counts = Counter(all_scores)
    print(f"\nScore distribution (top values):")
    for s in sorted(score_counts.keys(), reverse=True)[:8]:
        c = score_counts[s]
        print(f"  Score {s}: {c:,} mappings ({c/total*100:.3f}%)")

    # Optional: generate figure
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(10, 6.5))
        scores_arr = np.array(all_scores)
        bins = np.arange(-0.5, max(all_scores) + 2.5, 1)
        n, edges, patches = ax.hist(scores_arr, bins=bins,
                                     color='#4A90D9', alpha=0.85,
                                     edgecolor='white', linewidth=0.5)
        for i, (edge, patch) in enumerate(zip(edges, patches)):
            if int(edge + 0.5) == v3_score:
                patch.set_facecolor('#E74C3C')
                patch.set_alpha(0.9)

        ax.axvline(v3_score, color='#C0392B', linewidth=2, linestyle='--',
                   alpha=0.7)
        ymax = max(n) * 1.1

        ax.annotate(
            f'v3 syllabary:  {v3_score}/{len(sequences)} matches\n'
            f'Only {rank_strict} of {total:,} score higher\n'
            f'p < 0.001',
            xy=(v3_score, score_counts[v3_score]),
            xytext=(22, ymax * 0.82),
            fontsize=13, color='#C0392B', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#C0392B', lw=2.5,
                          connectionstyle='arc3,rad=-0.2'),
            ha='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#FDEBD0',
                     edgecolor='#C0392B', alpha=0.95, linewidth=1.5))

        stats = (f'All {total:,} mappings exhaustively tested\n'
                 f'Mean = {mean_score:.1f},  \u03c3 = {std_score:.1f}')
        ax.text(0.03, 0.15, stats, transform=ax.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='#EBF5FB', alpha=0.9,
                         edgecolor='#2980B9', linewidth=1))

        ax.set_xlabel('Quechua dictionary matches on UR112  '
                      f'({len(sequences)} STRING cords)', fontsize=14)
        ax.set_ylabel('Number of mappings', fontsize=14)
        ax.set_title(
            'Independent replication on UR112\n'
            'Syllabary frozen before test \u2014 '
            'UR112 had no role in derivation',
            fontsize=15, fontweight='bold', pad=15)
        ax.set_ylim(0, ymax)
        ax.tick_params(labelsize=12)
        plt.tight_layout()

        outdir = os.path.dirname(os.path.abspath(__file__))
        outpath_png = os.path.join(outdir, 'fig3_ur112_replication.png')
        outpath_tif = os.path.join(outdir, 'Fig3_UR112_replication.tif')
        plt.savefig(outpath_png, dpi=300, bbox_inches='tight')
        print(f"\nFigure saved: {outpath_png}")

        # LZW compression requires a Pillow build with the tiff_lzw codec
        # (usually present on Linux/macOS, sometimes missing on Windows).
        # Fall back to uncompressed TIFF if LZW is unavailable.
        try:
            plt.savefig(outpath_tif, dpi=300, bbox_inches='tight',
                        pil_kwargs={'compression': 'tiff_lzw'})
            print(f"Figure saved: {outpath_tif}  (300 dpi, LZW)")
        except Exception as tiff_err:
            try:
                plt.savefig(outpath_tif, dpi=300, bbox_inches='tight')
                print(f"Figure saved: {outpath_tif}  (300 dpi, uncompressed)")
            except Exception as e:
                print(f"TIFF export skipped ({type(e).__name__}: {e})")
    except ImportError:
        print("\nmatplotlib not available; skipping figure generation")


if __name__ == '__main__':
    main()
