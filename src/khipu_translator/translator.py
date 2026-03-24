"""
Khipu Translator — Multi-level translation engine.

Produces three levels of translation:
  Level 1 (Cord): Raw cord-by-cord data (type, value, syllabic reading, color, level)
  Level 2 (Record): Structured records grouped by cluster (spreadsheet view)
  Level 3 (Document): Interpreted reading with document-type detection

Reference: Sivan, J. (2026). "The Khipu as a Layered Information System."
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from khipu_translator.database import KhipuDB, KhipuRecord
from khipu_translator.dictionary import (
    DICTIONARY,
    DOMAIN_GLOSSARIES,
    GLOSSARY,
    analyze_morphology,
)
from khipu_translator.locke import cord_type, decode_locke_value
from khipu_translator.syllabary import (
    FIGURE_EIGHT_SYLLABLE,
    TURNS_TO_ONSET,
    TURNS_TO_SYLLABLE,
    VALID_TURNS,
)


# --- Color roles (validated cross-corpus, chi2=480, p<1e-17) -----------------

COLOR_ROLES: dict[str, str] = {
    "LK": "text/governance",
    "FB": "action",
    "PR": "action/material",
    "GG": "identity/justice",
    "DB": "objects",
    "LC": "ritual",
    "LB": "interrogative",
    "BG": "identity",
    "AB": "subject/mixed",
    "W":  "data/neutral",
    "MB": "category/data",
    "KB": "data",
    "B":  "geographic",
    "HB": "data",
}


# --- Data structures ---------------------------------------------------------


@dataclass
class CordTranslation:
    """Level 1: Translation of a single cord."""
    cord_id: int
    cord_type: str           # 'INT', 'STRING', 'EMPTY'
    level: int               # hierarchical depth (1 = pendant, 2 = subsidiary, ...)
    ordinal: int             # position within cluster (CLUSTER_ORDINAL)
    global_ordinal: int      # position on primary cord (CORD_ORDINAL)
    color: str               # OKR color code
    color_role: str          # semantic role of this color

    # Numerical channel (Locke)
    locke_value: Optional[int]
    locke_confidence: str    # 'exact', 'uniform_kvt', 'ambiguous', 'none'

    # Textual channel (ALBA)
    alba_reading: Optional[str]       # proposed syllabic reading
    alba_gloss_en: Optional[str]      # English gloss
    alba_gloss_fr: Optional[str]      # French gloss
    alba_confirmed: bool              # matches dictionary
    alba_confidence: str              # 'high', 'medium', 'low', 'unconfirmed', 'none'
    alba_compound: Optional[str]      # compound decomposition if applicable

    # Knot sequence: raw description of knots on this cord
    # e.g. "S10 S10 L3" or "L3 L4 E" or "S100 S10 L5"
    knot_sequence: str = ""

    # Numerical prefix (S-knots on STRING cords)
    s_prefix: int = 0

    # L-1 flag (NULL turns in OKR -> unreadable)
    is_l1_null: bool = False

    # Tree structure
    parent_cord_id: Optional[int] = None
    children: list[CordTranslation] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to a flat dictionary for export."""
        d = {
            "cord_id": self.cord_id,
            "type": self.cord_type,
            "level": self.level,
            "ordinal": self.ordinal,
            "global_ordinal": self.global_ordinal,
            "color": self.color,
            "color_role": self.color_role,
            "locke_value": self.locke_value,
            "locke_confidence": self.locke_confidence,
            "alba_reading": self.alba_reading,
            "alba_gloss_en": self.alba_gloss_en,
            "alba_gloss_fr": self.alba_gloss_fr,
            "alba_confirmed": self.alba_confirmed,
            "alba_confidence": self.alba_confidence,
            "alba_compound": self.alba_compound,
            "knot_sequence": self.knot_sequence,
            "s_prefix": self.s_prefix,
            "is_l1_null": self.is_l1_null,
            "parent_cord_id": self.parent_cord_id,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class ClusterRecord:
    """Level 2: A single cluster (row in the khipu spreadsheet)."""
    cluster_index: int
    cluster_id: Optional[int]
    cords: list[CordTranslation]

    @property
    def total_value(self) -> int:
        return sum(c.locke_value or 0 for c in self.cords)

    @property
    def string_readings(self) -> list[str]:
        return [c.alba_reading for c in self.cords if c.alba_reading]

    @property
    def colors(self) -> list[str]:
        return [c.color for c in self.cords]

    def to_dict(self) -> dict:
        return {
            "cluster_index": self.cluster_index,
            "total_value": self.total_value,
            "string_readings": self.string_readings,
            "colors": self.colors,
            "cords": [c.to_dict() for c in self.cords],
        }


# --- Document-type detection -------------------------------------------------

DOCUMENT_PROFILES: dict[str, set[str]] = {
    "administrative_register": {"kama", "kamay", "ypa", "pataka", "qapa", "kapa",
                                 "llaqa", "pata"},
    "kinship_lineage":         {"kaka", "mama", "papa", "tata", "pana", "tayta",
                                 "panaka", "tayka", "nana"},
    "labor_tribute":           {"maki", "taka", "kata", "paka", "maka", "paki",
                                 "makay", "takay", "kiki", "kaki", "tama"},
    "ritual_oracle":           {"taki", "naqa", "pama", "napa", "naku", "tina",
                                 "llapa", "nay", "waka"},
    "judicial_proceeding":     {"llalla", "mana", "taq", "pay", "kay", "sina",
                                 "pi", "piqa", "taka", "maqa", "kata"},
    "astronomical_journal":    {"kama", "mama", "paka", "maqa"},  # CORE only
    "agro_pastoral":           {"kaki", "kaqa", "wama", "chaqa", "paki", "taki",
                                 "taqa", "siqa", "maki"},
    "cadastral_survey":        {"qaqa", "kaqa", "taqa", "chiqa", "paqa", "naqa",
                                 "siqa", "piqa", "qata", "qama"},
}


def detect_document_type(
    vocabulary: Counter,
    string_ratio: float = 0.0,
    color_counts: Optional[dict[str, int]] = None,
    total_cords: int = 0,
    string_cords: int = 0,
    num_clusters: int = 0,
    cluster_regularity: float = 0.0,
    sparsity: float = 0.0,
    n_colors: int = 1,
) -> tuple[str, float]:
    """
    Detect the most likely document type from vocabulary, structure, and
    statistical signals.

    Categories:
      - astronomical_journal:  3+ core astro words (kama/mama/paka/maqa + kaki)
      - agro_pastoral:         regular full table + agro vocab (kaqa, wama, chaqa)
      - cadastral_survey:      toponym vocabulary (-qa words)
      - judicial_proceeding:   action + kinship co-occurrence
      - labor_tribute:         maki + companions (kiki, kaki, tama)
      - ritual_oracle:         taki, pama, napa, nay
      - kinship_lineage:       pure kinship vocabulary
      - event_register:        >50% sparse, punctual data
      - regular_table:         >80% regular, low sparsity, no clear vocab signal
      - numerical_record:      mostly INT, few STRING, no vocab match

    Returns (document_type, score).
    """
    words = set(vocabulary.keys())
    scores: dict[str, float] = {}

    for doc_type, profile_words in DOCUMENT_PROFILES.items():
        overlap = words & profile_words
        weighted = sum(vocabulary.get(w, 0) for w in overlap)
        scores[doc_type] = weighted / max(len(profile_words), 1)

    # Also initialize structural types
    scores.setdefault("event_register", 0)
    scores.setdefault("regular_table", 0)
    scores.setdefault("numerical_record", 0)

    string_pct = 100 * string_cords / total_cords if total_cords > 0 else 0

    # --- Vocabulary-based boosts ---

    # Astronomical: need CORE astro words (strict: kama, mama, paka, maqa)
    # kaki is shared with agriculture so it's NOT core astro
    core_astro = {"kama", "mama", "paka", "maqa"}
    core_astro_hits = len(words & core_astro)
    has_kaki = "kaki" in words
    if core_astro_hits >= 2 or (core_astro_hits >= 1 and has_kaki and string_pct < 25):
        scores["astronomical_journal"] *= 2.5
        scores["astronomical_journal"] = max(scores["astronomical_journal"], 2.0)

    # Agro-pastoral: kaqa/wama/chaqa are agro-specific (not shared with astro)
    agro_specific = {"kaqa", "wama", "chaqa", "siqa"}
    agro_hits = len(words & agro_specific)
    if agro_hits >= 2:
        scores["agro_pastoral"] *= 2.0
        scores["agro_pastoral"] = max(scores["agro_pastoral"], 1.5)
    # Regular full table + agro vocab = strong agro signal
    if agro_hits >= 1 and cluster_regularity > 80 and sparsity < 15:
        scores["agro_pastoral"] *= 1.5

    # Judicial: action + kinship co-occurrence
    action_words = {"taka", "kata", "maqa", "maka", "llalla"}
    kinship_words = {"kaka", "tata", "mama", "pana"}
    if len(words & action_words) >= 1 and len(words & kinship_words) >= 1:
        scores["judicial_proceeding"] *= 2.0
        scores["kinship_lineage"] *= 0.6

    # Labor: maki + companions
    if "maki" in words:
        labor_companions = {"kiki", "kaki", "tama", "paki", "kata"}
        if len(words & labor_companions) >= 1:
            scores["labor_tribute"] *= 2.0

    # Cadastral: -qa toponyms
    qa_toponyms = {"qaqa", "kaqa", "taqa", "chiqa", "paqa", "naqa", "siqa", "piqa"}
    qa_hits = len(words & qa_toponyms)
    if qa_hits >= 2:
        scores["cadastral_survey"] *= 1.5

    # --- Structure-based detection ---

    # Event register: very sparse (>50% empty cells)
    if sparsity > 50:
        scores["event_register"] = 2.0
        # Penalize types that expect dense data
        for t in ("astronomical_journal", "agro_pastoral", "cadastral_survey"):
            scores[t] *= 0.3

    # Regular table: high regularity + low sparsity + multiple colors
    if cluster_regularity > 80 and sparsity < 15:
        if n_colors >= 3:
            scores["regular_table"] = max(scores["regular_table"], 1.5)
        # Penalize event register
        scores["event_register"] *= 0.3

    # Numerical record: very few STRING cords, no clear vocab
    if string_pct < 3 and total_cords > 50:
        top_score = max(scores.values()) if scores else 0
        if top_score < 1.0:
            scores["numerical_record"] = 1.0

    # --- Pick winner ---

    best_type = max(scores, key=scores.get) if scores else "unknown"
    best_score = scores.get(best_type, 0)

    threshold = 0.5 if total_cords < 50 else 1.0
    return (best_type, best_score) if best_score >= threshold else ("unknown", 0)


# --- Architecture detection --------------------------------------------------

def detect_architecture(cords_df: pd.DataFrame) -> str:
    """
    Detect khipu architecture: 0-SEUL, 1-PAIRE, 2+-ARBRE.

    Based on subsidiary depth distribution.
    """
    if "CORD_LEVEL" not in cords_df.columns:
        return "0-SEUL"
    max_level = cords_df["CORD_LEVEL"].max()
    if max_level <= 1:
        return "0-SEUL"
    l2_count = (cords_df["CORD_LEVEL"] == 2).sum()
    l1_count = (cords_df["CORD_LEVEL"] == 1).sum()
    if l1_count > 0 and l2_count / l1_count > 1.5:
        return "2+-ARBRE"
    if l2_count > 0:
        return "1-PAIRE"
    return "0-SEUL"


# --- Translation result ------------------------------------------------------


@dataclass
class TranslationResult:
    """
    Complete multi-level translation of a khipu.

    Attributes
    ----------
    khipu : KhipuRecord
        Metadata about the source khipu.
    cords : list[CordTranslation]
        Level 1: All cords with their translations.
    clusters : list[ClusterRecord]
        Level 2: Cords grouped into structured records.
    document_type : str
        Level 3: Detected document type.
    architecture : str
        Structural type: '0-SEUL', '1-PAIRE', '2+-ARBRE'.
    vocabulary : Counter
        Word frequency counts for STRING cords.
    stats : dict
        Summary statistics.
    """
    khipu: KhipuRecord
    cords: list[CordTranslation]
    clusters: list[ClusterRecord]
    document_type: str
    document_type_score: float
    architecture: str
    vocabulary: Counter
    stats: dict

    # --- Level 1: Cord-level output ------------------------------------------

    def level1_dataframe(self) -> pd.DataFrame:
        """Level 1 export: one row per cord."""
        rows = [c.to_dict() for c in self.cords]
        # Flatten (remove children for DataFrame)
        for r in rows:
            r.pop("children", None)
        return pd.DataFrame(rows)

    # --- Level 2: Record-level output ----------------------------------------

    def level2_records(self) -> list[dict]:
        """Level 2 export: one record per cluster."""
        return [cl.to_dict() for cl in self.clusters]

    # --- Level 3: Document-level output --------------------------------------

    def level3_document(self, lang: str = "en") -> dict:
        """Level 3 export: full document interpretation."""
        return {
            "khipu_id": self.khipu.investigator_num,
            "provenance": self.khipu.provenance,
            "museum": self.khipu.museum_name,
            "document_type": self.document_type,
            "architecture": self.architecture,
            "stats": self.stats,
            "vocabulary": {
                w: {
                    "count": c,
                    "gloss": self._gloss(w, lang),
                    **({"astro": self._domain_gloss(w, lang)}
                       if self._domain_gloss(w, lang) else {}),
                }
                for w, c in self.vocabulary.most_common()
            },
            "clusters": self.level2_records(),
        }

    def _gloss(self, word: str, lang: str) -> str:
        base = ""
        if word in GLOSSARY:
            fr, en, _ = GLOSSARY[word]
            base = en if lang == "en" else fr
        else:
            morph = analyze_morphology(word, lang)
            if morph.compound_parts:
                if lang == "fr":
                    base = " + ".join(p[1] for p in morph.compound_parts)
                else:
                    base = " + ".join(p[2] for p in morph.compound_parts)
            elif morph.is_decomposable and morph.root_gloss_en:
                g = morph.root_gloss_en if lang == "en" else morph.root_gloss_fr
                if morph.suffixes:
                    suf_str = "+".join(s[1] for s in morph.suffixes)
                    base = f"{g} [{suf_str}]"
                else:
                    base = g
        return base

    def _domain_gloss(self, word: str, lang: str) -> str:
        """Return domain-specific meaning if available for this document type."""
        glossary = DOMAIN_GLOSSARIES.get(self.document_type)
        if glossary and word in glossary:
            fr, en = glossary[word]
            return en if lang == "en" else fr
        return ""

    # --- Export methods -------------------------------------------------------

    @staticmethod
    def _ensure_dir(path: str) -> None:
        """Create parent directories if they don't exist."""
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def to_json(self, path: str, level: int = 3, lang: str = "en") -> None:
        """Export translation to JSON file."""
        import json
        self._ensure_dir(path)
        if level == 1:
            data = [c.to_dict() for c in self.cords]
        elif level == 2:
            data = self.level2_records()
        else:
            data = self.level3_document(lang=lang)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def to_csv(self, path: str) -> None:
        """Export Level 1 (cord-level) to CSV."""
        self._ensure_dir(path)
        self.level1_dataframe().to_csv(path, index=False, encoding="utf-8")

    def to_xml(self, path: str, lang: str = "en") -> None:
        """Export Level 2 (record-level) to XML."""
        self._ensure_dir(path)
        import xml.etree.ElementTree as ET
        from xml.dom.minidom import parseString

        root = ET.Element("khipu")
        root.set("id", self.khipu.investigator_num)
        root.set("provenance", self.khipu.provenance or "unknown")
        root.set("document_type", self.document_type)
        root.set("architecture", self.architecture)

        for cl in self.clusters:
            cl_elem = ET.SubElement(root, "cluster")
            cl_elem.set("index", str(cl.cluster_index))
            cl_elem.set("total_value", str(cl.total_value))

            for c in cl.cords:
                cord_elem = ET.SubElement(cl_elem, "cord")
                cord_elem.set("id", str(c.cord_id))
                cord_elem.set("type", c.cord_type)
                cord_elem.set("color", c.color)
                cord_elem.set("color_role", c.color_role)
                cord_elem.set("level", str(c.level))

                if c.locke_value is not None:
                    val_elem = ET.SubElement(cord_elem, "value")
                    val_elem.set("confidence", c.locke_confidence)
                    val_elem.text = str(c.locke_value)

                if c.alba_reading:
                    text_elem = ET.SubElement(cord_elem, "reading")
                    text_elem.set("confirmed", str(c.alba_confirmed).lower())
                    text_elem.set("confidence", c.alba_confidence)
                    text_elem.text = c.alba_reading
                    gloss = c.alba_gloss_en if lang == "en" else c.alba_gloss_fr
                    if gloss:
                        gloss_elem = ET.SubElement(cord_elem, "gloss")
                        gloss_elem.text = gloss
                    if c.alba_compound:
                        compound_elem = ET.SubElement(cord_elem, "compound")
                        compound_elem.text = c.alba_compound

                if c.s_prefix:
                    prefix_elem = ET.SubElement(cord_elem, "numeric_prefix")
                    prefix_elem.text = str(c.s_prefix)

                if c.is_l1_null:
                    cord_elem.set("l1_null", "true")

        xml_str = ET.tostring(root, encoding="unicode")
        pretty = parseString(xml_str).toprettyxml(indent="  ")
        with open(path, "w", encoding="utf-8") as f:
            f.write(pretty)

    def to_xlsx(self, path: str, lang: str = "en") -> None:
        """
        Export a human-friendly Excel workbook.

        Sheet 1 "Resume": khipu metadata, statistics, vocabulary with glosses.
        Sheet 2 "Traduction": one row per cord, readable column names, color coding.
        Sheet 3 "Tableur" (if applicable): spreadsheet view for regular-structure
                 khipus (astronomical journals, paired registers).

        Requires openpyxl: pip install khipu-translator[xlsx]
        """
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            raise ImportError(
                "openpyxl is required for Excel export.\n"
                "Install it with: pip install khipu-translator[xlsx]"
            )

        self._ensure_dir(path)
        wb = Workbook()

        # --- Color constants ---
        HEADER_FILL = PatternFill("solid", fgColor="2C3E50")
        HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
        TITLE_FONT = Font(bold=True, size=14)
        SUBTITLE_FONT = Font(bold=True, size=11)
        LABEL_FONT = Font(bold=True, size=10)
        CONFIRMED_FONT = Font(bold=True, color="006400")
        UNCONFIRMED_FONT = Font(italic=True, color="8B4513")
        STRING_FILL = PatternFill("solid", fgColor="FFF8DC")
        INT_FILL = PatternFill("solid", fgColor="F0F8FF")
        EMPTY_FILL = PatternFill("solid", fgColor="F5F5F5")
        CLUSTER_FILL = PatternFill("solid", fgColor="E8E8E8")
        THIN_BORDER = Border(
            bottom=Side(style="thin", color="CCCCCC"),
        )
        CLUSTER_BORDER = Border(
            top=Side(style="medium", color="2C3E50"),
        )

        gloss_key = "fr" if lang == "fr" else "en"
        gl = lambda w: self._gloss(w, lang)  # noqa: E731
        dg = lambda w: self._domain_gloss(w, lang)  # noqa: E731

        # =====================================================================
        # Sheet 1: Resume
        # =====================================================================
        ws1 = wb.active
        ws1.title = "Resume"
        ws1.sheet_properties.tabColor = "2C3E50"

        # Title
        ws1["A1"] = f"Khipu {self.khipu.investigator_num}"
        ws1["A1"].font = TITLE_FONT
        ws1.merge_cells("A1:D1")

        # Metadata
        meta = [
            ("Provenance", self.khipu.provenance or "Inconnue"),
            ("Musee", self.khipu.museum_name or "Inconnu"),
            ("Type de document", self.document_type.replace("_", " ").title()),
            ("Architecture", self.architecture),
            ("Cordes totales", self.stats["total_cords"]),
            ("Cordes INT (nombres)", self.stats["int_cords"]),
            ("Cordes STRING (texte)", self.stats["string_cords"]),
            ("Cordes vides", self.stats["empty_cords"]),
            ("Clusters", self.stats["num_clusters"]),
            ("Hits dictionnaire", f"{self.stats['dict_hits']}/{self.stats['string_cords']}"
                f" ({self.stats['coverage_pct']:.0f}%)"),
            ("Valeur numerique totale", f"{self.stats['total_value']:,}"),
        ]
        if self.stats.get("l1_null_cords", 0) > 0:
            meta.append(("Cordes illisibles (L-1)", self.stats["l1_null_cords"]))

        for i, (label, value) in enumerate(meta, start=3):
            ws1.cell(row=i, column=1, value=label).font = LABEL_FONT
            ws1.cell(row=i, column=2, value=str(value))

        # Colors
        row = len(meta) + 4
        ws1.cell(row=row, column=1, value="Couleurs").font = SUBTITLE_FONT
        row += 1
        if self.stats.get("color_distribution"):
            for color, count in sorted(
                self.stats["color_distribution"].items(), key=lambda x: -x[1]
            ):
                role = COLOR_ROLES.get(color.strip(), "")
                ws1.cell(row=row, column=1, value=color.strip())
                ws1.cell(row=row, column=2, value=count)
                ws1.cell(row=row, column=3, value=role)
                row += 1

        # Vocabulary
        row += 1
        ws1.cell(row=row, column=1, value="Vocabulaire").font = SUBTITLE_FONT
        row += 1
        vocab_headers = ["Mot", "Occurrences", "Traduction", "Domaine", "Confirme"]
        for j, h in enumerate(vocab_headers, start=1):
            c = ws1.cell(row=row, column=j, value=h)
            c.fill = HEADER_FILL
            c.font = HEADER_FONT
        row += 1
        for word, count in self.vocabulary.most_common():
            ws1.cell(row=row, column=1, value=word).font = (
                CONFIRMED_FONT if word in DICTIONARY else UNCONFIRMED_FONT
            )
            ws1.cell(row=row, column=2, value=count)
            ws1.cell(row=row, column=3, value=gl(word))
            domain = dg(word)
            if domain:
                ws1.cell(row=row, column=4, value=domain)
            ws1.cell(row=row, column=5, value="oui" if word in DICTIONARY else "non")
            row += 1

        # Column widths
        ws1.column_dimensions["A"].width = 25
        ws1.column_dimensions["B"].width = 18
        ws1.column_dimensions["C"].width = 35
        ws1.column_dimensions["D"].width = 35
        ws1.column_dimensions["E"].width = 10

        # Knowledge section (what we know about this khipu)
        from khipu_translator.knowledge import get_knowledge
        knowledge = get_knowledge(self.khipu.investigator_num)
        if knowledge:
            row += 1
            ws1.cell(row=row, column=1, value="What We Know").font = SUBTITLE_FONT
            row += 1
            ws1.cell(row=row, column=1,
                     value=knowledge.get("summary", "")).font = Font(
                         bold=True, size=10)
            row += 1
            ws1.cell(row=row, column=1,
                     value=f"Confidence: {knowledge.get('confidence', '?')}").font = (
                         Font(italic=True, size=10))
            row += 1
            for line in knowledge.get("interpretation", "").strip().split("\n"):
                ws1.cell(row=row, column=1, value=line)
                if line.strip() and not line.startswith(" "):
                    ws1.cell(row=row, column=1).font = Font(bold=True, size=10)
                row += 1
            if knowledge.get("reconstructed_xlsx"):
                row += 1
                ws1.cell(row=row, column=1,
                         value=f"Reconstructed library file: "
                         f"{knowledge['reconstructed_xlsx']}").font = Font(
                             bold=True, color="2E86C1", size=10)
                row += 1
            if knowledge.get("references"):
                row += 1
                ws1.cell(row=row, column=1, value="References:").font = Font(
                    bold=True, size=10)
                row += 1
                for ref in knowledge["references"]:
                    ws1.cell(row=row, column=1, value=f"  - {ref}")
                    row += 1

        # =====================================================================
        # Sheet 2: Traduction
        # =====================================================================
        ws2 = wb.create_sheet("Traduction")
        ws2.sheet_properties.tabColor = "E67E22"

        headers = [
            "Cluster", "Position", "Niveau", "Couleur", "Role couleur",
            "Type", "Noeuds", "Valeur", "Lecture", "Traduction",
            "Domaine", "Confiance", "Prefixe num.",
        ]
        for j, h in enumerate(headers, start=1):
            c = ws2.cell(row=1, column=j, value=h)
            c.fill = HEADER_FILL
            c.font = HEADER_FONT
            c.alignment = Alignment(horizontal="center")
        ws2.freeze_panes = "A2"

        L2_FILL = PatternFill("solid", fgColor="EBF5FB")
        L3_FILL = PatternFill("solid", fgColor="D5F5E3")

        row = 2
        prev_cluster = None
        # Track L2/L3 row ranges for grouping
        group_ranges: list[tuple[int, int, int]] = []  # (start, end, level)

        for cl in self.clusters:
            # Cluster separator row
            if prev_cluster is not None:
                for j in range(1, len(headers) + 1):
                    c = ws2.cell(row=row, column=j, value="")
                    c.border = CLUSTER_BORDER
                row += 1

            def _write_cord(
                cord: CordTranslation, cluster_idx: int, r: int,
            ) -> int:
                indent = "    " * (cord.level - 1)

                ws2.cell(row=r, column=1, value=cluster_idx)
                ws2.cell(row=r, column=2, value=cord.ordinal)
                ws2.cell(row=r, column=3, value=f"{indent}L{cord.level}")
                ws2.cell(row=r, column=4, value=cord.color.strip())
                ws2.cell(row=r, column=5, value=cord.color_role)

                # Choose fill based on level
                if cord.level >= 3:
                    level_fill = L3_FILL
                elif cord.level == 2:
                    level_fill = L2_FILL
                else:
                    level_fill = None

                # Column 7: knot sequence (always written)
                if cord.knot_sequence:
                    ws2.cell(row=r, column=7, value=cord.knot_sequence)

                if cord.cord_type == "STRING":
                    ws2.cell(row=r, column=6, value="TEXTE")
                    reading = cord.alba_reading or "(illisible)"
                    c_read = ws2.cell(row=r, column=9, value=reading)
                    if cord.alba_confirmed:
                        c_read.font = CONFIRMED_FONT
                    else:
                        c_read.font = UNCONFIRMED_FONT
                    gloss_val = (cord.alba_gloss_fr if lang == "fr"
                                 else cord.alba_gloss_en) or ""
                    ws2.cell(row=r, column=10, value=gloss_val)
                    domain_val = dg(cord.alba_reading) if cord.alba_reading else ""
                    if domain_val:
                        ws2.cell(row=r, column=11, value=domain_val)
                    ws2.cell(row=r, column=12, value=cord.alba_confidence)
                    if cord.s_prefix:
                        ws2.cell(row=r, column=13, value=cord.s_prefix)
                    base_fill = STRING_FILL if cord.level == 1 else level_fill
                    for j in range(1, len(headers) + 1):
                        ws2.cell(row=r, column=j).fill = base_fill or STRING_FILL

                elif cord.cord_type == "INT":
                    ws2.cell(row=r, column=6, value="NOMBRE")
                    if cord.locke_value is not None:
                        ws2.cell(row=r, column=8, value=int(cord.locke_value))
                    ws2.cell(row=r, column=12, value=cord.locke_confidence)
                    base_fill = INT_FILL if cord.level == 1 else level_fill
                    for j in range(1, len(headers) + 1):
                        ws2.cell(row=r, column=j).fill = base_fill or INT_FILL

                else:
                    ws2.cell(row=r, column=6, value="VIDE")
                    base_fill = EMPTY_FILL if cord.level == 1 else level_fill
                    for j in range(1, len(headers) + 1):
                        ws2.cell(row=r, column=j).fill = base_fill or EMPTY_FILL

                for j in range(1, len(headers) + 1):
                    ws2.cell(row=r, column=j).border = THIN_BORDER

                r += 1

                # Write children and track their row range for grouping
                if cord.children:
                    child_start = r
                    for child in cord.children:
                        r = _write_cord(child, cluster_idx, r)
                    child_end = r - 1
                    outline_level = min(cord.level, 2)  # L1→group level 1, L2→level 2
                    group_ranges.append((child_start, child_end, outline_level))

                return r

            for cord in cl.cords:
                row = _write_cord(cord, cl.cluster_index, row)

            prev_cluster = cl.cluster_index

        # Apply row grouping (collapsible outlines)
        for start, end, level in group_ranges:
            if start <= end:
                ws2.row_dimensions.group(start, end,
                                         outline_level=level, hidden=False)

        # Column widths (13 columns now)
        # Cluster, Position, Niveau, Couleur, Role, Type, Noeuds, Valeur, Lecture, Traduction, Domaine, Confiance, Prefixe
        widths = [8, 8, 8, 8, 18, 8, 18, 10, 20, 30, 30, 12, 10]
        for j, w in enumerate(widths, start=1):
            col_letter = chr(64 + j) if j <= 26 else "Z"
            ws2.column_dimensions[col_letter].width = w

        # =====================================================================
        # Sheet 3: Tableur (spreadsheet view for regular-structure khipus)
        # =====================================================================
        # Detect structure type:
        #   A) Regular columns: most clusters have same # of L1 cords
        #   B) Paired label->measure: alternating color pairs (LC/DB, B/DB)

        # Filter out single-cord clusters (separators) and empty-only clusters
        data_clusters = [
            cl for cl in self.clusters
            if len(cl.cords) > 1
            and any(c.cord_type != "EMPTY" for c in cl.cords)
        ]
        cluster_sizes = [len(cl.cords) for cl in data_clusters]

        if cluster_sizes:
            from collections import Counter as Ctr
            size_counts = Ctr(cluster_sizes)
            # Accept top 2 sizes if they're close (e.g. 6 and 7 = same format +-1)
            top_sizes = size_counts.most_common(2)
            mode_size = top_sizes[0][0]
            total_regular = top_sizes[0][1]
            if (len(top_sizes) > 1
                    and abs(top_sizes[1][0] - mode_size) <= 1
                    and top_sizes[1][1] >= 5):
                total_regular += top_sizes[1][1]
            mode_ratio = total_regular / len(cluster_sizes)

            # --- Type A: Regular N-column table (up to 12 columns) ---
            # Model: P1 = annotation (word OR number), P2..PN = data columns
            # STRING values in data columns are rare annotations, shown inline.
            # For larger tables (>12 cols), use Type C (block-repetitive).
            if mode_ratio >= 0.5 and 3 <= mode_size <= 12:
                n_cols = mode_size
                if len(top_sizes) > 1 and top_sizes[1][0] > mode_size:
                    n_cols = top_sizes[1][0]

                # Count data columns (exclude P1 which is the annotation)
                n_data = n_cols - 1

                ws3 = wb.create_sheet("Tableur")
                ws3.sheet_properties.tabColor = "27AE60"

                # Functional column names for known formats
                # 9-col astronomical journal (UR006): validated
                ASTRO_9COL = {
                    2: "Obs. (flag)",
                    3: "Position",
                    4: "Secondaire",
                    5: "Objet suivi",
                    6: "Comptage",
                    7: "Voie Lactee",
                    8: "Duree",
                    9: "Nuits claires",
                }
                # 9-col agro-pastoral (UR1136): Nazca
                AGRO_9COL = {
                    2: "Mesure 1",
                    3: "Mesure 2",
                    4: "Mesure 3",
                    5: "Mesure 4",
                    6: "Mesure 5",
                    7: "Mesure 6",
                    8: "Mesure 7",
                    9: "Mesure 8",
                }

                # Pick functional names by document type
                func_names = {}
                if self.document_type == "astronomical_journal":
                    if n_cols == 9:
                        func_names = ASTRO_9COL
                elif self.document_type == "agro_pastoral":
                    if n_cols == 9:
                        func_names = AGRO_9COL

                # Build headers: # | Annotation | Traduction | data columns
                headers = ["#", "Annotation", "Traduction"]
                for i in range(n_data):
                    col_num = i + 2  # P2, P3, ...
                    if col_num in func_names:
                        headers.append(func_names[col_num])
                    else:
                        headers.append(f"P{col_num}")
                for j, h in enumerate(headers):
                    c = ws3.cell(row=1, column=j + 1, value=h)
                    c.fill = HEADER_FILL
                    c.font = HEADER_FONT
                    c.alignment = Alignment(horizontal="center")
                ws3.freeze_panes = "D2"

                # Data rows
                row_num = 2
                entry = 1
                for cl in data_clusters:
                    if abs(len(cl.cords) - n_cols) > 1:
                        continue

                    cords = list(cl.cords)

                    # Column A: row number
                    ws3.cell(row=row_num, column=1, value=entry)

                    # Column B: Annotation (P1 = first cord)
                    p1 = cords[0] if cords else None
                    if p1 and p1.alba_reading:
                        cell = ws3.cell(row=row_num, column=2, value=p1.alba_reading)
                        cell.fill = STRING_FILL
                        cell.font = (CONFIRMED_FONT if p1.alba_confirmed
                                     else UNCONFIRMED_FONT)
                        # Column C: Translation
                        d_val = dg(p1.alba_reading)
                        g_val = gl(p1.alba_reading)
                        ws3.cell(row=row_num, column=3, value=d_val or g_val)
                    elif p1 and p1.locke_value is not None:
                        ws3.cell(row=row_num, column=2,
                                 value=int(p1.locke_value)).fill = INT_FILL
                    else:
                        ws3.cell(row=row_num, column=2, value="").fill = EMPTY_FILL

                    # Columns D+: Data (P2..PN)
                    for i in range(n_data):
                        col = i + 4  # D=4, E=5, ...
                        cord_idx = i + 1  # skip P1
                        if cord_idx >= len(cords):
                            ws3.cell(row=row_num, column=col, value="").fill = EMPTY_FILL
                        else:
                            cord = cords[cord_idx]
                            if cord.cord_type == "INT" and cord.locke_value is not None:
                                ws3.cell(row=row_num, column=col,
                                         value=int(cord.locke_value)).fill = INT_FILL
                            elif cord.cord_type == "STRING" and cord.alba_reading:
                                # Rare annotation in a data column
                                d_val = dg(cord.alba_reading) or gl(cord.alba_reading)
                                text = (f"{cord.alba_reading} ({d_val})"
                                        if d_val else cord.alba_reading)
                                cell = ws3.cell(row=row_num, column=col, value=text)
                                cell.fill = STRING_FILL
                                cell.font = UNCONFIRMED_FONT
                            else:
                                ws3.cell(row=row_num, column=col,
                                         value="").fill = EMPTY_FILL

                        ws3.cell(row=row_num, column=col).border = THIN_BORDER

                    entry += 1
                    row_num += 1

                # Column widths
                ws3.column_dimensions["A"].width = 5
                ws3.column_dimensions["B"].width = 15
                ws3.column_dimensions["C"].width = 25
                for i in range(n_data):
                    letter = chr(68 + i) if i < 22 else "Z"
                    ws3.column_dimensions[letter].width = 10

            # --- Type C: Block-repetitive (like UR006: 4 blocks x 4 + coda) --
            # Detected when mode cluster size > 12 and color pattern repeats
            elif mode_size > 12 and mode_ratio >= 0.3:
                ref_cl = max(data_clusters, key=lambda cl: sum(
                    1 for c in cl.cords if c.cord_type != "EMPTY"))
                colors = [c.color.strip() for c in ref_cl.cords]

                best_block = 4
                for block_size in (4, 3, 5):
                    if len(colors) < block_size * 3:
                        continue
                    first = colors[:block_size]
                    matches = 0
                    for start in range(block_size, len(colors) - block_size + 1,
                                       block_size):
                        candidate = colors[start:start + block_size]
                        diffs = sum(1 for a, b in zip(first, candidate) if a != b)
                        if diffs <= 1:
                            matches += 1
                    if matches >= 2:
                        best_block = block_size
                        break

                ws3 = wb.create_sheet("Tableur")
                ws3.sheet_properties.tabColor = "27AE60"

                n_main = (len(ref_cl.cords) // best_block) * best_block
                n_blocks = n_main // best_block
                coda_size = len(ref_cl.cords) - n_main
                if coda_size == 0 and n_blocks > 1:
                    last_colors = colors[-best_block:]
                    first_colors = colors[:best_block]
                    if sum(1 for a, b in zip(first_colors, last_colors)
                           if a != b) > best_block // 2:
                        n_blocks -= 1
                        coda_size = best_block
                        n_main -= best_block

                # Headers: B1-c1 B1-c2 B1-c3 B1-c4 | B2-c1 ... | Resume
                color_pattern = colors[:best_block]
                headers = ["#"]
                for b in range(min(n_blocks, 6)):
                    for col in color_pattern:
                        headers.append(f"B{b+1}-{col}")
                headers.append("Resume")

                for j, h in enumerate(headers):
                    c = ws3.cell(row=1, column=j + 1, value=h)
                    c.fill = HEADER_FILL
                    c.font = HEADER_FONT
                    c.alignment = Alignment(horizontal="center")
                ws3.freeze_panes = "B2"

                row_num = 2
                entry = 1
                for cl in data_clusters:
                    if len(cl.cords) < best_block * 2:
                        continue

                    ws3.cell(row=row_num, column=1, value=entry)
                    cords = list(cl.cords)
                    cl_main = min(n_main, len(cords))

                    col_idx = 2
                    for i in range(cl_main):
                        cord = cords[i]
                        if cord.alba_reading:
                            cell = ws3.cell(row=row_num, column=col_idx,
                                            value=cord.alba_reading)
                            cell.fill = STRING_FILL
                            cell.font = (CONFIRMED_FONT if cord.alba_confirmed
                                         else UNCONFIRMED_FONT)
                        elif cord.locke_value is not None:
                            ws3.cell(row=row_num, column=col_idx,
                                     value=int(cord.locke_value)).fill = INT_FILL
                        else:
                            ws3.cell(row=row_num, column=col_idx,
                                     value="").fill = EMPTY_FILL
                        ws3.cell(row=row_num, column=col_idx).border = THIN_BORDER
                        col_idx += 1

                    # Coda
                    if cl_main < len(cords):
                        coda = []
                        for c in cords[cl_main:]:
                            if c.alba_reading:
                                coda.append(c.alba_reading)
                            elif c.locke_value is not None:
                                coda.append(str(int(c.locke_value)))
                        if coda:
                            ws3.cell(row=row_num, column=col_idx,
                                     value=" | ".join(coda))

                    entry += 1
                    row_num += 1

                ws3.column_dimensions["A"].width = 5
                for j in range(1, min(len(headers), 27)):
                    letter = chr(65 + j) if j < 26 else "Z"
                    ws3.column_dimensions[letter].width = 7

            # --- Type B: Paired label->measure (like UR1145 catalog) ----------
            elif any(len(cl.cords) >= 4 for cl in data_clusters):
                # Check for alternating pattern: color1->color2->color1->color2
                paired_clusters = []
                for cl in data_clusters:
                    if len(cl.cords) < 4:
                        continue
                    colors = [c.color.strip() for c in cl.cords]
                    unique = list(dict.fromkeys(colors))
                    if len(unique) == 2:
                        c1, c2 = unique
                        is_alternating = all(
                            colors[i] == (c1 if i % 2 == 0 else c2)
                            for i in range(len(colors))
                        )
                        if is_alternating:
                            paired_clusters.append(cl)

                if paired_clusters:
                    ws3 = wb.create_sheet("Tableur")
                    ws3.sheet_properties.tabColor = "27AE60"

                    all_pairs: list[tuple[int, str, str, int]] = []
                    for cl in paired_clusters:
                        for i in range(0, len(cl.cords) - 1, 2):
                            label_cord = cl.cords[i]
                            value_cord = cl.cords[i + 1]

                            label = ""
                            if label_cord.alba_reading:
                                d = dg(label_cord.alba_reading)
                                g = gl(label_cord.alba_reading)
                                label = (f"{label_cord.alba_reading} ({d or g})"
                                         if (d or g) else label_cord.alba_reading)
                            elif label_cord.locke_value is not None:
                                label = f"[{int(label_cord.locke_value)}]"

                            val = (int(value_cord.locke_value)
                                   if value_cord.locke_value else 0)
                            all_pairs.append((
                                cl.cluster_index, label,
                                label_cord.alba_reading or "", val
                            ))

                    ws3.cell(row=1, column=1, value="Catalogue").font = TITLE_FONT
                    ws3.merge_cells("A1:D1")

                    row = 3
                    for j, h in enumerate(
                        ["Etiquette", "Valeur", "Domaine"], start=1
                    ):
                        c = ws3.cell(row=row, column=j, value=h)
                        c.fill = HEADER_FILL
                        c.font = HEADER_FONT
                    ws3.freeze_panes = "A4"
                    row += 1

                    for cl_idx, label, reading, val in all_pairs:
                        ws3.cell(row=row, column=1, value=label).font = (
                            CONFIRMED_FONT if reading in DICTIONARY
                            else LABEL_FONT
                        )
                        ws3.cell(row=row, column=2,
                                 value=val if val else "").fill = INT_FILL
                        domain_val = dg(reading) if reading else ""
                        if domain_val:
                            ws3.cell(row=row, column=3, value=domain_val)
                        for j in range(1, 4):
                            ws3.cell(row=row, column=j).border = THIN_BORDER
                        row += 1

                    ws3.column_dimensions["A"].width = 30
                    ws3.column_dimensions["B"].width = 15
                    ws3.column_dimensions["C"].width = 35

        wb.save(path)

    # --- Summary -------------------------------------------------------------

    def summary(self, lang: str = "en") -> str:
        """Human-readable summary of the translation."""
        s = self.stats
        lines = [
            f"{'=' * 60}",
            f"  {self.khipu.investigator_num}",
            f"{'=' * 60}",
            f"  Provenance: {self.khipu.provenance or 'Unknown'}",
            f"  Museum: {self.khipu.museum_name or 'Unknown'}",
            f"  Cords: {s['total_cords']} (INT: {s['int_cords']}, "
            f"STRING: {s['string_cords']}, EMPTY: {s['empty_cords']})",
            f"  Clusters: {s['num_clusters']}",
            f"  Architecture: {self.architecture}",
        ]

        if s.get("l1_null_cords", 0) > 0:
            lines.append(
                f"  L-1 (unreadable): {s['l1_null_cords']} cords "
                f"(NULL turns in OKR)"
            )

        # Colors
        if s.get("color_distribution"):
            top_colors = sorted(
                s["color_distribution"].items(), key=lambda x: -x[1]
            )[:5]
            color_str = ", ".join(f"{c}({n})" for c, n in top_colors)
            lines.append(f"  Colors: {color_str}")

        if s["string_cords"] > 0:
            lines.append("")
            lines.append(
                f"  Dictionary hits: {s['dict_hits']}/{s['string_cords']} "
                f"({s['coverage_pct']:.0f}%)"
            )
            lines.append(f"  Document type: {self.document_type}")
            lines.append(f"  Vocabulary ({len(self.vocabulary)} unique words):")
            for word, count in self.vocabulary.most_common(20):
                gloss = self._gloss(word, lang)
                from khipu_translator.dictionary import normalize_onset
                is_known = (word in DICTIONARY
                            or normalize_onset(word) in DICTIONARY)
                morph = analyze_morphology(word)
                # * = dictionary match, + = decomposable (morphology/compound), ~ = unknown
                if is_known:
                    marker = "*"
                elif morph.is_decomposable:
                    marker = "+"
                else:
                    marker = "~"
                compound = ""
                if morph.compound_parts:
                    parts = " + ".join(
                        p[2] if lang == "en" else p[1]
                        for p in morph.compound_parts
                    )
                    compound = f" -> {parts}"
                astro = self._domain_gloss(word, lang)
                astro_str = f"  ({astro})" if astro else ""
                lines.append(
                    f"    {marker}{word:20s} x{count:<3d} {gloss}{compound}{astro_str}"
                )
        else:
            lines.append("")
            lines.append("  This khipu is purely numerical (no STRING cords).")
            if s.get("total_value"):
                lines.append(f"  Total numerical value: {s['total_value']:,}")

        lines.append(f"\n{'=' * 60}")
        return "\n".join(lines)


# --- Main translate function -------------------------------------------------


def _read_alba_word(terminal_knots: pd.DataFrame) -> tuple[Optional[str], bool]:
    """
    Decode a STRING cord's terminal knots into a proposed Quechua word.

    Uses onset polyphony (v3): the first knot may read differently.

    Returns
    -------
    (word, is_l1_null) : tuple
        word is None if unreadable. is_l1_null flags NULL turns in OKR.
    """
    syllables = []
    has_null_turns = False

    for i, (_, knot) in enumerate(terminal_knots.iterrows()):
        tc = str(knot.get("TYPE_CODE", "")).strip()
        is_first = (i == 0)

        if tc == "E":
            syllables.append(FIGURE_EIGHT_SYLLABLE)
        elif tc == "L":
            turns = knot.get("NUM_TURNS")
            if pd.isna(turns) or turns is None:
                has_null_turns = True
                return None, True
            turns = int(turns)
            if is_first:
                syl = TURNS_TO_ONSET.get(turns)
            else:
                syl = TURNS_TO_SYLLABLE.get(turns)
            if syl is None:
                return None, False  # unknown turn count (e.g. L1)
            syllables.append(syl)

    word = "".join(syllables) if syllables else None
    return word, has_null_turns


def translate(
    khipu_name: str,
    db: Optional[KhipuDB] = None,
    lang: str = "en",
) -> TranslationResult:
    """
    Translate a khipu from the OKR database.

    Parameters
    ----------
    khipu_name : str
        Khipu identifier (e.g. 'UR039', 'AS030', 'UR268').
    db : KhipuDB, optional
        Database connection. If None, creates one (auto-downloads OKR).
    lang : str
        Language for glosses: 'en' (English) or 'fr' (French).

    Returns
    -------
    TranslationResult
        Multi-level translation with export capabilities.

    Examples
    --------
    >>> result = translate("UR039")
    >>> print(result.summary())
    >>> result.to_json("UR039_level3.json", level=3)
    >>> result.to_csv("UR039_cords.csv")
    >>> result.to_xml("UR039.xml")
    """
    close_db = False
    if db is None:
        db = KhipuDB()
        close_db = True

    try:
        khipu = db.get_khipu(khipu_name)
        cords_df = db.get_cords(khipu.khipu_id)
        knots_df = db.get_knots(khipu.khipu_id)
    finally:
        if close_db:
            db.close()

    # --- Process each cord ---------------------------------------------------

    cord_translations: dict[int, CordTranslation] = {}
    vocabulary: Counter = Counter()
    l1_null_count = 0
    color_distribution: Counter = Counter()

    for _, cord_row in cords_df.iterrows():
        cid = int(cord_row["CORD_ID"])
        cord_knots = knots_df[knots_df["CORD_ID"] == cid].sort_values(
            ["CLUSTER_ORDINAL", "KNOT_ORDINAL"]
        )

        # Classify cord
        terminal = cord_knots[cord_knots["TYPE_CODE"].isin(["L", "E"])]
        simple = cord_knots[cord_knots["TYPE_CODE"] == "S"]
        ctype = "EMPTY"
        if len(cord_knots) > 0:
            ctype = "STRING" if len(terminal) >= 2 else "INT"

        # Color
        color = str(cord_row.get("color", "?"))
        color_distribution[color] += 1
        color_role = COLOR_ROLES.get(color, "unknown")

        # Build knot sequence string
        knot_seq_parts = []
        for _, kn in cord_knots.iterrows():
            tc = str(kn.get("TYPE_CODE", "")).strip()
            turns = kn.get("NUM_TURNS")
            kvt = kn.get("knot_value_type", 0) or 0
            if tc == "S":
                knot_seq_parts.append(f"S{int(kvt)}")
            elif tc == "L":
                t = int(turns) if pd.notna(turns) else "?"
                knot_seq_parts.append(f"L{t}")
            elif tc == "E":
                knot_seq_parts.append("E")
        knot_sequence = " ".join(knot_seq_parts)

        # Decode channels
        locke_val = None
        locke_conf = "none"
        alba_word = None
        alba_gloss_en = None
        alba_gloss_fr = None
        alba_confirmed = False
        alba_confidence = "none"
        alba_compound = None
        s_prefix = 0
        is_l1_null = False

        if ctype == "INT":
            # Numerical channel
            knot_dicts = cord_knots.to_dict("records")
            lv = decode_locke_value(knot_dicts)
            if lv:
                locke_val = lv.value
                locke_conf = lv.confidence

        elif ctype == "STRING":
            # Textual channel
            alba_word, is_l1_null = _read_alba_word(terminal)
            if is_l1_null:
                l1_null_count += 1

            if alba_word:
                from khipu_translator.dictionary import normalize_onset
                alba_confirmed = (
                    alba_word in DICTIONARY
                    or normalize_onset(alba_word) in DICTIONARY
                )
                morph = analyze_morphology(alba_word, lang=lang)
                alba_gloss_en = morph.root_gloss_en or None
                alba_gloss_fr = morph.root_gloss_fr or None

                if morph.compound_parts:
                    alba_compound = " + ".join(
                        f"{p[0]}({p[2]})" for p in morph.compound_parts
                    )
                    alba_confidence = "medium"
                elif alba_confirmed:
                    alba_confidence = "high"
                elif morph.is_decomposable:
                    alba_confidence = "medium"
                else:
                    alba_confidence = "low"

                vocabulary[alba_word] += 1

            # Numerical prefix (S-knots on STRING cords)
            if len(simple) > 0:
                s_prefix = int(simple["knot_value_type"].sum())

        # Level
        cord_level = int(cord_row.get("CORD_LEVEL", 1))

        ct = CordTranslation(
            cord_id=cid,
            cord_type=ctype,
            level=cord_level,
            ordinal=int(cord_row["CLUSTER_ORDINAL"]) if pd.notna(
                cord_row.get("CLUSTER_ORDINAL")) else 0,
            global_ordinal=int(cord_row["CORD_ORDINAL"]) if pd.notna(
                cord_row.get("CORD_ORDINAL")) else 0,
            color=color,
            color_role=color_role,
            locke_value=locke_val,
            locke_confidence=locke_conf,
            alba_reading=alba_word,
            alba_gloss_en=alba_gloss_en,
            alba_gloss_fr=alba_gloss_fr,
            alba_confirmed=alba_confirmed,
            alba_confidence=alba_confidence,
            alba_compound=alba_compound,
            knot_sequence=knot_sequence,
            s_prefix=s_prefix,
            is_l1_null=is_l1_null,
            parent_cord_id=(
                int(cord_row["PENDANT_FROM"])
                if pd.notna(cord_row.get("PENDANT_FROM"))
                else None
            ),
        )
        cord_translations[cid] = ct

    # --- Build tree ----------------------------------------------------------

    for ct in cord_translations.values():
        if ct.parent_cord_id and ct.parent_cord_id in cord_translations:
            cord_translations[ct.parent_cord_id].children.append(ct)

    for ct in cord_translations.values():
        ct.children.sort(key=lambda c: c.global_ordinal)

    # --- Group into clusters (Level 2) ---------------------------------------

    clusters_map: dict = defaultdict(list)
    for _, cord_row in cords_df.iterrows():
        cid = int(cord_row["CORD_ID"])
        level = int(cord_row.get("CORD_LEVEL", 1))
        if level == 1:  # only L1 cords form cluster rows
            cl_id = cord_row.get("CLUSTER_ID")
            key = cl_id if pd.notna(cl_id) else f"_orphan_{cid}"
            clusters_map[key].append(cord_translations[cid])

    for key in clusters_map:
        clusters_map[key].sort(key=lambda c: c.global_ordinal)

    sorted_keys = sorted(
        clusters_map.keys(),
        key=lambda k: min(c.global_ordinal for c in clusters_map[k]),
    )

    clusters = [
        ClusterRecord(
            cluster_index=i + 1,
            cluster_id=k if not str(k).startswith("_orphan") else None,
            cords=clusters_map[k],
        )
        for i, k in enumerate(sorted_keys)
    ]

    # --- Architecture --------------------------------------------------------

    architecture = detect_architecture(cords_df)

    # --- Document type detection (Level 3) -----------------------------------

    # --- Statistics (compute before doc type, needed for structural signals) --

    all_cords = list(cord_translations.values())
    string_cords = [c for c in all_cords if c.cord_type == "STRING" and c.alba_reading]
    dict_hits = sum(1 for c in string_cords if c.alba_confirmed)

    n_string = len(string_cords)
    stats = {
        "total_cords": len(all_cords),
        "int_cords": sum(1 for c in all_cords if c.cord_type == "INT"),
        "string_cords": n_string,
        "empty_cords": sum(1 for c in all_cords if c.cord_type == "EMPTY"),
        "l1_null_cords": l1_null_count,
        "dict_hits": dict_hits,
        "coverage_pct": (100 * dict_hits / n_string) if n_string else 0,
        "num_clusters": len(clusters),
        "unique_words": len(vocabulary),
        "total_value": sum(c.locke_value or 0 for c in all_cords if c.cord_type == "INT"),
        "color_distribution": dict(color_distribution),
    }

    # --- Document type detection (Level 3) — uses structural stats -----------

    # Compute structural signals for classification
    _data_cl = [cl for cl in clusters if len(cl.cords) > 1
                and any(c.cord_type != "EMPTY" for c in cl.cords)]
    _cl_sizes = [len(cl.cords) for cl in _data_cl]
    _cluster_regularity = 0.0
    if _cl_sizes:
        _size_counts = Counter(_cl_sizes)
        _mode_n = _size_counts.most_common(1)[0][1]
        _cluster_regularity = 100 * _mode_n / len(_cl_sizes)
    _total_cells = sum(len(cl.cords) for cl in _data_cl)
    _empty_cells = sum(1 for cl in _data_cl for c in cl.cords if c.cord_type == "EMPTY")
    _sparsity = 100 * _empty_cells / _total_cells if _total_cells else 0
    _n_colors = len([c for c, n in color_distribution.items()
                     if n > 5 and c.strip() != "?"])

    doc_type, doc_score = detect_document_type(
        vocabulary,
        color_counts=dict(color_distribution),
        total_cords=len(all_cords),
        string_cords=n_string,
        num_clusters=len(clusters),
        cluster_regularity=_cluster_regularity,
        sparsity=_sparsity,
        n_colors=_n_colors,
    )

    return TranslationResult(
        khipu=khipu,
        cords=all_cords,
        clusters=clusters,
        document_type=doc_type,
        document_type_score=doc_score,
        architecture=architecture,
        vocabulary=vocabulary,
        stats=stats,
    )
