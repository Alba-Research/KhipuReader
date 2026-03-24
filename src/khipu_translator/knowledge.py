"""
Knowledge database — what we know about specific khipus.

This module stores research notes, interpretations, and commentary
for khipus that have been analyzed in depth. These notes are included
in the "Resume" sheet of xlsx exports.

Each entry is a dict with:
  - summary: descriptive explanation of what the khipu is and why
  - interpretation: multi-line research notes (English)
  - confidence: overall confidence level
  - references: list of references
  - reconstructed_xlsx: filename of the reconstructed "library" Excel file, if available
"""

from __future__ import annotations

# khipu_id -> knowledge dict
KNOWLEDGE_DB: dict[str, dict] = {

    "UR006": {
        "summary": ("Astronomical observation journal (~1500 CE, Leymebamba). "
                    "24 months x 9 columns tracking Moon, Mars, Pleiades and dark "
                    "constellations. Confirmed by 5 independent proofs: Mars ephemerides "
                    "(r=0.62), Pleiades invisibility matching Blas Valera, eclipse at "
                    "month 9, local climate in P9, and cross-site validation with UR1136."),
        "confidence": "High (5 convergent proofs)",
        "interpretation": """IDENTIFICATION
  Monthly astronomical observation journal kept at Leymebamba for ~5 years (~1500 CE).
  874 cords = largest translated khipu in the corpus.
  9-column standardized format, 24 monthly observations.

FORMAT
  Alternating structure: large data clusters (daily detail) separated by
  summary cords with 9 L2 subsidiaries (monthly totals).
  Column names written in months 3-5 at odd positions (1,3,5,7,9),
  then never repeated — headers written once like a lab notebook.
  Month 5 is a TOTAL row (P8=521 = sum of all other Moon values ±1).

THE 9 COLUMNS
  P1 = Observation count (small integers 1-7)
  P2 = Binary flag: observation performed yes/no
  P3 = Position/duration — Pleiades tracking from month 5
  P4 = Secondary count
  P5 = Mars (months 1-4), then heliacal rising/setting (months 5+)
  P6 = Additional count/flag
  P7 = Dark constellations (Milky Way) — correlated with P8 (r=0.90)
  P8 = Moon (Mama Killa) — never changes assignment
  P9 = Clear nights available (mode=20 = 67% = Leymebamba climate)

5 CONVERGENT PROOFS
  1. PLEIADES: P8=61 days matches Blas Valera's Pachaquipu (63d at Cusco, -2d for latitude)
  2. ECLIPSE: Month 9 highest values, matching Feb 9 1533 total lunar eclipse
  3. MARS: r=0.62, p=0.001 with JPL DE431t ephemerides (only planet that correlates)
  4. CLIMATE: P9 mode=20 = 67% clear nights = Leymebamba cloud forest
  5. CROSS-SITE: UR1136 (Nazca) same 9-column format, 800 km apart = imperial protocol

WHAT DOES NOT WORK
  Cumulative alignments (total=1772d = 3×Venus) fail permutation test (p=0.22).
  Mars dating uncorrected for multiple comparisons.""",
        "references": [
            "Sivan 2026, ALBA Project",
            "Blas Valera, Pachaquipu (1618)",
            "JPL DE431t ephemerides",
        ],
        "reconstructed_xlsx": "UR006_observatory_journal.xlsx",
    },

    "AS076": {
        "summary": ("Naming ceremony (rutuchikuy = first hair cutting). 16 cords, "
                    "62% text. Vocabulary is entirely about identity: chiki/chikiki/"
                    "chikikiqa (self/your-identity/regarding-your-identity), plus "
                    "tata (father), mama (mother), taki (ritual song), qaki (frost "
                    "= season or child's name). Same format as AS014 (British Museum)."),
        "confidence": "Medium (vocabulary coherent, structure matches AS014)",
        "interpretation": """IDENTIFICATION
  Naming ceremony record (rutuchikuy = first hair cutting / identity declaration).
  16 cords, 62% STRING — a textual khipu, not numerical.
  Musee de l'Homme, Paris.

VOCABULARY (100% explained)
  chiki (x2) = "self" (onset form of kiki)
  chikiki (x2) = "your identity" (kiki + POSS)
  chikikiqa (x1) = "regarding your identity" (kiki + POSS + TOP)
  tata (x1) = father
  mama (x1) = mother
  taki (x1) = ceremony/ritual song
  chika (x1) = "so much/such"
  qaki (x1) = frost/freeze — season marker or child's name

READING
  Cluster 1 (ceremony): "[2 days of] such ceremony for the self, in frost season.
    1 mother, 2 [children?]"
  Cluster 2 (identity): "[2 declarations of] your identity: father and self.
    2. Regarding your identity: 3. Frost."

  Colors: W(white) = identity data, B(brown) = father/formal acts,
  YB(yellow-brown) = special markers.

  qaki (frost) x2 at positions 5 and 8 = either the SEASON of the ceremony
  (June-July, cold season in the Andes) or the child's NAME ("born during frost").

COMPARISON
  Similar format to AS014 (British Museum) — also identified as rutuchikuy.
  Two naming ceremony khipus in two different museums, same structure.""",
        "references": [
            "Sivan 2026, ALBA Project",
            "Compare AS014 (British Museum naming ceremony)",
        ],
    },

    "HP020": {
        "summary": ("Cadastral survey or location instruction (Pachacamac). 29 cords, "
                    "paired with HP019 (22 cords, same museum, consecutive numbering). "
                    "Contains qaqa(rock) x4, chiqa(benchmark), taqataqa(boundary), plus "
                    "a unique triangulation (7-7 symmetric) pointing to a specific sacred "
                    "rock (qaqaqa on the only GG cord) and a personal signature (takiki). "
                    "6 anomalies distinguish it from a standard cadastre."),
        "confidence": "Medium-High (vocabulary matches UR1095, triangulation structure)",
        "interpretation": """IDENTIFICATION
  29 cords, Museo de Sitio de Pachacamac. Paired with HP019 (22 cords).
  Cadastral vocabulary + anomalous structure suggesting location instruction.

VOCABULARY
  qaqa (x4) = rocky landmarks / toponyms
  chiqa (x1) = survey benchmark (v3: truth/right -> borne)
  maka (x1) = landmark (not weapon — no juridical context)
  chikaqa = "the wall" (chi + kaqa AY)
  qaqaqa = "THE rock" (qa + qaqa, topicalized)
  taqataqa = "boundary" (redoubled: taqa + taqa)
  takiki = "self-mark" (ta + kiki) — surveyor's signature?
  makimaqa = hapax (unique in 619 khipus OKR)

6 ANOMALIES vs standard cadastre:
  1. Too small (29 cords vs 150-971 for normal cadastres)
  2. Single GG cord = sacred marker on "THE rock"
  3. maka without juridical context
  4. makimaqa = hapax (word created for this document)
  5. takiki in a cadastre (never appears in other cadastres)
  6. Symmetric 7-7 triangulation in cluster 5

HP019+HP020 PAIR: consecutive numbering, same museum, complementary vocabulary.
  HP020 = route (how to get there), HP019 = local geometry (what's on site).""",
        "references": [
            "Sivan 2026, ALBA Project",
            "HP019 companion document",
            "UR1095 (Pachacamac full cadastre) for vocabulary comparison",
        ],
    },

    "AS080": {
        "summary": ("Cadastral survey — a 6-step surveyor's route with distances and "
                    "landmarks. All 4 STRING words are cadastral (100% hit rate): "
                    "paqa(east), chiqa(benchmark), taqa(boundary), kaqa(wall). "
                    "Large numbers (170, 70, 50) suggest long distances. "
                    "Same format as HP020 (Pachacamac)."),
        "confidence": "High (4/4 cadastral words, 100% dictionary hits)",
        "interpretation": """IDENTIFICATION
  40 cords, Musee de l'Homme, Paris. Provenance unknown.
  4 STRING words, ALL cadastral: paqa, chiqa, taqa, kaqa (100% hits).

FORMAT
  Cluster 1 = route with 6 waypoints:
    Pos 1: 170 units, direction EST (paqa)
    Pos 2: 70 units, sub-measures 60 + 10
    Pos 3: BOUNDARY (taqa) with measures 20 + 30
    Pos 4: 50 units
    Pos 5: WALL (kaqa, natural limit), 10 units
    Pos 6: 10 units, arrives at BENCHMARK (chiqa)

  Cluster 2 = detail register (8 cords, multi-color L2)
  Cluster 3 = closure (2 cords)

  Colors: BS(brown-sand) = main measurements, GL(olive-green) = annotations/terrain,
  W(white) = data, R(red) = special markers.

  Same format as HP020 (Pachacamac): route + landmarks + distances.""",
        "references": [
            "Sivan 2026, ALBA Project",
            "Compare HP020 (Pachacamac cadastre)",
        ],
    },

    "AS077": {
        "summary": ("Zone inventory — 5 entries in a regular 4-column format "
                    "(flag | place1 | place2 | measurement). All words start with "
                    "qa-: qaqa(rock), qama(dwelling), qaki, qaka = 4 named geographic "
                    "zones. Followed by 4 clusters of pure numbers (recap). "
                    "A mini-cadastre of 4 neighborhoods."),
        "confidence": "Medium (regular 4-column structure, geographic vocabulary)",
        "interpretation": """IDENTIFICATION
  33 cords, Musee de l'Homme, Paris. Provenance unknown.
  9 STRING words, 4 unique: qaki(x4), qaka(x3), qaqa(x1), qama(x1).
  All words start with qa- (geographic vocabulary).

FORMAT
  Clusters 1-5: regular 4-column structure:
    [B/YB] flag=1 | [W] place_name | [AB] place_name | [W] measurement

  4 zone names:
    qaqa = rock/mountain
    qama = dwelling/residential area
    qaki = frost zone? or place name
    qaka = wall/cliff or place name

  Clusters 6-9: numerical summary (no STRING).

  Inventory of 5 geographic zones with one measurement each,
  followed by a numerical recap. Mini-cadastre of 4 named areas.""",
        "references": [
            "Sivan 2026, ALBA Project",
        ],
    },

    "AS075": {
        "summary": ("Pilgrimage register (Pachacamac oracle). 186 cords from Pachacamac. "
                    "4 words in the header match the 4 documented stages of the "
                    "Pachacamac pilgrimage: waqaki(ritual weeping), taki(ceremonial "
                    "song), chaki(walking on foot through 3 enclosures), piqa(ascent "
                    "to the summit/Temple of the Sun). Small monthly counts (1-15) "
                    "= pilgrimage events tracked over ~3 years."),
        "confidence": "Medium (vocabulary matches documented Pachacamac rituals)",
        "interpretation": """IDENTIFICATION
  186 cords, Musee de l'Homme, Paris. Provenance: Pachacamac.
  4 STRING words concentrated in cluster 1 (the header).

VOCABULARY = 4 stages of the Pachacamac pilgrimage:
  waqaki = weeping + POSS = "ritual lamentation" (pilgrims wept before the oracle)
  taki = ceremonial song (accompanied each stage)
  chaki = foot = pilgrimage on foot (through the 3 enclosures)
  piqa = summit = ascent to the Temple of the Sun (highest point)

FORMAT
  Cluster 1 = header with labels + cumulative totals (106, 27, 16)
  Clusters 2-39 = monthly data in 5-6 columns, small values (1-15)
  = counting pilgrimage events per month over ~3 years.

HISTORICAL MATCH
  Documented protocol: pilgrims fasted 20 days, progressed through
  3 successive courts, spent up to 1 year before reaching the holy of holies.
  The 4 words match the 4 documented stages exactly.""",
        "references": [
            "Sivan 2026, ALBA Project",
            "Pachacamac pilgrimage: the-past.com/feature/pachacamac-pilgrimages",
            "Oracle protocol: elmundomagico.org/the-oracle-of-pachacamac",
        ],
    },
    "UR1091": {
        "summary": ("Murder case — the most violent khipu in the corpus. Contains the ONLY "
                    "occurrence of 'mana' (negation) across all 619 khipus. The death of the "
                    "mother (mama) is encoded as a 3-element periphrasis: tana(family support) "
                    "+ mana(no more) + llapa(divine lightning of Illapa). The uncle (kaka x3) "
                    "is the accused, armed with maka (weapon x3). 9 testimony votes of guilty. "
                    "Compensation of 682 units paid to the father. The khipu opens with S0 S0 "
                    "(explicit double-zero) — one of only 2 such cords in the entire corpus — "
                    "signaling the victim is 'counted at zero' = dead."),
        "confidence": "Medium (single occurrence but 4 converging signals: S0 S0 + tana mana + llapa + 4x compensation)",
        "interpretation": """IDENTIFICATION
  89 cords, 21 clusters, 14 STRING. Museum Fur Volkerkunde, Munich.
  9-phase judicial dossier separated by empty cords.
  Contains the ONLY occurrence of "mana" (negation) in 619 khipus.

THE DEATH SIGNAL: 3 ELEMENTS
  1. S0 S0 (cord 2): explicit double-zero = the victim is counted at zero = DEAD.
     Only 2 such cords exist in the entire OKR (54,000 cords). 0.004% frequency.
  2. "tana mana" (cords 6-7): "the family support is no more" = verbal euphemism.
     The word wañuy (to die) cannot be written in ALBA (ñ is not encodable).
     The scribe uses a periphrasis instead.
  3. "llapa" with S-prefix=20 (cord 12): divine lightning of Illapa.
     Illapa "punished wrongdoers by throwing lightning to disappear them from
     this world" (colonial sources). llapa = divine judgment / death sentence.

9-PHASE READING
  Phase 1: [0, 0] + [50, 50, 30, 20]
    → S0 S0 = victim dead. Then: victim's assets (total=150).
  Phase 2: tana(support) mana(no more) maka(weapon) mama(mother) maka(weapon) chiy(?) llapa=20(divine lightning)
    → "The support is no more. Weapon against the mother. Divine judgment."
    → Then: 110, 4, 4, 3, 4 = fine amounts.
  Phase 2b: maka(weapon) kaka(uncle x3) kaki(?)
    → The accused: the uncle, who had the weapon.
  Phases 3-5: 9x figure-eight (value=1 each)
    → 9 testimony votes: GUILTY.
  Phase 6: [13, 21, 6, 5, 12] + mama(mother)
    → Compensation amounts due for the dead mother.
  Phases 7-8: [4,3,3,2,3,3] [5,3,3,2,3,5] [5,2,2,1,1,3]
    → Payment schedule details (symmetric registers).
  Phase 9: papi=10(father?) + [9,10,9,7,6,11,17,6,4,5,7] + 116(total)
    → Closure. Father receives compensation. Final total = 116.

COMPARATIVE EVIDENCE
  UR110 and UR112 have same violence+kinship pattern (maka+kaka+mama)
  but WITHOUT tana/mana/llapa/S0 → assault cases, not murder.
  Their compensation totals (169, 188) are 4x LOWER than UR1091 (682).
  The death markers are what distinguish murder from assault.

LINGUISTIC DISCOVERY
  The Quechua word wañuy (to die) is unwritable in ALBA because the
  phoneme ñ (palatal nasal) has no knot encoding. This forces the scribe
  to use a periphrasis: "tana mana" = "the support is no more".
  This structural limitation of the syllabary explains why "death" never
  appears as a single word in any of the 619 khipus.""",
        "references": [
            "Sivan 2026, ALBA Project",
            "Illapa thunder god: mythlok.com/illapa",
            "Illapa punishment: peruvianshades.com/en/blog/god-of-thunder-lightning-and-rain-illapa",
            "Compare UR110, UR112 (assault without death markers)",
        ],
    },
}


def get_knowledge(khipu_id: str) -> Optional[dict]:
    """Return knowledge entry for a khipu, or None."""
    return KNOWLEDGE_DB.get(khipu_id)
