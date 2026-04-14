"""Tests for the merged OKR × KFG corpus.

These tests exercise the corpus built by ``scripts/merge_okr_kfg.py``.
They are *integration* tests: they rely on the existence of
``data/merged/*.json`` + ``merged_corpus.sqlite`` at the repo root, and
will be skipped (with a clear reason) if the corpus has not been built.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from khipu_translator.corpus import MergedCorpus, DEFAULT_MERGED_DIR, DEFAULT_SQLITE


pytestmark = pytest.mark.skipif(
    not DEFAULT_SQLITE.exists(),
    reason="merged corpus not built — run scripts/merge_okr_kfg.py",
)


@pytest.fixture(scope="module")
def corpus():
    c = MergedCorpus()
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Structural sanity
# ---------------------------------------------------------------------------

def test_corpus_has_many_khipus(corpus):
    assert len(corpus.list_kh_ids()) > 500  # ≈ 704 in production


def test_resolve_known_aliases(corpus):
    assert corpus.resolve_kh_id("UR052") == "KH0282"
    assert corpus.resolve_kh_id("UR278") == "KH0517"
    assert corpus.resolve_kh_id("KH0282") == "KH0282"


def test_unknown_alias_returns_none(corpus):
    assert corpus.resolve_kh_id("ZZ9999") is None


# ---------------------------------------------------------------------------
# UR052 — high-agreement flagship
# ---------------------------------------------------------------------------

def test_ur052_agreement(corpus):
    """UR052 (KH0282) should have > 90 % AGREED cords in its twinned cords."""
    rec = corpus.load("UR052")
    assert rec["kh_id"] == "KH0282"
    assert rec["sources"]["okr"] and rec["sources"]["kfg"]
    q = corpus.quality_stats("KH0282")
    agreed = q.get("AGREED", 0) + q.get("ASCHER_VALIDATED", 0)
    # twinned cord population (excluding OKR-only subsidiaries)
    twinned = agreed + q.get("DIVERGENT", 0) + q.get("KFG_RESOLVED", 0)
    assert twinned > 0
    assert agreed / twinned > 0.90


def test_ur052_has_27_sums(corpus):
    rec = corpus.load("UR052")
    assert len(rec["ascher_sums"]) == 27


# ---------------------------------------------------------------------------
# UR278 — heavy L? resolution via KFG
# ---------------------------------------------------------------------------

def test_ur278_l_unknown_resolution(corpus):
    """UR278 (KH0517) should have ≥ 150 KFG_RESOLVED cords (OKR L? → KFG value)."""
    q = corpus.quality_stats("KH0517")
    assert q.get("KFG_RESOLVED", 0) >= 150


def test_ur278_sample_repair(corpus):
    """Sample check: KH0517 p72 had L? in OKR; KFG resolves it to turn=7."""
    rec = corpus.load("KH0517")
    p72 = next(c for c in rec["cords"] if c.get("cord_num") == 72)
    assert p72["quality"] == "KFG_RESOLVED"
    assert p72.get("long_knot_turns") == [7]
    assert p72["locke_value"]["merged"] == 117.0


# ---------------------------------------------------------------------------
# Ascher validation
# ---------------------------------------------------------------------------

def test_ascher_validated_exists(corpus):
    """ASCHER_VALIDATED is a defined quality — should have > 0 such cords."""
    rows = corpus.sql(
        "SELECT COUNT(*) AS n FROM cords WHERE quality='ASCHER_VALIDATED'"
    )
    assert rows[0]["n"] > 0


# ---------------------------------------------------------------------------
# No data loss
# ---------------------------------------------------------------------------

def test_no_okr_khipu_lost():
    """Every OKR khipu appears in the merged corpus (twinned or synthesised)."""
    c = MergedCorpus()
    try:
        from khipu_translator.database import KhipuDB
        db = KhipuDB()
        try:
            okr_nums = db.list_khipus()["INVESTIGATOR_NUM"].tolist()
        finally:
            db.close()
    except Exception:
        pytest.skip("OKR database not available")

    missing = []
    for inv in okr_nums:
        if not isinstance(inv, str):
            continue
        if c.resolve_kh_id(inv) is None:
            missing.append(inv)
    c.close()
    assert len(missing) == 0, f"OKR khipus missing from merged corpus: {missing[:10]}"


def test_cord_counts_are_positive(corpus):
    """Every khipu in the corpus has at least one cord row."""
    rows = corpus.sql("SELECT kh_id, n_cords FROM khipus WHERE n_cords = 0")
    assert rows == []


# ---------------------------------------------------------------------------
# Divergences file
# ---------------------------------------------------------------------------

def test_divergences_csv_schema():
    """divergences.csv must exist and have the expected header."""
    path = DEFAULT_MERGED_DIR / "divergences.csv"
    assert path.exists()
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == [
        "kh_id", "aliases", "cord_num", "kfg_id",
        "locke_okr", "locke_kfg", "knots_okr", "knots_kfg",
    ]


def test_divergent_cords_accounted_for(corpus):
    """Every DIVERGENT cord in the SQLite should appear in divergences.csv."""
    path = DEFAULT_MERGED_DIR / "divergences.csv"
    assert path.exists()
    csv_count = sum(1 for _ in csv.reader(path.open(encoding="utf-8"))) - 1
    rows = corpus.sql(
        "SELECT COUNT(*) AS n FROM cords WHERE quality='DIVERGENT'"
    )
    sql_count = rows[0]["n"]
    assert csv_count == sql_count


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def test_merge_report_exists():
    path = DEFAULT_MERGED_DIR / "merge_report.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    for section in ("Corpus", "Cord quality distribution", "Credits"):
        assert section in content
