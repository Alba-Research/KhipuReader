#!/usr/bin/env python3
"""
KhipuReader CLI — Read and analyze Andean khipus from the command line.

Usage:
    khipu translate UR039                     # Translate a khipu
    khipu translate UR039 --lang fr --xlsx out.xlsx
    khipu suggest UR039                       # Find similar khipus
    khipu compare UR039 UR144                 # Side-by-side comparison
    khipu unclaimed                           # List unanalyzed khipus
    khipu submit UR039                        # Generate contribution template
    khipu list                                # List all 619 khipus
    khipu search Pachacamac                   # Search by keyword
    khipu info UR039                          # Khipu metadata
    khipu syllabary                           # Show the ALBA syllabary
    khipu progress                            # Generate PROGRESS.md
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

    if not args.quiet:
        print(result.summary(lang=args.lang))


def cmd_suggest(args):
    """Find khipus similar to a given one."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.suggest import suggest_similar

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()

    print(f"Analyzing {args.khipu} and comparing with all khipus...")
    print("(this may take a few minutes on first run)\n")

    try:
        ref, scores = suggest_similar(args.khipu, db=db, top_n=args.top)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    print(f"Reference: {ref.khipu.investigator_num}")
    print(f"  Type: {ref.document_type}")
    print(f"  Cords: {ref.stats['total_cords']}, STRING: {ref.stats['string_cords']}")
    print(f"  Provenance: {ref.khipu.provenance or '?'}")
    print(f"  Words: {list(ref.vocabulary.keys())[:8]}")
    print()

    print(f"Top {len(scores)} most similar khipus:")
    print(f"{'Rank':>4s}  {'Khipu':>10s}  {'Score':>6s}  {'Vocab':>5s}  {'Struct':>6s}  "
          f"{'Prov':>4s}  {'Color':>5s}  {'Type':>20s}  {'Provenance'}")
    print("-" * 100)
    for i, s in enumerate(scores, 1):
        print(f"{i:>4d}  {s.khipu_id:>10s}  {s.total_score:>.3f}  "
              f"{s.vocab_score:>.2f}  {s.structure_score:>.3f}  "
              f"{s.provenance_score:>.1f}  {s.color_score:>.2f}  "
              f"{s.document_type:>20s}  {s.provenance[:25]}")


def cmd_compare(args):
    """Compare two khipus side by side."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.suggest import compare_khipus

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()

    try:
        r1, r2, comp = compare_khipus(args.khipu1, args.khipu2, db=db)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    w = 35
    print(f"{'':>{w}s} | {r1.khipu.investigator_num:>15s} | {r2.khipu.investigator_num:>15s}")
    print("-" * (w + 36))
    print(f"{'Provenance':>{w}s} | {str(r1.khipu.provenance or '?')[:15]:>15s} | {str(r2.khipu.provenance or '?')[:15]:>15s}")
    print(f"{'Museum':>{w}s} | {str(r1.khipu.museum_name or '?')[:15]:>15s} | {str(r2.khipu.museum_name or '?')[:15]:>15s}")
    print(f"{'Cords':>{w}s} | {r1.stats['total_cords']:>15d} | {r2.stats['total_cords']:>15d}")
    print(f"{'STRING':>{w}s} | {r1.stats['string_cords']:>15d} | {r2.stats['string_cords']:>15d}")
    print(f"{'Architecture':>{w}s} | {r1.architecture:>15s} | {r2.architecture:>15s}")
    print(f"{'Document type':>{w}s} | {r1.document_type:>15s} | {r2.document_type:>15s}")
    print()
    print(f"Vocabulary similarity: {comp['vocab_similarity']:.2f}")
    print(f"Structure similarity:  {comp['structure_similarity']:.2f}")
    print(f"Provenance similarity: {comp['provenance_similarity']:.2f}")
    print(f"Color similarity:      {comp['color_similarity']:.2f}")
    print()
    if comp["shared_words"]:
        print(f"Shared words: {', '.join(comp['shared_words'])}")
    if comp["only_in_1"]:
        print(f"Only in {r1.khipu.investigator_num}: {', '.join(comp['only_in_1'])}")
    if comp["only_in_2"]:
        print(f"Only in {r2.khipu.investigator_num}: {', '.join(comp['only_in_2'])}")


def cmd_unclaimed(args):
    """List khipus not yet analyzed by the community."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.submit import load_contributions

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()
    all_khipus = db.list_khipus()
    db.close()

    contributions = load_contributions()
    claimed = set(contributions.keys())

    unclaimed = []
    for _, row in all_khipus.iterrows():
        kid = str(row["INVESTIGATOR_NUM"])
        if kid not in claimed:
            prov = str(row.get("PROVENANCE", "?"))[:30]
            museum = str(row.get("MUSEUM_NAME", "?"))[:30]
            unclaimed.append((kid, prov, museum))

    print(f"Unclaimed khipus: {len(unclaimed)}/{len(all_khipus)}")
    print(f"(Analyzed: {len(claimed)})\n")

    print(f"{'ID':<15s}  {'Provenance':<30s}  Museum")
    print("-" * 80)
    for kid, prov, museum in unclaimed[:args.limit]:
        print(f"{kid:<15s}  {prov:<30s}  {museum}")

    if len(unclaimed) > args.limit:
        print(f"\n... and {len(unclaimed) - args.limit} more. "
              f"Use --limit to see more.")


def cmd_submit(args):
    """Generate a contribution template for a khipu."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.submit import generate_contribution

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()

    try:
        path = generate_contribution(args.khipu, db=db)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    print(f"Contribution template generated: {path}")
    print()
    print("Next steps:")
    print(f"  1. Edit {path}")
    print("  2. Fill in: summary, interpretation, confidence, references")
    print("  3. Submit a Pull Request to the KhipuReader repository")


def cmd_progress(args):
    """Generate PROGRESS.md from contributions."""
    from pathlib import Path
    from khipu_translator.database import KhipuDB
    from khipu_translator.progress import generate_progress

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()
    output = Path(args.output) if args.output else Path("PROGRESS.md")

    md = generate_progress(db=db, output_path=output)
    db.close()

    print(md)
    print(f"\nSaved to {output}")


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


def cmd_header(args):
    """Show the 'identity card' of a khipu (first cluster analysis)."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.translator import translate
    from khipu_translator.header import analyze_header, format_header

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()

    try:
        result = translate(args.khipu, db=db, lang=args.lang)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    header = analyze_header(result, lang=args.lang)
    print(format_header(header))


def cmd_syllabary(args):
    """Print the ALBA syllabary."""
    from khipu_translator.syllabary import describe_syllabary
    print(describe_syllabary())


def main():
    parser = argparse.ArgumentParser(
        prog="khipu",
        description="KhipuReader — Read and analyze Andean khipus. "
                    "Reading the lost library of the Inca Empire, together.",
    )

    db_help = "Path to khipu.db (default: auto-download OKR)"
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # translate
    p_tr = sub.add_parser("translate", aliases=["t"], help="Translate a khipu")
    p_tr.add_argument("khipu", help="Khipu ID (e.g. UR039, AS030)")
    p_tr.add_argument("--db", help=db_help)
    p_tr.add_argument("--level", type=int, choices=[1, 2, 3], default=None)
    p_tr.add_argument("--lang", choices=["en", "fr", "es"], default="en")
    p_tr.add_argument("--json", metavar="FILE")
    p_tr.add_argument("--csv", metavar="FILE")
    p_tr.add_argument("--xml", metavar="FILE")
    p_tr.add_argument("--xlsx", metavar="FILE")
    p_tr.add_argument("--quiet", "-q", action="store_true")
    p_tr.set_defaults(func=cmd_translate)

    # suggest
    p_sg = sub.add_parser("suggest", help="Find similar khipus")
    p_sg.add_argument("khipu", help="Reference khipu ID")
    p_sg.add_argument("--db", help=db_help)
    p_sg.add_argument("--top", type=int, default=5, help="Number of results")
    p_sg.set_defaults(func=cmd_suggest)

    # compare
    p_cp = sub.add_parser("compare", help="Compare two khipus side by side")
    p_cp.add_argument("khipu1", help="First khipu ID")
    p_cp.add_argument("khipu2", help="Second khipu ID")
    p_cp.add_argument("--db", help=db_help)
    p_cp.set_defaults(func=cmd_compare)

    # header
    p_hd = sub.add_parser("header", aliases=["h"], help="Show document identity card")
    p_hd.add_argument("khipu", help="Khipu ID")
    p_hd.add_argument("--db", help=db_help)
    p_hd.add_argument("--lang", choices=["en", "fr", "es"], default="en")
    p_hd.set_defaults(func=cmd_header)

    # unclaimed
    p_uc = sub.add_parser("unclaimed", help="List unanalyzed khipus")
    p_uc.add_argument("--db", help=db_help)
    p_uc.add_argument("--limit", type=int, default=30, help="Max results to show")
    p_uc.set_defaults(func=cmd_unclaimed)

    # submit
    p_su = sub.add_parser("submit", help="Generate contribution template")
    p_su.add_argument("khipu", help="Khipu ID")
    p_su.add_argument("--db", help=db_help)
    p_su.set_defaults(func=cmd_submit)

    # progress
    p_pr = sub.add_parser("progress", help="Generate PROGRESS.md")
    p_pr.add_argument("--db", help=db_help)
    p_pr.add_argument("--output", "-o", help="Output file (default: PROGRESS.md)")
    p_pr.set_defaults(func=cmd_progress)

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
