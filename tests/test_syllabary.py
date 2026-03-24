"""Tests for the ALBA syllabary module."""

from khipu_translator.syllabary import (
    ALBA_SYLLABARY,
    TURNS_TO_SYLLABLE,
    TURNS_TO_ONSET,
    VALID_TURNS,
    knot_to_syllable,
    Confidence,
)


def test_syllabary_has_13_symbols():
    assert len(ALBA_SYLLABARY) == 13


def test_base_mapping():
    assert TURNS_TO_SYLLABLE[0] == "lla"
    assert TURNS_TO_SYLLABLE[2] == "ki"
    assert TURNS_TO_SYLLABLE[3] == "ma"
    assert TURNS_TO_SYLLABLE[4] == "ka"
    assert TURNS_TO_SYLLABLE[5] == "ta"
    assert TURNS_TO_SYLLABLE[6] == "pa"
    assert TURNS_TO_SYLLABLE[7] == "y"
    assert TURNS_TO_SYLLABLE[8] == "na"
    assert TURNS_TO_SYLLABLE[9] == "pi"


def test_onset_polyphony():
    assert TURNS_TO_ONSET[7] == "wa"   # y -> wa
    assert TURNS_TO_ONSET[8] == "cha"  # na -> cha
    assert TURNS_TO_ONSET[2] == "chi"  # ki -> chi


def test_non_polyphonic_onset_unchanged():
    assert TURNS_TO_ONSET[3] == "ma"   # no onset variant
    assert TURNS_TO_ONSET[4] == "ka"
    assert TURNS_TO_ONSET[5] == "ta"


def test_figure_eight():
    assert knot_to_syllable("E", None) == "qa"


def test_knot_to_syllable_basic():
    assert knot_to_syllable("L", 3) == "ma"
    assert knot_to_syllable("L", 4) == "ka"
    assert knot_to_syllable("L", 6, is_onset=False) == "pa"


def test_knot_to_syllable_onset():
    assert knot_to_syllable("L", 7, is_onset=True) == "wa"
    assert knot_to_syllable("L", 7, is_onset=False) == "y"
    assert knot_to_syllable("L", 8, is_onset=True) == "cha"
    assert knot_to_syllable("L", 8, is_onset=False) == "na"
    assert knot_to_syllable("L", 2, is_onset=True) == "chi"
    assert knot_to_syllable("L", 2, is_onset=False) == "ki"


def test_unknown_turn_count():
    assert knot_to_syllable("L", 1) is None    # L1 eliminated
    assert knot_to_syllable("L", 99) is None   # nonexistent
    assert knot_to_syllable("X", 5) is None    # unknown type


def test_confidence_levels():
    high_count = sum(1 for m in ALBA_SYLLABARY if m.confidence == Confidence.HIGH)
    assert high_count == 10  # L0, L2, L3, L4, L5, L6, L7, L8, L9, E
    medium_count = sum(1 for m in ALBA_SYLLABARY if m.confidence == Confidence.MEDIUM)
    assert medium_count == 1  # L10
    low_count = sum(1 for m in ALBA_SYLLABARY if m.confidence == Confidence.LOW)
    assert low_count == 2   # L11, L12


def test_valid_turns_excludes_l1():
    assert 1 not in VALID_TURNS
    assert 0 in VALID_TURNS
    assert 2 in VALID_TURNS


def test_mama_can_be_spelled():
    """The word 'mama' should be L3+L3 = ma+ma."""
    s1 = knot_to_syllable("L", 3, is_onset=True)
    s2 = knot_to_syllable("L", 3, is_onset=False)
    assert s1 + s2 == "mama"


def test_qaqa_can_be_spelled():
    """The word 'qaqa' should be E+E = qa+qa."""
    s1 = knot_to_syllable("E", None, is_onset=True)
    s2 = knot_to_syllable("E", None, is_onset=False)
    assert s1 + s2 == "qaqa"


def test_waka_onset():
    """'waka' = L7(onset:wa) + L4(ka)."""
    s1 = knot_to_syllable("L", 7, is_onset=True)
    s2 = knot_to_syllable("L", 4, is_onset=False)
    assert s1 + s2 == "waka"


def test_chaki_onset():
    """'chaki' = L8(onset:cha) + L2(ki)."""
    s1 = knot_to_syllable("L", 8, is_onset=True)
    s2 = knot_to_syllable("L", 2, is_onset=False)
    assert s1 + s2 == "chaki"


def test_chiqa_onset():
    """'chiqa' = L2(onset:chi) + E(qa)."""
    s1 = knot_to_syllable("L", 2, is_onset=True)
    s2 = knot_to_syllable("E", None, is_onset=False)
    assert s1 + s2 == "chiqa"
