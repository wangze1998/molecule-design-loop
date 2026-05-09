#!/usr/bin/env python3
"""Render molecule-design candidate CSV rows into a standalone HTML gallery."""

from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", help="Candidate or filtered candidate CSV")
    parser.add_argument("output_html", help="Standalone HTML gallery output")
    parser.add_argument("--title", default="Molecule Design Candidate Gallery")
    parser.add_argument("--limit", type=int, default=None, help="Optional max rows to render")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def choose_smiles(row: dict[str, str]) -> str:
    return (row.get("canonical_smiles") or row.get("smiles") or "").strip()


def molecule_svg(smiles: str, width: int = 320, height: int = 220) -> str:
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return '<div class="invalid-mol">Invalid SMILES</div>'

    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.drawOptions().padding = 0.05
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText().replace("svg:", "")


def badge(label: str, value: str) -> str:
    safe_label = html.escape(label)
    safe_value = html.escape(value or "n/a")
    return f'<span class="badge"><strong>{safe_label}:</strong> {safe_value}</span>'


def metadata_rows(row: dict[str, str]) -> str:
    skip = {"smiles", "canonical_smiles"}
    lines: list[str] = []
    for key, value in row.items():
        if key in skip or not value:
            continue
        lines.append(
            "<tr>"
            f"<th>{html.escape(key)}</th>"
            f"<td>{html.escape(value)}</td>"
            "</tr>"
        )
    return "".join(lines)


def candidate_card(row: dict[str, str]) -> str:
    candidate_id = row.get("candidate_id") or "unknown_candidate"
    smiles = choose_smiles(row)
    decision = row.get("filter_decision") or "unreviewed"
    reason = row.get("filter_reason") or "n/a"
    target_constraint = row.get("target_constraint") or "n/a"
    design_move = row.get("design_move") or "n/a"
    rationale = row.get("rationale") or "n/a"

    return (
        '<article class="card">'
        f'<div class="mol">{molecule_svg(smiles)}</div>'
        '<div class="card-body">'
        f"<h2>{html.escape(candidate_id)}</h2>"
        f"<p class=\"smiles\">{html.escape(smiles or 'missing_smiles')}</p>"
        '<div class="badges">'
        f"{badge('filter_decision', decision)}"
        f"{badge('target_constraint', target_constraint)}"
        f"{badge('design_move', design_move)}"
        "</div>"
        f"<p><strong>Filter reason:</strong> {html.escape(reason)}</p>"
        f"<p><strong>Rationale:</strong> {html.escape(rationale)}</p>"
        '<details><summary>All metadata</summary>'
        '<table class="meta-table"><tbody>'
        f"{metadata_rows(row)}"
        "</tbody></table></details>"
        "</div>"
        "</article>"
    )


def render_html(rows: list[dict[str, str]], title: str) -> str:
    total = len(rows)
    passed = sum(1 for row in rows if (row.get("filter_decision") or "") == "pass")
    rejected = sum(1 for row in rows if (row.get("filter_decision") or "") == "reject")
    cards = "".join(candidate_card(row) for row in rows)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f7f7f3;
      --panel: #fffdf7;
      --ink: #1f1f1a;
      --muted: #6d6a5f;
      --line: #d9d4c7;
      --accent: #1f6f5f;
      --warn: #9f4d1f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      background: linear-gradient(180deg, #faf8f1 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      margin-bottom: 24px;
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255, 253, 247, 0.9);
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: clamp(28px, 4vw, 44px);
      line-height: 1.05;
    }}
    .summary {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      color: var(--muted);
    }}
    .summary strong {{ color: var(--ink); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 18px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 22px;
      overflow: hidden;
      background: var(--panel);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.05);
    }}
    .mol {{
      padding: 14px;
      border-bottom: 1px solid var(--line);
      background:
        radial-gradient(circle at top left, rgba(31, 111, 95, 0.10), transparent 35%),
        linear-gradient(180deg, #fffefa 0%, #f6f1e5 100%);
      min-height: 240px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .mol svg {{
      width: 100%;
      height: auto;
      max-height: 220px;
    }}
    .invalid-mol {{
      color: var(--warn);
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .card-body {{
      padding: 18px;
    }}
    .card-body h2 {{
      margin: 0 0 8px;
      font-size: 22px;
    }}
    .smiles {{
      margin: 0 0 12px;
      color: var(--muted);
      font-family: "SFMono-Regular", "Menlo", monospace;
      word-break: break-all;
    }}
    .badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .badge {{
      display: inline-flex;
      gap: 4px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #f5f1e5;
      font-size: 13px;
    }}
    p {{
      margin: 0 0 10px;
      line-height: 1.45;
    }}
    details {{
      margin-top: 12px;
    }}
    summary {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 700;
    }}
    .meta-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 14px;
    }}
    .meta-table th,
    .meta-table td {{
      text-align: left;
      vertical-align: top;
      padding: 8px 10px;
      border-top: 1px solid var(--line);
    }}
    .meta-table th {{
      width: 36%;
      color: var(--muted);
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{html.escape(title)}</h1>
      <div class="summary">
        <span><strong>Total:</strong> {total}</span>
        <span><strong>Pass:</strong> {passed}</span>
        <span><strong>Reject:</strong> {rejected}</span>
      </div>
    </header>
    <section class="grid">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_csv)
    output_path = Path(args.output_html)

    rows = read_rows(input_path)
    if args.limit is not None:
        rows = rows[: args.limit]

    if not rows:
        raise SystemExit(f"No rows found in {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(rows, args.title), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
