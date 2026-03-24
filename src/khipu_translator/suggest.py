"""
Similarity engine — find khipus similar to a given one.

Compares on 4 axes:
  1. Vocabulary overlap (Jaccard similarity of ALBA words)
  2. Structural similarity (cord count, cluster regularity, architecture)
  3. Provenance match (same site or museum)
  4. Color pattern similarity (cosine of color frequency vectors)

Used by `khipu suggest` and `khipu compare` CLI commands.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from khipu_translator.database import KhipuDB
from khipu_translator.translator import TranslationResult, translate


@dataclass
class SimilarityScore:
    """Similarity between two khipus."""
    khipu_id: str
    provenance: str
    total_score: float
    vocab_score: float
    structure_score: float
    provenance_score: float
    color_score: float
    document_type: str
    total_cords: int
    string_cords: int


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _cosine(a: Counter, b: Counter) -> float:
    """Cosine similarity between two frequency counters."""
    keys = set(a.keys()) | set(b.keys())
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _structure_sim(r1: TranslationResult, r2: TranslationResult) -> float:
    """Structural similarity: cord count ratio + architecture match."""
    # Cord count ratio (closer = more similar)
    c1, c2 = r1.stats["total_cords"], r2.stats["total_cords"]
    if c1 == 0 or c2 == 0:
        return 0.0
    ratio = min(c1, c2) / max(c1, c2)

    # Architecture match bonus
    arch_bonus = 0.3 if r1.architecture == r2.architecture else 0.0

    # STRING ratio similarity
    s1 = r1.stats["string_cords"] / max(c1, 1)
    s2 = r2.stats["string_cords"] / max(c2, 1)
    string_sim = 1.0 - abs(s1 - s2)

    return (ratio * 0.4 + string_sim * 0.3 + arch_bonus)


def _provenance_sim(r1: TranslationResult, r2: TranslationResult) -> float:
    """Provenance similarity: same site or same museum."""
    score = 0.0
    p1 = (r1.khipu.provenance or "").lower().strip()
    p2 = (r2.khipu.provenance or "").lower().strip()
    m1 = (r1.khipu.museum_name or "").lower().strip()
    m2 = (r2.khipu.museum_name or "").lower().strip()

    if p1 and p2 and p1 == p2:
        score = 1.0
    elif m1 and m2 and m1 == m2:
        score = 0.5
    elif p1 and p2:
        # Partial match (e.g. both contain "Pachacamac")
        words1 = set(p1.split())
        words2 = set(p2.split())
        if words1 & words2:
            score = 0.3
    return score


def suggest_similar(
    khipu_name: str,
    db: Optional[KhipuDB] = None,
    top_n: int = 5,
) -> tuple[TranslationResult, list[SimilarityScore]]:
    """
    Find khipus most similar to the given one.

    Parameters
    ----------
    khipu_name : str
        The reference khipu ID.
    db : KhipuDB, optional
        Database connection.
    top_n : int
        Number of results to return.

    Returns
    -------
    (reference_result, list of SimilarityScore)
    """
    close_db = False
    if db is None:
        db = KhipuDB()
        close_db = True

    try:
        ref = translate(khipu_name, db=db)
        ref_vocab = set(ref.vocabulary.keys())
        ref_colors = Counter(ref.stats.get("color_distribution", {}))

        all_khipus = db.list_khipus()
        scores = []

        for _, row in all_khipus.iterrows():
            kid = str(row["INVESTIGATOR_NUM"])
            if kid == ref.khipu.investigator_num:
                continue

            try:
                other = translate(kid, db=db)
            except Exception:
                continue

            other_vocab = set(other.vocabulary.keys())
            other_colors = Counter(other.stats.get("color_distribution", {}))

            vocab = _jaccard(ref_vocab, other_vocab)
            structure = _structure_sim(ref, other)
            provenance = _provenance_sim(ref, other)
            color = _cosine(ref_colors, other_colors)

            # Weighted total: vocab 40%, structure 25%, provenance 20%, color 15%
            total = vocab * 0.40 + structure * 0.25 + provenance * 0.20 + color * 0.15

            scores.append(SimilarityScore(
                khipu_id=kid,
                provenance=other.khipu.provenance or "?",
                total_score=total,
                vocab_score=vocab,
                structure_score=structure,
                provenance_score=provenance,
                color_score=color,
                document_type=other.document_type,
                total_cords=other.stats["total_cords"],
                string_cords=other.stats["string_cords"],
            ))

        scores.sort(key=lambda s: -s.total_score)
        return ref, scores[:top_n]

    finally:
        if close_db:
            db.close()


def compare_khipus(
    name1: str,
    name2: str,
    db: Optional[KhipuDB] = None,
) -> tuple[TranslationResult, TranslationResult, dict]:
    """
    Compare two khipus side by side.

    Returns (result1, result2, comparison_dict).
    """
    close_db = False
    if db is None:
        db = KhipuDB()
        close_db = True

    try:
        r1 = translate(name1, db=db)
        r2 = translate(name2, db=db)

        v1 = set(r1.vocabulary.keys())
        v2 = set(r2.vocabulary.keys())
        c1 = Counter(r1.stats.get("color_distribution", {}))
        c2 = Counter(r2.stats.get("color_distribution", {}))

        comparison = {
            "shared_words": sorted(v1 & v2),
            "only_in_1": sorted(v1 - v2),
            "only_in_2": sorted(v2 - v1),
            "vocab_similarity": _jaccard(v1, v2),
            "structure_similarity": _structure_sim(r1, r2),
            "provenance_similarity": _provenance_sim(r1, r2),
            "color_similarity": _cosine(c1, c2),
            "same_type": r1.document_type == r2.document_type,
            "same_architecture": r1.architecture == r2.architecture,
        }

        return r1, r2, comparison

    finally:
        if close_db:
            db.close()
