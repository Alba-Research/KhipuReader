# Knowledge JSON v4 schema

**Version**: 4 (introduced 2026-04-15)
**Scope**: every file under `KhipuReader/contributions/validated/*.json`
**Backward compatibility**: the v3 schema is a strict subset. Legacy fields (`interpretation`, `confidence`, `document_type_override`, `references`, `reconstructed_xlsx`) are kept verbatim. New v4 fields are **additive and optional** — a consumer must treat them as `null` when absent.

---

## 1. Top-level shape

```jsonc
{
  // ── identity ────────────────────────────────────────────────
  "khipu":       "UR050",                      // required, string, matches OKR INVESTIGATOR_NUM
  "contributor": "Julien Sivan <…@alba-project.org>",  // required, string
  "date":        "2026-04-14",                 // required, ISO 8601 YYYY-MM-DD
  "status":      "proposed",                   // required, enum (see §2)

  // ── classification (v3) ─────────────────────────────────────
  "document_type_override": "commodity_accounting",   // required, string
  "reader_version":         "v3 (merged OKR*KFG + Ascher layer)",  // required, string
  "confidence":             "medium-high",     // required, legacy 4-tier label (see §3)

  // ── prose (v3 legacy) ───────────────────────────────────────
  "summary":        "2-5 sentences …",         // required, string
  "interpretation": "long markdown blob …",    // required in v3; v4 keeps it verbatim (legacy rollup)

  // ── v4 additive fields ─────────────────────────────────────
  "narrative":        "…",                     // optional, string | null
  "attribution":      { … },                   // optional, object | null  (see §4)
  "companions":       [ … ],                   // optional, array           (see §5)
  "confidence_axes":  { … },                   // optional, object | null  (see §6)

  // ── other legacy ────────────────────────────────────────────
  "references":         [ "…" ],               // required, array of strings
  "reconstructed_xlsx": null                   // required, string | null
}
```

---

## 2. `status` enum

| Value | Meaning |
|---|---|
| `draft` | Work-in-progress, not yet peer-reviewed |
| `proposed` | Published as a deep-read hypothesis; open to review |
| `validated` | Reviewed and accepted by peer experts (not yet used in the corpus) |
| `retracted` | Previously proposed, subsequently withdrawn |

---

## 3. `confidence` (legacy, 4-tier)

`low | medium | medium-high | high`

The v4 fine-grained alternative is `confidence_axes` (§6). Consumers that render a single confidence chip should use `confidence_axes` when present, fall back to this field otherwise.

---

## 4. `attribution` (object | null)

Separates prior scholarship from the contribution of this specific deep read.

```jsonc
"attribution": {
  "prior_work": [
    {"citation": "Urton & Chu 2015", "contribution": "Identified the 47-constant as a peanut-khipu signature"},
    {"citation": "Rostworowski 1999", "contribution": "Quechua polysemy of kaki = Pleiades = Qollqa"}
  ],
  "v3_contribution": [
    {"label": "Syllabary readings", "detail": "ALBA syllabary resolved 142 of 322 cords as lexical tokens"},
    {"label": "Cross-khipu signal", "detail": "UR266 transcribes UR278's row totals R1–R8 in order (null p < 1e-5)"}
  ]
}
```

### Constraints
- `prior_work[*]` : required keys `citation` (string, free-form scholarly ref) and `contribution` (string, one-line description of what the prior work contributed).
- `v3_contribution[*]` : required keys `label` (short noun-phrase, string) and `detail` (string, one-line specific claim).
- Either array may be empty `[]`; the object itself is `null` when the khipu has no ATTRIBUTION block authored yet.

---

## 5. `companions` (array)

Khipus linked to this one, rendered by the frontend as navigable chips.

```jsonc
"companions": [
  {
    "id":       "UR055",
    "relation": "paired_twin",
    "note":     "Black oracle counterpart of this white cadastral register"
  },
  {
    "id":       "UR266",
    "relation": "audit_recap",
    "note":     "This khipu's row totals R1–R8 are transcribed by UR266",
    "evidence": {
      "type":    "statistical",
      "p_value": 1e-5,
      "matches": 7
    }
  },
  {
    "id":       "UR278",
    "relation": "audit_target",
    "note":     "Inverse of UR266.audit_recap — transcribes THIS khipu's totals"
  }
]
```

### 5.1 `relation` enum

| Value | Meaning | Directionality |
|---|---|---|
| `paired_twin` | Same ledger in inverted convention (e.g. white/black) | symmetric |
| `audit_recap` | This khipu recaps / summarises the other | this → other |
| `audit_target` | This khipu is recapped by the other (inverse of `audit_recap`) | other → this |
| `same_provenance` | Both from the same excavation unit (same UE, same site) | symmetric |
| `same_document_type` | Same classification, useful for browsing siblings | symmetric |
| `cross_khipu_signal` | Statistical or structural match without clear recap direction | symmetric |
| `parent` | This khipu is the head/root; the other is a member of the cluster | this → other |
| `child` | This khipu is a member; the other is the cluster head | other → this |
| `other` | Relationship exists but does not fit the above | — |

**Bidirectional navigation**: `audit_recap` and `audit_target` are inverses. UR266 has `{id: UR278, relation: audit_recap}`; UR278 has `{id: UR266, relation: audit_target}`. Same for `parent`/`child`. Both entries live in each khipu's own JSON.

### 5.2 `evidence` (optional object)

When the link is quantified, include the supporting signal.

```jsonc
"evidence": {
  "type":    "statistical",   // statistical | structural | semantic | colour | other
  "p_value": 1e-5,            // present when type == "statistical"
  "matches": 7,               // count of matching items (cords, sequences, etc.)
  "note":    "…"              // optional free-text qualifier
}
```

Omit `evidence` entirely when the link is an editorial judgement (e.g. `same_provenance`).

---

## 6. `confidence_axes` (object | null)

Four separate axes. Each has a `level` (4-tier) and an optional `note` explaining the judgement.

```jsonc
"confidence_axes": {
  "word_reading": {
    "level": "high",
    "note":  "142/322 cords glossed via ALBA syllabary (43% dict-confirmed)"
  },
  "document_type": {
    "level": "high",
    "note":  "commodity_accounting score 5.4 vs runner-up 2.8"
  },
  "narrative": {
    "level": "medium",
    "note":  "Story extrapolates structure from 11 verified Ascher sums"
  },
  "data_integrity": {
    "level": "medium-high",
    "note":  "OKR×KFG agreement 0.99; 11/12 Ascher sums verified"
  }
}
```

### 6.1 The four axes

| Axis | Question it answers |
|---|---|
| `word_reading` | Are the lexical tokens in this khipu confidently glossed by the ALBA syllabary? |
| `document_type` | Is the classification (commodity / cadastral / oracle / …) well-separated from runners-up? |
| `narrative` | How much of the Story is supported by the cords vs extrapolated by the reader? |
| `data_integrity` | How clean is the source data — OKR×KFG agreement, Ascher arithmetic integrity, `L?` gap-fill coverage? |

### 6.2 `level` enum

`low | medium | medium-high | high`

- `low` — many unknowns, reading is speculative
- `medium` — reasoned but with substantive uncertainty
- `medium-high` — strong evidence, minor gaps
- `high` — externally verifiable / corpus-canonical

### 6.3 Authoring

**The contributor fills these by hand**, per khipu. No algorithmic derivation. Each axis is a deliberate scholarly judgement, not a computed metric.

### 6.4 Fallback

- The whole `confidence_axes` object may be `null` when the khipu has not been deep-read beyond the translation.
- Individual axes may be `null` (e.g. a khipu whose narrative has not been drafted yet).

---

## 7. `narrative` (string | null)

Prose-only story. The human-first telling of what this khipu IS, free of citations, free of analytic markers (`p<`, cord ranges, statistical scores), free of ATTRIBUTION bullets.

- Length guidance: 300–800 words for a mid-complexity khipu.
- Style: paragraphs, historical-present voice, cord citations allowed (e.g. "cord 65 is the only number"), no section headers.
- Fallback: `null` when the story has not been drafted yet. The frontend renders the legacy `interpretation` as a fallback.

---

## 8. Note on onset polyphony and `root`

Several v4 consumers (e.g. the API's `vocabulary_grouped` block) use `khipu_translator.dictionary.analyze_morphology` to derive `root`. The syllabary's onset polyphony rules (Sivan 2026) mean:

- `chaqa` → root `naqa` (cha/na onset pair, dictionary-match on `naqa` = slaughter)
- `chiki` → root `kiki` (chi/ki onset pair, dictionary-match on `kiki` = self)
- `wapa` → root `ypa` (wa/y onset pair, dictionary-match on `ypa` = Aymara economist)

This is **semantically correct** but **surprising for casual readers** who see `chaqa` on the cord and read `naqa` in the schema. Consumers rendering UI should expose both:

- the canonical `root` (from morphology) as the grouping key
- the surface `word` (as used on the khipu cord) in the `forms[*].word` field

This is a display/decomposition decision, not a schema constraint.

---

## 9. Migration matrix (v3 → v4)

| v3 field | v4 | Action |
|---|---|---|
| `khipu`, `contributor`, `date`, `status`, `document_type_override`, `reader_version`, `summary`, `references`, `reconstructed_xlsx` | unchanged | keep as-is |
| `interpretation` | legacy rollup | keep as-is; **new** `narrative` / `attribution` / `companions` fields are authored in parallel (the interpretation blob is not deleted) |
| `confidence` | legacy | keep as-is; prefer `confidence_axes` when rendering |
| — | `narrative` | NEW: extract from the `THE STORY` block inside `interpretation`, cleaned of attribution markers |
| — | `attribution` | NEW: extract from the `ATTRIBUTION (prior work vs v3 novelty)` block at the top of `interpretation` |
| — | `companions` | NEW: extract from "see also URxxx" / "twin URxxx" / "recapped by URxxx" mentions |
| — | `confidence_axes` | NEW: AUTHORED BY HAND, 4 axes, 4 levels, no algorithmic derivation |

Migration is semi-automated per `scripts/migrate_knowledge_to_v4.py`. Each migrated candidate is **reviewed by a human** before commit. See `MIGRATION_V4.md` for the batched list.

---

## 10. JSON Schema (draft 7, informal)

For consumers wanting a machine-readable contract, the following JSON Schema fragment captures the v4-only additions. Use alongside §1 for the full shape.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["khipu", "contributor", "date", "status"],
  "properties": {
    "narrative": {"type": ["string", "null"]},
    "attribution": {
      "type": ["object", "null"],
      "properties": {
        "prior_work": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["citation", "contribution"],
            "properties": {
              "citation":     {"type": "string"},
              "contribution": {"type": "string"}
            }
          }
        },
        "v3_contribution": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["label", "detail"],
            "properties": {
              "label":  {"type": "string"},
              "detail": {"type": "string"}
            }
          }
        }
      }
    },
    "companions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "relation"],
        "properties": {
          "id":       {"type": "string"},
          "relation": {"enum": ["paired_twin", "audit_recap", "audit_target",
                                 "same_provenance", "same_document_type",
                                 "cross_khipu_signal", "parent", "child", "other"]},
          "note":     {"type": ["string", "null"]},
          "evidence": {
            "type": ["object", "null"],
            "properties": {
              "type":    {"enum": ["statistical", "structural", "semantic", "colour", "other"]},
              "p_value": {"type": ["number", "null"]},
              "matches": {"type": ["integer", "null"]},
              "note":    {"type": ["string", "null"]}
            }
          }
        }
      }
    },
    "confidence_axes": {
      "type": ["object", "null"],
      "properties": {
        "word_reading":    {"$ref": "#/definitions/axis"},
        "document_type":   {"$ref": "#/definitions/axis"},
        "narrative":       {"$ref": "#/definitions/axis"},
        "data_integrity":  {"$ref": "#/definitions/axis"}
      }
    }
  },
  "definitions": {
    "axis": {
      "type": ["object", "null"],
      "properties": {
        "level": {"enum": ["low", "medium", "medium-high", "high"]},
        "note":  {"type": ["string", "null"]}
      }
    }
  }
}
```

---

## 11. Authoring checklist (for new deep reads)

When writing a new deep-read JSON from scratch, fill:

1. `khipu`, `contributor`, `date`, `status = "proposed"`
2. `document_type_override`, `reader_version`, `confidence` (legacy 4-tier)
3. `summary` (2–5 sentences)
4. `interpretation` (full legacy markdown blob with ATTRIBUTION + sections + THE STORY)
5. **`narrative`** (v4) — extract the pure story from `interpretation`, strip citations
6. **`attribution`** (v4) — structured pairs
7. **`companions`** (v4) — with bidirectional relations filled on both sides
8. **`confidence_axes`** (v4) — 4 axes, hand-filled with justifying notes
9. `references` (array of citation strings)

Migration tool `scripts/migrate_knowledge_to_v4.py` drafts 5–7 from 4 for older JSONs; humans review and add 8.
