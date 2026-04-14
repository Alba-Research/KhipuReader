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

    # Optionally load the merged OKR × KFG corpus for L? gap-filling.
    merged_corpus = None
    if getattr(args, "from_merged", False):
        from khipu_translator.corpus import MergedCorpus, DEFAULT_SQLITE
        if not DEFAULT_SQLITE.exists():
            print("[!] --from-merged requires the merged corpus. "
                  "Run: python3 scripts/merge_okr_kfg.py", file=sys.stderr)
            db.close()
            sys.exit(2)
        merged_corpus = MergedCorpus()

    try:
        result = translate(args.khipu, db=db, lang=args.lang,
                           merged_corpus=merged_corpus)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Use 'khipu list' to see available khipus.", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
        if merged_corpus is not None:
            merged_corpus.close()

    # Opt-in Ascher layer (v2): enrich with KFG pendant-pendant constraints.
    if getattr(args, "ascher", False):
        _apply_ascher_layer(result, args.khipu)

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
        if getattr(args, "ascher", False):
            print(_format_ascher_report(result))


def _okr_to_kh_id(okr_id: str) -> str:
    """Resolve an OKR khipu identifier (e.g. 'UR052') to the KFG KH ID
    ('KH0282'). Returns '' if not found.

    Uses the merged-corpus alias index if available (covers all 703 KFG
    khipus, not just those with sum pages). Falls back to scanning the
    sums-index if the merged corpus has not been built.
    """
    # Preferred path: the merged corpus already indexes every alias of
    # every khipu (OKR + KFG + synthesised), built from data/merged/*.json.
    try:
        from khipu_translator.corpus import MergedCorpus, DEFAULT_SQLITE
        if DEFAULT_SQLITE.exists():
            c = MergedCorpus()
            try:
                kh = c.resolve_kh_id(okr_id)
                if kh and kh.startswith("KH"):
                    return kh
            finally:
                c.close()
    except Exception:
        pass

    # Fallback: scan the pendant-pendant-sum index (only khipus with sums,
    # ~385 out of 703). Kept for environments where the merged corpus
    # hasn't been built.
    from khipu_translator.ascher import KFGClient, parse_kh_index, parse_khipu_xlsx
    client = KFGClient()
    try:
        kh_list = parse_kh_index(client.fetch_index())
    except Exception:
        return ""
    for kh in kh_list:
        if kh in ("CM009",) or not kh.startswith("KH"):
            continue
        try:
            xlsx = client.fetch_xlsx(kh)
        except Exception:
            continue
        try:
            kd = parse_khipu_xlsx(xlsx, kh)
        except Exception:
            continue
        # Exact token match to avoid substring false-positives
        # (e.g. "UR269" must not match "UR2690").
        aliases = [a.strip() for a in (kd.alias or "").replace("/", ",").split(",")]
        if okr_id in aliases:
            return kh
    return ""


def _apply_ascher_layer(result, okr_id: str) -> None:
    """Locate the KFG twin, build the AscherGraph, run 2+3A+3B+3C."""
    from khipu_translator.ascher import (
        AscherGraph, KFGClient,
        apply_ascher_constraints, apply_reclassification, apply_constraint_propagation,
    )
    kh_id = _okr_to_kh_id(okr_id)
    if not kh_id:
        print(f"[ascher] no KFG twin found for {okr_id} — skipping layer",
              file=sys.stderr)
        return
    try:
        graph = AscherGraph.from_kfg(kh_id, client=KFGClient())
    except Exception as e:
        print(f"[ascher] failed to build graph for {kh_id}: {e}", file=sys.stderr)
        return
    apply_ascher_constraints(result, graph)
    apply_reclassification(result, graph)
    apply_constraint_propagation(result, graph)
    # Stash the KH id so the report can display it.
    result.stats["ascher_kh_id"] = kh_id
    # Pre-compute headline numbers for the report.
    headers = [c for c in result.cords if c.ascher
               and c.ascher.role in ("HEADER", "BOTH")]
    verified = sum(1 for c in headers if c.ascher.verified is True)
    result.stats["ascher_n_header"] = len(headers)
    result.stats["ascher_n_verified"] = verified
    result.stats["ascher_max_depth"] = graph.max_cascade_depth()
    result.stats["ascher_n_sums"] = len(graph.relations)


def _format_ascher_report(result) -> str:
    """Short textual report appended to ``khipu translate --ascher``."""
    s = result.stats
    kh_id = s.get("ascher_kh_id")
    if not kh_id:
        return ""
    lines = [
        "",
        "=== Ascher Integrity ===",
        f"KFG twin:            {kh_id}",
        f"Pendant-pendant sums: {s.get('ascher_n_sums', 0)}",
        f"Sum-cords verified:  {s.get('ascher_n_verified', 0)} / "
        f"{s.get('ascher_n_header', 0)}",
        f"Max cascade depth:   {s.get('ascher_max_depth', 0)}  (Merkle tree)",
        f"Reclassified (3A):   {s.get('ascher_reclassified', 0)} INT→STRING in STRING context",
        f"Propagated (3C):     {s.get('ascher_propagated', 0)} unique-unknown constraints solved",
    ]
    return "\n".join(lines)


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


def cmd_schema(args):
    """Detect the physical schema of a khipu."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.translator import translate
    from khipu_translator.schema import detect_schema, format_schema

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()

    try:
        result = translate(args.khipu, db=db)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    schema = detect_schema(result)
    print(f"{'=' * 50}")
    print(f"  {result.khipu.investigator_num} — Schema")
    print(f"{'=' * 50}")
    print(format_schema(schema))
    print(f"{'=' * 50}")


def cmd_header(args):
    """Show the 'identity card' of a khipu (first cluster analysis)."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.translator import translate
    from khipu_translator.header import analyze_header, format_header
    from khipu_translator.dating import extract_date, format_date

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

    # Also show date if detectable
    date = extract_date(result)
    if date:
        date.khipu_id = result.khipu.investigator_num
        print("\n  DATE DETECTED")
        print(f"  {'─' * 40}")
        print(format_date(date))


def cmd_date(args):
    """Extract date from a khipu."""
    from khipu_translator.database import KhipuDB
    from khipu_translator.translator import translate
    from khipu_translator.dating import extract_date, format_date, DEFAULT_EPOCH

    db = KhipuDB(db_path=args.db) if args.db else KhipuDB()
    epoch = args.epoch or DEFAULT_EPOCH

    try:
        result = translate(args.khipu, db=db)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    date = extract_date(result, epoch=epoch)
    if date:
        date.khipu_id = result.khipu.investigator_num
        print(f"{'=' * 50}")
        print(f"  {result.khipu.investigator_num} — Date")
        print(f"{'=' * 50}")
        print(f"  Provenance: {result.khipu.provenance or 'Unknown'}")
        print(format_date(date))
        print(f"{'=' * 50}")
    else:
        print(f"{result.khipu.investigator_num}: no date pattern detected")


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
    p_tr.add_argument(
        "--ascher", action="store_true",
        help="Enrich with KFG Ascher pendant-pendant constraints "
             "(roles, checksum verification, Merkle cascade depth)"
    )
    p_tr.add_argument(
        "--from-merged", action="store_true",
        help="Fill unreadable L? cords with KFG turn counts from the "
             "merged OKR × KFG corpus (data/merged/). Requires merge_okr_kfg.py"
             " to have been run."
    )
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

    # schema
    p_sc = sub.add_parser("schema", help="Detect physical schema type")
    p_sc.add_argument("khipu", help="Khipu ID")
    p_sc.add_argument("--db", help=db_help)
    p_sc.set_defaults(func=cmd_schema)

    # header
    p_hd = sub.add_parser("header", aliases=["h"], help="Show document identity card")
    p_hd.add_argument("khipu", help="Khipu ID")
    p_hd.add_argument("--db", help=db_help)
    p_hd.add_argument("--lang", choices=["en", "fr", "es"], default="en")
    p_hd.set_defaults(func=cmd_header)

    # date
    p_dt = sub.add_parser("date", aliases=["d"], help="Extract date from a khipu")
    p_dt.add_argument("khipu", help="Khipu ID")
    p_dt.add_argument("--db", help=db_help)
    p_dt.add_argument("--epoch", type=int, default=None,
                       help="Reference epoch (default: 1438 CE)")
    p_dt.set_defaults(func=cmd_date)

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
