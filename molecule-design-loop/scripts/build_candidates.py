#!/usr/bin/env python3
"""Assemble ROUND_N_CANDIDATES.csv from a compact YAML config (Step 3).

Why this exists
---------------
The candidate table is mostly derived data: four copies of the same SMILES, atom
indices, repeat-unit drawings, and per-round boilerplate that is identical across
rows. Writing those by hand costs output tokens on every round and is the step
where transcription errors enter. This script derives them, so the config holds
only what needs chemical judgement: which fragments go on which scaffold, and the
per-candidate rationale.

Config sections (all optional unless noted)
-------------------------------------------
allowed_elements : list of element symbols every structure must stay within.
count_smarts     : {name: SMARTS}. Each structure's match count must equal what
                   the pieces declare: `counts` on each fragment used, plus the
                   template's own `counts` (fixed parts such as an end group) and
                   `counts_per_unit` x number of units. Catches assembly errors
                   that still parse -- a ring closure that ate a carbonyl, or a
                   fragment that attached twice.
fragments        : {name: {smiles, desc, label, counts}}. `smiles` may reference
                   other fragments as `{other_name}`.
text_blocks      : {name: text}. Prose reused across candidates, written once.
                   Referenced from any string field as `{{name}}` and expanded
                   with the row's own fields available as `{candidate_id}` etc.
scaffolds        : {name: {...}} for discrete molecules. Required: `template`
                   with one `{slot}` per attachment point.
chains           : {name: {...}} for polymers/oligomers. Required: `start`,
                   `segment` (one string or a list cycled over positions, each
                   holding `{x}` for the side chain), `end`.
defaults         : column values shared by every candidate.
candidates       : REQUIRED list. Each needs `candidate_id` plus either
                   `scaffold` + `slots`, or `chain` + `units`. Any other key
                   that names a schema column is copied through.

Usage
-----
  build_candidates.py --config round1.yaml --out ROUND_1_CANDIDATES.csv
  build_candidates.py --config round1.yaml --check-only    # validate, write nothing
  build_candidates.py --print-columns                      # list emitted columns

Writes one line per candidate to stdout and stops at the first chemistry failure;
a config that produces a wrong structure should fail loudly, not silently.
"""
import argparse
import csv
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - import guard
    sys.exit("PyYAML is required: pip install pyyaml")

try:
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors
    from rdkit import RDLogger
except ImportError:  # pragma: no cover - import guard
    sys.exit("RDKit is required: conda install -c conda-forge rdkit")

RDLogger.DisableLog("rdApp.*")

# Columns this script emits. Judgement columns are passed through from the config;
# derived columns are computed here and must not appear in the config.
PASSTHROUGH_COLUMNS = [
    "candidate_id", "parent_or_seed", "zotero_source_key", "zotero_source_title",
    "zotero_grounding", "proposal_family", "role", "design_move", "target_constraint",
    "rationale", "expected_proxy_effect", "risk", "source_hint", "synthesis_hypothesis",
    "make_or_buy_hint", "building_block_source", "route_risk", "experimental_readout",
    "design_mode", "constraint_coverage", "novelty_class",
    "small_molecule_design_mode", "small_molecule_target_type",
    "mechanism_or_property_hypothesis", "scaffold_policy", "key_positions",
    "experimental_priority", "recommended_experiments", "computational_evidence_role",
    "prior_computational_evidence", "polymer_design_mode", "structure_property_hypothesis",
    "primary_mechanism_to_tune", "synthesis_feasibility_notes", "polymer_html_view",
    "target_type", "graft_density_pct", "polymer_notation", "monomer_smiles",
    "xtb_input_model", "xtb_input_geometry_source", "target_polymer_property",
    "surrogate_scope", "polymer_xtb_preflight_status", "polymer_xtb_preflight_notes",
    "gemini_adversarial_flag",
]

DERIVED_COLUMNS = [
    "smiles", "canonical_smiles", "oligomer_model_smiles", "rdkit_input_smiles",
    "rdkit_display_smiles", "molecular_formula", "molecular_weight",
    "scaffold", "chain", "repeat_unit_display_smiles", "repeat_unit_caption",
    "sru_bracket_schematic", "repeat_unit_handles_explanation", "oligomer_n",
    "end_group_model", "backbone_start_atom", "backbone_end_atom",
    "backbone_connection_points", "backbone_path_atoms", "backbone_direction_label",
    "side_chain_attachment_atoms", "side_chain_fragment_smiles",
    "side_chain_descriptions", "polymerization_route", "comonomer_ratio",
    "tacticity_or_regioregularity",
]

COLUMNS = PASSTHROUGH_COLUMNS + DERIVED_COLUMNS

# Derived columns a config may still set explicitly (a hand-written schematic or
# scope note beats a generated one). Everything else in DERIVED_COLUMNS is refused
# in the config, so the CSV cannot disagree with the structure it was built from.
CONFIG_MAY_SET = {
    "sru_bracket_schematic", "repeat_unit_handles_explanation", "repeat_unit_caption",
    "end_group_model", "polymerization_route", "comonomer_ratio",
    "tacticity_or_regioregularity", "backbone_direction_label", "oligomer_n",
    # `scaffold` / `chain` name the template to assemble from; they are echoed into
    # the CSV rather than derived, so the config must be allowed to set them.
    "scaffold", "chain",
}


class ConfigError(Exception):
    """A problem with the config or a structure it produced."""


def expand(text, mapping, kind, depth=0):
    """Expand `{name}` references against `mapping` until none remain."""
    if depth > 10:
        raise ConfigError(f"{kind} reference nested more than 10 deep: {text}")
    names = re.findall(r"\{(\w+)\}", text)
    if not names:
        return text
    for name in names:
        if name not in mapping:
            raise ConfigError(f"unknown {kind} {{{name}}}")
        value = mapping[name]
        value = value["smiles"] if isinstance(value, dict) else str(value)
        text = text.replace("{" + name + "}", expand(value, mapping, kind, depth + 1))
    return text


def fragment_smiles(name, fragments):
    if name not in fragments:
        raise ConfigError(f"unknown fragment {name!r}")
    return expand(fragments[name]["smiles"], fragments, "fragment")


def fragment_label(name, fragments):
    return fragments.get(name, {}).get("label", name)


def assemble(cand, cfg):
    """Return (smiles, unit_names, template) for one candidate."""
    fragments = cfg.get("fragments", {})
    if "scaffold" in cand:
        scaffolds = cfg.get("scaffolds", {})
        if cand["scaffold"] not in scaffolds:
            raise ConfigError(f"unknown scaffold {cand['scaffold']!r}")
        tpl = scaffolds[cand["scaffold"]]
        slots = cand.get("slots") or {}
        text = tpl["template"]
        needed = set(re.findall(r"\{(\w+)\}", text))
        missing = needed - set(slots)
        if missing:
            raise ConfigError(f"scaffold {cand['scaffold']!r} needs slots {sorted(missing)}")
        for slot, frag in slots.items():
            text = text.replace("{" + slot + "}", fragment_smiles(frag, fragments))
        return text, list(dict.fromkeys(slots.values())), tpl
    if "chain" in cand:
        chains = cfg.get("chains", {})
        if cand["chain"] not in chains:
            raise ConfigError(f"unknown chain {cand['chain']!r}")
        tpl = chains[cand["chain"]]
        units = cand.get("units")
        if not units:
            raise ConfigError(f"{cand['candidate_id']}: chain candidates need `units`")
        segments = tpl["segment"]
        segments = segments if isinstance(segments, list) else [segments]
        body = "".join(
            segments[i % len(segments)].replace("{x}", fragment_smiles(u, fragments))
            for i, u in enumerate(units)
        )
        return tpl.get("start", "") + body + tpl.get("end", ""), units, tpl
    raise ConfigError(f"{cand['candidate_id']}: needs either `scaffold` or `chain`")


def expected_motif_counts(units, cfg, tpl):
    """How many of each `count_smarts` motif this assembly should contain.

    Contributions come from three places: the fragments used, the template's own
    fixed parts (`counts`, e.g. an end group's amide), and the per-unit repeat
    (`counts_per_unit`, e.g. one backbone amide per residue).
    """
    count_smarts = cfg.get("count_smarts") or {}
    fragments = cfg.get("fragments", {})
    expected = {k: 0 for k in count_smarts}

    def add(source, table, multiplier=1):
        for key, n in (table or {}).items():
            if key not in expected:
                raise ConfigError(f"{source} counts unknown motif {key!r}")
            expected[key] += n * multiplier

    for unit in units:
        add(f"fragment {unit!r}", fragments.get(unit, {}).get("counts"))
    add("template", tpl.get("counts"))
    add("template", tpl.get("counts_per_unit"), len(units))
    return expected


def validate(cid, smiles, units, cfg, tpl):
    """Parse and check one structure. Returns the molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ConfigError(f"{cid}: SMILES does not parse: {smiles}")
    allowed = cfg.get("allowed_elements")
    if allowed:
        seen = {a.GetSymbol() for a in mol.GetAtoms()}
        extra = seen - set(allowed)
        if extra:
            raise ConfigError(f"{cid}: elements outside {sorted(allowed)}: {sorted(extra)}")
    max_charge = cfg.get("max_abs_formal_charge", 0)
    charge = Chem.GetFormalCharge(mol)
    if abs(charge) > max_charge:
        raise ConfigError(f"{cid}: net formal charge {charge} exceeds {max_charge}")
    count_smarts = cfg.get("count_smarts") or {}
    if count_smarts:
        expected = expected_motif_counts(units, cfg, tpl)
        for key, smarts in count_smarts.items():
            query = Chem.MolFromSmarts(smarts)
            if query is None:
                raise ConfigError(f"count_smarts[{key}] is not valid SMARTS: {smarts}")
            found = len(mol.GetSubstructMatches(query))
            if found != expected[key]:
                raise ConfigError(
                    f"{cid}: {key} count {found}, expected {expected[key]} from units {units}"
                )
    return mol


def check_stereo(cid, mol, tpl):
    """Check CIP labels at the template's stereocentres, when it declares them."""
    wanted = tpl.get("stereo_cip")
    smarts = tpl.get("stereo_smarts")
    if not wanted or not smarts:
        return
    from rdkit.Chem import rdCIPLabeler

    rdCIPLabeler.AssignCIPLabels(mol)
    query = Chem.MolFromSmarts(smarts)
    if query is None:
        raise ConfigError(f"{cid}: stereo_smarts is not valid SMARTS: {smarts}")
    centres = [m[0] for m in mol.GetSubstructMatches(query)]
    if not centres:
        raise ConfigError(f"{cid}: stereo_smarts matched no atom, so stereochemistry is unchecked")
    for i, idx in enumerate(centres):
        label = mol.GetAtomWithIdx(idx).GetPropsAsDict().get("_CIPCode", "?")
        expected = wanted[i % len(wanted)]
        if label != expected:
            raise ConfigError(
                f"{cid}: stereocentre #{i} (atom {idx}) is {label}, expected {expected}"
            )


def path_atoms(mol, tpl):
    """Main-chain atom indices, via the template's `path_smarts` + `path_keep`."""
    smarts = tpl.get("path_smarts")
    if not smarts:
        return []
    query = Chem.MolFromSmarts(smarts)
    if query is None:
        raise ConfigError(f"path_smarts is not valid SMARTS: {smarts}")
    keep = tpl.get("path_keep") or [0]
    atoms = []
    for match in mol.GetSubstructMatches(query):
        atoms += [match[i] for i in keep if i < len(match)]
    return sorted(dict.fromkeys(atoms))


def derive(cand, cfg, mol, units, tpl, display_mol, display_smiles):
    """Derived columns for one candidate."""
    fragments = cfg.get("fragments", {})
    canonical = Chem.MolToSmiles(mol)
    uniq = list(dict.fromkeys(units))
    out = {
        "smiles": canonical,
        "canonical_smiles": canonical,
        "rdkit_input_smiles": canonical,
        "rdkit_display_smiles": display_smiles,
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": f"{rdMolDescriptors.CalcExactMolWt(mol):.2f}",
        "side_chain_fragment_smiles": ";".join(
            f"{fragment_label(u, fragments)}:[*]{fragment_smiles(u, fragments)}" for u in uniq
        ),
        "side_chain_descriptions": "; ".join(
            f"{fragment_label(u, fragments)} = {fragments.get(u, {}).get('desc', u)}" for u in uniq
        ),
    }
    if "scaffold" in cand:
        out["scaffold"] = cand["scaffold"]
        return out

    # Polymer rows: the finite structure is a surrogate, so say so in its own columns.
    out["chain"] = cand["chain"]
    out["oligomer_model_smiles"] = canonical
    out["oligomer_n"] = str(len(units))
    for key in ("end_group_model", "polymerization_route", "backbone_direction_label"):
        if tpl.get(key):
            out[key] = tpl[key]
    if tpl.get("tacticity"):
        out["tacticity_or_regioregularity"] = tpl["tacticity"]
    if tpl.get("display_unit"):
        unit = tpl["display_unit"].replace("{x}", fragment_smiles(units[0], fragments))
        if Chem.MolFromSmiles(unit) is None:
            raise ConfigError(f"{cand['candidate_id']}: repeat-unit SMILES does not parse: {unit}")
        out["repeat_unit_display_smiles"] = unit
    path = path_atoms(display_mol, tpl)
    if path:
        out["backbone_path_atoms"] = " ".join(map(str, path))
        out["backbone_start_atom"] = str(path[0])
        out["backbone_end_atom"] = str(path[-1])
        out["backbone_connection_points"] = (
            f"{path[0]} (chain start, {tpl.get('start_label', 'START')}); "
            f"{path[-1]} (chain end, {tpl.get('end_label', 'END')})"
        )
        every = tpl.get("sidechain_every")
        if every:
            offset, stride = every[0], every[1]
            out["side_chain_attachment_atoms"] = " ".join(map(str, path[offset::stride]))
    return out


def apply_text_blocks(row, blocks):
    """Expand `{{block}}` in every field, then `{column}` against the row itself."""
    for key, value in list(row.items()):
        if not isinstance(value, str) or "{" not in value:
            continue
        text = re.sub(
            r"\{\{(\w+)\}\}",
            lambda m: blocks.get(m.group(1), "{{" + m.group(1) + "}}"),
            value,
        )
        text = re.sub(
            r"\{(\w+)\}",
            lambda m: str(row.get(m.group(1), "{" + m.group(1) + "}")),
            text,
        )
        row[key] = text
    return row


def flatten(value):
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def build_rows(cfg):
    candidates = cfg.get("candidates")
    if not candidates:
        raise ConfigError("config has no `candidates`")
    defaults = cfg.get("defaults") or {}
    blocks = cfg.get("text_blocks") or {}
    seen_ids, rows = set(), []
    for cand in candidates:
        cid = cand.get("candidate_id")
        if not cid:
            raise ConfigError("every candidate needs a candidate_id")
        if cid in seen_ids:
            raise ConfigError(f"duplicate candidate_id {cid!r}")
        seen_ids.add(cid)
        forbidden = (set(cand) | set(defaults)) & set(DERIVED_COLUMNS) - CONFIG_MAY_SET
        if forbidden:
            raise ConfigError(
                f"{cid}: {sorted(forbidden)} are derived from the structure; remove them from the config"
            )
        smiles, units, tpl = assemble(cand, cfg)
        mol = validate(cid, smiles, units, cfg, tpl)
        check_stereo(cid, mol, tpl)
        # Atom indices must refer to the structure the gallery draws, so index the
        # canonical form rather than the assembly order.
        display_smiles = Chem.MolToSmiles(mol)
        display_mol = Chem.MolFromSmiles(display_smiles)

        row = {col: "" for col in COLUMNS}
        row.update({k: flatten(v) for k, v in defaults.items() if k in row})
        row.update({k: flatten(v) for k, v in cand.items() if k in row})
        row.update(derive(cand, cfg, mol, units, tpl, display_mol, display_smiles))
        # A config-supplied value wins over the generated one for the few columns
        # where a human phrasing is better than a template.
        for key in CONFIG_MAY_SET:
            if cand.get(key) or defaults.get(key):
                row[key] = flatten(cand.get(key, defaults.get(key)))
        rows.append(apply_text_blocks(row, blocks))
        print(f"  {cid}: ok  {row['molecular_formula']}  {display_mol.GetNumAtoms()} atoms")
    return rows


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", help="YAML config describing the round")
    parser.add_argument("--out", help="ROUND_N_CANDIDATES.csv to write")
    parser.add_argument(
        "--check-only", action="store_true", help="validate structures, write nothing"
    )
    parser.add_argument(
        "--print-columns", action="store_true", help="print emitted columns and exit"
    )
    args = parser.parse_args()

    if args.print_columns:
        print("passthrough (write these in the config):")
        print("  " + " ".join(PASSTHROUGH_COLUMNS))
        print("derived (do not write these; computed from the structure):")
        print("  " + " ".join(DERIVED_COLUMNS))
        return
    if not args.config:
        parser.error("--config is required")
    if not args.out and not args.check_only:
        parser.error("--out is required unless --check-only")

    with open(args.config, encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    try:
        rows = build_rows(cfg)
    except ConfigError as err:
        sys.exit(f"error: {err}")

    if args.check_only:
        print(f"{len(rows)} candidates validated; nothing written")
        return
    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} candidates -> {args.out}")


if __name__ == "__main__":
    main()
