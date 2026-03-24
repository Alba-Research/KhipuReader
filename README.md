# 🪢 KhipuReader

**Open-source framework for reading Andean khipus.**

Combines the established **Locke decimal system** (numerical channel, 1923) with the **ALBA syllabary** (textual channel, Sivan 2026) to produce multi-level readings of khipus from the [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository).

> ⚠️ **Research hypothesis.** The ALBA syllabary is a proposed decipherment (p = 0.001, Sivan 2026) — not a confirmed reading system. Use with appropriate scholarly caution. See [the paper](https://doi.org/10.5281/zenodo.XXXXXXX) for methodology, statistical tests, and falsification criteria.

---

## Installation

```bash
pip install KhipuReader
```

On first use, the tool automatically downloads the OKR database from GitHub (~50 MB, requires `git`).

### From source

```bash
git clone https://github.com/alba-project/KhipuReader.git
cd KhipuReader
pip install -e ".[dev]"
```

---

## Quick start

### Python API

```python
from khipu_translator import translate

# Translate a khipu (auto-downloads OKR database on first use)
result = translate("UR039")

# Human-readable summary
print(result.summary())

# Export at different levels
result.to_csv("UR039_cords.csv")        # Level 1: one row per cord
result.to_xml("UR039_records.xml")       # Level 2: structured clusters
result.to_json("UR039_full.json")        # Level 3: full document interpretation

# Access data programmatically
df = result.level1_dataframe()           # pandas DataFrame
records = result.level2_records()        # list of dicts
document = result.level3_document()      # nested dict
```

### Command line

```bash
# Translate a khipu
khipu translate UR039

# French glosses
khipu translate AS030 --lang fr

# Export to files
khipu translate UR039 --json output.json --csv cords.csv --xml records.xml

# Browse the database
khipu list                    # all 619 khipus
khipu search Pachacamac       # search by keyword
khipu info UR039              # metadata for one khipu

# View the syllabary
khipu syllabary
```

---

## Three levels of translation

Khipus are structured data objects — closer to spreadsheets than books. A single "translation" needs multiple views:

### Level 1 — Cord (raw data)

Each cord gets one row with all channels decoded:

| cord_id | type   | color | level | locke_value | alba_reading | alba_gloss_en | confirmed |
|---------|--------|-------|-------|-------------|-------------|---------------|-----------|
| 42301   | INT    | W     | 1     | 150         |             |               |           |
| 42302   | STRING | MB    | 1     |             | llaqa       | village       | ✓         |
| 42303   | STRING | AB    | 2     |             | qaqa        | rock/mountain | ✓         |

### Level 2 — Record (structured)

Cords grouped by cluster, like rows in a spreadsheet. Exported as JSON or XML with the khipu's hierarchical structure preserved.

```xml
<khipu id="UR268" provenance="Incahuasi" document_type="labor_tribute">
  <cluster index="1" total_value="15030">
    <cord id="42301" type="INT" color="W">
      <value>15030</value>
    </cord>
    <cord id="42302" type="STRING" color="MB">
      <reading confirmed="true">llaqa</reading>
      <gloss>village</gloss>
    </cord>
  </cluster>
</khipu>
```

### Level 3 — Document (interpreted)

Full interpretation: document type detection, vocabulary analysis, archaeological context. This is the "what does it say?" view.

---

## How it works

The khipu is a **layered information system** (Sivan 2026):

| Layer | Khipu component | What it encodes |
|-------|----------------|-----------------|
| 1. Format | Structural clusters (5 types) | How data is organized |
| 2. Metadata | Cord color, direction, depth | How data is classified |
| 3. Numbers | Simple knots (Locke system) | Quantitative values |
| 4. Text | Long knots + figure-eight (ALBA) | Qualitative labels |

The **5.4% of knotted cords** that carry multiple long/figure-eight knots are incompatible with the Locke decimal system. These "STRING" cords are candidates for textual encoding.

### The ALBA syllabary v3 (13 base symbols + positional polyphony)

Three symbols read differently depending on position: **onset** (first knot in a word) vs **coda** (last knot). This positional polyphony follows natural phonological patterns — weaker consonants in coda, stronger in onset.

| Knot | Turns | Onset (1st position) | Coda (other positions) | Confidence |
|------|-------|---------------------|----------------------|------------|
| L0   | 0     | lla                 | lla                  | High       |
| L2   | 2     | **chi**             | ki                   | High / High |
| L3   | 3     | ma                  | ma                   | High       |
| L4   | 4     | ka                  | ka                   | High       |
| L5   | 5     | ta                  | ta                   | High       |
| L6   | 6     | pa                  | pa                   | High       |
| L7   | 7     | **wa**              | y                    | High / High |
| L8   | 8     | **cha**             | na                   | High / High |
| L9   | 9     | pi                  | pi                   | High       |
| L10  | 10    | si                  | si                   | Medium     |
| L11  | 11    | ti                  | ti                   | Low        |
| L12  | 12    | ku                  | ku                   | Low        |
| E    | fig-8 | (text flag)         | qa                   | High       |

**16 effective symbols** (13 base + 3 onset variants: wa/y, cha/na, chi/ki).

The v3 polyphony was discovered by exhaustive scan of the OKR: +229 cords gained, 0 losses. Zero-loss property: every cord matching under v2 also matches under v3. Words previously unspellable become readable: *wasi* (house), *chaki* (foot), *pacha* (earth), *wata* (year), *chiqa* (truth).

---

## Project structure

```
KhipuReader/
├── src/khipu_translator/
│   ├── __init__.py          # Public API
│   ├── syllabary.py         # ALBA syllabary (13 symbols + onset polyphony)
│   ├── locke.py             # Locke decimal system decoder
│   ├── dictionary.py        # Quechua/Aymara dictionary & morphology
│   ├── translator.py        # Core translation engine (3 levels)
│   ├── database.py          # OKR database interface (auto-download)
│   ├── cli.py               # Command-line interface
│   ├── data/                # Bundled dictionaries
│   └── exporters/           # Export format modules
├── tests/                   # Unit tests
├── docs/                    # Documentation
├── pyproject.toml           # Package configuration
├── LICENSE                  # MIT
└── README.md
```

---

## Contributing

This is an open research project. Contributions welcome:

- **Linguists:** Improve the Quechua/Aymara dictionary and morphological analysis
- **Archaeologists:** Validate readings against site contexts
- **Developers:** Add export formats, improve CLI, write documentation
- **Statisticians:** Run additional permutation tests, improve document-type detection

```bash
# Development setup
git clone https://github.com/alba-project/KhipuReader.git
cd KhipuReader
pip install -e ".[dev]"
pytest
```

### Key areas for improvement

1. **Dictionary expansion** — digitize colonial Quechua dictionaries (González Holguín 1608)
2. **Fiber channel** — integrate Hyland (2017) fiber/ply data when available in OKR
3. **Visualization** — HTML/SVG renderer for khipu structure
4. **Bilingual matching** — tools to compare readings with colonial Spanish transcripts
5. **Statistical validation** — permutation test framework for new khipus

---

## Citation

If you use this tool in research, please cite:

```bibtex
@article{sivan2026khipu,
  title={The Khipu as a Layered Information System: Document Types, Metadata, 
         and a Proposed Syllabic Content Channel},
  author={Sivan, Julien},
  journal={ALBA Project Preprint},
  year={2026},
  doi={10.5281/zenodo.XXXXXXX}
}
```

---

## Related projects

- [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository) — The OKR database (619 khipus)
- [ALBA Project](https://alba-project.org) — The research project behind the syllabary

---

## License

MIT — see [LICENSE](LICENSE).
