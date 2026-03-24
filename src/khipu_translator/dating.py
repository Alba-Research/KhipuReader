"""
Khipu dating system — extract dates from the first pendant cords.

Two modes:
  Mode A (Explicit): C1 = year offset from epoch (~1438 CE), C2 = month (1-12),
                     C3 = day (1-30). For standalone official documents.
  Mode B (Checkbox): First 12 positions contain mostly zeros + one "10" tick mark.
                     The position of the "10" (1-indexed) = month.
                     For periodic registers where the year is archive context.

Reference: Sivan (2026), "Dating the Inca Archive."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from khipu_translator.translator import TranslationResult


# Reference epoch: Pachacutec's accession, start of Inca imperial expansion
DEFAULT_EPOCH = 1438

# Inca month names (Guaman Poma 1615), Month 1 = June (Pleiades rising)
INCA_MONTHS = {
    1:  ("Inti Raymi",      "June",      "Dry (harvest festival)"),
    2:  ("Chahua Huarquiz", "July",      "Dry"),
    3:  ("Yapaquis",        "August",    "Dry (planting prep)"),
    4:  ("Coya Raymi",      "September", "Transition"),
    5:  ("Uma Raymi",       "October",   "Wet (planting)"),
    6:  ("Ayamarca",        "November",  "Wet"),
    7:  ("Qhapaq Raymi",    "December",  "Wet (solstice)"),
    8:  ("Camay",           "January",   "Wet"),
    9:  ("Jatun Pucuy",     "February",  "Wet (rains peak)"),
    10: ("Pacha Pucuy",     "March",     "Transition"),
    11: ("Inca Raymi",      "April",     "Dry (harvest begins)"),
    12: ("Aymuray",         "May",       "Dry"),
}


@dataclass
class KhipuDate:
    """Extracted date from a khipu."""
    khipu_id: str
    mode: str                    # 'A' (explicit) or 'B' (checkbox) or 'AB' (both)
    year_offset: Optional[int]   # C1 value (offset from epoch)
    year_ce: Optional[int]       # absolute year (epoch + offset)
    month: Optional[int]         # 1-12 (Inca calendar, 1=June)
    day: Optional[int]           # 1-30 or None
    month_name: Optional[str]    # Inca month name
    gregorian_month: Optional[str]  # Gregorian equivalent
    season: Optional[str]        # Dry/Wet/Transition
    confidence: str              # 'high', 'medium', 'low'
    epoch: int                   # reference epoch used
    notes: str                   # explanation

    # Checkbox details
    checkbox_ticks: list[int]    # positions of "10" values (1-indexed)
    checkbox_double: bool        # True if 2 ticks (date range)


def extract_date(
    result: TranslationResult,
    epoch: int = DEFAULT_EPOCH,
) -> Optional[KhipuDate]:
    """
    Extract a date from a khipu's first pendant cords.

    Parameters
    ----------
    result : TranslationResult
        A translated khipu.
    epoch : int
        Reference epoch (default: 1438 CE).

    Returns
    -------
    KhipuDate or None
        The extracted date, or None if no date pattern detected.
    """
    # Get first 20 L1 cord RAW LOCKE values in order.
    # CRITICAL: for dating, use the raw Locke value (sum of ALL knot_value_type)
    # regardless of STRING/INT classification. A cord with 2 L-knots (turns=2+3)
    # has Locke value 5 even though it's classified as STRING. For dates, we
    # read the NUMBER, not the text.
    first_values = []
    first_types = []
    for cl in result.clusters:
        for c in cl.cords:
            if c.level == 1:
                # Use locke_value if available (INT cords)
                # For STRING cords, compute raw Locke from s_prefix + locke
                # For EMPTY cords, value is 0
                if c.cord_type == "EMPTY":
                    first_values.append(0)
                    first_types.append("EMPTY")
                elif c.locke_value is not None:
                    first_values.append(int(c.locke_value))
                    first_types.append(c.cord_type)
                elif c.cord_type == "STRING":
                    # STRING cord: the Locke value is the S-prefix
                    # BUT we also need the L-knot turn values summed
                    # The translator stores s_prefix but not the L-knot sum
                    # We need to compute it from knot_sequence
                    raw_val = c.s_prefix  # S-knot contribution
                    # Parse knot_sequence to get L-knot values
                    # Format: "L3 L4" or "S10 L6 E" etc.
                    if c.knot_sequence:
                        for part in c.knot_sequence.split():
                            if part.startswith("L") and part[1:].isdigit():
                                raw_val += int(part[1:])
                            elif part == "E":
                                raw_val += 1  # figure-8 = 1 in Locke
                    first_values.append(raw_val if raw_val > 0 else 0)
                    first_types.append("STRING")
                else:
                    first_values.append(0)
                    first_types.append("OTHER")
            if len(first_values) >= 20:
                break
        if len(first_values) >= 20:
            break

    if len(first_values) < 3:
        return None

    # Try Mode A (Explicit)
    mode_a = _try_mode_a(first_values, first_types, epoch)

    # Try Mode B (Checkbox)
    mode_b = _try_mode_b(first_values, first_types, epoch)

    # Return best result
    if mode_a and mode_b:
        # Both modes detected — combine
        mode_a.mode = "AB"
        if mode_a.month is None and mode_b.month is not None:
            mode_a.month = mode_b.month
            _fill_month_info(mode_a)
        mode_a.checkbox_ticks = mode_b.checkbox_ticks
        mode_a.checkbox_double = mode_b.checkbox_double
        mode_a.notes += f" Checkbox confirms month {mode_b.month}."
        return mode_a
    elif mode_a:
        return mode_a
    elif mode_b:
        return mode_b

    return None


def _try_mode_a(
    values: list,
    types: list,
    epoch: int,
) -> Optional[KhipuDate]:
    """
    Try Mode A (v4): explicit year/month/day.

    Rules:
      YEAR: first non-round INT (13-100) in positions 0-2
      MONTH: next INT 1-12 after year (skip STRING cords, max 3 positions forward)
      DAY: next INT 1-30 after month (optional)
      CONFIDENCE: HIGH if month != 10, MEDIUM if month == 10
    """
    # Step 1: find YEAR in positions 0-2
    year_val = None
    year_pos = None
    for i in range(min(3, len(values))):
        v = values[i]
        if v is not None and isinstance(v, int) and 13 <= v <= 100 and v % 10 != 0:
            year_val = v
            year_pos = i
            break

    if year_val is None:
        return None

    # Step 2: find MONTH after year (max 3 positions forward)
    # DO NOT skip STRING — their raw Locke value may be the month
    month_val = None
    month_pos = None
    for offset in range(1, 4):
        pos = year_pos + offset
        if pos >= len(values):
            break
        v = values[pos]
        if v is not None and isinstance(v, int) and 1 <= v <= 12:
            month_val = v
            month_pos = pos
            break

    if month_val is None:
        return None

    # Step 3: find DAY after month (next position, optional)
    day_val = None
    if month_pos is not None:
        day_pos = month_pos + 1
        if day_pos < len(values):
            v = values[day_pos]
            if v is not None and isinstance(v, int) and 1 <= v <= 30:
                day_val = v

    year_ce = epoch + year_val

    # Confidence: HIGH if month != 10, MEDIUM if month == 10
    # (month 10 = value 10 = ambiguous with tick mark)
    confidence = "HIGH" if month_val != 10 else "MEDIUM"

    notes = f"Mode A (v4): year={year_val} (pos {year_pos}), month={month_val} (pos {month_pos})"
    if day_val:
        notes += f", day={day_val}"

    date = KhipuDate(
        khipu_id="",
        mode="A",
        year_offset=year_val,
        year_ce=year_ce,
        month=month_val,
        day=day_val,
        month_name=None,
        gregorian_month=None,
        season=None,
        confidence=confidence,
        epoch=epoch,
        notes=notes,
        checkbox_ticks=[],
        checkbox_double=False,
    )
    _fill_month_info(date)
    return date


def _try_mode_b(
    values: list,
    types: list,
    epoch: int,
) -> Optional[KhipuDate]:
    """
    Try Mode B (v4): checkbox pattern.

    Scan first 12 positions for a lone non-zero value among zeros/STRING.
    The non-zero value should be >= 10 (a tick mark).
    Position (1-indexed) = month.
    """
    if len(values) < 6:
        return None

    # Don't apply checkbox if Mode A already found a clear year
    # (avoid double-counting)
    for i in range(min(3, len(values))):
        v = values[i]
        if v is not None and isinstance(v, int) and 13 <= v <= 100 and v % 10 != 0:
            return None  # Mode A handles this khipu

    # Scan first 12 positions
    n_scan = min(12, len(values))
    ticks = []
    for i in range(n_scan):
        v = values[i]
        t = types[i]
        # A tick is a non-zero INT value (typically 10, but could be other)
        if v is not None and isinstance(v, int) and v > 0 and t == "INT":
            ticks.append((i + 1, v))  # (position 1-indexed, value)

    if len(ticks) == 0:
        return None

    # Check sparsity: most positions should be 0 or STRING
    n_zero_or_string = sum(
        1 for i in range(n_scan)
        if values[i] is None or values[i] == 0 or types[i] in ("STRING", "EMPTY")
    )
    sparsity = n_zero_or_string / n_scan

    if sparsity < 0.6:
        return None  # too many non-zero values = not a checkbox

    # Single tick
    if len(ticks) == 1:
        month = ticks[0][0]
        tick_val = ticks[0][1]
        confidence = "HIGH" if tick_val == 10 and sparsity >= 0.8 else "MEDIUM"

        date = KhipuDate(
            khipu_id="",
            mode="B",
            year_offset=None,
            year_ce=None,
            month=month,
            day=None,
            month_name=None,
            gregorian_month=None,
            season=None,
            confidence=confidence,
            epoch=epoch,
            notes=f"Mode B: checkbox tick={tick_val} at position {month} (sparsity {sparsity:.0%})",
            checkbox_ticks=[month],
            checkbox_double=False,
        )
        _fill_month_info(date)
        return date

    # Double tick (date range)
    if len(ticks) == 2:
        m1 = ticks[0][0]
        m2 = ticks[1][0]

        date = KhipuDate(
            khipu_id="",
            mode="B",
            year_offset=None,
            year_ce=None,
            month=m1,
            day=None,
            month_name=None,
            gregorian_month=None,
            season=None,
            confidence="MEDIUM",
            epoch=epoch,
            notes=f"Mode B: double tick at positions {m1} and {m2} (range months {m1}-{m2})",
            checkbox_ticks=[m1, m2],
            checkbox_double=True,
        )
        _fill_month_info(date)
        return date

    # Triple+ ticks — too many, probably not a date
    return None


def _fill_month_info(date: KhipuDate) -> None:
    """Fill in month name, Gregorian equivalent, and season."""
    if date.month and date.month in INCA_MONTHS:
        name, greg, season = INCA_MONTHS[date.month]
        date.month_name = name
        date.gregorian_month = greg
        date.season = season


def format_date(date: KhipuDate) -> str:
    """Format a KhipuDate for display."""
    lines = []

    if date.year_ce and date.month:
        day_str = f"/{date.day:02d}" if date.day else ""
        lines.append(f"  Date: {date.year_ce}/{date.month:02d}{day_str} CE")
    elif date.month:
        lines.append(f"  Month: {date.month}")

    if date.month_name:
        lines.append(f"  Inca month: {date.month_name} ({date.gregorian_month}, {date.season})")

    if date.year_offset:
        lines.append(f"  Year offset: {date.year_offset} from epoch {date.epoch}")

    lines.append(f"  Mode: {date.mode} ({_mode_desc(date.mode)})")
    lines.append(f"  Confidence: {date.confidence}")
    lines.append(f"  {date.notes}")

    if date.checkbox_ticks:
        lines.append(f"  Checkbox ticks: positions {date.checkbox_ticks}")

    return "\n".join(lines)


def _mode_desc(mode: str) -> str:
    if mode == "A":
        return "explicit year/month/day"
    elif mode == "B":
        return "checkbox month indicator"
    elif mode == "AB":
        return "explicit + checkbox"
    return mode
