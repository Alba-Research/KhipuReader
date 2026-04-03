"""
Knowledge database — loads research notes from contributions/ JSON files.

Each khipu's knowledge is stored as a separate JSON file in contributions/.
This module loads them on demand and provides a unified interface.

JSON format:
  {
    "khipu": "UR006",
    "contributor": "Name <email>",
    "date": "2026-03-25",
    "status": "proposed|reviewed|confirmed",
    "confidence": "low|medium|medium-high|high",
    "summary": "One paragraph description...",
    "interpretation": "Multi-line research notes...",
    "references": ["Source 1", "Source 2"],
    "reconstructed_xlsx": "filename.xlsx" or null
  }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


CONTRIBUTIONS_BASE = Path(__file__).parent.parent.parent / "contributions"
VALIDATED_DIR = CONTRIBUTIONS_BASE / "validated"
PROPOSED_DIR = CONTRIBUTIONS_BASE / "proposed"


def _find_json(khipu_id: str) -> Optional[Path]:
    """Find the JSON file for a khipu, checking validated/ first then proposed/.

    For composite IDs like 'LL01/UR176', also tries each part individually.
    """
    ids_to_try = [khipu_id]
    if "/" in khipu_id:
        ids_to_try.extend(khipu_id.split("/"))
    for kid in ids_to_try:
        for d in (VALIDATED_DIR, PROPOSED_DIR):
            path = d / f"{kid}.json"
            if path.exists():
                return path
    return None


def get_knowledge(khipu_id: str) -> Optional[dict]:
    """
    Load knowledge entry for a khipu from its JSON file.

    Checks validated/ first, then proposed/.

    Parameters
    ----------
    khipu_id : str
        Khipu identifier (e.g. 'UR006').

    Returns
    -------
    dict or None
        The knowledge entry, or None if no file exists.
    """
    path = _find_json(khipu_id)
    if path is None:
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if not data.get("summary") or "TODO" in data.get("summary", ""):
        return None

    return data


def list_known_khipus() -> list[str]:
    """Return list of khipu IDs that have knowledge entries."""
    known = []
    for d in (VALIDATED_DIR, PROPOSED_DIR):
        if not d.exists():
            continue
        for path in sorted(d.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("summary") and "TODO" not in data.get("summary", ""):
                    kid = data.get("khipu", path.stem)
                    if kid not in known:
                        known.append(kid)
            except (json.JSONDecodeError, OSError):
                continue
    return known
