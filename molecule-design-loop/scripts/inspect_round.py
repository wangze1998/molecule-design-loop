#!/usr/bin/env python3
"""Inspect round files without reading them whole (stdlib only).

Why this exists
---------------
`cat ROUND_N_CANDIDATES.csv` costs thousands of tokens and is almost never what
was wanted: the question is usually "which rows failed", "what is in these three
columns", or "did the gallery render". Every mode here prints a bounded summary
and says when it truncated, so the answer is cheap and the omission is visible.

Modes
-----
  summary  : shape, column names, fill rate, and flag-column tallies
  cols     : chosen columns for all rows (the common 'show me the decisions' view)
  row      : one row as a field list, long values clipped
  grep     : rows whose any field matches a pattern, as the `cols` view
  check    : required columns present, ids unique, no empty required cells
  html     : size and element tallies for a rendered gallery, never its markup

Usage
-----
  inspect_round.py summary ROUND_1_FILTERED.csv
  inspect_round.py cols ROUND_1_FILTERED.csv candidate_id filter_decision filter_reason
  inspect_round.py row ROUND_1_CANDIDATES.csv C1
  inspect_round.py grep ROUND_1_FILTERED.csv fail --columns candidate_id filter_reason
  inspect_round.py check ROUND_1_CANDIDATES.csv --required candidate_id smiles rationale
  inspect_round.py html ROUND_1_CANDIDATE_GALLERY.html
"""
import argparse
import csv
import os
import re
import sys

csv.field_size_limit(10_000_000)

# Columns whose small vocabulary makes a tally informative.
FLAG_COLUMNS = [
    "filter_decision", "synthesis_gate_status", "make_or_buy_status", "role",
    "gemini_adversarial_flag", "prior_art_status", "auditor_flag", "building_block_source",
    "experimental_priority", "synthesis_cost", "time_to_first_sample",
    "overall_yield_estimate", "hazard_toxicity_flag", "success_status",
    "polymer_xtb_preflight_status", "evidence_level", "design_mode",
]
DEFAULT_WIDTH = 60


def load(path):
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        sys.exit(f"{path}: no data rows")
    return rows


def clip(value, width):
    value = " ".join((value or "").split())
    if width and len(value) > width:
        return value[: width - 1] + "…"
    return value


def mode_summary(args):
    rows = load(args.path)
    columns = list(rows[0])
    print(f"{os.path.basename(args.path)}: {len(rows)} rows x {len(columns)} columns "
          f"({os.path.getsize(args.path)} bytes)")
    empty = [c for c in columns if not any((r.get(c) or "").strip() for r in rows)]
    if empty:
        print(f"\nalways empty ({len(empty)}): {' '.join(empty)}")
    print(f"\npopulated columns: {' '.join(c for c in columns if c not in empty)}")
    for column in FLAG_COLUMNS:
        if column not in columns:
            continue
        tally = {}
        for row in rows:
            tally[(row.get(column) or "").strip() or "(empty)"] = (
                tally.get((row.get(column) or "").strip() or "(empty)", 0) + 1
            )
        joined = "  ".join(f"{k}={v}" for k, v in sorted(tally.items(), key=lambda x: -x[1]))
        print(f"  {column}: {joined}")


def print_table(rows, columns, width):
    missing = [c for c in columns if c not in rows[0]]
    columns = [c for c in columns if c in rows[0]]
    if not columns:
        sys.exit(f"none of those columns exist; available: {' '.join(rows[0])}")
    widths = [
        min(width, max(len(c), *(len(clip(r.get(c), width)) for r in rows))) for c in columns
    ]
    print("  ".join(c.ljust(w) for c, w in zip(columns, widths)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(clip(row.get(c), width).ljust(w) for c, w in zip(columns, widths)))
    if missing:
        print(f"\n(absent from this file: {' '.join(missing)})")


def mode_cols(args):
    rows = load(args.path)
    print_table(rows, args.columns, args.width)
    print(f"\n{len(rows)} rows; values clipped at {args.width} characters")


def mode_row(args):
    rows = load(args.path)
    key = args.candidate_id
    matches = [r for r in rows if (r.get("candidate_id") or "").strip() == key]
    if not matches:
        sys.exit(f"no row with candidate_id {key!r}")
    for column, value in matches[0].items():
        value = (value or "").strip()
        if value or args.show_empty:
            print(f"{column}: {clip(value, args.width)}")


def mode_grep(args):
    rows = load(args.path)
    pattern = re.compile(args.pattern, re.I)
    hits = [r for r in rows if any(pattern.search(v or "") for v in r.values())]
    if not hits:
        print(f"no row matches {args.pattern!r} ({len(rows)} rows searched)")
        return
    columns = args.columns or [c for c in ("candidate_id", "filter_decision", "role") if c in rows[0]]
    shown = hits[: args.limit]
    print_table(shown, columns, args.width)
    print(f"\n{len(hits)} of {len(rows)} rows match", end="")
    print(f"; showing {len(shown)} (raise --limit for more)" if len(shown) < len(hits) else "")


def mode_check(args):
    rows = load(args.path)
    problems = []
    missing = [c for c in args.required if c not in rows[0]]
    if missing:
        problems.append(f"missing columns: {' '.join(missing)}")
    ids = [(r.get("candidate_id") or "").strip() for r in rows]
    if "" in ids:
        problems.append(f"{ids.count('')} row(s) have no candidate_id")
    duplicates = sorted({i for i in ids if i and ids.count(i) > 1})
    if duplicates:
        problems.append(f"duplicate candidate_id: {' '.join(duplicates)}")
    for column in args.required:
        if column in rows[0]:
            blank = [i or "?" for i, r in zip(ids, rows) if not (r.get(column) or "").strip()]
            if blank:
                problems.append(f"{column} empty for: {' '.join(blank[:10])}"
                                + (" ..." if len(blank) > 10 else ""))
    if problems:
        print(f"{os.path.basename(args.path)}: {len(problems)} problem(s)")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    print(f"{os.path.basename(args.path)}: {len(rows)} rows, all checks pass")


def mode_html(args):
    size = os.path.getsize(args.path)
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    title = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    print(f"{os.path.basename(args.path)}: {size} bytes ({size / 1_048_576:.1f} MB)")
    if title:
        print(f"title: {' '.join(title.group(1).split())}")
    for label, pattern in (
        ("candidate blocks", r'class="[^"]*candidate'),
        ("<svg> drawings", r"<svg"),
        ("embedded images", r"data:image/"),
        ("tables", r"<table"),
    ):
        print(f"  {label}: {len(re.findall(pattern, text, re.I))}")
    ids = re.findall(r'id="(?:candidate-)?([A-Za-z0-9_.-]{1,40})"', text)
    if ids:
        shown = ids[:15]
        print(f"  element ids ({len(ids)}): {' '.join(shown)}" + (" ..." if len(ids) > len(shown) else ""))
    print("\nThis is a size and structure check. Open the file in a browser to review it;\n"
          "do not read its markup into the conversation.")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # --width is accepted before or after the subcommand, since either reads naturally.
    # SUPPRESS, not a default: an unset subcommand flag must leave the parent's
    # value alone, or `--width 40 cols ...` would be silently overwritten by 60.
    width = argparse.ArgumentParser(add_help=False)
    width.add_argument("--width", type=int, default=argparse.SUPPRESS,
                       help=f"clip values at this many characters (default {DEFAULT_WIDTH})")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("summary", help="shape, populated columns, flag tallies")
    p.add_argument("path")
    p.set_defaults(func=mode_summary)

    p = sub.add_parser("cols", help="chosen columns for every row", parents=[width])
    p.add_argument("path")
    p.add_argument("columns", nargs="+")
    p.set_defaults(func=mode_cols)

    p = sub.add_parser("row", help="one row, long values clipped", parents=[width])
    p.add_argument("path")
    p.add_argument("candidate_id")
    p.add_argument("--show-empty", action="store_true")
    p.set_defaults(func=mode_row)

    p = sub.add_parser("grep", help="rows matching a pattern", parents=[width])
    p.add_argument("path")
    p.add_argument("pattern")
    p.add_argument("--columns", nargs="*")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=mode_grep)

    p = sub.add_parser("check", help="required columns, unique ids, no blanks")
    p.add_argument("path")
    p.add_argument("--required", nargs="+", default=["candidate_id", "smiles"])
    p.set_defaults(func=mode_check)

    p = sub.add_parser("html", help="gallery size and element tallies")
    p.add_argument("path")
    p.set_defaults(func=mode_html)

    args = parser.parse_args()
    if not os.path.exists(args.path):
        sys.exit(f"no such file: {args.path}")
    args.func(args)


if __name__ == "__main__":
    main()
