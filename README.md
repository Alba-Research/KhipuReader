*[Leer en español](README.es.md)*

# KhipuReader

**An open-source tool for reading Andean khipus using the ALBA syllabary (Sivan, 2026).**

619 khipus survive in museums around the world. Each one is a knotted-cord document from the Inca Empire — a tax record, an astronomical journal, a legal proceeding, a census, a map. We can read the numbers (Locke 1923). We are starting to read the words (ALBA syllabary, Sivan 2026).

KhipuReader translates any khipu from the [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository) — install it, pick a khipu, and read what's on it.

For those who want to go further, the project also hosts a **community effort** to build the reconstructed library of the Inca Empire — one khipu at a time.

## Community progress

```
[======>                        ] 70/619 khipus analyzed (11.3%)
```

| Khipu | Type | Summary |
|-------|------|---------|
| AS069 | Astronomical catalog | Observation catalog, dated April 1453 CE, Lluta Valley |
| AS075 | Pilgrimage register | Pachacamac oracle ceremonies, 186 cords |
| AS076 | Naming ceremony | Identity declaration (rutuchikuy), Paris |
| AS077 | Zone inventory | 4 geographic zones, regular 4-column format, Paris |
| AS080 | Cadastral survey | 6-step surveyor's route with landmarks, Paris |
| HP020 | Cadastral survey | Location instruction, Pachacamac |
| UR006 | Astronomical journal | 24 months x 9 columns, dated June 1473 CE, Leymebamba |
| UR050 | Lineage land registry | Cadastral record on 164 all-white cords |
| UR051 | Labor corvée | Corvée register with chiastic poetic structure, 98 cords |
| UR054 | Physical assets register | Blue twin of UR050 (white land registry), 115 cords |
| UR055 | Succession oracle | Administrator consults oracle, 180 cords, dated Feb 1519 CE |
| UR176 | Judicial proceeding | Murder of Chuquitanta — mother slaughtered, the falcon condemned |
| UR193 | Oracle consultation | Consultation register from Pachacamac, 41 sessions |
| UR1091 | Judicial proceeding | Murder case — death periphrasis (tana mana...llapa) |

Run `khipu progress` to generate the full progress report, or see [PROGRESS.md](PROGRESS.md).

---

## Quick start

### Install

```bash
pip install khipu-reader
```

On first use, the tool automatically downloads the [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository) database (~50 MB).

### Translate a khipu

```bash
khipu translate UR039 --lang en
```

### Find similar khipus

```bash
khipu suggest UR039
```

### Compare two khipus

```bash
khipu compare UR039 UR144
```

### Contribute your reading

```bash
khipu submit UR039          # generates contributions/UR039.json
# Edit the file, add your analysis
# Submit a Pull Request
```

### See what's left to do

```bash
khipu unclaimed             # 549 khipus waiting to be read
```

---

## How it works

Khipus encode information on two channels:

| Channel | Component | Decoding |
|---------|-----------|----------|
| **Numbers** | Simple knots (S-type) | Locke decimal system (1923) — established |
| **Text** | Long knots + figure-eight | ALBA syllabary (Sivan 2026) — proposed |

5.4% of knotted cords carry multiple long/figure-eight knots, making them incompatible with the decimal system. These "STRING" cords are candidates for textual encoding.

### The ALBA syllabary v3

| Knot | Turns | Onset | Coda | Confidence |
|------|-------|-------|------|------------|
| L0 | 0 | lla | lla | High |
| L2 | 2 | **chi** | ki | High |
| L3 | 3 | ma | ma | High |
| L4 | 4 | ka | ka | High |
| L5 | 5 | ta | ta | High |
| L6 | 6 | pa | pa | High |
| L7 | 7 | **wa** | y | High |
| L8 | 8 | **cha** | na | High |
| L9 | 9 | pi | pi | High |
| L10 | 10 | si | si | Medium |
| L11 | 11 | ti | ti | Low |
| L12 | 12 | ku | ku | Low |
| E | fig-8 | — | qa | High |

16 effective symbols. Three onset variants (wa/y, cha/na, chi/ki) follow natural phonological patterns.

> **Research hypothesis.** The ALBA syllabary is a proposed decipherment (p = 0.001) — not a confirmed reading system. Use with scholarly caution.

---

## CLI reference

| Command | Description |
|---------|-------------|
| `khipu translate ID` | Translate a khipu (summary + optional exports) |
| `khipu suggest ID` | Find the 5 most similar khipus |
| `khipu compare ID1 ID2` | Side-by-side comparison |
| `khipu unclaimed` | List unanalyzed khipus |
| `khipu submit ID` | Generate contribution template (JSON) |
| `khipu progress` | Generate PROGRESS.md |
| `khipu list` | List all 619 khipus |
| `khipu search KEYWORD` | Search by provenance, museum, ID |
| `khipu info ID` | Show khipu metadata |
| `khipu syllabary` | Print the ALBA syllabary |

All commands accept `--db path/to/khipu.db` to use a local database.

---

## How to contribute

You don't need to be a Quechua speaker. There are 4 levels:

### Level 1 — Triage
Run `khipu translate` and describe what you see: "looks like a cadastre", "purely numerical", "lots of kinship words". Anyone can do this.

### Level 2 — Context
Research the provenance. What site is it from? What museum? Are there other khipus from the same place? Historians and archaeologists shine here.

### Level 3 — Interpretation
Propose column names, identify the document type, cross-reference with colonial sources. Linguists and Andean specialists needed.

### Level 4 — Reconstruction
Create the "library" Excel file — the khipu as the Inca would have written it in a spreadsheet. The expert level.

### The workflow

```bash
khipu submit UR039                    # 1. Generate template
nano contributions/UR039.json         # 2. Add your analysis
git add contributions/UR039.json      # 3. Commit
# Submit a Pull Request                # 4. Community reviews
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Project structure

```
KhipuReader/
├── src/khipu_translator/    # Core translation engine
├── contributions/           # One JSON per analyzed khipu (community-built)
├── scripts/                 # Validation and reproducibility scripts
├── library/                 # Reconstructed Excel files
├── tests/                   # Unit tests
├── PROGRESS.md              # Auto-generated progress report
├── CONTRIBUTING.md          # How to contribute
└── README.md
```

---

## Reproducibility

All validation scripts referenced in the preprint (Sivan 2026) are in `scripts/`:

| Script | Paper section | What it does |
|--------|:---:|---|
| `brute_force_derivation.py` | 2.4 | Exhaustive search of 46,512 CV mappings on UR039 |
| `negative_controls.py` | 2.8 | Aymara control, pseudo-dictionary, length-preserving shuffle |
| `replication_ur112.py` | 3.2 | Independent replication: all 154,440 mappings on UR112 |
| `export_translations.py` | Suppl. | Cord-by-cord CSV export for all 70 analyzed khipus |

```bash
# Run the brute-force derivation
python scripts/brute_force_derivation.py

# Run all three negative controls
python scripts/negative_controls.py

# Run the independent replication (generates Fig. 3)
python scripts/replication_ur112.py

# Export cord-by-cord translations
python scripts/export_translations.py
```

---

## Citation

```bibtex
@article{sivan2026khipu,
  title={The Khipu as a Layered Information System: Document Types, Metadata,
         and a Proposed Syllabic Content Channel},
  author={Sivan, Julien},
  journal={ALBA Project Preprint},
  year={2026},
  doi={10.5281/zenodo.19184002}
}
```

---

## Data source

This tool reads khipus from the **Open Khipu Repository** (OKR):

> Urton, G. & Brezine, C. (2009–2024). *Open Khipu Repository*.
> Harvard University. DOI: [10.5281/zenodo.5037551](https://doi.org/10.5281/zenodo.5037551)

The OKR database (619 khipus, ~50 MB) is downloaded automatically on first use.

## Related projects

- [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository) — The OKR database
- [ALBA Project](https://alba-project.org) — The research project behind the syllabary

## License

MIT — see [LICENSE](LICENSE).
