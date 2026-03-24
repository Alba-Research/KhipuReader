"""
khipu-translator — Open-source framework for translating Andean khipus.

Combines the Locke decimal system (numerical channel, 1923) with the
ALBA syllabary (textual channel, Sivan 2026) to produce multi-level
translations of khipus from the Open Khipu Repository.

Usage:
    from khipu_translator import translate

    result = translate("UR039")
    print(result.summary())
    result.to_json("UR039.json")
"""

from khipu_translator.translator import translate, TranslationResult

__version__ = "0.1.0"
__all__ = ["translate", "TranslationResult"]
