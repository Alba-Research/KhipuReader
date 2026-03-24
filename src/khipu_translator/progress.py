"""
Progress tracker — generate PROGRESS.md from contributions.

Reads all JSON files in contributions/, cross-references with OKR,
and generates a progress report.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Optional

from khipu_translator.database import KhipuDB
from khipu_translator.submit import load_contributions


def generate_progress(
    db: Optional[KhipuDB] = None,
    contributions_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate PROGRESS.md content.

    Returns the markdown string and optionally writes to file.
    """
    close_db = False
    if db is None:
        db = KhipuDB()
        close_db = True

    try:
        all_khipus = db.list_khipus()
        total = len(all_khipus)
    finally:
        if close_db:
            db.close()

    contributions = load_contributions(contributions_dir)
    analyzed = len(contributions)
    pct = 100 * analyzed / total if total > 0 else 0

    # Progress bar
    bar_len = 30
    filled = int(bar_len * analyzed / total) if total > 0 else 0
    bar = "=" * filled + ">" + " " * (bar_len - filled - 1)

    # Per-status breakdown
    statuses = Counter(c.get("status", "unknown") for c in contributions.values())

    # Per-type breakdown
    types = Counter(
        c.get("auto_translation", {}).get("document_type", "unknown")
        for c in contributions.values()
    )

    # Per-museum breakdown
    museums = Counter()
    for c in contributions.values():
        museum = c.get("auto_translation", {}).get("museum", "Unknown")
        if museum:
            # Shorten museum name
            short = museum.strip('"')[:40]
            museums[short] += 1

    # Recently analyzed (by date)
    recent = sorted(
        contributions.items(),
        key=lambda x: x[1].get("date", ""),
        reverse=True,
    )[:10]

    # Contributors
    contributors = Counter()
    for c in contributions.values():
        name = c.get("contributor", "Unknown")
        if "TODO" not in name and "example" not in name:
            contributors[name] += 1

    # Build markdown
    lines = [
        "# KhipuReader — Progress",
        "",
        f"## [{bar}] {analyzed}/{total} khipus analyzed ({pct:.1f}%)",
        "",
        f"*Auto-generated. Last updated from `contributions/` directory.*",
        "",
    ]

    # Status
    lines.extend([
        "## By status",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ])
    for status, count in statuses.most_common():
        lines.append(f"| {status} | {count} |")

    # Document types
    lines.extend([
        "",
        "## By document type",
        "",
        "| Type | Count |",
        "|------|-------|",
    ])
    for dtype, count in types.most_common():
        lines.append(f"| {dtype} | {count} |")

    # Museums
    if museums:
        lines.extend([
            "",
            "## By museum",
            "",
            "| Museum | Analyzed |",
            "|--------|----------|",
        ])
        for museum, count in museums.most_common():
            lines.append(f"| {museum} | {count} |")

    # Recent
    if recent:
        lines.extend([
            "",
            "## Recently analyzed",
            "",
            "| Khipu | Date | Summary |",
            "|-------|------|---------|",
        ])
        for kid, data in recent:
            d = data.get("date", "?")
            s = data.get("summary", "")[:60]
            lines.append(f"| {kid} | {d} | {s} |")

    # Contributors
    if contributors:
        lines.extend([
            "",
            "## Contributors",
            "",
            "| Name | Contributions |",
            "|------|--------------|",
        ])
        for name, count in contributors.most_common():
            lines.append(f"| {name} | {count} |")

    # Most wanted
    lines.extend([
        "",
        "## Most wanted (unanalyzed khipus with high STRING %)",
        "",
        "*Run `khipu unclaimed` to see the full list.*",
        "",
        f"**{total - analyzed} khipus** still waiting to be read.",
    ])

    md = "\n".join(lines) + "\n"

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)

    return md
