"""
Quechua and Aymara dictionary for khipu translation.

Contains:
  - A word set for dictionary-match validation
  - A glossary mapping words to translations (French/English)
  - Morphological decomposition tools (root + suffix analysis)
  - Compound word detection (root + root)
  - Suffix definitions for Quechua agglutinative grammar

Sources:
  - Kaikki (modern Quechua, 2024)
  - Gonzalez Holguin (colonial, 1608)
  - AULEX (academic, 2005)
  - Manual additions validated by ALBA corpus analysis
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# --- Quechua suffixes --------------------------------------------------------

QUECHUA_SUFFIXES: dict[str, tuple[str, str, str]] = {
    # syllable: (grammatical_label, french, english)
    "ta":  ("ACC",   "objet",        "object"),
    "pa":  ("GEN",   "de",           "of"),
    "y":   ("INF",   "action",       "action/infinitive"),
    "qa":  ("TOP",   "sujet",        "topic/subject"),
    "ki":  ("POSS",  "ton/ta",       "your"),
    "na":  ("OBL",   "lieu/pour",    "place/for"),
    "ku":  ("REFL",  "soi-meme",     "self/reflexive"),
    "ma":  ("DIR",   "vers",         "toward"),
    "ka":  ("PASS",  "passif",       "passive"),
    "si":  ("RECIP", "aussi",        "also/reciprocal"),
    "ti":  ("CAUS",  "faire",        "causative"),
    "lla": ("LIM",   "seulement",    "only/limitative"),
    "pi":  ("INTER", "qui?",         "who?/interrogative"),
}


# --- Glossary ----------------------------------------------------------------

# word -> (french_gloss, english_gloss, domain)
GLOSSARY: dict[str, tuple[str, str, str]] = {
    # Kinship
    "mama":   ("mere",              "mother",           "kinship"),
    "papa":   ("pere/patate",       "father/potato",    "kinship"),
    "tata":   ("pere",              "father",           "kinship"),
    "kaka":   ("oncle maternel",    "maternal uncle",   "kinship"),
    "pana":   ("soeur",             "sister",           "kinship"),
    "nana":   ("douleur/soeur",     "pain/sister",      "kinship"),
    "tayta":  ("seigneur/pere",     "lord/father",      "kinship"),
    "panaka": ("lignee royale",     "royal lineage",    "kinship"),

    # Governance
    "kama":   ("creer/gouverner",   "to create/govern",   "governance"),
    "kamay":  ("creer [INF]",       "to create [INF]",    "governance"),
    "ypa":    ("economiste",        "economist",          "governance"),
    "qapaq":  ("empereur",          "emperor",            "governance"),
    "qapa":   ("noble",             "noble",              "governance"),
    "kapa":   ("noble/riche",       "noble/rich",         "governance"),

    # Geography / cadastral
    "qaqa":   ("roche/montagne",    "rock/mountain",    "geography"),
    "llaqa":  ("village",           "village",          "geography"),
    "pata":   ("terrain/parcelle",  "terrace/plot",     "geography"),
    "mata":   ("bosquet",           "grove",            "geography"),
    "paqa":   ("aube/est",          "dawn/east",        "geography"),
    "kaqa":   ("paroi [AY]",        "wall [AY]",        "geography"),
    "taqa":   ("separer/frontiere", "to separate/boundary", "geography"),
    "siqa":   ("montee/rampe",      "climb/ramp",       "geography"),
    "piqa":   ("sommet",            "summit",           "geography"),
    "qata":   ("pente/toit",        "slope/roof",       "geography"),
    "qama":   ("habiter",           "to dwell",         "geography"),
    "chiqa":  ("verite/droit",      "truth/right",      "geography"),

    # Body / labor
    "maki":   ("main/travail",      "hand/labor",       "labor"),
    "kiki":   ("soi-meme",          "self",             "identity"),
    "siki":   ("base/fond",         "base/bottom",      "body"),
    "chaki":  ("pied",              "foot",             "body"),

    # Actions
    "taka":   ("frapper",           "to hit",           "action"),
    "kata":   ("proteger/dissimuler", "to protect/conceal", "action"),
    "paka":   ("cache/secret",      "hidden/secret",    "action"),
    "maka":   ("arme/massue",       "weapon/club",      "action"),
    "tapa":   ("protection",        "protection",       "action"),
    "paki":   ("casser",            "to break",         "action"),
    "maqa":   ("frapper fort",      "to strike hard",   "action"),
    "naqa":   ("egorger",           "to slaughter",     "action"),
    "kita":   ("fuir",              "to flee",          "action"),
    "wana":   ("corriger/punir",    "to correct/punish","action"),

    # Action infinitives
    "takay":  ("frapper [INF]",     "to hit [INF]",     "action"),
    "katay":  ("proteger [INF]",    "to protect [INF]", "action"),
    "pakay":  ("cacher [INF]",      "to hide [INF]",    "action"),
    "tapay":  ("demander [INF]",    "to ask [INF]",     "action"),
    "makay":  ("combattre [INF]",   "to fight [INF]",   "action"),
    "patay":  ("monter [INF]",      "to ascend [INF]",  "action"),
    "nanay":  ("souffrir [INF]",    "to suffer [INF]",  "action"),

    # Pronouns / grammar
    "pay":    ("il/elle",           "he/she",           "pronoun"),
    "kay":    ("etre",              "to be",            "pronoun"),
    "may":    ("ou (lieu)",         "where",            "pronoun"),
    "nay":    ("ressentir",         "to feel",          "pronoun"),
    "pi":     ("qui (INTER)",       "who (INTER)",      "pronoun"),
    "mana":   ("non/pas",           "no/not",           "grammar"),
    "taq":    ("mais",              "but",              "grammar"),
    "paq":    ("pour (datif)",      "for (dative)",     "grammar"),
    "kaq":    ("le/la (det.)",      "the (det.)",       "grammar"),
    "sina":   ("comme/similaire",   "like/similar",     "grammar"),
    "paypa":  ("son/sa (poss.)",    "his/her (poss.)",  "grammar"),
    "kaypa":  ("de ceci (GEN)",     "of this (GEN)",    "grammar"),
    "kaypi":  ("ici",               "here",             "grammar"),
    "chay":   ("ceci/cela",        "this/that",         "grammar"),

    # Nature / animals
    "llama":  ("lama",              "llama",            "nature"),
    "killa":  ("lune/mois",         "moon/month",       "nature"),
    "llapa":  ("tous/eclair",       "all/lightning",    "nature"),

    # Ritual
    "taki":   ("chant/rituel",      "song/ritual",      "ritual"),
    "napa":   ("salutation",        "greeting",         "ritual"),
    "naku":   ("reciproque",        "reciprocal",       "ritual"),
    "pama":   ("formule",           "formula",          "ritual"),
    "tina":   ("fuseau",            "spindle",          "craft"),

    # Nature / climate
    "qaki":   ("gelee/gel",         "frost/freeze",        "nature"),
    "chika":  ("tant/tellement",    "so much/such",        "grammar"),

    # Astronomy — base glosses (see ASTRO_GLOSSARY for context-dependent meanings)
    "kaki":   ("mais sec/Pleiades", "dried corn/Pleiades", "astronomy"),

    # Juridical
    "llalla": ("mentir/tromper",    "to deceive",       "moral"),
    "qalla":  ("commencer",         "to begin",         "action"),
    "palla":  ("princesse",         "princess",         "kinship"),
    "kipa":   ("apres",             "after",            "time"),

    # Housing / construction
    "tana":   ("pilier",            "pillar",           "housing"),
    "wasi":   ("maison",            "house",            "housing"),
    "chaka":  ("pont",              "bridge",           "housing"),
    "qara":   ("peau/cuir",        "skin/leather",     "material"),

    # v3 onset polyphony words
    "wata":   ("annee",             "year",             "time"),
    "waka":   ("huaca/sacre",       "huaca/sacred",     "ritual"),
    "wayna":  ("jeune homme",       "young man",        "kinship"),
    "waqa":   ("pleurer",           "to cry",           "emotion"),
    "wayta":  ("fleur",             "flower",           "nature"),
    "chama":  ("nourriture/force",  "food/strength",    "body"),
    "chana":  ("secher/canal",      "to dry/canal",     "geography"),
    "chapa":  ("gardien",           "guardian",         "governance"),
    "chaku":  ("chasse communautaire", "communal hunt", "labor"),
    "china":  ("femelle/servante",  "female/servant",   "kinship"),

    # Aymara
    "taypa":  ("centre/milieu [AY]","center [AY]",      "aymara"),
    "tayka":  ("mere/femelle [AY]", "mother [AY]",      "aymara"),
    "masi":   ("compagnon [AY]",    "companion [AY]",   "aymara"),
    "pataka": ("cent [AY]",         "hundred [AY]",     "aymara"),
    "nanaka": ("nous [AY]",         "we [AY]",          "aymara"),
    "kuti":   ("fois/tour [AY]",    "time/turn [AY]",   "aymara"),

    # Misc
    "tama":   ("groupe/troupeau",   "group/herd",       "admin"),
    "tiki":   ("tout/chaque",       "all/each",         "grammar"),
    "kiti":   ("avare",             "miser",            "moral"),
    "paku":   ("champignon",        "mushroom",         "nature"),
    "piki":   ("puce",              "flea",             "nature"),
    "piku":   ("sommet",            "summit",           "geography"),
    "makana": ("massue de guerre",  "war club",         "weapon"),
    "llaki":  ("tristesse",         "sadness",          "emotion"),
}


# --- Astronomical glossary (domain-specific meanings) ------------------------
# Validated on 9 observatories: UR006, UR1136, UR1145, UR1176, AS069, UR270,
# UR278, AS070, UR113. See project_quipu_astro_detailed.md.
# These meanings apply when document_type == "astronomical_journal".

ASTRO_GLOSSARY: dict[str, tuple[str, str]] = {
    # word: (french_astro, english_astro)
    "mama":   ("Lune (Mama Killa)",          "Moon (Mama Killa)"),
    "kaki":   ("Pleiades",                   "Pleiades"),
    "qaqa":   ("constellations sombres (Voie Lactee)", "dark constellations (Milky Way)"),
    "paka":   ("lever/coucher heliaque",     "heliacal rising/setting"),
    "kama":   ("Mars (planete)",             "Mars (planet)"),
    "maki":   ("constellation Main?",        "Hand constellation?"),
    "maqa":   ("eclipse",                    "eclipse"),
    "taki":   ("ceremonie astronomique",     "astronomical ceremony"),
    "llama":  ("constellation Lama (Yacana)","Llama constellation (Yacana)"),
    "pama":   ("formule d'observation",      "observation formula"),
    "chaki":  ("pied (constellation?)",      "foot (constellation?)"),
    "chama":  ("force celeste",              "celestial force"),
    "tama":   ("groupe d'etoiles",           "star cluster"),
    "mata":   ("amas/nebuleuse?",            "cluster/nebula?"),
}


# --- Juridical glossary (domain-specific meanings) ---------------------------
# Validated on 26 juridical khipus cross-corpus.
# See project_quipu_juridical.md.
# These meanings apply when document_type == "judicial_proceeding".

JURIDICAL_GLOSSARY: dict[str, tuple[str, str]] = {
    # word: (french_juridical, english_juridical)
    "taka":   ("violence/agression (chef d'accusation)",  "violence/assault (the charge)"),
    "kata":   ("dissimulation (le delit)",                "concealment (the offense)"),
    "kaka":   ("partie adverse (oncle)",                  "opposing party (uncle)"),
    "tata":   ("plaignant (pere)",                        "plaintiff (father)"),
    "maka":   ("piece a conviction (arme)",               "exhibit/evidence (weapon)"),
    "pata":   ("objet du litige (terrain)",               "disputed property (land)"),
    "tama":   ("objet du litige (troupeau)",              "disputed property (herd)"),
    "llalla": ("fraude",                                  "fraud"),
    "kama":   ("intendant/juge",                          "intendant/judge"),
    "kapa":   ("noble/autorite",                          "noble/authority"),
    "tapa":   ("protection/tutelle",                      "protection/guardianship"),
    "pana":   ("soeur (temoin/victime)",                  "sister (witness/victim)"),
    "mama":   ("mere (temoin/victime)",                   "mother (witness/victim)"),
    "nay":    ("verdict/sentence",                        "verdict/sentence"),
    "piqa":   ("accuse (qui?)",                           "accused (who?)"),
}


# --- Cadastral glossary (domain-specific meanings) ---------------------------
# Validated on 17 cadastral khipus. 174 toponym occurrences cross-corpus.
# See project_quipu_cadastre.md.
# These meanings apply when document_type == "cadastral_survey".

CADASTRAL_GLOSSARY: dict[str, tuple[str, str]] = {
    # word: (french_cadastral, english_cadastral)
    "qaqa":   ("point de repere rocheux / toponyme",      "rocky landmark / toponym"),
    "chiqa":  ("borne d'arpentage",                       "survey benchmark"),
    "taqa":   ("frontiere administrative",                 "administrative boundary"),
    "kaqa":   ("limite naturelle (paroi)",                 "natural boundary (wall)"),
    "paqa":   ("orientation est",                          "east orientation"),
    "siqa":   ("rampe/montee (pyramide)",                  "ramp/ascent (pyramid)"),
    "piqa":   ("point culminant / sommet",                 "summit / highest point"),
    "qama":   ("zone residentielle",                       "residential zone"),
    "qata":   ("pente",                                    "slope"),
    "naqa":   ("lieu-dit (toponyme)",                       "place name (toponym)"),
    "maka":   ("repere / lieu-dit",                        "landmark / place name"),
    "kiki":   ("signature de l'arpenteur",                 "surveyor's mark"),
}


# --- Labor/tribute glossary (domain-specific meanings) -----------------------
# Validated on 15 labor register khipus. 3 formats identified.
# See project_quipu_travail.md.
# These meanings apply when document_type == "labor_tribute".

LABOR_GLOSSARY: dict[str, tuple[str, str]] = {
    # word: (french_labor, english_labor)
    "maki":   ("travail officiel (mit'a)",                "official labor (mit'a)"),
    "kama":   ("superviseur / chef de chantier",          "supervisor / foreman"),
    "kiki":   ("identification du travailleur",           "worker identification"),
    "kaki":   ("rations (mais distribue)",                "rations (distributed corn)"),
    "paki":   ("extraction / construction",               "extraction / construction"),
    "taki":   ("chant rituel de travail",                 "ritual work song"),
    "tama":   ("unite de production (troupeau)",          "production unit (herd)"),
    "kaka":   ("responsable lignee (oncle)",              "lineage chief (uncle)"),
    "tata":   ("responsable (pere)",                      "person in charge (father)"),
    "maka":   ("outil / equipement",                      "tool / equipment"),
    "kata":   ("couverture / protection",                 "cover / protection"),
    "qapa":   ("noble commanditaire",                     "commissioning noble"),
}


# --- Ritual glossary (domain-specific meanings) ------------------------------
# Validated on 3 true ritual khipus (UR055, AS170, AS014).
# See project_quipu_rituel.md.
# These meanings apply when document_type == "ritual_oracle".

RITUAL_GLOSSARY: dict[str, tuple[str, str]] = {
    # word: (french_ritual, english_ritual)
    "nay":    ("voix de l'oracle",                        "voice of the oracle"),
    "taki":   ("ceremonie / rite",                        "ceremony / rite"),
    "pama":   ("paroles rituelles officielles",           "official ritual words"),
    "napa":   ("protocole d'entree",                      "entry protocol"),
    "naqa":   ("sacrifice (lieu sacre)",                  "sacrifice (sacred place)"),
    "maka":   ("offrande d'arme",                         "weapon offering"),
    "mama":   ("Pachamama / deesse mere",                 "Pachamama / mother goddess"),
    "waka":   ("huaca / lieu sacre",                      "huaca / sacred place"),
    "llapa":  ("eclair / Illapa (dieu tonnerre)",         "lightning / Illapa (thunder god)"),
    "kaka":   ("ancetre invoque",                         "invoked ancestor"),
    "tata":   ("ancetre invoque (pere)",                  "invoked ancestor (father)"),
    "paka":   ("element cache/secret du rite",            "hidden/secret element of rite"),
    "kiki":   ("declaration identitaire",                 "identity declaration"),
    "piki":   ("offrande",                                "offering"),
}


# --- Agro-pastoral glossary (domain-specific meanings) -----------------------
# Validated on UR1136 (Nazca, 9-col table, 100% regular).
# These meanings apply when document_type == "agro_pastoral".

AGRO_GLOSSARY: dict[str, tuple[str, str]] = {
    # word: (french_agro, english_agro)
    "kaki":   ("mais (recolte/semis)",             "corn (harvest/sowing)"),
    "kaqa":   ("mur de terrasse",                  "terrace wall"),
    "wama":   ("faucon (marqueur saisonnier)",     "hawk (seasonal marker)"),
    "chaqa":  ("pont / canal d'irrigation",        "bridge / irrigation canal"),
    "taki":   ("chant de semailles",               "sowing song"),
    "paki":   ("defrichage / cassage de terre",    "clearing / breaking ground"),
    "taqa":   ("limite de parcelle",               "plot boundary"),
    "siqa":   ("rampe / montee de terrasse",       "terrace ramp / ascent"),
    "maki":   ("travail des champs",               "field work"),
    "qaqa":   ("rocher (repere de terrain)",       "rock (field landmark)"),
    "chiqa":  ("mesure exacte / borne",            "exact measure / benchmark"),
}


# --- Domain glossary registry ------------------------------------------------
# Maps document_type -> domain-specific glossary

DOMAIN_GLOSSARIES: dict[str, dict[str, tuple[str, str]]] = {
    "astronomical_journal":  ASTRO_GLOSSARY,
    "judicial_proceeding":   JURIDICAL_GLOSSARY,
    "cadastral_survey":      CADASTRAL_GLOSSARY,
    "labor_tribute":         LABOR_GLOSSARY,
    "ritual_oracle":         RITUAL_GLOSSARY,
    "agro_pastoral":         AGRO_GLOSSARY,
}


# --- Dictionary word set (for validation) ------------------------------------

# All words from the glossary + additional attested forms
DICTIONARY: set[str] = set(GLOSSARY.keys()) | {
    # Additional attested forms (roots, inflected, compounds)
    "tatay", "mamay", "kakay", "papay", "yapay",
    "makita", "mamata", "makiy", "pakiy",
    "piqa", "pita", "pika", "piy", "pina", "pipa",
    "sipa", "sipi", "qapi",
    "nama", "mapa", "kaki", "pataki", "kutina",
    "kanana", "pakita", "makatana", "takina", "pakina",
    "wanay", "waqay", "watay", "watana", "wasiy", "wallaqa",
    "waki", "wama", "wapa", "way",
    "chay", "chapi", "chaqa", "challay", "chapay",
    "chiqan", "chikay", "chipa",
    "tay", "qa", "naq", "kiy", "pati", "ysi",
    "naka", "pipi", "pima", "pila", "napi", "mapi", "tapi",
}


# --- Syllable inventory (for morphological decomposition) --------------------

# All syllables the ALBA system can produce, sorted longest-first for greedy match
ALL_SYLLABLES = sorted(
    ["lla", "ki", "ma", "ka", "ta", "pa", "y", "na", "pi", "si", "ti", "ku", "qa",
     "wa", "cha", "chi"],
    key=len, reverse=True,
)


def split_syllables(word: str) -> Optional[list[str]]:
    """
    Split a word into ALBA syllables using greedy longest-match.

    Returns None if the word cannot be fully decomposed.
    """
    syllables: list[str] = []
    i = 0
    while i < len(word):
        matched = False
        for s in ALL_SYLLABLES:
            if word[i:i + len(s)] == s:
                syllables.append(s)
                i += len(s)
                matched = True
                break
        if not matched:
            return None
    return syllables


# Onset polyphony normalization: convert onset forms back to coda forms
# for dictionary lookup. chi→ki, wa→y, cha→na (only in first syllable).
ONSET_TO_CODA = {"chi": "ki", "wa": "y", "cha": "na"}


def normalize_onset(word: str) -> str:
    """
    Normalize a word by converting onset polyphony back to coda form.

    'chiki' → 'kiki', 'waka' → 'yaka', 'chama' → 'nama'

    This allows dictionary lookup of onset-variant words.
    """
    syls = split_syllables(word)
    if not syls or len(syls) < 1:
        return word
    first = syls[0]
    if first in ONSET_TO_CODA:
        syls[0] = ONSET_TO_CODA[first]
    return "".join(syls)


@dataclass
class MorphAnalysis:
    """Result of morphological analysis."""
    word: str
    root: str
    root_gloss_fr: str
    root_gloss_en: str
    suffixes: list[tuple[str, str, str, str]]  # (syllable, label, french, english)
    compound_parts: list[tuple[str, str, str]]  # (root, french, english) for compounds
    is_dictionary_match: bool
    is_decomposable: bool


def analyze_morphology(word: str, lang: str = "en") -> MorphAnalysis:
    """
    Analyze a word's morphological structure.

    Tries in order:
      1. Direct dictionary lookup
      2. Root + 1-3 known suffixes
      3. Compound: root + root (two known words joined)

    Parameters
    ----------
    word : str
        The proposed reading from the syllabary.
    lang : str
        Language for glosses ('en' or 'fr').

    Returns
    -------
    MorphAnalysis
    """
    # 1. Direct match
    if word in GLOSSARY:
        fr, en, _ = GLOSSARY[word]
        return MorphAnalysis(
            word=word, root=word,
            root_gloss_fr=fr, root_gloss_en=en,
            suffixes=[], compound_parts=[],
            is_dictionary_match=True, is_decomposable=True,
        )

    # 1b. Try onset-normalized form (chi→ki, wa→y, cha→na)
    normalized = normalize_onset(word)
    if normalized != word and normalized in GLOSSARY:
        fr, en, _ = GLOSSARY[normalized]
        return MorphAnalysis(
            word=word, root=normalized,
            root_gloss_fr=fr, root_gloss_en=en,
            suffixes=[], compound_parts=[],
            is_dictionary_match=True, is_decomposable=True,
        )

    syls = split_syllables(word)

    # Helper: look up a root in GLOSSARY, trying onset normalization
    def _lookup(w: str) -> Optional[tuple[str, str, str, str]]:
        """Return (actual_key, fr, en, domain) or None."""
        if w in GLOSSARY:
            fr, en, dom = GLOSSARY[w]
            return (w, fr, en, dom)
        nw = normalize_onset(w)
        if nw != w and nw in GLOSSARY:
            fr, en, dom = GLOSSARY[nw]
            return (nw, fr, en, dom)
        return None

    # 2. Compound: root1 + root2 (two glossary words) — try BEFORE suffixes
    #    for words with 4+ syllables, compounds are more likely than root+2 suffixes
    if syls and len(syls) >= 4:
        for split_at in range(1, len(syls)):
            part1 = "".join(syls[:split_at])
            part2 = "".join(syls[split_at:])
            h1 = _lookup(part1)
            h2 = _lookup(part2)
            if h1 and h2:
                _, fr1, en1, _ = h1
                _, fr2, en2, _ = h2
                return MorphAnalysis(
                    word=word, root=part1,
                    root_gloss_fr=fr1, root_gloss_en=en1,
                    suffixes=[],
                    compound_parts=[(part1, fr1, en1), (part2, fr2, en2)],
                    is_dictionary_match=False,
                    is_decomposable=True,
                )

    # 3. Root + suffixes (try 3, 2, then 1 suffix)
    if syls and len(syls) >= 2:
        for n_suf in (3, 2, 1):
            if len(syls) <= n_suf:
                continue
            root = "".join(syls[:-n_suf])
            suffix_syls = syls[-n_suf:]

            hit = _lookup(root)
            if hit and all(s in QUECHUA_SUFFIXES for s in suffix_syls):
                root_key, fr, en, _ = hit
                suf_info = [
                    (s, *QUECHUA_SUFFIXES[s]) for s in suffix_syls
                ]
                return MorphAnalysis(
                    word=word, root=root_key,
                    root_gloss_fr=fr, root_gloss_en=en,
                    suffixes=suf_info, compound_parts=[],
                    is_dictionary_match=word in DICTIONARY,
                    is_decomposable=True,
                )

    # 4. Compound fallback for shorter words (2-3 syllables)
    if syls and len(syls) >= 2 and len(syls) < 4:
        for split_at in range(1, len(syls)):
            part1 = "".join(syls[:split_at])
            part2 = "".join(syls[split_at:])
            if part1 in GLOSSARY and part2 in GLOSSARY:
                fr1, en1, _ = GLOSSARY[part1]
                fr2, en2, _ = GLOSSARY[part2]
                return MorphAnalysis(
                    word=word, root=part1,
                    root_gloss_fr=fr1, root_gloss_en=en1,
                    suffixes=[],
                    compound_parts=[(part1, fr1, en1), (part2, fr2, en2)],
                    is_dictionary_match=False,
                    is_decomposable=True,
                )

    # 5. No match
    is_dict = word in DICTIONARY
    return MorphAnalysis(
        word=word, root=word,
        root_gloss_fr="", root_gloss_en="",
        suffixes=[], compound_parts=[],
        is_dictionary_match=is_dict, is_decomposable=is_dict,
    )
