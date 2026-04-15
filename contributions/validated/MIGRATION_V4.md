# Knowledge JSON v4 migration log

Tracks the v4 schema migration of `contributions/validated/*.json`.
See `SCHEMA.md` for the target fields; see `scripts/migrate_knowledge_to_v4.py` for the semi-automated pipeline.

## Statuses

| Status | Meaning |
|---|---|
| `pending` | Not yet touched |
| `auto-migrated` | Script emitted a candidate with narrative + attribution; awaiting review |
| `reviewed & committed` | Human-polished and committed into `URxxx.json` in place |
| `needs_full_manual_drafting` | Legacy JSON has no THE STORY / ATTRIBUTION markers — drafted from scratch in a follow-up batch |

---

## Priority batch (2026-04-15)

The seven khipus featured in the Translate-view redesign.

| Khipu | Status | Notes |
|---|---|---|
| UR055 | reviewed & committed | Auto-migrated (3348c narrative, 3 prior + 4 v3, 4 companions). Polished: companion relations (`other` → `same_document_type` / `paired_twin` / `same_provenance`); `v3_contribution` labels cleaned into noun phrases; 4-axis confidence hand-filled. |
| UR266 | reviewed & committed | Auto-migrated (3220c narrative, 4 prior + 3 v3, 8 companions). Polished companion relations and added `evidence` object for UR278 recap (statistical, p=1e-5, matches=7). |
| UR278 | reviewed & committed | Attribution-only from script; narrative drafted from scratch (2923c). 7 companions with bidirectional `audit_target` to UR266. Confidence axes reflect the classification shift from astronomical_journal. |
| UR268 | reviewed & committed | Attribution-only from script; narrative drafted from scratch (3521c). 6 companions, including `cross_khipu_signal` to UR266 (shared presentation binding). |
| UR050 | needs_full_manual_drafting | Legacy JSON predates v3 ATTRIBUTION convention. No THE STORY section. Defer to follow-up batch. |
| UR039 | needs_full_manual_drafting | Same — legacy pre-v3 JSON. Follow-up batch. |
| UR112 | needs_full_manual_drafting | Same — legacy pre-v3 JSON. Follow-up batch. |

**Batch summary** : 4 / 7 priority khipus fully migrated; 3 deferred to follow-up. API returns `null` on v4 fields for the deferred trio; frontend degrades gracefully.

---

## Follow-up batches

The remaining ~63 JSONs plus the 3 deferred priority khipus, migrated over subsequent sessions. Run

```bash
python scripts/migrate_knowledge_to_v4.py --report UR050 UR039 UR112 ...
```

first to scope each khipu's status before committing.

| Khipu | Status | Notes |
|---|---|---|
| — | — | To be populated as follow-up batches ship |

---

## Per-khipu migration workflow

1. Run `python scripts/migrate_knowledge_to_v4.py URxxx` → emits `URxxx.v4.json` candidate (does NOT overwrite).
2. Human opens both files side-by-side and verifies:
   - `narrative` captures the story cleanly (no ATTRIBUTION bleed)
   - `attribution.prior_work` / `v3_contribution` bullets correctly split (look for `citation: see text` rows and add proper citations)
   - `companions[*].relation` direction is right (easy to flip `audit_recap` ↔ `audit_target`; default `other` should be refined)
   - `confidence_axes` filled in by hand (4 axes, 4 levels, notes explaining each judgement)
3. Fix issues manually in the v4 JSON.
4. Run `python scripts/migrate_knowledge_to_v4.py --apply URxxx` to overwrite the original JSON in place.
5. Commit with message `knowledge: migrate URxxx to v4 schema (reviewed)`.
6. Tick the row in this table.

**No silent automated commits.** The script emits candidates, humans ship.
