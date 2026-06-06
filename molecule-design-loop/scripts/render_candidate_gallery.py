#!/usr/bin/env python3
"""Render molecule-design candidate CSV rows into a standalone HTML gallery."""

from __future__ import annotations

import argparse
import csv
import html
import re
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D


BACKBONE_COLOR = (0.12, 0.44, 0.37)
SIDE_CHAIN_COLOR = (0.82, 0.46, 0.18)
CONNECTION_COLOR = (0.78, 0.12, 0.18)


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
    for key in (
        "rdkit_display_smiles",
        "oligomer_model_smiles",
        "rdkit_input_smiles",
        "canonical_smiles",
        "smiles",
    ):
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def choose_repeat_unit_smiles(row: dict[str, str]) -> str:
    for key in ("repeat_unit_display_smiles", "repeat_unit_smiles"):
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def parse_atom_indices(value: str, atom_count: int | None = None) -> list[int]:
    raw = [int(match) for match in re.findall(r"\d+", value or "")]
    if not raw:
        return []
    zero_based = [idx for idx in raw if atom_count is None or 0 <= idx < atom_count]
    if zero_based:
        return list(dict.fromkeys(zero_based))
    one_based = [idx - 1 for idx in raw if atom_count is None or 1 <= idx <= atom_count]
    return list(dict.fromkeys(one_based))


def parse_side_chain_fragments(value: str) -> list[tuple[str, str]]:
    fragments: list[tuple[str, str]] = []
    for index, chunk in enumerate(re.split(r"[;|]", value or ""), start=1):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            label, smiles = chunk.split(":", 1)
            fragments.append((label.strip() or f"side_chain_{index}", smiles.strip()))
        else:
            fragments.append((f"side_chain_{index}", chunk))
    return fragments


def parse_path_tokens(value: str, start: str = "", end: str = "") -> list[str]:
    tokens = [
        token.strip()
        for token in re.split(r"\s*(?:->|=>|,|;|\|)\s*", value or "")
        if token.strip()
    ]
    if not tokens:
        tokens = [token for token in (start.strip(), end.strip()) if token]
    if start.strip() and (not tokens or tokens[0] != start.strip()):
        tokens.insert(0, start.strip())
    if end.strip() and (not tokens or tokens[-1] != end.strip()):
        tokens.append(end.strip())
    return tokens


def parse_callout_tokens(value: str) -> list[str]:
    return [
        token.strip()
        for token in re.split(r"\s*(?:;|\|)\s*", value or "")
        if token.strip()
    ]


def path_bonds(mol: Chem.Mol, atom_indices: list[int]) -> list[int]:
    bonds: list[int] = []
    for begin, end in zip(atom_indices, atom_indices[1:]):
        bond = mol.GetBondBetweenAtoms(begin, end)
        if bond is not None:
            bonds.append(bond.GetIdx())
    return bonds


def molecule_svg(
    smiles: str,
    width: int = 320,
    height: int = 220,
    add_atom_indices: bool = False,
    show_repeat_handles: bool = False,
    highlight_atoms: dict[int, tuple[float, float, float]] | None = None,
    highlight_bonds: dict[int, tuple[float, float, float]] | None = None,
) -> str:
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return '<div class="invalid-mol">Invalid SMILES</div>'

    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    options = drawer.drawOptions()
    options.padding = 0.05
    options.addAtomIndices = add_atom_indices
    if show_repeat_handles:
        for atom in mol.GetAtoms():
            if atom.GetAtomicNum() == 0 and atom.GetAtomMapNum():
                options.atomLabels[atom.GetIdx()] = f"*:{atom.GetAtomMapNum()}"
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer,
        mol,
        highlightAtoms=list((highlight_atoms or {}).keys()),
        highlightBonds=list((highlight_bonds or {}).keys()),
        highlightAtomColors=highlight_atoms or {},
        highlightBondColors=highlight_bonds or {},
    )
    drawer.FinishDrawing()
    return drawer.GetDrawingText().replace("svg:", "")


def backbone_svg(smiles: str, backbone_atoms: list[int], backbone_only_smiles: str = "") -> str:
    if backbone_only_smiles.strip():
        return molecule_svg(backbone_only_smiles.strip(), width=300, height=180, add_atom_indices=True)
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None or len(backbone_atoms) < 2:
        return '<div class="invalid-mol">Backbone path unavailable</div>'
    bonds = path_bonds(mol, backbone_atoms)
    if not bonds:
        return '<div class="invalid-mol">Backbone bonds unavailable</div>'
    submol = Chem.PathToSubmol(mol, bonds)
    backbone_smiles = Chem.MolToSmiles(submol)
    return molecule_svg(backbone_smiles, width=300, height=180, add_atom_indices=True)


def badge(label: str, value: str) -> str:
    safe_label = html.escape(label)
    safe_value = html.escape(value or "n/a")
    return f'<span class="badge"><strong>{safe_label}:</strong> {safe_value}</span>'


def metadata_rows(row: dict[str, str]) -> str:
    skip = {"smiles", "canonical_smiles", "rdkit_display_smiles"}
    lines: list[str] = []
    for key, value in row.items():
        if key is None:
            continue
        if key in skip or not value:
            continue
        lines.append(
            "<tr>"
            f"<th>{html.escape(key)}</th>"
            f"<td>{html.escape(value)}</td>"
            "</tr>"
        )
    return "".join(lines)


def polymer_guide(row: dict[str, str]) -> str:
    fields = [
        ("sru_bracket_schematic", "SRU schematic"),
        ("repeat_unit_handles_explanation", "repeat-unit handles"),
        ("polymer_notation", "polymer"),
        ("rdkit_display_smiles", "display"),
        ("monomer_smiles", "monomer"),
        ("repeat_unit_smiles", "repeat unit"),
        ("oligomer_model_smiles", "oligomer model"),
        ("backbone_start_atom", "backbone start"),
        ("backbone_end_atom", "backbone end"),
        ("backbone_connection_points", "connection points"),
        ("backbone_direction_label", "backbone direction"),
        ("backbone_path_atoms", "backbone path"),
        ("side_chain_attachment_atoms", "side-chain atoms"),
        ("side_chain_fragment_smiles", "side-chain fragments"),
        ("side_chain_descriptions", "side chains"),
        ("end_group_model", "end groups"),
        ("surrogate_scope", "scope"),
    ]
    items = []
    for key, label in fields:
        value = (row.get(key) or "").strip()
        if value:
            items.append(f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>")
    if not items:
        return ""
    return '<section class="polymer-guide"><h3>Polymer map</h3><dl>' + "".join(items) + "</dl></section>"


def sru_bracket_view(row: dict[str, str]) -> str:
    schematic = (row.get("sru_bracket_schematic") or "").strip()
    handles = (row.get("repeat_unit_handles_explanation") or "").strip()
    repeat_smiles = choose_repeat_unit_smiles(row)
    if not schematic and not handles and not repeat_smiles:
        return ""
    candidate_id = row.get("candidate_id") or "candidate"
    side_text = (row.get("side_chain_descriptions") or "").strip()
    side_html = f'<p class="sru-side">{html.escape(side_text)}</p>' if side_text else ""
    schematic_html = f'<div class="sru-schematic">{html.escape(schematic)}</div>' if schematic else ""
    caption = (row.get("repeat_unit_caption") or "").strip()
    if not caption:
        caption_lines = [
            f"{candidate_id} intended repeat unit",
            "[*:1] and [*:2] = polymer chain extension",
        ]
        if side_text:
            caption_lines.append(side_text)
        caption = "\n".join(caption_lines)
    repeat_unit_html = ""
    if repeat_smiles:
        repeat_unit_html = (
            '<figure class="repeat-unit-figure">'
            f"{molecule_svg(repeat_smiles, width=760, height=360, show_repeat_handles=True)}"
            f"<figcaption>{html.escape(caption)}</figcaption>"
            "</figure>"
        )
    handles_html = f'<pre class="handles-explanation">{html.escape(handles)}</pre>' if handles else ""
    return (
        '<section class="sru-view">'
        "<h3>Primary polymer view</h3>"
        f"{repeat_unit_html}"
        f"{schematic_html}"
        f"{handles_html}"
        f"{side_html}"
        "</section>"
    )


def backbone_direction_schematic(row: dict[str, str]) -> str:
    start = row.get("backbone_start_atom") or "START"
    end = row.get("backbone_end_atom") or "END"
    path_value = row.get("backbone_direction_label") or row.get("backbone_path_atoms") or ""
    tokens = parse_path_tokens(path_value, start, end)
    if len(tokens) < 2:
        return ""

    nodes = []
    for index, token in enumerate(tokens):
        node_class = "chain-node"
        label = html.escape(token)
        if index == 0:
            node_class += " chain-start"
            label = f"<strong>START</strong><span>{label}</span>"
        elif index == len(tokens) - 1:
            node_class += " chain-end"
            label = f"<strong>END</strong><span>{label}</span>"
        else:
            label = f"<span>{label}</span>"
        nodes.append(f'<span class="{node_class}">{label}</span>')
        if index != len(tokens) - 1:
            nodes.append('<span class="chain-arrow">-&gt;</span>')

    side_descriptions = parse_callout_tokens(row.get("side_chain_descriptions") or "")
    side_attachments = parse_callout_tokens(row.get("side_chain_attachment_atoms") or "")
    side_fragments = parse_side_chain_fragments(row.get("side_chain_fragment_smiles") or "")
    callouts = []
    for index, description in enumerate(side_descriptions):
        attachment = side_attachments[index] if index < len(side_attachments) else ""
        prefix = f"{attachment}: " if attachment else ""
        callouts.append(f"<li>{html.escape(prefix + description)}</li>")
    for label, smiles in side_fragments:
        callouts.append(f"<li>{html.escape(label)}: <code>{html.escape(smiles)}</code></li>")

    callout_html = ""
    if callouts:
        callout_html = '<ul class="side-callouts">' + "".join(callouts) + "</ul>"

    return (
        '<section class="backbone-direction">'
        "<h4>Backbone direction</h4>"
        '<div class="chain-track">'
        + "".join(nodes)
        + "</div>"
        + callout_html
        + "</section>"
    )


def polymer_depiction_packet(row: dict[str, str], smiles: str) -> str:
    if not has_polymer_map(row):
        return ""
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    atom_count = mol.GetNumAtoms() if mol is not None else None
    backbone_atoms = parse_atom_indices(row.get("backbone_path_atoms") or "", atom_count)
    side_atoms = parse_atom_indices(row.get("side_chain_attachment_atoms") or "", atom_count)
    connection_atoms = parse_atom_indices(
        " ".join(
            [
                row.get("connection_point_atoms") or "",
                row.get("backbone_start_atom") or "",
                row.get("backbone_end_atom") or "",
                row.get("backbone_connection_points") or "",
            ]
        ),
        atom_count,
    )
    highlight_atoms = {idx: BACKBONE_COLOR for idx in backbone_atoms}
    highlight_atoms.update({idx: SIDE_CHAIN_COLOR for idx in side_atoms})
    highlight_atoms.update({idx: CONNECTION_COLOR for idx in connection_atoms})
    highlight_bonds = {}
    if mol is not None:
        highlight_bonds = {idx: BACKBONE_COLOR for idx in path_bonds(mol, backbone_atoms)}

    full = molecule_svg(
        smiles,
        add_atom_indices=True,
        highlight_atoms=highlight_atoms,
        highlight_bonds=highlight_bonds,
    )
    backbone = backbone_svg(smiles, backbone_atoms, row.get("backbone_only_smiles") or "")
    side_fragments = parse_side_chain_fragments(row.get("side_chain_fragment_smiles") or "")
    side_cards = []
    for label, fragment_smiles in side_fragments:
        side_cards.append(
            '<div class="side-fragment">'
            f"<h4>{html.escape(label)}</h4>"
            f"{molecule_svg(fragment_smiles, width=220, height=150, add_atom_indices=True)}"
            f'<p class="smiles">{html.escape(fragment_smiles)}</p>'
            "</div>"
        )
    if not side_cards:
        side_cards.append(
            '<div class="side-fragment text-only">'
            f"<p>{html.escape(row.get('side_chain_descriptions') or 'No side-chain fragments provided.')}</p>"
            "</div>"
        )

    return (
        '<section class="polymer-packet">'
        "<h3>Polymer depiction packet</h3>"
        f"{backbone_direction_schematic(row)}"
        '<div class="packet-grid">'
        f'<div><h4>Full oligomer</h4>{full}</div>'
        f'<div><h4>Backbone only</h4>{backbone}</div>'
        f'<div><h4>Side chains</h4>{"".join(side_cards)}</div>'
        "</div>"
        '<p class="legend"><span class="legend-backbone">main chain</span> '
        '<span class="legend-side">side-chain attachments</span> '
        '<span class="legend-connection">extension points</span></p>'
        "</section>"
    )


def has_polymer_map(row: dict[str, str]) -> bool:
    keys = {
        "polymer_notation",
        "sru_bracket_schematic",
        "repeat_unit_handles_explanation",
        "repeat_unit_display_smiles",
        "repeat_unit_caption",
        "rdkit_display_smiles",
        "backbone_start_atom",
        "backbone_end_atom",
        "backbone_connection_points",
        "backbone_direction_label",
        "backbone_path_atoms",
        "side_chain_attachment_atoms",
        "side_chain_fragment_smiles",
        "side_chain_descriptions",
    }
    return any((row.get(key) or "").strip() for key in keys)


def candidate_card(row: dict[str, str]) -> str:
    candidate_id = row.get("candidate_id") or "unknown_candidate"
    smiles = choose_smiles(row)
    decision = row.get("filter_decision") or "unreviewed"
    reason = row.get("filter_reason") or "n/a"
    target_constraint = row.get("target_constraint") or "n/a"
    design_move = row.get("design_move") or "n/a"
    rationale = row.get("rationale") or "n/a"
    is_polymer = has_polymer_map(row)
    top_mol = "" if is_polymer else f'<div class="mol">{molecule_svg(smiles)}</div>'

    return (
        '<article class="card">'
        f"{top_mol}"
        '<div class="card-body">'
        f"<h2>{html.escape(candidate_id)}</h2>"
        f"{sru_bracket_view(row)}"
        f"<p class=\"smiles\">{html.escape(smiles or 'missing_smiles')}</p>"
        '<div class="badges">'
        f"{badge('filter_decision', decision)}"
        f"{badge('target_constraint', target_constraint)}"
        f"{badge('design_move', design_move)}"
        "</div>"
        f"<p><strong>Filter reason:</strong> {html.escape(reason)}</p>"
        f"<p><strong>Rationale:</strong> {html.escape(rationale)}</p>"
        f"{polymer_depiction_packet(row, smiles)}"
        f"{polymer_guide(row)}"
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
    .sru-view {{
      margin: 0 0 14px;
      padding: 14px;
      border: 2px solid var(--accent);
      border-radius: 8px;
      background: #f1faf6;
    }}
    .sru-view h3 {{
      margin: 0 0 8px;
      font-size: 15px;
      color: var(--accent);
    }}
    .sru-schematic {{
      font-family: "SFMono-Regular", "Menlo", monospace;
      font-size: 18px;
      font-weight: 800;
      line-height: 1.5;
      word-break: break-word;
      color: var(--ink);
    }}
    .repeat-unit-figure {{
      margin: 0;
      text-align: center;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }}
    .repeat-unit-figure svg {{
      width: 100%;
      max-width: 760px;
      height: auto;
    }}
    .repeat-unit-figure figcaption {{
      margin-top: 8px;
      white-space: pre-wrap;
      font-family: "SFMono-Regular", "Menlo", monospace;
      font-size: 13px;
      line-height: 1.35;
      color: var(--ink);
    }}
    .sru-side {{
      margin: 8px 0 0;
      color: var(--muted);
    }}
    .handles-explanation {{
      margin: 10px 0 0;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fffef8;
      white-space: pre-wrap;
      font-family: "SFMono-Regular", "Menlo", monospace;
      font-size: 14px;
      line-height: 1.45;
    }}
    .polymer-packet {{
      margin: 14px 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fffaf0;
    }}
    .polymer-packet h3 {{
      margin: 0 0 10px;
      font-size: 15px;
      color: var(--accent);
    }}
    .backbone-direction {{
      margin: 10px 0 14px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f4faf5;
    }}
    .backbone-direction h4 {{
      margin: 0 0 10px;
      font-size: 14px;
      color: var(--accent);
    }}
    .chain-track {{
      display: flex;
      align-items: stretch;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 4px;
    }}
    .chain-node {{
      min-width: 96px;
      max-width: 220px;
      padding: 8px 10px;
      border: 2px solid #8bb8a8;
      border-radius: 8px;
      background: #ffffff;
      font-size: 13px;
      line-height: 1.25;
      word-break: break-word;
    }}
    .chain-node strong {{
      display: block;
      margin-bottom: 4px;
      font-size: 12px;
      letter-spacing: 0.06em;
    }}
    .chain-start {{
      border-color: #c71f2d;
      background: #fff1f1;
    }}
    .chain-end {{
      border-color: #245fd4;
      background: #eef4ff;
    }}
    .chain-arrow {{
      display: inline-flex;
      align-items: center;
      color: var(--accent);
      font-weight: 800;
      font-size: 20px;
      flex: 0 0 auto;
    }}
    .side-callouts {{
      margin: 10px 0 0;
      padding-left: 20px;
      color: var(--muted);
      font-size: 14px;
    }}
    .side-callouts code {{
      font-family: "SFMono-Regular", "Menlo", monospace;
      color: var(--ink);
    }}
    .packet-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .packet-grid h4,
    .side-fragment h4 {{
      margin: 0 0 6px;
      font-size: 13px;
      color: var(--muted);
    }}
    .packet-grid svg,
    .side-fragment svg {{
      max-width: 100%;
      height: auto;
      background: #fffef8;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    .side-fragment {{
      margin-bottom: 8px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 8px 0 0;
      font-size: 13px;
    }}
    .legend span::before {{
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      margin-right: 5px;
      border-radius: 50%;
    }}
    .legend-backbone::before {{ background: #1f6f5f; }}
    .legend-side::before {{ background: #d1752e; }}
    .legend-connection::before {{ background: #c71f2d; }}
    .polymer-guide {{
      margin: 14px 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbf7ed;
    }}
    .polymer-guide h3 {{
      margin: 0 0 8px;
      font-size: 15px;
      color: var(--accent);
    }}
    .polymer-guide dl {{
      display: grid;
      grid-template-columns: minmax(100px, 34%) 1fr;
      gap: 6px 10px;
      margin: 0;
      font-size: 14px;
    }}
    .polymer-guide dt {{
      color: var(--muted);
      font-weight: 700;
    }}
    .polymer-guide dd {{
      margin: 0;
      word-break: break-word;
      font-family: "SFMono-Regular", "Menlo", monospace;
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
