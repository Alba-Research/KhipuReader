#!/usr/bin/env python3
"""
khipu-translator CLI — Translate khipus from the command line.

Usage:
    khipu translate UR039                     # Print summary
    khipu translate UR039 --lang fr           # French glosses
    khipu translate UR039 --json out.json     # Export JSON
    khipu translate UR039 --csv out.csv       # Export CSV (Level 1)
    khipu translate UR039 --xml out.xml       # Export XML (Level 2)
    khipu list                                # List all khipus
    khipu search Pachacamac                   # Search by keyword
    khipu info UR039                          # Khipu metadata
    khipu syllabary                           # Show the ALBA syllabary
"""

from __future__ import annotations

import argparse
import sys


def cmd_translate(args):
    """Translate a khipu."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.translator import translate

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()

    try:
        result = translate(args.khipu, db=db, lang=args.lang)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Use 'khipu list' to see available khipus.", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    # Export options
    if args.json:
        level = args.level or 3
        result.to_json(args.json, level=level, lang=args.lang)
        print(f"Exported Level {level} to {args.json}")
    if args.csv:
        result.to_csv(args.csv)
        print(f"Exported Level 1 (cords) to {args.csv}")
    if args.xml:
        result.to_xml(args.xml, lang=args.lang)
        print(f"Exported Level 2 (records) to {args.xml}")
    if args.xlsx:
        result.to_xlsx(args.xlsx, lang=args.lang)
        print(f"Exported Excel workbook to {args.xlsx}")

    # Print summary unless --quiet
    if not args.quiet:
        print(result.summary(lang=args.lang))


def cmd_list(args):
    """List all khipus in the database."""
    from khipu_translator.database import KhipuDB

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()
    df = db.list_khipus()
    db.close()

    print(f"{'ID':<15s}  {'Provenance':<35s}  Museum")
    print("-" * 80)
    for _, row in df.iterrows():
        inv = str(row["INVESTIGATOR_NUM"]) if row["INVESTIGATOR_NUM"] else "?"
        prov = str(row.get("PROVENANCE", "?"))[:35]
        mus = str(row.get("MUSEUM_NAME", "?"))[:25]
        print(f"{inv:<15s}  {prov:<35s}  {mus}")
    print(f"\nTotal: {len(df)} khipus")


def cmd_search(args):
    """Search khipus by keyword."""
    from khipu_translator.database import KhipuDB

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()
    df = db.list_khipus(search=args.query)
    db.close()

    print(f"Search: '{args.query}' -> {len(df)} results\n")
    for _, row in df.iterrows():
        inv = str(row["INVESTIGATOR_NUM"]) if row["INVESTIGATOR_NUM"] else "?"
        prov = str(row.get("PROVENANCE", "?"))[:40]
        print(f"  {inv:<15s}  {prov}")


def cmd_info(args):
    """Show metadata for a khipu."""
    from khipu_translator.database import KhipuDB

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()
    try:
        khipu = db.get_khipu(args.khipu)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    print(f"ID:         {khipu.investigator_num}")
    print(f"Provenance: {khipu.provenance or 'Unknown'}")
    print(f"Museum:     {khipu.museum_name or 'Unknown'}")
    print(f"Cords:      {khipu.num_cords}")
    print(f"Knots:      {khipu.num_knots}")
    if khipu.notes:
        print(f"Notes:      {khipu.notes[:200]}")


def cmd_syllabary(args):
    """Print the ALBA syllabary."""
    from khipu_translator.syllabary import describe_syllabary
    print(describe_syllabary())


def main():
    parser = argparse.ArgumentParser(
        prog="khipu",
        description="Translate Andean khipus using the Locke decimal system "
                    "and ALBA syllabary.",
    )

    # Shared argument for all subcommands
    db_help = "Path to khipu.db (default: auto-download OKR)"

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # translate
    p_tr = sub.add_parser("translate", aliases=["t"], help="Translate a khipu")
    p_tr.add_argument("khipu", help="Khipu ID (e.g. UR039, AS030)")
    p_tr.add_argument("--db", help=db_help)
    p_tr.add_argument("--level", type=int, choices=[1, 2, 3], default=None,
                       help="Detail level for export (1=cord, 2=record, 3=document)")
    p_tr.add_argument("--lang", choices=["en", "fr"], default="en",
                       help="Language for glosses")
    p_tr.add_argument("--json", metavar="FILE", help="Export to JSON")
    p_tr.add_argument("--csv", metavar="FILE", help="Export Level 1 to CSV")
    p_tr.add_argument("--xml", metavar="FILE", help="Export Level 2 to XML")
    p_tr.add_argument("--xlsx", metavar="FILE",
                       help="Export human-friendly Excel workbook (requires openpyxl)")
    p_tr.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress summary output")
    p_tr.set_defaults(func=cmd_translate)

    # list
    p_ls = sub.add_parser("list", aliases=["ls"], help="List all khipus")
    p_ls.add_argument("--db", help=db_help)
    p_ls.set_defaults(func=cmd_list)

    # search
    p_se = sub.add_parser("search", aliases=["s"], help="Search khipus by keyword")
    p_se.add_argument("query", help="Search term")
    p_se.add_argument("--db", help=db_help)
    p_se.set_defaults(func=cmd_search)

    # info
    p_in = sub.add_parser("info", aliases=["i"], help="Khipu metadata")
    p_in.add_argument("khipu", help="Khipu ID")
    p_in.add_argument("--db", help=db_help)
    p_in.set_defaults(func=cmd_info)

    # syllabary
    p_sy = sub.add_parser("syllabary", help="Show the ALBA syllabary")
    p_sy.set_defaults(func=cmd_syllabary)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
