"""
khipu-translator — Open-source framework for translating Andean khipus.

Combines the Locke decimal system (numerical channel, 1923), the ALBA
syllabary (textual channel, Sivan 2026), the merged OKR x KFG corpus
(unlocks L? cords via KFG turn counts), and the Ascher erasure-code
layer (pendant-pendant sums as checksums; arithmetic repair).

Usage:
    from khipu_translator import translate, MergedCorpus
    from khipu_translator import AscherGraph, KFGClient
    from khipu_translator import (
        apply_ascher_constraints,
        apply_reclassification,
        apply_constraint_propagation,
        apply_pure_arithmetic_repair,
    )

    # Basic v1 translation
    result = translate("UR039")

    # v3 translation (merged corpus + Ascher layer)
    corpus = MergedCorpus()
    r = translate("UR268", merged_corpus=corpus)
    g = AscherGraph.from_kfg(corpus.resolve_kh_id("UR268"), client=KFGClient())
    apply_ascher_constraints(r, g)
    apply_reclassification(r, g)
    apply_constraint_propagation(r, g)
    apply_pure_arithmetic_repair(r, g)
"""

from khipu_translator.translator import translate, TranslationResult
from khipu_translator.corpus import MergedCorpus
from khipu_translator.ascher import (
    AscherGraph,
    KFGClient,
    apply_ascher_constraints,
    apply_reclassification,
    apply_constraint_propagation,
    apply_pure_arithmetic_repair,
)

__version__ = "0.3.0"
__all__ = [
    "translate",
    "TranslationResult",
    "MergedCorpus",
    "AscherGraph",
    "KFGClient",
    "apply_ascher_constraints",
    "apply_reclassification",
    "apply_constraint_propagation",
    "apply_pure_arithmetic_repair",
]
