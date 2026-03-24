"""
OKR Database interface — download, setup, and query the Open Khipu Repository.

The OKR (Open Khipu Repository) is a SQLite database containing digitized
records of 619 khipus, 54,403 cords, and 110,677 knots.

Original project: https://github.com/khipulab/open-khipu-repository
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

# Default paths
DEFAULT_DATA_DIR = Path.home() / ".khipu-translator"
OKR_REPO_URL = "https://github.com/khipulab/open-khipu-repository.git"
OKR_DB_RELATIVE = "data/khipu.db"


@dataclass
class KhipuRecord:
    """Metadata for a single khipu."""
    khipu_id: int
    investigator_num: str
    provenance: Optional[str]
    museum_name: Optional[str]
    notes: Optional[str]
    num_cords: int = 0
    num_knots: int = 0


class KhipuDB:
    """
    Interface to the Open Khipu Repository database.

    On first use, clones the OKR from GitHub (requires git).
    Subsequent uses reuse the local copy.

    Parameters
    ----------
    data_dir : str or Path, optional
        Where to store the OKR database. Default: ~/.khipu-translator/
    db_path : str or Path, optional
        Direct path to an existing khipu.db file. Overrides data_dir.

    Examples
    --------
    >>> db = KhipuDB()                          # auto-downloads OKR
    >>> db = KhipuDB(db_path="./khipu.db")      # use local file
    >>> khipu = db.get_khipu("UR039")
    >>> cords = db.get_cords(khipu.khipu_id)
    """

    def __init__(
        self,
        data_dir: Optional[str | Path] = None,
        db_path: Optional[str | Path] = None,
    ):
        if db_path:
            self._db_path = Path(db_path)
            if not self._db_path.exists():
                raise FileNotFoundError(f"Database not found: {self._db_path}")
        else:
            self._data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
            self._db_path = self._data_dir / "open-khipu-repository" / OKR_DB_RELATIVE
            if not self._db_path.exists():
                self._setup_okr()

        self._conn: Optional[sqlite3.Connection] = None

    def _setup_okr(self) -> None:
        """Clone the OKR repository from GitHub."""
        repo_dir = self._data_dir / "open-khipu-repository"

        if repo_dir.exists():
            print(f"OKR directory exists at {repo_dir}, checking for database...")
            if self._db_path.exists():
                return
            print("Database not found. Re-cloning...")

        self._data_dir.mkdir(parents=True, exist_ok=True)
        print(f"Downloading Open Khipu Repository to {repo_dir}...")
        print(f"  Source: {OKR_REPO_URL}")
        print("  This is a one-time setup (~50 MB).")

        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", OKR_REPO_URL, str(repo_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "git is required to download the OKR database.\n"
                "Install git: https://git-scm.com/downloads\n"
                "Or download khipu.db manually from:\n"
                f"  {OKR_REPO_URL}"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone OKR repository:\n{e.stderr}")

        if not self._db_path.exists():
            raise RuntimeError(
                f"OKR cloned but database not found at {self._db_path}.\n"
                "The repository structure may have changed."
            )

        print(f"  OKR database ready: {self._db_path}")

    @property
    def connection(self) -> sqlite3.Connection:
        """Lazy-open SQLite connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # --- Query methods -------------------------------------------------------

    def list_khipus(self, search: Optional[str] = None) -> pd.DataFrame:
        """
        List all khipus, optionally filtered by keyword.

        Parameters
        ----------
        search : str, optional
            Search term to filter by ID, provenance, museum, or notes.

        Returns
        -------
        pd.DataFrame
            Columns: INVESTIGATOR_NUM, PROVENANCE, MUSEUM_NAME
        """
        if search:
            query = (
                "SELECT INVESTIGATOR_NUM, PROVENANCE, MUSEUM_NAME FROM khipu_main "
                "WHERE INVESTIGATOR_NUM LIKE ? OR PROVENANCE LIKE ? "
                "OR MUSEUM_NAME LIKE ? "
                "ORDER BY INVESTIGATOR_NUM"
            )
            param = f"%{search}%"
            return pd.read_sql(query, self.connection, params=[param] * 3)
        else:
            return pd.read_sql(
                "SELECT INVESTIGATOR_NUM, PROVENANCE, MUSEUM_NAME "
                "FROM khipu_main ORDER BY INVESTIGATOR_NUM",
                self.connection,
            )

    def get_khipu(self, name: str) -> KhipuRecord:
        """
        Get metadata for a khipu by its investigator number.

        Parameters
        ----------
        name : str
            Khipu identifier, e.g. 'UR039', 'AS030'.

        Returns
        -------
        KhipuRecord

        Raises
        ------
        KeyError
            If the khipu is not found.
        """
        # Try exact match first, then LIKE
        df = pd.read_sql(
            "SELECT * FROM khipu_main WHERE INVESTIGATOR_NUM = ?",
            self.connection,
            params=[name],
        )
        if len(df) == 0:
            df = pd.read_sql(
                "SELECT * FROM khipu_main WHERE INVESTIGATOR_NUM LIKE ?",
                self.connection,
                params=[f"%{name}%"],
            )
        if len(df) == 0:
            raise KeyError(f"Khipu '{name}' not found in database.")

        row = df.iloc[0]
        kid = int(row["KHIPU_ID"])

        num_cords = pd.read_sql(
            "SELECT COUNT(*) as n FROM cord WHERE KHIPU_ID=?",
            self.connection, params=[kid],
        ).iloc[0]["n"]

        num_knots = pd.read_sql(
            "SELECT COUNT(*) as n FROM knot WHERE CORD_ID IN "
            "(SELECT CORD_ID FROM cord WHERE KHIPU_ID=?)",
            self.connection, params=[kid],
        ).iloc[0]["n"]

        return KhipuRecord(
            khipu_id=kid,
            investigator_num=str(row.get("INVESTIGATOR_NUM", "?")),
            provenance=row.get("PROVENANCE"),
            museum_name=row.get("MUSEUM_NAME"),
            notes=str(row.get("NOTES", "")) if pd.notna(row.get("NOTES")) else None,
            num_cords=int(num_cords),
            num_knots=int(num_knots),
        )

    def get_cords(self, khipu_id: int) -> pd.DataFrame:
        """Get all cords for a khipu, with color info and hierarchical level."""
        cords = pd.read_sql(
            "SELECT * FROM cord WHERE KHIPU_ID=? ORDER BY CORD_ORDINAL",
            self.connection, params=[khipu_id],
        )
        # Merge colors
        colors = pd.read_sql(
            "SELECT CORD_ID, COLOR_CD_1 FROM ascher_cord_color "
            "WHERE KHIPU_ID=? AND PCORD_FLAG=0",
            self.connection, params=[khipu_id],
        )
        if not colors.empty:
            cp = colors.drop_duplicates(subset="CORD_ID", keep="first")
            cords = cords.merge(cp[["CORD_ID", "COLOR_CD_1"]], on="CORD_ID", how="left")
            cords["color"] = cords["COLOR_CD_1"].fillna("?")
        else:
            cords["color"] = "?"

        # Compute hierarchical level from PENDANT_FROM chain
        cord_ids = set(cords["CORD_ID"].values)
        pendant_map = {}
        for _, row in cords.iterrows():
            pf = row.get("PENDANT_FROM")
            if pd.notna(pf) and int(pf) in cord_ids:
                pendant_map[int(row["CORD_ID"])] = int(pf)

        def _level(cid: int, depth: int = 1) -> int:
            parent = pendant_map.get(cid)
            if parent is None:
                return depth
            return _level(parent, depth + 1)

        cords["CORD_LEVEL"] = cords["CORD_ID"].apply(lambda cid: _level(int(cid)))

        return cords

    def get_knots(self, khipu_id: int) -> pd.DataFrame:
        """Get all knots for a khipu."""
        return pd.read_sql(
            "SELECT * FROM knot WHERE CORD_ID IN "
            "(SELECT CORD_ID FROM cord WHERE KHIPU_ID=?) "
            "ORDER BY CORD_ID, KNOT_ORDINAL",
            self.connection, params=[khipu_id],
        )

    def get_cord_knots(self, cord_id: int) -> pd.DataFrame:
        """Get all knots for a specific cord."""
        return pd.read_sql(
            "SELECT * FROM knot WHERE CORD_ID=? "
            "ORDER BY CLUSTER_ORDINAL, KNOT_ORDINAL",
            self.connection, params=[cord_id],
        )
