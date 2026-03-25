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
        "summary": ("Astronomical observation journal, dated June 1473 CE (Leymebamba). "
                    "24 months x 9 columns tracking Moon (mama), Mars (kama/maki), "
                    "Pleiades (kaki), Scorpio (chaki), and dark constellations (qaqa). "
                    "10 celestial labels identified. Multi-object dating (5 objects "
                    "simultaneously) yields p=0.0002, survives Bonferroni correction. "
                    "Cross-validated: P8=13 matches 12-day Pleiades invisibility, "
                    "Mars opposition = highest monthly total, local climate in P9. "
                    "Third site confirmed: AS070 (Mollepampa) shares 6/7 labels."),
        "confidence": "High (multi-object dating p=0.0002, 5 cross-validations, 3 independent sites)",
        "interpretation": """IDENTIFICATION
  Monthly astronomical observation journal kept at Leymebamba.
  874 cords = largest translated khipu in the corpus.
  9-column standardized format, 24 monthly observations.
  Date: June 1473 CE (multi-object astronomical dating, p=0.0002).

DATING
  Multi-object method: Mars (35%), Jupiter (20%), Saturn (15%),
  Scorpio/Antares (15%), Pleiades (15%) correlated simultaneously
  with UR006's 24 monthly section totals.
  Best fit: June 1473 (r_combined=0.703). Permutation test: p=0.0002.
  Bonferroni correction (0.05/86 = 0.0006): SURVIVES (p < threshold).
  Historical context: Tupac Inca conquered Leymebamba ~1470-1475.
  The catalog documents June 1473 to May 1475 = consolidation period.
  Cross-validation: UR220 (Ica) = 1473/02 by header dating = same year,
  different site, different method.

FORMAT
  Alternating structure: large data clusters (daily detail) separated by
  summary cords with 9 L2 subsidiaries (monthly totals).
  Column names written in months 3-5 at odd positions (1,3,5,7,9),
  then never repeated — headers written once like a lab notebook.
  Month 5 is a TOTAL row (P8=521 = sum of all other Moon values +/-1).

THE 9 COLUMNS
  P1 = Observation count (small integers 1-7)
  P2 = Binary flag: observation performed yes/no
  P3 = Position/duration — Pleiades tracking from month 5
  P4 = Secondary count
  P5 = Mars events (months 1-4), then heliacal rising/setting (months 5+)
  P6 = Additional count/flag
  P7 = Dark constellations (Milky Way) — correlated with P8 (r=0.90)
  P8 = Moon (Mama Killa) — never changes assignment
  P9 = Clear nights available (mode=20 = 67% = Leymebamba climate)

CELESTIAL LABELS (10 identified, glossary v3)
  HIGH:   mama=Moon, kama=Mars(events), qaqa=dark constell., kaki=Pleiades,
          chaki=Scorpio (Chaki T'aklla = foot-plough, Runasimi dictionary)
  MEDIUM: maki=Mars(observations), paka=heliacal setting, maqa=eclipse
  LOW:    taki=Saturn?, chapa=guardian star?, mapa=?

5 SECTION-LEVEL CROSS-VALIDATIONS (June 1473)
  1. Section 1 (Jun 73): P8=13 vs 12-day Pleiades invisibility (diff 1 day)
  2. Section 12 (May 74): Pleiades invisible (elong=-2 deg)
  3. Section 9 (Feb 74): Mars at opposition (+161 deg) = highest total (83)
  4. Sections 17-24: Mars near Sun (16-31 deg) = lowest totals (11-39)
  5. Section 11 (Apr 74): Pleiades heliacal rise (+27 deg), P9=3 (special)

OBSERVATORY NETWORK
  3 confirmed sites with shared 9-column format:
  - UR006 (Leymebamba, 1473): 10 labels, 24 months
  - UR1145 (Pachacamac, 1481-1533): 7 labels, 52-year catalog
  - AS070 (Mollepampa): 5 labels, 6-level hierarchy

WHAT DOES NOT WORK
  Single-planet cumulative alignments (total=1772d = 3x Venus) fail
  permutation test (p=0.22). The multi-object method supersedes this.""",
        "references": [
            "Sivan 2026, ALBA Project",
            "Sivan 2026, Dating the Inca Archive",
            "Blas Valera, Pachaquipu (1618)",
            "JPL DE431t ephemerides",
            "Runasimi astronomical dictionary (Lucre, Cusco)",
            "Thompson 2024, Ethnohistory (AS069/AS070 pivot pair)",
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
    "UR055": {
        "summary": ("Oracle verdict — the longest text in the corpus. 180 cords, 96% STRING, "
                    "all in LK (black = governance text). Symmetric structure 89+pivot+89. "
                    "A land dispute: the father (papa) hid something about his terrain (pata). "
                    "The intendant (wapa, ~30 occurrences) renders the verdict at a huaca "
                    "(sacred site). The pivot (cords 87-94) contains: silence, 'this' (chayy), "
                    "'intendant-father', 3 empty HB cords (color change = solemn silence), "
                    "then [10] = the sentence. 90.9% total coverage after Locke Word Splitting."),
        "confidence": "Medium (90.9% coverage, coherent narrative, but many short fragments remain ambiguous)",
        "interpretation": """IDENTIFICATION
  180 cords, 172 STRING (96%), 1 cluster, all LK (black = text/governance).
  Museo Oro, Fundacion Miguel Mujica Gallo, Lima.
  The longest continuous text in the entire khipu corpus.
  Symmetric structure: 89 + pivot (6 cords) + 89.

LOCKE WORD SPLITTING
  Before splitting: 149 unique 'words', 17% dictionary hits.
  After splitting: 90 unique words, 72% dictionary hits, 90.9% total coverage.
  Long 'words' (7-13 syllables) were actually multiple words encoded on
  one cord, separated by knot_value_type positional resets.

THE STORY: LAND DISPUTE BEFORE THE ORACLE
  Part 1 (cords 1-86): The case is presented.
    - Opening: ritual formula (pama) for the fathers (papapa) at the huaca (waka)
    - The terrain (pata) of the father (papa) is disputed
    - A guardian (chapa) is involved
    - Constant interrogatives: pi (who?), pita (who-ACC), pinay (who-OBL)
    - The intendant (wapa) presides — appears ~30 times
    - The father has HIDDEN something (papapaka = father+hidden, x3)
    - Year (wata) references = temporal dimension of the dispute

  Pivot (cords 87-94): THE VERDICT
    87: wa + siy (and also)
    88: (empty)
    89: chayy = THIS (emphatic)
    90: wapapapa = intendant + father
    91-93: empty x3, color HB (ONLY non-LK cords = solemn silence)
    94: [10] = THE SENTENCE (the only number in the body)

  Part 2 (cords 95-180): The resolution.
    95-101: father+hidden, father+terrain, year+huaca, this+hidden
    158: tapa = PROTECTION (granted)
    159: ma + kama = the authority DECIDES
    178: paka + tata = hidden + father (the father's secret)
    179: waka + watata = huaca + year-ACC (the sacred year)
    180: wapa = INTENDANT (final word = the authority closes)

KEY VOCABULARY
  wapa (intendant/economist): ~30x — the presiding authority
  papa (father): ~15x — the accused
  pata (terrain/plot): ~10x — the disputed property
  chapa (guardian): ~10x — the guardian of the terrain
  wata (year): ~8x — temporal references
  pi/pita/pinay (who?): ~8x — interrogatives (it's a trial)
  paka (hidden/secret): ~5x — what the father concealed
  waka (huaca/sacred): ~3x — the sacred site of judgment

COMPARISON WITH UR1091
  UR055 = the full ORATION of an oracle verdict (180 cords, text)
  UR1091 = the administrative FORM of a murder case (89 cords, data)
  Both are judicial, both have an intendant, both have a sentence.
  Different formats for the same function: Inca justice.""",
        "references": [
            "Sivan 2026, ALBA Project",
            "Locke Word Splitting: knot_value_type positional resets",
            "Compare UR1091 (judicial dossier, murder case)",
        ],
    },

    "AS069": {
        "summary": ("Astronomical observation catalog, dated April 1453 CE (Lluta Valley, "
                    "Arica, Chile). The world's largest khipu (1,831 cords). 6/10 ALBA "
                    "celestial labels: kaki(Pleiades) x3, maki(Mars-obs) x3, maqa(eclipse) x3, "
                    "qaqa(dark constell.) x2, paqa(heliacal) x1, waqa x1. Flat table format "
                    "(7 columns x ~130 sections). Peak total 1616 at section 20 = Mars+Jupiter "
                    "double opposition (Dec 1454). p<0.00001, survives Bonferroni. "
                    "Paired with AS070 (Thompson 2024): same data in hierarchical format."),
        "confidence": "High (p<0.00001, Bonferroni OK, cross-validated with UR006 Mars cycle)",
        "interpretation": """IDENTIFICATION
  World's largest khipu: 1,831 cords, 458 groups.
  Lluta Valley, Arica, Chile. Owner: Percy Dauelsberg.
  KFG ref: KH0082. Ascher ref: AS069.
  Flat table format, 7 columns (Thompson 2024).
  Date: April 1453 CE (multi-object astronomical dating, p<0.00001).

DATING
  Multi-object correlation with 130 non-zero sections.
  Best fit: April 1453 (r=0.330, p<0.00001, survives Bonferroni).
  Peak 1616 at section 20 (Nov 1454) = Mars opposition (154 deg)
  + Jupiter quasi-opposition (172 deg) = double opposition event.
  Second peak 866 at section 28 (Jul 1455) = Saturne (112 deg),
  not Mars (38 deg) — multi-planetary tracking.

CROSS-VALIDATION WITH UR006
  AS069 covers ~1453-1465, UR006 covers 1473-1475. No overlap but
  same Mars clock: 5 Mars oppositions in AS069 (Dec 54, Jan 57,
  Feb 59, Mar 61, Apr 63), spaced 25-26 months = exact synodic cycle.
  UR006 Mars opposition (Feb 1474) = 5 cycles after AS069's last.

PAIRED WITH AS070
  Thompson (2024, Ethnohistory) demonstrated AS069 and AS070 encode
  the same data: AS069 as flat table, AS070 as 6-level hierarchy.
  A "pivot table" pair. AS070 has 7/10 astro labels vs AS069's 6/10.

CELESTIAL LABELS (6/10)
  kaki(Pleiades) x3, maki(Mars-obs) x3, maqa(eclipse) x3,
  qaqa(dark constell.) x2, paqa(heliacal) x1, waqa x1.
  Notable: maqa x3 = highest eclipse count in corpus.

HISTORICAL CONTEXT
  1453 = early reign of Pachacutec. The oldest dated astronomical
  khipu. Created at the southern frontier (Arica) during the first
  Inca expansions. The world's largest khipu = the empire's first
  great astronomical catalog.""",
        "references": [
            "Thompson 2024, Ethnohistory (AS069/AS070 numerical connection)",
            "Sivan 2026, ALBA Project",
            "JPL DE431t ephemerides",
        ],
    },

    "AS070": {
        "summary": ("Astronomical observation catalog in hierarchical format (Mollepampa, "
                    "Arica, Chile). 588 cords, depth 6 (deepest in corpus). "
                    "Companion of AS069 (Thompson 2024): same data reorganized as a "
                    "6-level tree. 7/10 ALBA celestial labels: chaki(Scorpio), "
                    "kaki(Pleiades), qaqa(dark constell.), maki(Mars), taki(Saturn?), "
                    "paqa(heliacal), waqa. Third confirmed astronomical site after "
                    "Leymebamba and Pachacamac. Dated ~April 1453 (same as AS069)."),
        "confidence": "High (7/10 astro labels, paired with AS069, Thompson 2024)",
        "interpretation": """IDENTIFICATION
  588 cords, 6 levels deep (deepest schema in corpus).
  Mollepampa, Arica, Chile. Museo Chileno de Arte Precolombino.
  KFG ref: KH0083. Ascher ref: AS070. Urton ref: UR035.
  Date: ~April 1453 (same period as paired khipu AS069).

PAIRED WITH AS069
  Thompson (2024, Ethnohistory) proved AS069 and AS070 encode the
  same data: AS069 as flat table (7 cols x ~130 sections), AS070
  as 6-level hierarchy. The rows of one are the columns of the other.
  A "pivot table" pair — the first documented in khipu studies.

CELESTIAL LABELS (7/10 — more than AS069)
  HIGH:   chaki(Scorpio) x1, kaki(Pleiades) x2, qaqa(dark constell.) x2
  MEDIUM: maki(Mars-obs) x1
  LOW:    taki(Saturn?) x3, paqa(heliacal) x1, waqa x1
  Notable: chaki (Scorpio) = astro-exclusive label, only on astro khipus.
  taki x3 on AS070 but 0 on AS069 — Saturn tracked in hierarchical
  format but not in flat format?

STRUCTURE
  Red (SR) cords = section separators (clusters 1, 2, 13).
  Astronomical labels at depth L3-L5 = sub-category tags.
  This is the deepest astronomical document: 6 levels of hierarchy
  for organizing multi-object observations.

OBSERVATORY NETWORK
  4th confirmed astronomical khipu (with AS069 as paired companion):
  - AS069/AS070 (Arica, 1453): flat + hierarchical pair
  - UR006 (Leymebamba, 1473): 9-column journal
  - UR1145 (Pachacamac, 1516): label-measure catalog""",
        "references": [
            "Thompson 2024, Ethnohistory (AS069/AS070 numerical connection)",
            "Sivan 2026, ALBA Project",
            "Runasimi astronomical dictionary (Lucre, Cusco) — chaki=Scorpio",
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

NOTE ON THE WORD "DEATH"
  The Quechua word wañuy (to die) appears to be unwritable in ALBA
  because the phoneme ñ (palatal nasal) has no known knot encoding.
  If correct, this would require the scribe to use a periphrasis such
  as "tana mana" (the support is no more) instead of a single word.
  This is a tentative observation — the reading of UR1091 as a murder
  case is one plausible interpretation among others.""",
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
