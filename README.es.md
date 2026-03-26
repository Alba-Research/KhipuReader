*[Read in English](README.md)*

# KhipuReader

**Una herramienta de código abierto para leer khipus andinos.**

619 khipus sobreviven en museos de todo el mundo. Cada uno es un documento de cuerdas anudadas del Imperio Inca — un registro tributario, un diario astronómico, un acta judicial, un censo, un mapa. Podemos leer los números (Locke 1923). Estamos comenzando a leer las palabras (silabario ALBA, Sivan 2026).

KhipuReader traduce cualquier khipu del [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository) — instálalo, elige un khipu y lee lo que contiene.

Para quienes quieran ir más allá, el proyecto también alberga un **esfuerzo comunitario** para reconstruir la biblioteca perdida del Imperio Inca — un khipu a la vez.

## Progreso comunitario

```
[=>                            ] 6/619 khipus analizados (1.0%)
```

| Khipu | Tipo | Resumen |
|-------|------|---------|
| UR006 | Diario astronómico | 24 meses x 9 columnas, Luna/Marte/Pléyades, ~1500 d.C. |
| AS076 | Ceremonia de nombramiento | Declaración de identidad (rutuchikuy), París |
| HP020 | Registro catastral | Instrucción de localización, Pachacamac |
| AS080 | Registro catastral | Ruta de 6 pasos con hitos, París |
| AS077 | Inventario de zonas | 4 zonas geográficas, París |
| AS075 | Registro de peregrinaje | Ceremonias del oráculo de Pachacamac, París |

Ejecuta `khipu progress` para el informe completo, o consulta [PROGRESS.md](PROGRESS.md).

---

## Inicio rápido

### Instalar

```bash
pip install khipu-reader
```

En el primer uso, la herramienta descarga automáticamente la base de datos del OKR (~50 MB).

### Traducir un khipu

```bash
khipu translate UR039 --lang en
```

### Encontrar khipus similares

```bash
khipu suggest UR039
```

### Comparar dos khipus

```bash
khipu compare UR039 UR144
```

### Contribuir tu lectura

```bash
khipu submit UR039          # genera contributions/UR039.json
# Edita el archivo, añade tu análisis
# Envía un Pull Request
```

### Ver lo que falta por hacer

```bash
khipu unclaimed             # 613 khipus esperando ser leídos
```

---

## Cómo funciona

Los khipus codifican información en dos canales:

| Canal | Componente | Decodificación |
|-------|-----------|----------------|
| **Números** | Nudos simples (tipo S) | Sistema decimal de Locke (1923) — establecido |
| **Texto** | Nudos largos + ocho | Silabario ALBA (Sivan 2026) — propuesto |

El 5.4% de las cuerdas anudadas contienen múltiples nudos largos/ocho, haciéndolas incompatibles con el sistema decimal. Estas cuerdas "STRING" son candidatas para codificación textual.

### El silabario ALBA v3

| Nudo | Vueltas | Onset | Coda | Confianza |
|------|---------|-------|------|-----------|
| L0 | 0 | lla | lla | Alta |
| L2 | 2 | **chi** | ki | Alta |
| L3 | 3 | ma | ma | Alta |
| L4 | 4 | ka | ka | Alta |
| L5 | 5 | ta | ta | Alta |
| L6 | 6 | pa | pa | Alta |
| L7 | 7 | **wa** | y | Alta |
| L8 | 8 | **cha** | na | Alta |
| L9 | 9 | pi | pi | Alta |
| L10 | 10 | si | si | Media |
| L11 | 11 | ti | ti | Baja |
| L12 | 12 | ku | ku | Baja |
| E | ocho | — | qa | Alta |

16 símbolos efectivos. Tres variantes de onset (wa/y, cha/na, chi/ki) siguen patrones fonológicos naturales.

> **Hipótesis de investigación.** El silabario ALBA es un desciframiento propuesto (p = 0.001) — no un sistema de lectura confirmado. Úsese con cautela académica.

---

## Referencia de comandos

| Comando | Descripción |
|---------|-------------|
| `khipu translate ID` | Traducir un khipu |
| `khipu suggest ID` | Encontrar los 5 khipus más similares |
| `khipu compare ID1 ID2` | Comparación lado a lado |
| `khipu unclaimed` | Listar khipus no analizados |
| `khipu submit ID` | Generar plantilla de contribución (JSON) |
| `khipu progress` | Generar PROGRESS.md |
| `khipu list` | Listar los 619 khipus |
| `khipu search PALABRA` | Buscar por procedencia, museo, ID |
| `khipu info ID` | Metadatos del khipu |
| `khipu syllabary` | Mostrar el silabario ALBA |

Todos los comandos aceptan `--db ruta/a/khipu.db` para usar una base de datos local.

---

## Cómo contribuir

No necesitas hablar quechua. Hay 4 niveles:

### Nivel 1 — Clasificación
Ejecuta `khipu translate` y describe lo que ves: "parece un catastro", "puramente numérico", "muchas palabras de parentesco". Cualquiera puede hacer esto.

### Nivel 2 — Contexto
Investiga la procedencia. ¿De qué sitio es? ¿Qué museo? ¿Hay otros khipus del mismo lugar?

### Nivel 3 — Interpretación
Propón nombres de columnas, identifica el tipo de documento, cruza con fuentes coloniales.

### Nivel 4 — Reconstrucción
Crea el archivo Excel "biblioteca" — el khipu como el inca lo habría organizado en una hoja de cálculo.

### El flujo de trabajo

```bash
khipu submit UR039                    # 1. Genera plantilla
nano contributions/UR039.json         # 2. Añade tu análisis
git add contributions/UR039.json      # 3. Commit
# Envía un Pull Request                # 4. La comunidad revisa
```

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para la guía completa.

---

## Citación

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

## Fuente de datos

Esta herramienta lee khipus del **Open Khipu Repository** (OKR):

> Urton, G. & Brezine, C. (2009–2024). *Open Khipu Repository*.
> Harvard University. DOI: [10.5281/zenodo.5037551](https://doi.org/10.5281/zenodo.5037551)

La base de datos OKR (619 khipus, ~50 MB) se descarga automáticamente en el primer uso.

## Proyectos relacionados

- [Open Khipu Repository](https://github.com/khipulab/open-khipu-repository) — La base de datos OKR
- [ALBA Project](https://alba-project.org) — El proyecto de investigación detrás del silabario

## Licencia

MIT — ver [LICENSE](LICENSE).
