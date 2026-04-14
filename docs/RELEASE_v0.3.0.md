# KhipuReader v0.3.0 — Merged Corpus + Ascher Erasure-Code Layer

**Release date**: 2026-04-14
**Previous**: 0.1.0

## What's new

### 1. Merged OKR × KFG corpus

Version 0.3.0 fuses the two largest khipu databases into a single source of truth:

- **OKR** (Open Khipu Repository, Urton lab) — 703 khipus, standard numerical encoding with `L?` gaps for unreadable turns
- **KFG** (Khipu Field Guide, Khosla / Medrano) — independent recording of the same knots with different parsing conventions and access to the pendant-pendant sum registry

The merger resolves **2,702 previously-unreadable cords** (`L?` → concrete turn counts) by cross-filling from KFG turn counts when OKR is silent. On the Incahuasi UR255+ series, this can quadruple the readable vocabulary on a single document.

Each merged cord carries a quality label: **AGREED** (both sources concur), **KFG_RESOLVED** (OKR had `L?`, KFG supplied), **ASCHER_VALIDATED** (arithmetic constraint selected one reading), **DIVERGENT** (sources disagree), **OKR_ONLY** or **KFG_ONLY**.

### 2. Ascher erasure-code layer

Pendant-pendant sums — a structural feature catalogued by Marcia and Robert Ascher in the 1970s and re-catalogued by KFG — are now parseable by the reader and behave as an **erasure code** (Sivan 2026, cascade ρ=0.54, p=6×10⁻²⁹):

- **Pass 2** — annotate every cord with its role in any sum it participates in
- **Pass 3A** — reclassify single-L INT cords surrounded by STRING context as parallel syllabic candidates
- **Pass 3B** — verify sum arithmetic; report integrity rate per khipu
- **Pass 3C** — propagate constraints from sums with exactly one unknown summand
- **Pass 3D** — iteratively repair damaged `L?` cords using the fixed-point of all sum constraints

Controlled-damage ablation on UR052 shows the layer sustains ≥80% recovery at 30% damage. On ~50 Incahuasi khipus the merged corpus + Ascher layer together unlock 200+ additional syllabic readings that v1 could not see.

### 3. Public API

All v3 functionality is now exposed at the top-level package:

```python
from khipu_translator import (
    translate, TranslationResult, MergedCorpus,
    AscherGraph, KFGClient,
    apply_ascher_constraints, apply_reclassification,
    apply_constraint_propagation, apply_pure_arithmetic_repair,
)
```

### 4. CLI flags

```bash
python3 -m khipu_translator.cli translate UR268 --from-merged --ascher \
    --lang fr --json out.json --xlsx out.xlsx
```

- `--from-merged` : fill OKR `L?` with KFG turn counts (non-regression if no `L?` present)
- `--ascher` : run the full Ascher layer (2 + 3A + 3B + 3C + 3D)

### 5. New dependencies

`requests>=2.28` and `beautifulsoup4>=4.11` are now runtime requirements (KFG HTTP fetch and HTML parsing of the sum registry).

## Validated contributions refreshed

18 Incahuasi-related deep reads have been re-issued in v3 (session 2026-04-14), each carrying an `ATTRIBUTION` block that separates prior work (Urton & Chu 2015, Urton 2017, OKR field notes, colonial sources) from v3 contributions (ALBA syllabary readings, positional-constant maps, Ascher integrity quantification, cross-khipu signals).

Notable findings documented in `contributions/validated/`:

- **UR278** reclassified from astronomical_journal to commodity_accounting — 9 commodities × 26 annual cycles at UE 16, anchored by the Quechua polysemy kaki = Pleiades = Qollqa (granary)
- **UR266** transcribes UR278's row totals R1–R8 in correct order (null p < 10⁻⁵) — the first cross-khipu recap confirmed in the analyzed corpus
- **UR267A+UR267B** and **UR255+UR256** — two parallel aji (chili) day-book + audit pairs, each with the physical dual-binding convention Urton noted in field notes, now quantified via positional-constant maps (15 / 10) and Ascher integrity rates (0/13 vs 11/11 and 1/6 vs 8/10)
- **UR275** re-attributed as a peanut khipu (47 constant) per Urton-Chu 2015, extending the three-tier mani pipeline to a fourth member

## Reproducibility

All findings are reproducible from the published code (KhipuReader GitHub) plus the OKR database and the KFG HTML sum registry. The 18 JSONs in `contributions/validated/` cite specific cord positions and Ascher sum IDs for every claim.

## Attribution discipline

This release explicitly separates prior scholarship (Urton, Chu, Ascher, González Holguín, Bertonio, Zuidema, Bauer & Dearborn, and others) from the v3 technical contribution (ALBA syllabary + merged corpus + Ascher layer). The genuine novelty of the session is the statistical match UR266 ↔ UR278 and the cord-level verification of Urton's own predictions (e.g. the 4-cord → 3-cord phase transition on UR268 at p93).

## Install

```bash
pip install khipu-reader==0.3.0
```

## References

- Sivan, J. (2026). *The Khipu as a Layered Information System*. ALBA Project preprint.
- Sivan, J. (2026). *Ascher Sums as Erasure Codes*. ALBA Project preprint.
- Urton, G. & Chu, A. (2015). Accounting in the King's Storehouse: the Inkawasi Khipu Archive. *Latin American Antiquity* 26(4): 512–529.
- Urton, G. (2017). *Inka History in Knots*. University of Texas Press.
- Ascher, M. & Ascher, R. (1972–1978). *Code of the Quipu: Databook* + monograph.
- GitHub: https://github.com/Alba-Research/KhipuReader
- Zenodo DOI: https://doi.org/10.5281/zenodo.19184002
