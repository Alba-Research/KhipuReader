"""
Submit — generate a JSON contribution template for a khipu.

Pre-fills the template with auto-translation results.
The contributor fills in: summary, interpretation, confidence, references.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Optional

from khipu_translator.database import KhipuDB
from khipu_translator.translator import translate


CONTRIBUTIONS_DIR = Path(__file__).parent.parent.parent / "contributions"


def generate_contribution(
    khipu_name: str,
    db: Optional[KhipuDB] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Generate a JSON contribution template for a khipu.

    Parameters
    ----------
    khipu_name : str
        Khipu ID (e.g. 'UR039').
    db : KhipuDB, optional
        Database connection.
    output_dir : Path, optional
        Where to save. Default: contributions/

    Returns
    -------
    Path to the generated JSON file.
    """
    close_db = False
    if db is None:
        db = KhipuDB()
        close_db = True

    try:
        result = translate(khipu_name, db=db)
    finally:
        if close_db:
            db.close()

    # Build the template
    vocab_list = [
        {
            "word": word,
            "count": count,
            "gloss_en": result._gloss(word, "en"),
            "gloss_fr": result._gloss(word, "fr"),
            "confirmed": word in result.vocabulary,
        }
        for word, count in result.vocabulary.most_common()
    ]

    contribution = {
        "khipu": result.khipu.investigator_num,
        "contributor": "Your Name <your.email@example.com>",
        "date": date.today().isoformat(),
        "status": "proposed",
        "confidence": "low",
        "summary": "TODO: Describe what this khipu is and why you think so (1-3 sentences).",
        "interpretation": "TODO: Add your detailed analysis here.",
        "auto_translation": {
            "document_type": result.document_type,
            "architecture": result.architecture,
            "total_cords": result.stats["total_cords"],
            "int_cords": result.stats["int_cords"],
            "string_cords": result.stats["string_cords"],
            "empty_cords": result.stats["empty_cords"],
            "dict_hits": result.stats["dict_hits"],
            "coverage_pct": round(result.stats["coverage_pct"], 1),
            "provenance": result.khipu.provenance,
            "museum": result.khipu.museum_name,
            "vocabulary": vocab_list,
            "colors": result.stats.get("color_distribution", {}),
        },
        "column_names": {},
        "references": [],
        "reconstructed_xlsx": None,
    }

    # Save
    out_dir = output_dir or CONTRIBUTIONS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{result.khipu.investigator_num}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(contribution, f, ensure_ascii=False, indent=2)

    return out_path


def load_contributions(contributions_dir: Optional[Path] = None) -> dict[str, dict]:
    """Load all JSON contribution files."""
    d = contributions_dir or CONTRIBUTIONS_DIR
    contributions = {}
    if not d.exists():
        return contributions
    for f in sorted(d.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
                kid = data.get("khipu", f.stem)
                contributions[kid] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return contributions
