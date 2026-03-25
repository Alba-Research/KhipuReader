"""
Spanish glossary for khipu translation.

Quechua/Aymara → Spanish translations, carefully sourced from:
  - González Holguín, Diego (1608). Vocabulario de la Lengua General de todo el Perú.
  - Bertonio, Ludovico (1612). Vocabulario de la Lengua Aymara.
  - Academia Mayor de la Lengua Quechua (2005). Diccionario Quechua-Español-Quechua.
  - Standard archaeological Spanish terminology for Andean studies.

Note: Many Quechua words (llama, cóndor, huaca, mit'a, etc.) are already
loan words in Spanish and should be kept as-is or minimally glossed.
"""

from __future__ import annotations

# word → Spanish gloss
GLOSSARY_ES: dict[str, str] = {
    # Parentesco / Kinship
    "mama":   "madre",
    "papa":   "padre / papa (tubérculo)",
    "tata":   "padre",
    "kaka":   "tío materno",
    "pana":   "hermana",
    "nana":   "dolor / hermana",
    "tayta":  "señor / padre",
    "panaka": "linaje real (panaca)",

    # Gobierno / Governance
    "kama":   "crear / gobernar",
    "kamay":  "crear [INF]",
    "ypa":    "administrador / economista",
    "qapaq":  "emperador (Qhapaq)",
    "qapa":   "noble",
    "kapa":   "noble / rico",

    # Geografía / Geography
    "qaqa":   "roca / montaña (peñasco)",
    "llaqa":  "pueblo / aldea (llaqta)",
    "pata":   "terreno / parcela (andén)",
    "mata":   "bosquecillo",
    "paqa":   "amanecer / este",
    "kaqa":   "pared / muro [AY]",
    "taqa":   "separar / frontera (lindero)",
    "siqa":   "subida / rampa",
    "piqa":   "cumbre / cima",
    "qata":   "pendiente / techo",
    "qama":   "habitar / residir",
    "chiqa":  "verdad / derecho (hito de medición)",

    # Cuerpo / Labor
    "maki":   "mano / trabajo",
    "kiki":   "uno mismo (identidad)",
    "siki":   "base / fondo",
    "chaki":  "pie",

    # Acciones / Actions
    "taka":   "golpear",
    "kata":   "proteger / ocultar",
    "paka":   "escondido / secreto",
    "maka":   "arma / maza (macana)",
    "tapa":   "protección / tutela",
    "paki":   "romper / quebrar",
    "maqa":   "golpear fuerte",
    "naqa":   "degollar / sacrificar",
    "kita":   "huir / escapar",
    "wana":   "corregir / castigar",

    # Infinitivos / Infinitives
    "takay":  "golpear [INF]",
    "katay":  "proteger [INF]",
    "pakay":  "esconder [INF]",
    "tapay":  "preguntar [INF]",
    "makay":  "combatir [INF]",
    "patay":  "subir [INF]",
    "nanay":  "sufrir [INF]",

    # Pronombres / Grammar
    "pay":    "él / ella",
    "kay":    "ser / estar",
    "may":    "dónde (lugar)",
    "nay":    "sentir",
    "pi":     "quién (interrogativo)",
    "mana":   "no / negación",
    "taq":    "pero / sino",
    "paq":    "para (dativo)",
    "kaq":    "el / la (determinante)",
    "sina":   "como / similar",
    "paypa":  "su / de él (posesivo)",
    "kaypa":  "de esto (genitivo)",
    "kaypi":  "aquí",
    "chay":   "esto / eso (demostrativo)",

    # Naturaleza / Nature
    "llama":  "llama",
    "killa":  "luna / mes",
    "llapa":  "todos / rayo (Illapa)",
    "qaki":   "helada / escarcha",

    # Ritual
    "taki":   "canto / ritual (taqui)",
    "napa":   "saludo ritual",
    "naku":   "recíproco",
    "pama":   "fórmula ritual",
    "tina":   "huso (hilado)",

    # Astronomía
    "kaki":   "maíz seco / Pléyades",

    # Jurídico / Moral
    "llalla": "mentir / engañar",
    "qalla":  "comenzar",
    "palla":  "princesa (ñusta)",
    "kipa":   "después",

    # Vivienda / Construction
    "tana":   "pilar / columna",
    "wasi":   "casa",
    "chaka":  "puente",
    "qara":   "piel / cuero",

    # Polyphony v3 / Onset words
    "wata":   "año",
    "waka":   "huaca / lugar sagrado",
    "wayna":  "joven (varón)",
    "waqa":   "llorar",
    "wayta":  "flor",
    "chama":  "alimento / fuerza",
    "chana":  "secar / canal",
    "chapa":  "guardián / centinela",
    "chaku":  "cacería comunal (chaco)",
    "china":  "hembra / sirvienta",
    "chika":  "tanto / tal cantidad",

    # Aymara
    "taypa":  "centro / medio [AY]",
    "tayka":  "madre / hembra [AY]",
    "masi":   "compañero [AY]",
    "pataka": "cien [AY]",
    "nanaka": "nosotros [AY]",
    "kuti":   "vez / turno [AY]",

    # Varios / Misc
    "tama":   "grupo / rebaño",
    "tiki":   "todo / cada uno",
    "kiti":   "avaro / tacaño",
    "paku":   "hongo",
    "piki":   "pulga",
    "piku":   "cumbre",
    "makana": "maza de guerra (macana)",
    "llaki":  "tristeza / pena",

    # v4 — confirmados en análisis UR055
    "way":    "camino / vía",
    "chata":  "golpear [AY]",
    "sisi":   "hormiga",
    "sika":   "subir / trepar",
    "sipi":   "matar / estrangular",
    "tipi":   "arrancar / descortezar",
    "tiy":    "sentarse",
    "wama":   "halcón",
}


# --- Domain glossaries in Spanish ---

ASTRO_GLOSSARY_ES: dict[str, str] = {
    # ALTA confianza
    "mama":   "Luna (Mama Killa)",
    "kama":   "Marte — eventos (oposiciones, estaciones, retrogradaciones)",
    "qaqa":   "constelaciones oscuras (yana phuyu)",
    "kaki":   "Pléyades (Qollqa)",
    "chaki":  "Escorpio (Chaki T'aklla = arado de pie)",
    # MEDIA confianza
    "maki":   "Marte — observaciones (noches de trabajo)",
    "paka":   "ocaso helíaco (desaparición de un astro)",
    "maqa":   "eclipse / meteoro",
    # BAJA confianza
    "taki":   "¿Saturno? o ceremonia de observación",
    "chapa":  "guardián / centinela (¿estrella guardiana?)",
    "mapa":   "? (cera AY, no identificado)",
    "llama":  "constelación de la Llama (Yacana)",
}

JURIDICAL_GLOSSARY_ES: dict[str, str] = {
    "taka":   "violencia / agresión (cargo)",
    "kata":   "ocultamiento (delito)",
    "kaka":   "parte contraria (tío)",
    "tata":   "demandante (padre)",
    "maka":   "prueba material (arma)",
    "pata":   "objeto en litigio (terreno)",
    "tama":   "objeto en litigio (rebaño)",
    "llalla": "fraude",
    "kama":   "intendente / juez",
    "kapa":   "noble / autoridad",
    "tapa":   "protección / tutela",
    "pana":   "hermana (testigo / víctima)",
    "mama":   "madre (testigo / víctima)",
    "nay":    "veredicto / sentencia",
    "piqa":   "acusado (¿quién?)",
}

CADASTRAL_GLOSSARY_ES: dict[str, str] = {
    "qaqa":   "hito rocoso / topónimo",
    "chiqa":  "mojón de medición",
    "taqa":   "frontera administrativa (lindero)",
    "kaqa":   "límite natural (pared)",
    "paqa":   "orientación este",
    "siqa":   "rampa / subida (pirámide)",
    "piqa":   "punto más alto / cumbre",
    "qama":   "zona residencial",
    "qata":   "pendiente",
    "naqa":   "topónimo (lugar)",
    "maka":   "hito / punto de referencia",
    "kiki":   "marca del agrimensor",
}

LABOR_GLOSSARY_ES: dict[str, str] = {
    "maki":   "trabajo oficial (mit'a)",
    "kama":   "supervisor / capataz",
    "kiki":   "identificación del trabajador",
    "kaki":   "raciones (maíz distribuido)",
    "paki":   "extracción / construcción",
    "taki":   "canto ritual de trabajo",
    "tama":   "unidad de producción (rebaño)",
    "kaka":   "jefe de linaje (tío)",
    "tata":   "responsable (padre)",
    "maka":   "herramienta / equipo",
    "kata":   "cobertura / protección",
    "qapa":   "noble comitente",
}

RITUAL_GLOSSARY_ES: dict[str, str] = {
    "nay":    "voz del oráculo",
    "taki":   "ceremonia / rito (taqui)",
    "pama":   "palabras rituales oficiales",
    "napa":   "protocolo de entrada",
    "naqa":   "sacrificio (lugar sagrado)",
    "maka":   "ofrenda de arma",
    "mama":   "Pachamama / diosa madre",
    "waka":   "huaca / lugar sagrado",
    "llapa":  "rayo / Illapa (dios del trueno)",
    "kaka":   "ancestro invocado",
    "tata":   "ancestro invocado (padre)",
    "paka":   "elemento oculto/secreto del rito",
    "kiki":   "declaración de identidad",
    "piki":   "ofrenda",
}

AGRO_GLOSSARY_ES: dict[str, str] = {
    "kaki":   "maíz (cosecha / siembra)",
    "kaqa":   "muro de terraza (andén)",
    "wama":   "halcón (marcador estacional)",
    "chaqa":  "puente / canal de riego",
    "taki":   "canto de siembra",
    "paki":   "roturación / quiebra de tierra",
    "taqa":   "límite de parcela",
    "siqa":   "rampa de terraza (andén)",
    "maki":   "trabajo de campo",
    "qaqa":   "roca (hito de terreno)",
    "chiqa":  "medida exacta / mojón",
}

# Registry: document_type → Spanish domain glossary
DOMAIN_GLOSSARIES_ES: dict[str, dict[str, str]] = {
    "astronomical_journal":  ASTRO_GLOSSARY_ES,
    "judicial_proceeding":   JURIDICAL_GLOSSARY_ES,
    "cadastral_survey":      CADASTRAL_GLOSSARY_ES,
    "labor_tribute":         LABOR_GLOSSARY_ES,
    "ritual_oracle":         RITUAL_GLOSSARY_ES,
    "agro_pastoral":         AGRO_GLOSSARY_ES,
}
