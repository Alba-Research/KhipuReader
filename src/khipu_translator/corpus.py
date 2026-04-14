"""
corpus
======

Access layer for the merged OKR × KFG corpus (built by
``scripts/merge_okr_kfg.py``).

This module is additive: it does NOT replace the existing
:class:`khipu_translator.database.KhipuDB` or
:func:`khipu_translator.translator.translate` entry points. It exposes
read-only access to the merged JSON / SQLite artefacts so downstream tools
(tests, the v3 reader, research scripts) have one place to go.

Typical usage
-------------

    >>> from khipu_translator.corpus import MergedCorpus
    >>> corpus = MergedCorpus()
    >>> rec = corpus.load("UR052")          # resolves aliases
    >>> rec["sources"]["okr_kfg_agreement"]
    0.99
    >>> corpus.resolve_kh_id("UR278")
    'KH0517'
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MERGED_DIR = REPO_ROOT / "data" / "merged"
DEFAULT_SQLITE = DEFAULT_MERGED_DIR / "merged_corpus.sqlite"


# ---------------------------------------------------------------------------
# Resolution API
# ---------------------------------------------------------------------------

def _scan_alias_index(merged_dir: Path) -> Dict[str, str]:
    """Walk the merged directory, build a ``{alias: kh_id}`` map.

    Aliases include every element of each record's ``aliases`` list AND
    the KH id itself (so looking up ``'KH0282'`` returns ``'KH0282'``).
    For OKR-only synthetic records with ``kh_id='OKR_{inv}'``, the
    ``OKR_...`` id is also indexed.
    """
    mapping: Dict[str, str] = {}
    if not merged_dir.is_dir():
        return mapping
    for path in sorted(merged_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        kh_id = data.get("kh_id")
        if not kh_id:
            continue
        mapping.setdefault(kh_id, kh_id)
        for alias in data.get("aliases", []) or []:
            if alias:
                mapping.setdefault(alias, kh_id)
    return mapping


@dataclass
class CorpusIndex:
    """Lightweight directory of all merged records."""

    merged_dir: Path
    aliases: Dict[str, str]   # alias -> kh_id

    @property
    def kh_ids(self) -> List[str]:
        return sorted(set(self.aliases.values()))

    def all_aliases(self) -> Iterable[str]:
        return self.aliases.keys()


# ---------------------------------------------------------------------------
# Main facade
# ---------------------------------------------------------------------------

class MergedCorpus:
    """Read-only accessor for the merged corpus (JSON + SQLite).

    Parameters
    ----------
    merged_dir : Path, optional
        Directory holding ``KH*.json`` files. Default: ``data/merged/``.
    sqlite_path : Path, optional
        Path to ``merged_corpus.sqlite``. Lazily opened on first use.
    """

    def __init__(
        self,
        merged_dir: Optional[Path] = None,
        sqlite_path: Optional[Path] = None,
    ):
        self.merged_dir = Path(merged_dir) if merged_dir else DEFAULT_MERGED_DIR
        self.sqlite_path = Path(sqlite_path) if sqlite_path else DEFAULT_SQLITE
        self._index: Optional[CorpusIndex] = None
        self._conn: Optional[sqlite3.Connection] = None

    # -- Index -----------------------------------------------------------
    @property
    def index(self) -> CorpusIndex:
        if self._index is None:
            self._index = CorpusIndex(
                merged_dir=self.merged_dir,
                aliases=_scan_alias_index(self.merged_dir),
            )
        return self._index

    def resolve_kh_id(self, key: str) -> Optional[str]:
        """Resolve any alias (or KH id) to the canonical KH id. None if not found."""
        return self.index.aliases.get(key)

    def list_kh_ids(self) -> List[str]:
        return self.index.kh_ids

    # -- JSON record access ---------------------------------------------
    def path_for(self, key: str) -> Optional[Path]:
        """Return the filesystem path of the merged JSON for ``key`` (alias or kh_id)."""
        kh = self.resolve_kh_id(key)
        if kh is None:
            return None
        p = self.merged_dir / f"{kh}.json"
        return p if p.exists() else None

    @lru_cache(maxsize=64)
    def load(self, key: str) -> dict:
        """Load the merged JSON record for ``key`` (alias or kh_id).

        Raises ``KeyError`` if not found.
        """
        p = self.path_for(key)
        if p is None:
            raise KeyError(f"No merged record for '{key}'")
        return json.loads(p.read_text(encoding="utf-8"))

    # -- SQLite (corpus-wide queries) -----------------------------------
    def _open_sqlite(self) -> sqlite3.Connection:
        if self._conn is None:
            if not self.sqlite_path.exists():
                raise FileNotFoundError(
                    f"SQLite corpus not found at {self.sqlite_path}. "
                    "Run scripts/merge_okr_kfg.py first."
                )
            self._conn = sqlite3.connect(str(self.sqlite_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def sql(self, query: str, params: tuple = ()) -> list:
        """Execute a read-only SQL query on the corpus sqlite. Returns list of dict rows."""
        cur = self._open_sqlite().execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- Convenience helpers --------------------------------------------
    def quality_stats(self, kh_id: str) -> Dict[str, int]:
        """Return the quality-label distribution for a khipu."""
        rows = self.sql(
            "SELECT quality, COUNT(*) AS n FROM cords WHERE kh_id=? GROUP BY quality",
            (kh_id,),
        )
        return {r["quality"] or "UNKNOWN": int(r["n"]) for r in rows}

    def all_kh_ids_sql(self) -> List[str]:
        rows = self.sql("SELECT kh_id FROM khipus ORDER BY kh_id")
        return [r["kh_id"] for r in rows]

    def merged_locke(self, kh_id: str, cord_num) -> Optional[float]:
        """Return the merged (authoritative) Locke value for a cord, or None."""
        rows = self.sql(
            "SELECT merged_locke FROM cords WHERE kh_id=? AND cord_num=?",
            (kh_id, str(cord_num)),
        )
        return rows[0]["merged_locke"] if rows else None

    # -- Context manager ------------------------------------------------
    def __enter__(self) -> "MergedCorpus":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
