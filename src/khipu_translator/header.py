"""
Header analysis — decode the "identity card" of a khipu.

The first cluster of a khipu acts as a document cover:
  - Color = document type signal (LB=oracle, AB=identity, W=data, LK=judicial)
  - STRING words = toponym or section labels
  - Size = format indicator (1=summary, 4-6=standard register)
  - Numerical values = totals or period markers

This is not a sequential numbering system — it's a visual faceted
classification: color + first word + cluster size.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from khipu_translator.translator import TranslationResult, CordTranslation

# Color -> likely document purpose (based on cross-corpus analysis)
HEADER_COLOR_SIGNALS: dict[str, str] = {
    "LB": "oracle / interrogative",
    "AB": "identity / subject declaration",
    "W":  "data / tribute register",
    "LK": "judicial / governance text",
    "MB": "category / administrative",
    "KB": "data / accounting",
    "GG": "identity / justice / sacred",
    "DB": "objects / narrative",
    "LC": "ritual / ceremony",
    "FB": "action / verb-heavy",
    "B":  "geographic / cadastral",
    "YB": "special marker",
}


@dataclass
class KhipuHeader:
    """The 'identity card' decoded from the first cluster."""
    khipu_id: str
    provenance: Optional[str]
    museum: Optional[str]

    # First cluster analysis
    header_size: int              # number of cords in first cluster
    header_colors: list[str]      # colors of header cords
    dominant_color: str           # most frequent color
    color_signal: str             # what the color suggests

    # Content
    header_words: list[str]       # STRING readings in header
    header_glosses: list[str]     # glosses of those words
    header_values: list[int]      # INT values in header
    has_toponym: bool             # starts with qa- word (place name)
    toponym: Optional[str]        # the toponym if any

    # Structural
    header_differs_from_body: bool  # is header structurally different?
    body_cluster_mode: int          # typical body cluster size
    total_cords: int
    document_type: str
    architecture: str

    # Special signals
    has_s0: bool                  # explicit zero (death/absence signal)
    has_label_header: bool        # header contains section labels (like UR006)
    s_prefix_sum: int             # total S-prefix in header


def analyze_header(result: TranslationResult, lang: str = "en") -> KhipuHeader:
    """
    Analyze the first cluster of a khipu as its 'identity card'.

    Parameters
    ----------
    result : TranslationResult
        A translated khipu.
    lang : str
        Language for glosses.

    Returns
    -------
    KhipuHeader
    """
    clusters = result.clusters
    if not clusters:
        return _empty_header(result)

    first = clusters[0]
    body = clusters[1:] if len(clusters) > 1 else []

    # Header cords
    header_colors = [c.color.strip() for c in first.cords]
    from collections import Counter
    color_counts = Counter(header_colors)
    dominant = color_counts.most_common(1)[0][0] if color_counts else "?"
    color_signal = HEADER_COLOR_SIGNALS.get(dominant, "unknown")

    # Words and values
    header_words = []
    header_glosses = []
    header_values = []
    has_s0 = False
    s_prefix_sum = 0

    for c in first.cords:
        if c.alba_reading:
            header_words.append(c.alba_reading)
            header_glosses.append(result._gloss(c.alba_reading, lang))
            s_prefix_sum += c.s_prefix
        elif c.locke_value is not None:
            header_values.append(int(c.locke_value))
        if "S0" in c.knot_sequence:
            has_s0 = True

    # Toponym detection (qa- words = place names)
    toponym = None
    has_toponym = False
    qa_words = {"qaqa", "kaqa", "taqa", "paqa", "naqa", "siqa", "piqa",
                "qama", "chiqa", "waqa"}
    for w in header_words:
        if w in qa_words or w.startswith("qa") or w.endswith("qa"):
            has_toponym = True
            toponym = w
            break

    # Does header differ from body?
    body_sizes = [len(cl.cords) for cl in body if len(cl.cords) > 1]
    body_mode = Counter(body_sizes).most_common(1)[0][0] if body_sizes else 0
    header_differs = len(first.cords) != body_mode if body_mode > 0 else False

    # Label header: multiple STRING words in header = section labels
    has_label_header = len(header_words) >= 3

    return KhipuHeader(
        khipu_id=result.khipu.investigator_num,
        provenance=result.khipu.provenance,
        museum=result.khipu.museum_name,
        header_size=len(first.cords),
        header_colors=header_colors,
        dominant_color=dominant,
        color_signal=color_signal,
        header_words=header_words,
        header_glosses=header_glosses,
        header_values=header_values,
        has_toponym=has_toponym,
        toponym=toponym,
        header_differs_from_body=header_differs,
        body_cluster_mode=body_mode,
        total_cords=result.stats["total_cords"],
        document_type=result.document_type,
        architecture=result.architecture,
        has_s0=has_s0,
        has_label_header=has_label_header,
        s_prefix_sum=s_prefix_sum,
    )


def _empty_header(result: TranslationResult) -> KhipuHeader:
    """Return an empty header for khipus with no clusters."""
    return KhipuHeader(
        khipu_id=result.khipu.investigator_num,
        provenance=result.khipu.provenance,
        museum=result.khipu.museum_name,
        header_size=0, header_colors=[], dominant_color="?",
        color_signal="unknown", header_words=[], header_glosses=[],
        header_values=[], has_toponym=False, toponym=None,
        header_differs_from_body=False, body_cluster_mode=0,
        total_cords=result.stats["total_cords"],
        document_type=result.document_type,
        architecture=result.architecture,
        has_s0=False, has_label_header=False, s_prefix_sum=0,
    )


def format_header(h: KhipuHeader) -> str:
    """Format a KhipuHeader for display."""
    lines = [
        f"{'=' * 60}",
        f"  {h.khipu_id} — Document Identity Card",
        f"{'=' * 60}",
        f"  Provenance: {h.provenance or 'Unknown'}",
        f"  Museum: {h.museum or 'Unknown'}",
        f"  Document type: {h.document_type}",
        f"  Architecture: {h.architecture}",
        f"  Total cords: {h.total_cords}",
        "",
        f"  HEADER (first cluster: {h.header_size} cords)",
        f"  {'─' * 40}",
        f"  Dominant color: {h.dominant_color} = {h.color_signal}",
        f"  Colors: {' '.join(h.header_colors)}",
    ]

    if h.header_words:
        word_str = ", ".join(
            f"{w} ({g})" if g else w
            for w, g in zip(h.header_words, h.header_glosses)
        )
        lines.append(f"  Words: {word_str}")

    if h.has_toponym:
        lines.append(f"  Toponym: {h.toponym} (place name in header)")

    if h.header_values:
        lines.append(f"  Values: {h.header_values}")
        lines.append(f"  Sum: {sum(h.header_values)}")

    lines.append("")

    if h.has_s0:
        lines.append("  !! S0 signal: explicit zero (death/absence marker)")

    if h.has_label_header:
        lines.append(f"  Label header: {len(h.header_words)} section labels")

    if h.header_differs_from_body:
        lines.append(
            f"  Header differs from body: header={h.header_size} cords, "
            f"body mode={h.body_cluster_mode}"
        )
    else:
        lines.append("  Header matches body structure")

    if h.s_prefix_sum:
        lines.append(f"  Numerical prefix in header: {h.s_prefix_sum}")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)
