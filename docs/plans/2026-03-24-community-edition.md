# KhipuReader Community Edition — Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan.

**Goal:** Transform KhipuReader from a single-user tool into a collaborative platform where the community builds the reconstructed library of 619 khipus together.

**Architecture:** JSON contributions in `contributions/`, similarity engine in `suggest.py`, progress tracker in `progress.py`, template generator in `submit.py`. All new commands added to existing CLI. README rewritten with community vision.

**Tech Stack:** Python 3.9+, pandas, openpyxl (optional), json (stdlib)

---

## Task 1: Create suggest.py (similarity engine)

**Files:**
- Create: `src/khipu_translator/suggest.py`

The core engine. Compares any khipu against all 619 others on 4 axes:
1. Vocabulary overlap (Jaccard similarity of ALBA words)
2. Structural similarity (cord count ratio, cluster regularity, architecture match)
3. Provenance match (same site or museum = bonus)
4. Color pattern similarity (cosine similarity of color distributions)

Returns ranked list of most similar khipus + suggested document type.

---

## Task 2: Create submit.py (JSON template generator)

**Files:**
- Create: `src/khipu_translator/submit.py`

Translates a khipu, then generates a pre-filled JSON contribution file.
Auto-fills: khipu ID, date, stats, vocabulary, document type, provenance.
Leaves blank: contributor, summary, interpretation, column_names, confidence.

---

## Task 3: Create progress.py (progress tracker)

**Files:**
- Create: `src/khipu_translator/progress.py`

Reads all JSON files in `contributions/`, cross-references with OKR database.
Generates PROGRESS.md with:
- Global progress bar (N/619)
- Per-type breakdown
- Per-museum breakdown
- Recently analyzed
- "Most wanted" (large STRING% khipus not yet claimed)

---

## Task 4: Update CLI with 4 new commands

**Files:**
- Modify: `src/khipu_translator/cli.py`

Add: suggest, compare, unclaimed, submit subcommands.
- `khipu suggest UR039 --db path` — show top 5 similar + suggested type
- `khipu compare UR039 UR144 --db path` — side by side
- `khipu unclaimed --db path` — list unanalyzed, sorted by readability
- `khipu submit UR039 --db path` — generate contributions/UR039.json

---

## Task 5: Seed contributions/ with 6 JSON files

**Files:**
- Create: `contributions/UR006.json`
- Create: `contributions/AS076.json`
- Create: `contributions/HP020.json`
- Create: `contributions/AS080.json`
- Create: `contributions/AS077.json`
- Create: `contributions/AS075.json`

Convert the 6 entries from knowledge.py into JSON contribution files.

---

## Task 6: Rewrite README.md

**Files:**
- Rewrite: `README.md`

New structure:
1. Title + mission ("Reading the lost library of the Inca Empire, together")
2. Progress bar
3. Quick start (install → translate → contribute)
4. How it works (syllabary, 3 levels)
5. CLI reference (all commands)
6. How to contribute (4 levels)
7. Contributors
8. Citation + disclaimer

---

## Task 7: Create CONTRIBUTING.md

**Files:**
- Create: `CONTRIBUTING.md`

Guide for contributors: how to install, translate, analyze, submit.
4 contribution levels explained.
JSON format documented.
Review process explained.

---

## Task 8: Generate PROGRESS.md + create library/

**Files:**
- Create: `PROGRESS.md`
- Create: `library/.gitkeep`

---

## Task 9: Update pyproject.toml URLs + commit + push

**Files:**
- Modify: `pyproject.toml`

Fix URLs to point to julienTeam/KhipuReader.
Commit everything. Push to GitHub.
