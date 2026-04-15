#!/usr/bin/env python3
"""Semi-automated migrator from knowledge JSON v3 to v4.

For each input file (or the priority batch), emit a `*.v4.json` candidate next
to the original. Humans review the diff before committing.

Usage:
    python3 scripts/migrate_knowledge_to_v4.py UR050
    python3 scripts/migrate_knowledge_to_v4.py UR050 UR055 UR278
    python3 scripts/migrate_knowledge_to_v4.py --priority        # seven khipus
    python3 scripts/migrate_knowledge_to_v4.py --all             # every JSON
    python3 scripts/migrate_knowledge_to_v4.py --apply UR050     # overwrite in place after review
    python3 scripts/migrate_knowledge_to_v4.py --report          # just audit which khipus have markers

Outputs:
    contributions/validated/URxxx.v4.json  (candidate, human reviews)
    On review + approval, human runs with --apply to overwrite URxxx.json.

Status logged to MIGRATION_V4.md (append-only rows)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── paths ─────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent.parent
VALID_DIR = REPO / "contributions" / "validated"
MIGRATION_LOG = VALID_DIR / "MIGRATION_V4.md"

PRIORITY_BATCH = ["UR050", "UR055", "UR278", "UR266", "UR268", "UR039", "UR112"]

# ── parsing helpers ──────────────────────────────────────────────────

# ATTRIBUTION block markers. Tolerate a few spellings Claude used across sessions.
ATTRIBUTION_START = re.compile(r"^(ATTRIBUTION\b)", re.MULTILINE)

# A "top-level section" ends when we see one of these at column 0 (or after \n)
SECTION_HEADERS = [
    "IDENTIFICATION",
    "DATA QUALITY",
    "ASCHER LAYER",
    "STRUCTURAL SIGNATURE",
    "VOCABULARY",
    "VOCAB POSITIONS",
    "COLOR ROLE MAP",
    "HYPOTHESIS",
    "THE STORY",
    "SECTION-BY-SECTION",
    "HISTORICAL CONTEXT",
    "CROSS-CORPUS",
    "KEY PASSAGES",
    "WHAT IS VERIFIABLE",
    "CONFIDENCE",
    "STALE V1",
    "PRESERVED V1",
    "DATING",
    "ARCHIVING",
]
SECTION_RE = re.compile(
    r"^(" + "|".join(re.escape(h) for h in SECTION_HEADERS) + r"[^\n]*)$",
    re.MULTILINE,
)

# (a) item ; (b) next item ; (c) last item. Ends at '.' followed by space+capital or end.
# Also handles (1) (2) (3) for v3_contribution.
LETTER_ITEM = re.compile(r"\(([a-z])\)\s+(.+?)(?=\s*;\s*\([a-z]\)|\s*\.\s*$|\s*\.\s*\n|\Z)", re.DOTALL)
NUMBER_ITEM = re.compile(r"\((\d+)\)\s+(.+?)(?=\s*;\s*\(\d+\)|\s*\.\s*$|\s*\.\s*\n|\Z)", re.DOTALL)

# Fallback bullets: lines starting with '-' or numbers '1.' '2.'
BULLET_LINE = re.compile(r"^\s*[-\u2022]\s+(.+)$", re.MULTILINE)
NUMBERED_LINE = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)

# Citation-extraction: "(Author YYYY…)" inside an item
CITATION_IN_PAREN = re.compile(r"\(([A-Z][A-Za-z\-\s&.]+(?:19|20)\d{2}[^)]*)\)")
# Inline citation without parens: "Urton-Chu 2015" or "Urton 2017 p.163"
CITATION_INLINE = re.compile(r"\b([A-Z][A-Za-z\-]+(?:\s*(?:&|and)\s*[A-Z][A-Za-z\-]+)?)\s+((?:19|20)\d{2})(?:\s+p\.?\s*\d+)?")

# companion refs
KHIPU_ID = re.compile(r"\b(UR\d{3,4}[A-Z]?|AS\d{3}[A-Z]?|HP\d{3}|JC\d{3}|LL\d{2})\b")

# Sentence splitter (rough)
SENTENCE_SPLIT = re.compile(r"(?<=[\.\!\?])\s+(?=[A-Z])")

# v3_contribution label/detail separator: " -- " or " — " (double-dash, em-dash)
DETAIL_SEP = re.compile(r"\s+--\s+|\s+\u2014\s+")

# Relation inference
RELATION_VERBS = [
    (re.compile(r"\brecap(?:s|ped by)?\b", re.IGNORECASE), "audit_recap"),
    (re.compile(r"\brecapped by\b", re.IGNORECASE), "audit_target"),
    (re.compile(r"\btranscrib(?:es|ed by)\b", re.IGNORECASE), "audit_recap"),
    (re.compile(r"\btwin(?:ned with)?\b|\bpaired with\b", re.IGNORECASE), "paired_twin"),
    (re.compile(r"\bsame (?:UE|provenance|storeroom|site)\b", re.IGNORECASE), "same_provenance"),
    (re.compile(r"\bcompanion\b|\bmatch(?:es|ed)?\b|\bsee also\b", re.IGNORECASE), "other"),
]


# ── extractors ────────────────────────────────────────────────────────


@dataclass
class MigrationReport:
    khipu: str
    path: Path
    has_attribution_block: bool = False
    has_story_block: bool = False
    n_prior: int = 0
    n_v3: int = 0
    n_companions: int = 0
    story_chars: int = 0
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def status(self) -> str:
        if self.has_attribution_block and self.has_story_block:
            return "auto-migrated"
        if self.has_story_block and not self.has_attribution_block:
            return "story-only"
        if self.has_attribution_block and not self.has_story_block:
            return "attribution-only"
        return "needs_full_manual_drafting"


def _slice_section(interpretation: str, section_name: str) -> str | None:
    """Return the body of the named section, up to the next top-level header."""
    m = re.search(rf"^{re.escape(section_name)}[^\n]*\n", interpretation, re.MULTILINE)
    if not m:
        return None
    start = m.end()
    # Find next top-level section AFTER our start
    rest = interpretation[start:]
    nxt = SECTION_RE.search(rest)
    if nxt:
        body = rest[: nxt.start()]
    else:
        body = rest
    return body.strip()


def extract_attribution(interpretation: str) -> dict[str, list] | None:
    """Parse ATTRIBUTION block into {prior_work:[], v3_contribution:[]}.

    Accepts both formats:
      PRIOR WORK: (a) x; (b) y; (c) z.
      PRIOR WORK (context):
        - x
        - y
    """
    block = _slice_section(interpretation, "ATTRIBUTION")
    if block is None:
        return None

    # Split block into PRIOR WORK and V3 CONTRIBUTION sub-sections
    m_prior = re.search(r"PRIOR WORK\b[^:]*:\s*(.+?)(?=V3 (?:CONTRIBUTION|NOVELTY)\b|$)",
                         block, re.DOTALL | re.IGNORECASE)
    m_v3 = re.search(r"V3 (?:CONTRIBUTION|NOVELTY)\b[^:]*:\s*(.+?)$",
                      block, re.DOTALL | re.IGNORECASE)

    prior_work = []
    if m_prior:
        text = m_prior.group(1).strip()
        prior_work = _parse_items(text, kind="prior")

    v3_contribution = []
    if m_v3:
        text = m_v3.group(1).strip()
        v3_contribution = _parse_items(text, kind="v3")

    if not prior_work and not v3_contribution:
        return None
    return {"prior_work": prior_work, "v3_contribution": v3_contribution}


def _parse_items(text: str, kind: str) -> list[dict]:
    """Parse (a)/(b)/(c) or (1)/(2)/(3) inline lists, or bulleted lines."""
    items_text = []

    # Try (a) (b) (c) ... for prior, (1) (2) (3) ... for v3
    if kind == "prior":
        matches = LETTER_ITEM.findall(text)
        if matches:
            items_text = [m[1].strip() for m in matches]
    else:
        matches = NUMBER_ITEM.findall(text)
        if matches:
            items_text = [m[1].strip() for m in matches]

    # Fallback: bullet lines
    if not items_text:
        bullets = BULLET_LINE.findall(text)
        if bullets:
            items_text = [b.strip() for b in bullets]

    # Last fallback: split on "; " or "\n" at paragraph-level
    if not items_text:
        # split on ";" if any
        if ";" in text:
            items_text = [s.strip(" .") for s in text.split(";") if s.strip(" .")]

    # Convert to structured items
    out = []
    for raw in items_text:
        raw = raw.rstrip(".;,").strip()
        if not raw:
            continue
        if kind == "prior":
            citation, contrib = _split_citation(raw)
            out.append({"citation": citation, "contribution": contrib})
        else:
            label, detail = _split_label_detail(raw)
            out.append({"label": label, "detail": detail})
    return out


def _split_citation(text: str) -> tuple[str, str]:
    """Try to pull a scholarly citation out of a prior-work item.

    Preference:
    1. Parenthesised "(Author YYYY)" → citation, rest → contribution
    2. Inline "Author YYYY" at end of sentence → citation, prefix → contribution
    3. Otherwise citation="see text" and whole thing is contribution
    """
    # Try parens
    m = CITATION_IN_PAREN.search(text)
    if m:
        citation = m.group(1).strip()
        contribution = (text[: m.start()] + text[m.end():]).strip(" ,.;")
        return citation, contribution

    # Try inline
    m = CITATION_INLINE.search(text)
    if m:
        citation = f"{m.group(1)} {m.group(2)}".strip()
        # Keep full text as contribution (citation is embedded)
        return citation, text

    return "see text", text


def _split_label_detail(text: str) -> tuple[str, str]:
    """Try to split a v3_contribution item on ' -- ' into (label, detail)."""
    m = DETAIL_SEP.search(text)
    if m:
        label = text[: m.start()].strip(" ,.;:")
        detail = text[m.end():].strip(" ,.;")
        # Trim label to a short noun phrase if it's very long
        if len(label) > 120:
            label = label[:117].rstrip() + "…"
        return label, detail

    # No separator: label is the first ~6 words, detail is the full text.
    words = text.split()
    if len(words) <= 8:
        return text.strip(" .;"), text.strip(" .;")
    label = " ".join(words[:6]).rstrip(",:;")
    return label, text.strip(" .;")


def extract_narrative(interpretation: str) -> str | None:
    """Pull the THE STORY body, strip per-line leading indent (2 spaces)."""
    body = _slice_section(interpretation, "THE STORY")
    if body is None:
        return None
    # Strip the 2-space indent that deep-read JSONs use for prose
    lines = [re.sub(r"^  ", "", ln) for ln in body.split("\n")]
    return "\n".join(lines).strip()


def extract_companions(interpretation: str, summary: str) -> list[dict]:
    """Heuristic mentions: 'see also URxxx', 'recapped by URxxx', 'twin URxxx'.

    Builds one companion per (khipu_id, inferred_relation) pair seen.
    """
    text = (summary or "") + "\n\n" + (interpretation or "")
    ids_seen = {}
    self_id = None
    # Find KHIPU IDs and local relation context
    for m in KHIPU_ID.finditer(text):
        kid = m.group(1)
        # Look at ± 80 chars context
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 80)
        context = text[start:end]
        # Infer relation
        relation = _infer_relation(context)
        if kid not in ids_seen or relation != "other":
            # Take the most specific relation
            ids_seen[kid] = {"relation": relation, "context": context}
    companions = []
    for kid, info in ids_seen.items():
        note = _extract_sentence_around(info["context"], kid)
        companions.append({
            "id": kid,
            "relation": info["relation"],
            "note": note,
        })
    return companions


def _infer_relation(context: str) -> str:
    for pat, rel in RELATION_VERBS:
        if pat.search(context):
            return rel
    return "other"


def _extract_sentence_around(context: str, kid: str) -> str:
    """Return the single sentence containing `kid`."""
    for s in SENTENCE_SPLIT.split(context):
        if kid in s:
            return s.strip(" .;,")
    return context.strip(" .;,")[:200]


# ── migrator ────────────────────────────────────────────────────────


def migrate_one(khipu_id: str, apply_in_place: bool = False) -> MigrationReport:
    path = VALID_DIR / f"{khipu_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Not found: {path}")

    original = json.loads(path.read_text(encoding="utf-8"))
    report = MigrationReport(khipu=khipu_id, path=path)

    interp = original.get("interpretation", "") or ""

    narrative = extract_narrative(interp)
    if narrative:
        report.has_story_block = True
        report.story_chars = len(narrative)

    attribution = extract_attribution(interp)
    if attribution:
        report.has_attribution_block = True
        report.n_prior = len(attribution.get("prior_work", []))
        report.n_v3 = len(attribution.get("v3_contribution", []))

    companions = extract_companions(interp, original.get("summary", ""))
    # Remove self-reference if present
    companions = [c for c in companions if c["id"] != khipu_id]
    report.n_companions = len(companions)

    # Build v4 candidate
    v4 = dict(original)  # start from the original, additive
    if narrative:
        v4["narrative"] = narrative
    if attribution:
        v4["attribution"] = attribution
    if companions:
        v4["companions"] = companions
    # confidence_axes: LEAVE NULL — must be hand-authored
    if "confidence_axes" not in v4:
        v4["confidence_axes"] = None

    # Sanity checks
    if not narrative:
        report.warnings.append("No THE STORY section found")
    if not attribution:
        report.warnings.append("No ATTRIBUTION block found")
    if not companions:
        report.warnings.append("No companion khipu mentions found")

    target = path if apply_in_place else path.with_suffix(".v4.json")
    target.write_text(json.dumps(v4, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


# ── reporting / bootstrap ─────────────────────────────────────────────


def write_migration_log(reports: list[MigrationReport], mode: str):
    """Append or create MIGRATION_V4.md with the batch results."""
    header = "# Knowledge JSON v4 migration log\n\n" \
             "Tracks the auto-migration candidates emitted by `scripts/migrate_knowledge_to_v4.py`.\n" \
             "Each row below is reviewed by a human before the `*.v4.json` overrides the original.\n\n"
    table_header = (
        "| Khipu | Status | prior | v3 | companions | story (chars) | Warnings |\n"
        "|---|---|---:|---:|---:|---:|---|\n"
    )
    rows = []
    for r in reports:
        warns = "; ".join(r.warnings) if r.warnings else ""
        rows.append(
            f"| {r.khipu} | {r.status()} | {r.n_prior} | {r.n_v3} | {r.n_companions} | {r.story_chars} | {warns} |"
        )
    section = f"\n## Run — mode={mode}\n\n" + table_header + "\n".join(rows) + "\n"
    if MIGRATION_LOG.exists():
        MIGRATION_LOG.write_text(MIGRATION_LOG.read_text() + section, encoding="utf-8")
    else:
        MIGRATION_LOG.write_text(header + section, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--priority", action="store_true", help="migrate the priority batch (7 khipus)")
    g.add_argument("--all", action="store_true", help="migrate every JSON under contributions/validated/")
    g.add_argument("--report", action="store_true", help="scan only — no writes")
    ap.add_argument("--apply", action="store_true",
                    help="overwrite URxxx.json in place (post-review). Without --apply, emit URxxx.v4.json candidate.")
    ap.add_argument("khipus", nargs="*", help="explicit khipu IDs (e.g. UR050 UR055)")
    args = ap.parse_args()

    if args.priority:
        ids = PRIORITY_BATCH
    elif args.all:
        ids = sorted(p.stem for p in VALID_DIR.glob("*.json") if not p.stem.endswith(".v4"))
    else:
        ids = args.khipus
    if not ids:
        ap.error("Specify khipu IDs, --priority, --all, or --report (with IDs).")

    reports: list[MigrationReport] = []
    for kid in ids:
        try:
            if args.report:
                # scan only
                path = VALID_DIR / f"{kid}.json"
                original = json.loads(path.read_text(encoding="utf-8"))
                interp = original.get("interpretation", "") or ""
                report = MigrationReport(khipu=kid, path=path)
                narrative = extract_narrative(interp)
                if narrative:
                    report.has_story_block = True
                    report.story_chars = len(narrative)
                attribution = extract_attribution(interp)
                if attribution:
                    report.has_attribution_block = True
                    report.n_prior = len(attribution.get("prior_work", []))
                    report.n_v3 = len(attribution.get("v3_contribution", []))
                companions = extract_companions(interp, original.get("summary", ""))
                companions = [c for c in companions if c["id"] != kid]
                report.n_companions = len(companions)
            else:
                report = migrate_one(kid, apply_in_place=args.apply)
            reports.append(report)
            print(f"{kid:10s}  {report.status():35s} prior={report.n_prior:2d}  v3={report.n_v3:2d}  companions={report.n_companions:2d}  story={report.story_chars:5d}c  {'; '.join(report.warnings)}")
        except Exception as e:
            print(f"{kid:10s}  ERROR: {e}", file=sys.stderr)

    if reports and not args.report:
        mode = "priority" if args.priority else ("all" if args.all else "manual")
        if args.apply:
            mode += " --apply"
        write_migration_log(reports, mode)
        print(f"\nLogged to {MIGRATION_LOG.relative_to(REPO)}")


if __name__ == "__main__":
    main()
