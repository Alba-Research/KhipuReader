"""Tests for the Ascher structural layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from khipu_translator.ascher import (
    AscherGraph,
    AscherSum,
    CordParse,
    KFGClient,
    KhipuData,
    ROLE_BOTH,
    ROLE_DATA,
    ROLE_FREE,
    ROLE_HEADER,
    parse_khipu_xlsx,
    parse_knots,
    parse_sums_html,
    resolve_cord,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "kfg_cache"


# ---------------------------------------------------------------------------
# parse_knots — pure-function tests, no fixtures needed
# ---------------------------------------------------------------------------

def test_parse_knots_empty():
    cp = parse_knots("")
    assert cp.cord_type == "EMPTY"
    assert cp.locke_value == 0
    assert cp.n_long == 0


def test_parse_knots_none():
    cp = parse_knots(None)
    assert cp.cord_type == "EMPTY"


def test_parse_knots_single_l():
    # One long knot, 4 turns, value 4 -> INT, not STRING
    cp = parse_knots("4L(10.0,S),4")
    assert cp.cord_type == "INT"
    assert cp.n_long == 1
    assert cp.long_turns == [4]
    assert cp.locke_value == 4
    assert cp.l_value_total == 4
    assert cp.s_value_total == 0


def test_parse_knots_multi_l_is_string():
    # Four long knots - STRING classification
    cp = parse_knots("4L(16.0,S),4;4L(31.5,S),4;5L(41.0,S),5;7L(66.0,S),7")
    assert cp.cord_type == "STRING"
    assert cp.n_long == 4
    assert cp.long_turns == [4, 4, 5, 7]
    assert cp.locke_value == 20


def test_parse_knots_positional_decimal():
    # S-knots encode tens/hundreds, L-knots encode units. INT cord, value 46.
    cp = parse_knots("3S(7.0,Z),30;1S(14.0,Z),10;6L(23.5,Z),6")
    assert cp.cord_type == "INT"
    assert cp.locke_value == 46
    assert cp.s_value_total == 40
    assert cp.l_value_total == 6
    assert cp.n_simple == 2
    assert cp.n_long == 1


def test_parse_knots_figure_eight():
    # One figure-eight => INT
    cp = parse_knots("1E(24.0,Z),1")
    assert cp.cord_type == "INT"
    assert cp.n_eight == 1
    assert cp.e_value_total == 1


def test_parse_knots_two_eights_is_string():
    cp = parse_knots("1E(10.0,Z),1;1E(20.0,Z),1")
    assert cp.cord_type == "STRING"
    assert cp.n_eight == 2


# ---------------------------------------------------------------------------
# KhipuData / parse_khipu_xlsx — uses cached UR052 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def ur052_xlsx() -> Path:
    path = FIXTURE_DIR / "KH0282.xlsx"
    assert path.exists(), f"fixture missing: {path}"
    return path


@pytest.fixture
def ur052_sums_html() -> str:
    path = FIXTURE_DIR / "KH0282_sums.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def ur052_kd(ur052_xlsx) -> KhipuData:
    return parse_khipu_xlsx(ur052_xlsx, "KH0282")


@pytest.fixture
def ur052_sums(ur052_sums_html) -> list[AscherSum]:
    return parse_sums_html(ur052_sums_html, "KH0282")


def test_ur052_alias(ur052_kd):
    assert ur052_kd.alias == "UR052"


def test_ur052_cord_count(ur052_kd):
    # 98 rows in the Cords sheet for KH0282.
    assert len(ur052_kd.cords) == 98


def test_ur052_group_count(ur052_kd):
    # UR052 is laid out in 25 groups of 4 pendants each (= 100 slots,
    # some may be empty / not fully loaded in the xlsx).
    assert len(ur052_kd.groups) >= 20


def test_resolve_cord_pn_semantics(ur052_kd):
    # Group 2 starts at p5 (after a first group of 4 pendants). g2p3 -> p7.
    row = resolve_cord(ur052_kd, 2, 3)
    assert row is not None
    assert row["_cord_name"] == "p7"
    assert row["_index"] == 7   # physical position proxy
    assert row["_group"] == 2


def test_resolve_cord_out_of_range(ur052_kd):
    assert resolve_cord(ur052_kd, 2, 99) is None
    assert resolve_cord(ur052_kd, 999, 1) is None


def test_ur052_sum_count(ur052_sums):
    # 27 pendant-pendant sums on UR052.
    assert len(ur052_sums) == 27


def test_ur052_first_sum(ur052_sums):
    # First sum in the right-handed table: g2p3 : 29 = g10p3 + g11p1 + g11p2
    first = ur052_sums[0]
    assert first.hand == "right"
    assert (first.sum_group, first.sum_pos, first.sum_value) == (2, 3, 29.0)
    assert len(first.summands) == 3


def test_ur052_has_both_hands(ur052_sums):
    hands = {s.hand for s in ur052_sums}
    assert hands == {"right", "left"}


# ---------------------------------------------------------------------------
# AscherGraph — structural queries
# ---------------------------------------------------------------------------

@pytest.fixture
def ur052_graph(ur052_kd, ur052_sums) -> AscherGraph:
    return AscherGraph("KH0282", ur052_kd, ur052_sums)


def test_graph_resolves_all_sums(ur052_graph):
    assert len(ur052_graph.relations) == 27


def test_graph_roles(ur052_graph):
    # g2p3 -> p7 is a sum cord (HEADER)
    assert ur052_graph.get_role("p7") == ROLE_HEADER
    # g10p3 -> p(start_g10)+3-1 is a summand of p7 (DATA)
    # Compute its pendant number from the fixture:
    summands = ur052_graph.get_summands("p7")
    assert len(summands) == 3
    for s in summands:
        role = ur052_graph.get_role(s)
        # Some summands are themselves cascade intermediates (BOTH) on UR052
        assert role in {ROLE_DATA, ROLE_BOTH}


def test_graph_free_cords(ur052_graph):
    # p1 is the very first pendant, not involved in any sum
    assert ur052_graph.get_role("p1") == ROLE_FREE


def test_graph_sum_value(ur052_graph):
    assert ur052_graph.get_sum_value("p7") == 29.0


def test_graph_sum_hand(ur052_graph):
    assert ur052_graph.get_sum_hand("p7") == "right"


def test_graph_referenced_by(ur052_graph):
    # The first summand of p7 ought to record p7 as a referencer
    summs = ur052_graph.get_summands("p7")
    for s in summs:
        assert "p7" in ur052_graph.get_sums_referencing(s)


def test_graph_cascade_depth(ur052_graph):
    # UR052 has cascades up to depth 2 (somme de sommes)
    assert ur052_graph.max_cascade_depth() >= 2


def test_graph_is_dag(ur052_graph):
    # No cycles expected in KFG data
    import networkx as nx
    assert nx.is_directed_acyclic_graph(ur052_graph.graph)


# ---------------------------------------------------------------------------
# verify_sum + validate_mapping — integrity checks
# ---------------------------------------------------------------------------

def test_verify_sum_holds(ur052_graph, ur052_kd):
    # Build {cord_name: locke_value} from the xlsx
    vals = {}
    for _, row in ur052_kd.cords.iterrows():
        name = row.get("Cord_Name")
        v = row.get("Value")
        if isinstance(name, str) and v is not None:
            vals[name] = float(v)
    # Pick the first sum cord — the checksum must hold by construction
    first_sum = ur052_graph.relations[0].sum_cord
    assert ur052_graph.verify_sum(first_sum, vals) is True


def test_verify_sum_fails_on_tampering(ur052_graph, ur052_kd):
    vals = {}
    for _, row in ur052_kd.cords.iterrows():
        name = row.get("Cord_Name")
        v = row.get("Value")
        if isinstance(name, str) and v is not None:
            vals[name] = float(v)
    first = ur052_graph.relations[0]
    # Corrupt one summand
    vals[first.summands[0]] = vals[first.summands[0]] + 100
    assert ur052_graph.verify_sum(first.sum_cord, vals) is False


def test_verify_sum_unknown_returns_none(ur052_graph):
    assert ur052_graph.verify_sum("p99999", {}) is None


def test_validate_mapping_perfect(ur052_graph, ur052_kd):
    """If OKR values match KFG exactly, mismatch_ratio is 0."""
    vals = {}
    for _, row in ur052_kd.cords.iterrows():
        name = row.get("Cord_Name")
        v = row.get("Value")
        if isinstance(name, str) and v is not None:
            vals[name] = float(v)
    ratio, mism = ur052_graph.validate_mapping(vals)
    assert ratio == 0.0
    assert mism == []


def test_validate_mapping_detects_divergence(ur052_graph, ur052_kd):
    vals = {}
    for _, row in ur052_kd.cords.iterrows():
        name = row.get("Cord_Name")
        v = row.get("Value")
        if isinstance(name, str) and v is not None:
            vals[name] = float(v)
    # Break one value
    some_cord = next(iter(vals))
    vals[some_cord] = vals[some_cord] + 42
    ratio, mism = ur052_graph.validate_mapping(vals)
    assert ratio > 0.0
    assert some_cord in mism


# ---------------------------------------------------------------------------
# AscherGraph.from_kfg — end-to-end using the file-backed cache
# ---------------------------------------------------------------------------

def test_from_kfg_uses_cache_only():
    """Pointing KFGClient at the fixture dir must never touch the network."""
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    g = AscherGraph.from_kfg("KH0282", client=client)
    assert g.kh_id == "KH0282"
    assert len(g.relations) == 27


# ---------------------------------------------------------------------------
# apply_ascher_constraints — Pass 2 wrapper on a real TranslationResult
# ---------------------------------------------------------------------------

def test_apply_wrapper_non_regression():
    """Without invoking the wrapper, cord.ascher is None and to_dict omits it."""
    from khipu_translator.translator import translate
    r = translate("UR052")
    assert all(c.ascher is None for c in r.cords)
    d = r.cords[0].to_dict()
    assert "ascher" not in d


def test_apply_wrapper_annotates_cords():
    """On UR052 (KH0282), the wrapper annotates exactly the 27 sum-cords and
    their summands. Roles split into HEADER / DATA / BOTH with no leakage."""
    from khipu_translator.ascher import apply_ascher_constraints
    from khipu_translator.translator import translate
    r = translate("UR052")
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)

    n_header = sum(1 for c in r.cords if c.ascher and c.ascher.role == ROLE_HEADER)
    n_data   = sum(1 for c in r.cords if c.ascher and c.ascher.role == ROLE_DATA)
    n_both   = sum(1 for c in r.cords if c.ascher and c.ascher.role == ROLE_BOTH)
    # 27 sum relations → 23 pure HEADERs + 4 BOTH (intermediates)
    assert n_header + n_both == 27
    # Every annotated cord has a known role
    assert all(c.ascher.role in {ROLE_HEADER, ROLE_DATA, ROLE_BOTH}
               for c in r.cords if c.ascher)


def test_apply_wrapper_verifies_checksums():
    """On UR052, ≥25 of the 27 HEADER-or-BOTH cords pass arithmetic verification."""
    from khipu_translator.ascher import apply_ascher_constraints
    from khipu_translator.translator import translate
    r = translate("UR052")
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)

    header_cords = [c for c in r.cords if c.ascher and c.ascher.role in {ROLE_HEADER, ROLE_BOTH}]
    verified = sum(1 for c in header_cords if c.ascher.verified is True)
    assert verified >= 25, f"only {verified}/{len(header_cords)} sum-cords verified"


def test_apply_wrapper_preserves_v1_fields():
    """Annotation must NEVER mutate v1 fields (cord_type, reading, confidences)."""
    from khipu_translator.ascher import apply_ascher_constraints
    from khipu_translator.translator import translate
    before = translate("UR052")
    snapshot = [
        (c.cord_id, c.cord_type, c.locke_value, c.alba_reading,
         c.alba_confidence, c.alba_confirmed)
        for c in before.cords
    ]
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(before, graph)
    after = [
        (c.cord_id, c.cord_type, c.locke_value, c.alba_reading,
         c.alba_confidence, c.alba_confirmed)
        for c in before.cords
    ]
    assert before_matches_after(snapshot, after)


def before_matches_after(a, b) -> bool:
    if len(a) != len(b):
        return False
    return all(x == y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# apply_reclassification — Pass 3A
# ---------------------------------------------------------------------------

def test_reclassify_ur052_four_number_cords():
    """UR052 has 4 single-L INT summands in STRING context -> reclassified."""
    from khipu_translator.ascher import (
        apply_ascher_constraints, apply_reclassification,
    )
    from khipu_translator.translator import translate
    r = translate("UR052")
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)
    apply_reclassification(r, graph)

    recl = [c for c in r.cords
            if c.ascher and c.ascher.reclassified_cord_type == "STRING"]
    assert len(recl) == 4
    readings = {c.ascher.reclassified_reading for c in recl}
    # Exactly the four single-L syllables: L4=ka L5=ta L3=ma
    assert readings == {"ka", "ta", "ma"}
    # Every reclassification must carry a reason with context info
    assert all("STRING context" in c.ascher.reclassified_reason for c in recl)


def test_reclassify_preserves_cord_type():
    """Reclassification writes to a parallel field; cord_type must NOT change."""
    from khipu_translator.ascher import (
        apply_ascher_constraints, apply_reclassification,
    )
    from khipu_translator.translator import translate
    r = translate("UR052")
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)
    apply_reclassification(r, graph)
    for c in r.cords:
        if c.ascher and c.ascher.reclassified_cord_type:
            # The original cord_type field is left untouched.
            assert c.cord_type == "INT"


def test_constraint_propagation_runs_cleanly():
    """On UR052 the reader matches all KFG values -> zero propagations."""
    from khipu_translator.ascher import (
        apply_ascher_constraints, apply_constraint_propagation,
    )
    from khipu_translator.translator import translate
    r = translate("UR052")
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)
    apply_constraint_propagation(r, graph)
    assert r.stats.get("ascher_propagated") == 0


def test_pure_arithmetic_repair_runs():
    """Pass 3D runs cleanly on UR052 — all cords readable, so 0 repairs."""
    from khipu_translator.ascher import (
        apply_ascher_constraints, apply_pure_arithmetic_repair,
    )
    from khipu_translator.translator import translate
    r = translate("UR052")
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)
    apply_pure_arithmetic_repair(r, graph)
    assert r.stats.get("ascher_repaired") == 0
    # No L? cords in UR052 → no candidates
    assert r.stats.get("ascher_repair_unresolved") == 0


def test_pure_arithmetic_repair_preserves_v1():
    """Pass 3D must not mutate cord.cord_type / alba_reading / locke_value."""
    from khipu_translator.ascher import (
        apply_ascher_constraints, apply_pure_arithmetic_repair,
    )
    from khipu_translator.translator import translate
    r = translate("UR052")
    snapshot = [(c.cord_id, c.cord_type, c.locke_value, c.alba_reading) for c in r.cords]
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)
    apply_pure_arithmetic_repair(r, graph)
    after = [(c.cord_id, c.cord_type, c.locke_value, c.alba_reading) for c in r.cords]
    assert snapshot == after


def test_reclassify_stats_written():
    """apply_reclassification writes an 'ascher_reclassified' count into stats."""
    from khipu_translator.ascher import (
        apply_ascher_constraints, apply_reclassification,
    )
    from khipu_translator.translator import translate
    r = translate("UR052")
    client = KFGClient(cache_dir=FIXTURE_DIR, delay_s=0.0)
    graph = AscherGraph.from_kfg("KH0282", client=client)
    apply_ascher_constraints(r, graph)
    apply_reclassification(r, graph)
    assert r.stats.get("ascher_reclassified") == 4
