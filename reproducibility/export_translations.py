#!/usr/bin/env python3
"""
Export cord-by-cord translations for all validated khipus.

Generates a CSV file with one row per cord for each analyzed khipu,
including the ALBA syllabic reading, dictionary gloss, cord type,
color, level, and S-prefix value.

References:
    Sivan, J. (2026). Evidence for a Syllabic Mapping in Andean Khipu
    Long-Knot Turn Counts. DOI: 10.5281/zenodo.19184002

Usage:
    python scripts/export_translations.py

Output:
    reproducibility/cord_by_cord.csv
    reproducibility/summary.csv
"""

import sys
import os
import csv
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khipu_translator.translator import translate
from khipu_translator.knowledge import list_known_khipus


def main():
    # Write next to the other reproducibility artefacts so reviewers see
    # the CSV without needing to look in a separate, git-ignored folder.
    outdir = os.path.dirname(os.path.abspath(__file__))

    known = list_known_khipus()
    print(f"Exporting {len(known)} validated khipus...")

    # Cord-by-cord CSV
    cord_path = os.path.join(outdir, 'cord_by_cord.csv')
    summary_path = os.path.join(outdir, 'summary.csv')

    cord_rows = []
    summary_rows = []

    for kid in sorted(known):
        try:
            r = translate(kid)
        except Exception as e:
            print(f"  {kid}: FAILED ({e})")
            continue

        total = len(r.cords)
        string_count = sum(1 for c in r.cords if c.cord_type == 'STRING')
        int_count = sum(1 for c in r.cords if c.cord_type == 'INT')
        empty_count = sum(1 for c in r.cords if c.cord_type == 'EMPTY')

        # Load knowledge for document type
        from khipu_translator.knowledge import get_knowledge
        knowledge = get_knowledge(kid)
        doc_type = knowledge.get('document_type_override', '') if knowledge else ''

        summary_rows.append({
            'khipu': kid,
            'total_cords': total,
            'string_cords': string_count,
            'int_cords': int_count,
            'empty_cords': empty_count,
            'document_type': doc_type,
        })

        for i, c in enumerate(r.cords):
            cord_rows.append({
                'khipu': kid,
                'position': i + 1,
                'level': c.level,
                'color': c.color,
                'cord_type': c.cord_type,
                'alba_reading': c.alba_reading if c.cord_type == 'STRING' else '',
                'alba_gloss': c.alba_gloss_en or '' if c.cord_type == 'STRING' else '',
                's_prefix': c.s_prefix if c.cord_type == 'STRING' else '',
                'locke_value': c.locke_value if c.cord_type == 'INT' else '',
                'knot_sequence': c.knot_sequence or '',
            })

        print(f"  {kid}: {total} cords ({string_count} STRING)")

    # Write cord CSV
    with open(cord_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'khipu', 'position', 'level', 'color', 'cord_type',
            'alba_reading', 'alba_gloss', 's_prefix', 'locke_value',
            'knot_sequence'
        ])
        writer.writeheader()
        writer.writerows(cord_rows)

    # Write summary CSV
    with open(summary_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'khipu', 'total_cords', 'string_cords', 'int_cords',
            'empty_cords', 'document_type'
        ])
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nExported:")
    print(f"  {cord_path} ({len(cord_rows)} rows)")
    print(f"  {summary_path} ({len(summary_rows)} khipus)")


if __name__ == '__main__':
    main()
