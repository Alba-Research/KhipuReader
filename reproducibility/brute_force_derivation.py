#!/usr/bin/env python3
"""
ALBA — First Brute Force (UR039 / Huari)

This is the very first brute-force decipherment experiment that produced
the v2 syllabary. Extracted and condensed from alba_khipu_fat_session9.py
(sections 1-3, D1/D2/D5) so it can be re-run standalone.

Method
------
1. Extract STRING cords from UR039 (Huari, pre-Inca) as sequences of
   L-knot letters (e.g. L3s, L4s, L5s, L6s).
2. Build a small curated Quechua dictionary (2-syllable roots + 3-syllable
   root+suffix forms) and an Aymara reference dictionary.
3. Exhaustively score every ordered assignment of 4 syllables drawn from
   a 28-syllable pool to the 4 most frequent letters in UR039.
4. Rank mappings by number of distinct word types matched, then by total
   token frequency.

Inputs
------
- open-khipu-repository/data/khipu.db  (Open Khipu Repository SQLite DB)

Outputs
-------
- Prints to stdout:
    - UR039 STRING corpus summary
    - Top-10 Quechua mappings
    - Top-5 Aymara mappings
    - Top-5 Combined mappings
    - Full word-by-word translation of the best mapping
"""

import os
import sys
from itertools import permutations
from collections import Counter

import pandas as pd

# Make the installed khipu_translator package importable when the script
# is run directly from a source checkout (python reproducibility/brute_force_derivation.py).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from khipu_translator.database import KhipuDB

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

UR039_KID = 1000374

# -----------------------------------------------------------------------------
# 1. EXTRACT UR039 STRING CORPUS
# -----------------------------------------------------------------------------
print("=" * 70)
print("ALBA — First Brute Force (UR039)")
print("=" * 70)
print("\n[1] Extracting UR039 corpus...")

# KhipuDB auto-clones the Open Khipu Repository into ~/.khipu-translator/
# on first use (requires git + internet). Subsequent runs are offline.
db = KhipuDB()
cord_all = pd.read_sql('SELECT * FROM cord', db.connection)
knot_all = pd.read_sql('SELECT * FROM knot', db.connection)
db.close()

ur039_cords = cord_all[cord_all['KHIPU_ID'] == UR039_KID].sort_values('CORD_ORDINAL')
ur039_knots = knot_all[knot_all['CORD_ID'].isin(ur039_cords['CORD_ID'])]

string_entries = []
for _, cord in ur039_cords.iterrows():
    ck = ur039_knots[ur039_knots['CORD_ID'] == cord['CORD_ID']]
    ck = ck.sort_values(['CLUSTER_ORDINAL', 'KNOT_ORDINAL'])
    l_knots = ck[ck['TYPE_CODE'] == 'L']
    if len(l_knots) >= 2:
        letters = []
        for _, k in l_knots.iterrows():
            turns = int(k['NUM_TURNS']) if not pd.isna(k['NUM_TURNS']) and k['NUM_TURNS'] > 0 else 0
            d = str(k['DIRECTION']).strip().lower()[:1] if k['DIRECTION'] else '?'
            letters.append(f"L{turns}{d}")
        string_entries.append({'word': '.'.join(letters), 'letters': letters})

words = [e['word'] for e in string_entries]
word_freq = Counter(words)
unique_words = sorted(word_freq.keys(), key=lambda w: -word_freq[w])

all_letters = [l for e in string_entries for l in e['letters']]
letter_freq = Counter(all_letters)
active_letters = sorted(letter_freq.keys(), key=lambda l: -letter_freq[l])[:4]

print(f"  STRING cords: {len(string_entries)}")
print(f"  Unique words: {len(unique_words)}")
print(f"  Active letters (top 4): {active_letters}")
for l in active_letters:
    print(f"    {l:6s}: {letter_freq[l]:4d}")

# -----------------------------------------------------------------------------
# 2. DICTIONARIES
# -----------------------------------------------------------------------------
print("\n[2] Building dictionaries...")

quechua_roots_2syl = {
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

quechua_cv_suffixes = [
    'pa','ta','pi','qa','ri','na','ku','mu','ya','si',
    'chi','cha','mi','pu','ra','ka','ma',
]

quechua_3syl = set()
for root in quechua_roots_2syl:
    if len(root) == 4:
        for suf in quechua_cv_suffixes:
            quechua_3syl.add(root + suf)

quechua_3syl_roots = {
    'kuraka','yupana','kamana','tikana','papaya','wanaku','puriri','kutiri',
    'rimana','takiri','tukuri','tapara','kamari','wakana','tamari','rapaki',
    'tupana','pakana','munana','tiyapa',
}
quechua_3syl |= quechua_3syl_roots
quechua_dict = quechua_roots_2syl | quechua_3syl

aymara_roots = {
    'mama','tata','wawa','uma','uta','uru','naya','juma','yati','sata','wali',
    'kuna','paya','mara','jaya','wari','tama','japa','niya','wila','jupa','laka',
    'naka','jaqi','qullu','suma','tuku','sara','pata','masi','maya','qama',
    'yapa','maka','tapa','saya','runa','kama','taki','tupu','muyu','kuti','puyu',
    'waka','paka','mana','papa','suyu','kata','yaku','maki','puma','kuka',
}

combined_dict = quechua_dict | aymara_roots
print(f"  Quechua: {len(quechua_dict)} | Aymara: {len(aymara_roots)} | Combined: {len(combined_dict)}")

# -----------------------------------------------------------------------------
# 3. BRUTE FORCE
# -----------------------------------------------------------------------------
print("\n[3] Brute force search...")

syllable_pool = [
    'ka','ki','ku','ma','mi','mu','na','ni','pa','pi','pu','ta','ti','tu',
    'wa','ya','yu','ra','ri','ru','sa','si','su','la','cha','lla','qa','ha',
]
n_syms = len(active_letters)  # 4
n_perms = 1
for i in range(n_syms):
    n_perms *= (len(syllable_pool) - i)
print(f"  Pool: {len(syllable_pool)} syllables | P({len(syllable_pool)},{n_syms}) = {n_perms:,}")

letter_to_idx = {l: i for i, l in enumerate(active_letters)}
word_structures = []
for w in unique_words:
    idx = tuple(letter_to_idx.get(l, -1) for l in w.split('.'))
    word_structures.append((idx, word_freq[w], w))
total_cords = len(string_entries)


def score(syls, structs, dic):
    hits = types = 0
    for idx, freq, _ in structs:
        if -1 in idx:
            continue
        trans = ''.join(syls[i] for i in idx)
        if trans in dic:
            hits += freq
            types += 1
    return hits, types


def search(dic, label):
    results = []
    for perm in permutations(syllable_pool, n_syms):
        h, t = score(perm, word_structures, dic)
        if t >= 3:
            results.append({'mapping': perm, 'hits': h, 'types': t,
                            'cov': h / total_cords})
    results.sort(key=lambda r: (-r['types'], -r['hits']))
    print(f"\n  {label}: {len(results)} mappings with >=3 types")
    return results


best_q = search(quechua_dict, "D1 Quechua")
for i, m in enumerate(best_q[:10]):
    mp = ', '.join(f"{active_letters[j]}={m['mapping'][j]}" for j in range(n_syms))
    print(f"    {i+1:2d}  {mp:40s}  types={m['types']}  hits={m['hits']}  cov={m['cov']:.1%}")

best_a = search(aymara_roots, "D2 Aymara")
for i, m in enumerate(best_a[:5]):
    mp = ', '.join(f"{active_letters[j]}={m['mapping'][j]}" for j in range(n_syms))
    print(f"    {i+1:2d}  {mp:40s}  types={m['types']}  hits={m['hits']}  cov={m['cov']:.1%}")

best_c = search(combined_dict, "D5 Combined Q+A")
for i, m in enumerate(best_c[:5]):
    mp = ', '.join(f"{active_letters[j]}={m['mapping'][j]}" for j in range(n_syms))
    print(f"    {i+1:2d}  {mp:40s}  types={m['types']}  hits={m['hits']}  cov={m['cov']:.1%}")

# -----------------------------------------------------------------------------
# 4. BEST MAPPING — FULL TRANSLATION
# -----------------------------------------------------------------------------
if best_c:
    best = best_c[0]
    best_map = {active_letters[i]: best['mapping'][i] for i in range(n_syms)}
    print("\n" + "=" * 70)
    print(f"[4] BEST MAPPING: {best_map}")
    print(f"    Types: {best['types']}/{len(unique_words)}  "
          f"Coverage: {best['cov']:.1%} ({best['hits']}/{total_cords})")
    print("=" * 70)
    print(f"\n  {'Word':25s} {'Translation':15s} {'Freq':>4s}  {'Dict?'}")
    print(f"  {'-'*25} {'-'*15} {'-'*4}  {'-'*5}")
    for w in unique_words:
        trans = ''.join(best_map.get(l, '??') for l in w.split('.'))
        flag = 'YES' if trans in combined_dict else '.'
        print(f"  {w:25s} {trans:15s} {word_freq[w]:4d}  {flag}")

print("\nDone.")
