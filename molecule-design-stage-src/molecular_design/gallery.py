from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D


def render_gallery_csv(input_csv: Path, output_html: Path, title: str, limit: int | None = None) -> None:
    rows = read_rows(input_csv)
    if limit is not None:
        rows = rows[:limit]
    output_html.write_text(render_html(rows, title), encoding="utf-8")


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


def render_html(rows: list[dict[str, str]], title: str) -> str:
    cards = "\n".join(_card(row) for row in rows)
    passed = sum(1 for row in rows if row.get("filter_decision") == "pass")
    rejected = sum(1 for row in rows if row.get("filter_decision") == "reject")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ --bg:#f7f7f3; --panel:#fffdf7; --ink:#202018; --muted:#686456; --line:#d8d1c2; --accent:#1f6f5f; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }}
    main {{ max-width:1360px; margin:0 auto; padding:28px 18px 44px; }}
    header {{ margin-bottom:20px; border-bottom:1px solid var(--line); padding-bottom:18px; }}
    h1 {{ margin:0 0 8px; font-size:32px; }}
    .summary {{ color:var(--muted); display:flex; gap:14px; flex-wrap:wrap; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:16px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    .mol {{ min-height:232px; padding:14px; background:#fff; display:flex; align-items:center; justify-content:center; border-bottom:1px solid var(--line); }}
    .mol svg {{ width:100%; height:auto; max-height:220px; }}
    .body {{ padding:14px; }}
    h2 {{ margin:0 0 8px; font-size:18px; }}
    .smiles {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; overflow-wrap:anywhere; color:var(--muted); }}
    .badges {{ display:flex; flex-wrap:wrap; gap:6px; margin:10px 0; }}
    .badge {{ border:1px solid var(--line); border-radius:999px; padding:4px 8px; font-size:12px; background:#fff; }}
    table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:12px; }}
    th,td {{ border-top:1px solid var(--line); padding:6px; text-align:left; vertical-align:top; }}
    th {{ width:34%; color:var(--muted); font-weight:600; }}
    .invalid-mol {{ color:#9f4d1f; font-weight:700; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{html.escape(title)}</h1>
      <div class="summary"><span>Total: <strong>{len(rows)}</strong></span><span>Pass: <strong>{passed}</strong></span><span>Reject: <strong>{rejected}</strong></span></div>
    </header>
    <section class="grid">{cards}</section>
  </main>
</body>
</html>
"""


def _card(row: dict[str, str]) -> str:
    candidate_id = row.get("candidate_id") or "unknown"
    smiles = choose_smiles(row)
    metadata = "".join(
        f"<tr><th>{html.escape(key)}</th><td>{html.escape(value)}</td></tr>"
        for key, value in row.items()
        if value and key not in {"smiles", "canonical_smiles"}
    )
    badges = "".join(
        _badge(label, row.get(label, ""))
        for label in ("filter_decision", "target_constraint", "design_move")
        if row.get(label)
    )
    return (
        '<article class="card">'
        f'<div class="mol">{molecule_svg(smiles)}</div>'
        '<div class="body">'
        f"<h2>{html.escape(candidate_id)}</h2>"
        f'<p class="smiles">{html.escape(smiles or "missing_smiles")}</p>'
        f'<div class="badges">{badges}</div>'
        f"<p>{html.escape(row.get('filter_reason') or 'n/a')}</p>"
        "<details><summary>All metadata</summary><table><tbody>"
        f"{metadata}"
        "</tbody></table></details>"
        "</div></article>"
    )


def _badge(label: str, value: str) -> str:
    return f'<span class="badge"><strong>{html.escape(label)}:</strong> {html.escape(value)}</span>'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render molecular-design candidate gallery")
    parser.add_argument("input_csv")
    parser.add_argument("output_html")
    parser.add_argument("--title", default="Molecule Design Candidate Gallery")
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    render_gallery_csv(Path(args.input_csv), Path(args.output_html), args.title, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
