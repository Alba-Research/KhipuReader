"""
ALBA Syllabary v3 — Proposed mapping from khipu knot types to Quechua syllables.

Derived by brute-force optimization on UR039 (Sivan 2026).
Statistical assessment: p = 0.001 (Kaikki dictionary, 2,067 words).

The syllabary has three components:
  1. Base mapping: long-knot turn counts -> syllables (13 symbols)
  2. Figure-eight knot -> 'qa' (1 symbol)
  3. Onset polyphony: first knot in a word reads differently for 3 symbols (v3)

Confidence levels:
  HIGH   — L0(lla), L2(ki/chi), L3(ma), L4(ka), L5(ta), L6(pa), L7(y/wa),
           L8(na/cha), L9(pi), E(qa)
  MEDIUM — L10(si)
  LOW    — L11(ti), L12(ku)

Reference: Sivan, J. (2026). "The Khipu as a Layered Information System."
           ALBA Project preprint. doi:10.5281/zenodo.XXXXXXX
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Confidence(Enum):
    """Confidence level for a syllable mapping."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ELIMINATED = "eliminated"


@dataclass(frozen=True)
class SyllableMapping:
    """A single knot-type -> syllable mapping."""
    knot_type: str          # 'L0', 'L2', ..., 'L12', 'E'
    turns: Optional[int]    # number of turns (None for figure-eight)
    syllable: str           # proposed Quechua syllable
    onset_syllable: Optional[str]  # different reading when first in word (v3)
    confidence: Confidence
    examples: tuple[str, ...]  # supporting words


# --- Base mapping (coda position = default) ----------------------------------
# L1 is eliminated: 0 occurrences in STRING cords across the entire OKR.
# L13+ are too rare (<7 cords) for resolution.

ALBA_SYLLABARY: tuple[SyllableMapping, ...] = (
    SyllableMapping("L0",  0,  "lla", None,  Confidence.HIGH,
                    ("llama", "killa", "llaqa")),
    SyllableMapping("L2",  2,  "ki",  "chi", Confidence.HIGH,
                    ("kiki", "maki", "taki")),
    SyllableMapping("L3",  3,  "ma",  None,  Confidence.HIGH,
                    ("mama", "kama")),
    SyllableMapping("L4",  4,  "ka",  None,  Confidence.HIGH,
                    ("kaka", "taka")),
    SyllableMapping("L5",  5,  "ta",  None,  Confidence.HIGH,
                    ("tata", "pata")),
    SyllableMapping("L6",  6,  "pa",  None,  Confidence.HIGH,
                    ("papa", "pana", "panaka")),
    SyllableMapping("L7",  7,  "y",   "wa",  Confidence.HIGH,
                    ("kamay", "takay")),
    SyllableMapping("L8",  8,  "na",  "cha", Confidence.HIGH,
                    ("mana", "nana", "chaki", "chay")),
    SyllableMapping("L9",  9,  "pi",  None,  Confidence.HIGH,
                    ("pi", "kaypi", "sipa", "piqa")),
    SyllableMapping("L10", 10, "si",  None,  Confidence.MEDIUM,
                    ("sina", "wasi")),
    SyllableMapping("L11", 11, "ti",  None,  Confidence.LOW,
                    ("kiti", "tiki")),
    SyllableMapping("L12", 12, "ku",  None,  Confidence.LOW,
                    ("naku", "chaku")),
    SyllableMapping("E",   None, "qa", None,  Confidence.HIGH,
                    ("qaqa", "qapaq", "qama", "chiqa")),
)

# --- Lookup helpers ----------------------------------------------------------

# turn count -> syllable (coda / default position)
TURNS_TO_SYLLABLE: dict[int, str] = {
    m.turns: m.syllable for m in ALBA_SYLLABARY if m.turns is not None
}

# turn count -> syllable (onset / first position in word)
TURNS_TO_ONSET: dict[int, str] = {
    m.turns: (m.onset_syllable or m.syllable)
    for m in ALBA_SYLLABARY if m.turns is not None
}

# figure-eight -> syllable
FIGURE_EIGHT_SYLLABLE = "qa"

# Valid turn counts for STRING cords (L-1 filtering: NULL/NaN turns are invalid)
VALID_TURNS: set[int] = {m.turns for m in ALBA_SYLLABARY if m.turns is not None}


def knot_to_syllable(
    knot_type: str,
    num_turns: Optional[int],
    is_onset: bool = False,
) -> Optional[str]:
    """
    Convert a single knot to its proposed syllable.

    Parameters
    ----------
    knot_type : str
        'L' for long knot, 'E' for figure-eight knot.
    num_turns : int or None
        Number of turns (for long knots). Ignored for figure-eight.
    is_onset : bool
        If True, use onset polyphony (v3). First knot in a word
        may read differently for L2(chi), L7(wa), L8(cha).

    Returns
    -------
    str or None
        The proposed syllable, or None if the knot type is unknown.
    """
    if knot_type == "E":
        return FIGURE_EIGHT_SYLLABLE

    if knot_type == "L" and num_turns is not None:
        if is_onset:
            return TURNS_TO_ONSET.get(num_turns)
        return TURNS_TO_SYLLABLE.get(num_turns)

    return None


def describe_syllabary() -> str:
    """Return a human-readable description of the syllabary."""
    lines = [
        "ALBA Syllabary v3 -- 13 base symbols + 3 onset variants",
        "=" * 65,
        f"{'Knot':<6s} {'Turns':<6s} {'Coda':<8s} {'Onset':<8s} "
        f"{'Confidence':<12s} Examples",
        "-" * 65,
    ]
    for m in ALBA_SYLLABARY:
        turns_str = str(m.turns) if m.turns is not None else "fig-8"
        onset_str = m.onset_syllable or "--"
        examples_str = ", ".join(m.examples)
        lines.append(
            f"{m.knot_type:<6s} {turns_str:<6s} {m.syllable:<8s} "
            f"{onset_str:<8s} {m.confidence.value:<12s} {examples_str}"
        )
    return "\n".join(lines)
