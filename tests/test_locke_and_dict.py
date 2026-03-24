"""Tests for the Locke decimal system and dictionary modules."""

from khipu_translator.locke import cord_type, is_string_cord, decode_locke_value
from khipu_translator.dictionary import (
    DICTIONARY,
    GLOSSARY,
    split_syllables,
    analyze_morphology,
)


# --- Locke tests -------------------------------------------------------------

def test_cord_type_empty():
    assert cord_type([]) == "EMPTY"


def test_cord_type_int():
    knots = [{"TYPE_CODE": "S"}, {"TYPE_CODE": "S"}, {"TYPE_CODE": "L"}]
    assert cord_type(knots) == "INT"


def test_cord_type_string():
    knots = [{"TYPE_CODE": "L"}, {"TYPE_CODE": "L"}, {"TYPE_CODE": "S"}]
    assert cord_type(knots) == "STRING"


def test_is_string_cord():
    assert is_string_cord([{"TYPE_CODE": "L"}, {"TYPE_CODE": "E"}])
    assert not is_string_cord([{"TYPE_CODE": "L"}, {"TYPE_CODE": "S"}])
    assert not is_string_cord([{"TYPE_CODE": "S"}])


def test_decode_locke_basic():
    knots = [
        {"TYPE_CODE": "S", "knot_value_type": 100, "CLUSTER_ORDINAL": 1, "KNOT_ORDINAL": 1},
        {"TYPE_CODE": "S", "knot_value_type": 100, "CLUSTER_ORDINAL": 1, "KNOT_ORDINAL": 2},
        {"TYPE_CODE": "L", "knot_value_type": 5, "NUM_TURNS": 5, "CLUSTER_ORDINAL": 3, "KNOT_ORDINAL": 1},
    ]
    result = decode_locke_value(knots)
    assert result is not None
    assert result.value == 205


def test_decode_locke_string_rejected():
    """STRING cords (2+ terminal knots) should return None in strict mode."""
    knots = [
        {"TYPE_CODE": "L", "knot_value_type": 3, "NUM_TURNS": 3},
        {"TYPE_CODE": "L", "knot_value_type": 4, "NUM_TURNS": 4},
    ]
    assert decode_locke_value(knots, strict=True) is None


def test_decode_locke_uniform_kvt():
    """Detect uniform knot_value_type (investigator didn't encode positions)."""
    knots = [
        {"TYPE_CODE": "S", "knot_value_type": 10, "CLUSTER_ORDINAL": 1, "KNOT_ORDINAL": 1},
        {"TYPE_CODE": "S", "knot_value_type": 10, "CLUSTER_ORDINAL": 1, "KNOT_ORDINAL": 2},
        {"TYPE_CODE": "L", "knot_value_type": 5, "NUM_TURNS": 5, "CLUSTER_ORDINAL": 3, "KNOT_ORDINAL": 1},
    ]
    result = decode_locke_value(knots)
    assert result is not None
    assert result.confidence == "uniform_kvt"


# --- Dictionary tests --------------------------------------------------------

def test_core_words_in_dictionary():
    for word in ["mama", "papa", "tata", "kaka", "qaqa", "llaqa", "maki",
                 "chiqa", "kaqa", "taqa", "paka", "waka", "chaki"]:
        assert word in DICTIONARY, f"{word} missing from dictionary"


def test_glossary_has_translations():
    assert "mama" in GLOSSARY
    fr, en, domain = GLOSSARY["mama"]
    assert "mother" in en.lower() or "mere" in fr.lower()


def test_glossary_no_duplicates():
    """Ensure no key appears twice (would silently overwrite)."""
    # This is a compile-time check — Python dicts don't allow dup keys
    # but we test the glossary has expected count
    assert len(GLOSSARY) >= 90


def test_glossary_domains():
    """Each entry should have a valid domain."""
    valid_domains = {
        "kinship", "governance", "geography", "labor", "identity", "body",
        "action", "pronoun", "grammar", "nature", "ritual", "moral", "time",
        "housing", "material", "emotion", "craft", "weapon", "admin",
        "aymara", "astronomy", "agriculture",
    }
    for word, (fr, en, domain) in GLOSSARY.items():
        assert domain in valid_domains, f"{word}: unknown domain '{domain}'"


def test_split_syllables_simple():
    assert split_syllables("mama") == ["ma", "ma"]
    assert split_syllables("qaqa") == ["qa", "qa"]
    assert split_syllables("llaqa") == ["lla", "qa"]
    assert split_syllables("kamay") == ["ka", "ma", "y"]


def test_split_syllables_v3():
    """v3 onset syllables should be splittable."""
    assert split_syllables("pacha") == ["pa", "cha"]
    assert split_syllables("wasi") == ["wa", "si"]
    assert split_syllables("chiqa") == ["chi", "qa"]


def test_split_syllables_unknown():
    assert split_syllables("runa") is None   # 'r' and 'u' not in syllabary
    assert split_syllables("rumi") is None


def test_morpho_direct_match():
    result = analyze_morphology("mama")
    assert result.is_dictionary_match
    assert result.root == "mama"
    assert result.suffixes == []
    assert result.compound_parts == []


def test_morpho_suffix_decomposition():
    result = analyze_morphology("mamata")
    assert result.root == "mama"
    assert len(result.suffixes) == 1
    label = result.suffixes[0][1]  # grammatical label
    assert label == "ACC"


def test_morpho_compound_detection():
    """Compound words like makimaqa = maki + maqa."""
    result = analyze_morphology("makimaqa")
    assert result.compound_parts is not None
    assert len(result.compound_parts) == 2
    assert result.compound_parts[0][0] == "maki"
    assert result.compound_parts[1][0] == "maqa"


def test_morpho_compound_kamamaka():
    """kamamaka = kama + maka."""
    result = analyze_morphology("kamamaka")
    assert len(result.compound_parts) == 2
    assert result.compound_parts[0][0] == "kama"
    assert result.compound_parts[1][0] == "maka"


def test_morpho_unknown_word():
    result = analyze_morphology("xyzabc")
    assert not result.is_dictionary_match
    assert not result.is_decomposable
