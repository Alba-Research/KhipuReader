"""
Locke decimal positional system — the established numerical channel of khipus.

Simple knots (S-type) encode decimal values by their position on the cord:
  - Topmost cluster: thousands
  - Second cluster: hundreds
  - Third cluster: tens
  - Bottom cluster: units (encoded as long knots, but in INT cords only one)

Long knots in the units position encode 2-9 by their turn count.
Figure-eight knots in the units position encode 1.
A position with no knots encodes 0.

Reference: Locke, L. (1923). The Ancient Quipu, or Peruvian Knot Record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LockeValue:
    """A decoded Locke decimal value from a cord's simple knots."""
    value: int
    breakdown: dict[str, int]  # e.g. {'thousands': 1, 'hundreds': 2, ...}
    confidence: str  # 'exact', 'uniform_kvt', 'ambiguous'


def decode_locke_value(
    knots: list[dict],
    strict: bool = True,
) -> Optional[LockeValue]:
    """
    Decode a Locke decimal value from a list of knots on a single cord.

    Parameters
    ----------
    knots : list[dict]
        Knot records for a single cord, each with keys:
        'TYPE_CODE' (S/L/E), 'NUM_TURNS', 'CLUSTER_ORDINAL', 'KNOT_ORDINAL',
        'knot_value_type' (the positional value assigned by OKR).
    strict : bool
        If True, return None for cords with multiple L/E knots (STRING cords).

    Returns
    -------
    LockeValue or None
        The decoded decimal value, or None if the cord is not a valid INT cord.
    """
    if not knots:
        return None

    # Count terminal knots (L and E types)
    terminal_knots = [k for k in knots if k.get("TYPE_CODE") in ("L", "E")]
    simple_knots = [k for k in knots if k.get("TYPE_CODE") == "S"]

    # STRING detection: multiple terminal knots -> not a Locke number
    if strict and len(terminal_knots) > 1:
        return None

    # Sum the positional values (the OKR already computes these)
    total = 0
    breakdown = {"thousands": 0, "hundreds": 0, "tens": 0, "units": 0}

    for k in knots:
        val = k.get("knot_value_type", 0) or 0
        total += val

        if val >= 1000:
            breakdown["thousands"] += val
        elif val >= 100:
            breakdown["hundreds"] += val
        elif val >= 10:
            breakdown["tens"] += val
        else:
            breakdown["units"] += val

    # Detect uniform kvt (investigator didn't encode Locke positional values)
    # 158/479 khipus have all S-knots at the same kvt -> values are approximate
    s_kvts = {k.get("knot_value_type", 0) for k in simple_knots if k.get("knot_value_type")}
    if len(simple_knots) > 1 and len(s_kvts) == 1:
        confidence = "uniform_kvt"
    elif len(terminal_knots) <= 1:
        confidence = "exact"
    else:
        confidence = "ambiguous"

    return LockeValue(value=total, breakdown=breakdown, confidence=confidence)


def is_string_cord(knots: list[dict]) -> bool:
    """
    Determine if a cord carries STRING (textual) content.

    A cord is STRING if it has >= 2 terminal knots (long or figure-eight),
    which makes it incompatible with the Locke decimal system.

    This is the MULTI_TERMINAL criterion from Sivan (2026), Section 4.1:
    5.4% of knotted cords in the OKR meet this criterion.
    """
    terminal_count = sum(
        1 for k in knots if k.get("TYPE_CODE") in ("L", "E")
    )
    return terminal_count >= 2


def cord_type(knots: list[dict]) -> str:
    """
    Classify a cord as INT, STRING, or EMPTY.

    Returns
    -------
    str
        'STRING' -- >= 2 terminal knots (text candidate)
        'INT'    -- has knots but <= 1 terminal (standard Locke number)
        'EMPTY'  -- no knots at all
    """
    if not knots:
        return "EMPTY"
    if is_string_cord(knots):
        return "STRING"
    return "INT"
