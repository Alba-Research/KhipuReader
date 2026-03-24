# Contributing to KhipuReader

Thank you for helping read the lost library of the Inca Empire.

## Getting started

```bash
git clone https://github.com/julienTeam/KhipuReader.git
cd KhipuReader
pip install -e ".[dev]"
```

The first time you run a command, the OKR database (~50 MB) will be downloaded automatically.

## The contribution workflow

### 1. Pick a khipu

```bash
khipu unclaimed              # See what hasn't been analyzed yet
khipu translate UR039        # Look at the auto-translation
khipu suggest UR039          # Find similar khipus for comparison
```

### 2. Generate the template

```bash
khipu submit UR039
```

This creates `contributions/UR039.json` pre-filled with the auto-translation.

### 3. Add your analysis

Edit the JSON file:

```json
{
  "khipu": "UR039",
  "contributor": "Your Name <your.email@example.com>",
  "date": "2026-04-15",
  "status": "proposed",
  "confidence": "medium",
  "summary": "Labor tribute register from the Huari region. 5-column format with maki (labor) x15 and kaki (rations) x3, consistent with mit'a work organization.",
  "interpretation": "Your detailed analysis goes here. Cross-reference with other khipus, colonial sources, archaeological context.",
  "auto_translation": { ... },
  "column_names": {
    "P1": "Worker group",
    "P2": "Days worked"
  },
  "references": [
    "Urton 2017, Inka History in Knots",
    "Your source here"
  ],
  "reconstructed_xlsx": null
}
```

**Fields to fill in:**
- `contributor`: Your name and email
- `confidence`: `low`, `medium`, `medium-high`, or `high`
- `summary`: 1-3 sentences explaining what the khipu is and why you think so
- `interpretation`: Detailed analysis (as long as needed)
- `column_names`: If you identified what each column measures
- `references`: Sources you used

**Don't modify:**
- `auto_translation`: This is the machine-generated data for reference

### 4. Submit a Pull Request

```bash
git checkout -b reading/UR039
git add contributions/UR039.json
git commit -m "reading: UR039 — labor tribute register (Huari)"
git push origin reading/UR039
```

Then open a Pull Request on GitHub.

### 5. Community review

At least one other contributor reviews your reading. The status progresses:

- `proposed` — your initial submission
- `reviewed` — at least one peer has reviewed it
- `confirmed` — multiple reviewers agree

## Contribution levels

You don't need to be a Quechua expert. Pick the level that matches your skills:

### Level 1 — Triage
Just run `khipu translate` and describe what you see. "This looks like a cadastre because it has qaqa and taqa." No deep knowledge needed.

### Level 2 — Context
Research the provenance. What site is it from? What museum? Are there other khipus from the same place? Search for the site in the archaeological literature.

### Level 3 — Interpretation
Propose column names, identify the document type, cross-reference with colonial sources (Gonzalez Holguin 1608, Bertonio 1612, Blas Valera).

### Level 4 — Reconstruction
Create the "library" Excel file — the khipu presented as the Inca would have organized it in a modern spreadsheet. Place it in `library/` and reference it in the JSON.

## JSON format reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `khipu` | string | yes | Khipu ID (e.g. "UR039") |
| `contributor` | string | yes | Name and email |
| `date` | string | yes | ISO date (YYYY-MM-DD) |
| `status` | string | yes | `proposed`, `reviewed`, or `confirmed` |
| `confidence` | string | yes | `low`, `medium`, `medium-high`, or `high` |
| `summary` | string | yes | 1-3 sentence description |
| `interpretation` | string | no | Detailed analysis |
| `auto_translation` | object | auto | Machine-generated translation data |
| `column_names` | object | no | Column name mappings |
| `references` | array | no | List of sources |
| `reconstructed_xlsx` | string | no | Filename in `library/` |

## Code contributions

For changes to the translation engine itself:

```bash
pip install -e ".[dev]"
pytest                       # Run tests (34 tests)
ruff check src/              # Lint
```

Key areas where help is needed:
- **Dictionary expansion**: digitize colonial Quechua dictionaries
- **Document type detection**: improve classification accuracy
- **Visualization**: HTML/SVG renderer for khipu structure
- **Statistical validation**: permutation test framework

## Code of conduct

Be respectful. Khipus are the cultural heritage of Andean peoples. Credit your sources. When in doubt, mark your reading as `proposed` with `low` confidence.
