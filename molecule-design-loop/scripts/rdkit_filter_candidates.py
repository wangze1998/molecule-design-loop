#!/usr/bin/env python3
"""Filter molecule-design candidates with RDKit descriptors."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, FilterCatalog, Lipinski, QED, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold

try:
    from rdkit.Contrib.SA_Score import sascorer
except ImportError:
    sascorer = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", help="CSV with at least candidate_id and smiles columns")
    parser.add_argument("output_csv", help="Filtered/annotated output CSV")
    parser.add_argument("--min-mw", type=float, default=None)
    parser.add_argument("--max-mw", type=float, default=None)
    parser.add_argument("--max-rotatable", type=int, default=None)
    parser.add_argument("--min-qed", type=float, default=None)
    parser.add_argument("--max-logp", type=float, default=None)
    parser.add_argument("--max-tpsa", type=float, default=None)
    parser.add_argument("--max-hba", type=int, default=None)
    parser.add_argument("--max-hbd", type=int, default=None)
    parser.add_argument("--min-fsp3", type=float, default=None)
    parser.add_argument("--max-fsp3", type=float, default=None)
    parser.add_argument("--min-heavy-atoms", type=int, default=None)
    parser.add_argument("--max-heavy-atoms", type=int, default=None)
    parser.add_argument("--max-sa-score", type=float, default=None)
    parser.add_argument("--max-medchem-alerts", type=int, default=None)
    parser.add_argument("--reject-pains", action="store_true")
    parser.add_argument("--reject-brenk", action="store_true")
    parser.add_argument("--reject-scaffold-duplicates", action="store_true")
    parser.add_argument(
        "--allowed-elements",
        default=None,
        help="Comma-separated element symbols, e.g. C,H,N,O,S,F,Cl,Br,I",
    )
    parser.add_argument(
        "--forbidden-smarts",
        action="append",
        default=[],
        help="Forbidden SMARTS pattern. Can be passed multiple times.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def atom_symbols(mol: Chem.Mol) -> set[str]:
    return {atom.GetSymbol() for atom in mol.GetAtoms()}


def build_catalog(*catalogs: FilterCatalog.FilterCatalogParams.FilterCatalogs) -> FilterCatalog.FilterCatalog:
    params = FilterCatalog.FilterCatalogParams()
    for catalog in catalogs:
        params.AddCatalog(catalog)
    return FilterCatalog.FilterCatalog(params)


def catalog_descriptions(mol: Chem.Mol, catalog: FilterCatalog.FilterCatalog) -> list[str]:
    return sorted({entry.GetDescription() for entry in catalog.GetMatches(mol)})


def format_float(value: float | None, digits: int) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)

    allowed = None
    if args.allowed_elements:
        allowed = {item.strip() for item in args.allowed_elements.split(",") if item.strip()}

    if args.max_sa_score is not None and sascorer is None:
        print("SA score requested but rdkit.Contrib.SA_Score is unavailable", file=sys.stderr)
        return 2

    forbidden = []
    for smarts in args.forbidden_smarts:
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is None:
            print(f"Invalid forbidden SMARTS: {smarts}", file=sys.stderr)
            return 2
        forbidden.append((smarts, pattern))

    pains_catalog = build_catalog(
        FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_A,
        FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_B,
        FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_C,
    )
    brenk_catalog = build_catalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)

    rows = read_rows(input_path)
    if not rows:
        print(f"No rows found in {input_path}", file=sys.stderr)
        return 1

    out_rows: list[dict[str, str]] = []
    seen: dict[str, str] = {}
    seen_scaffolds: dict[str, str] = {}
    scaffold_counts: dict[str, int] = {}

    for row in rows:
        item = dict(row)
        smiles = (row.get("smiles") or "").strip()
        mol = Chem.MolFromSmiles(smiles) if smiles else None

        item.update(
            {
                "valid_smiles": "no",
                "canonical_smiles": "",
                "formula": "",
                "exact_mass": "",
                "mol_wt": "",
                "formal_charge": "",
                "rotatable_bonds": "",
                "aromatic_rings": "",
                "ring_count": "",
                "heavy_atoms": "",
                "qed": "",
                "clogp": "",
                "tpsa": "",
                "hba": "",
                "hbd": "",
                "fraction_csp3": "",
                "sa_score": "",
                "murcko_scaffold": "",
                "scaffold_duplicate_of": "",
                "scaffold_seen_count": "",
                "pains_alerts": "",
                "brenk_alerts": "",
                "medchem_alert_count": "",
                "forbidden_motif_hit": "",
                "hard_constraint_status": "fail",
                "filter_decision": "reject",
                "filter_reason": "invalid_smiles",
            }
        )

        if mol is None:
            out_rows.append(item)
            continue

        canonical = Chem.MolToSmiles(mol, canonical=True)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        exact_mass = Descriptors.ExactMolWt(mol)
        mol_wt = Descriptors.MolWt(mol)
        charge = Chem.GetFormalCharge(mol)
        rot_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol)
        aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
        ring_count = rdMolDescriptors.CalcNumRings(mol)
        heavy_atoms = mol.GetNumHeavyAtoms()
        qed = QED.qed(mol)
        clogp = Crippen.MolLogP(mol)
        tpsa = rdMolDescriptors.CalcTPSA(mol)
        hba = Lipinski.NumHAcceptors(mol)
        hbd = Lipinski.NumHDonors(mol)
        fraction_csp3 = rdMolDescriptors.CalcFractionCSP3(mol)
        sa_score = sascorer.calculateScore(mol) if sascorer is not None else None
        murcko_scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
        pains_hits = catalog_descriptions(mol, pains_catalog)
        brenk_hits = catalog_descriptions(mol, brenk_catalog)
        medchem_alert_count = len(pains_hits) + len(brenk_hits)

        reasons: list[str] = []
        candidate_id = row.get("candidate_id") or canonical
        if canonical in seen:
            reasons.append(f"duplicate_of:{seen[canonical]}")
        else:
            seen[canonical] = candidate_id

        scaffold_duplicate_of = ""
        scaffold_seen_count = ""
        if murcko_scaffold:
            scaffold_seen_count = str(scaffold_counts.get(murcko_scaffold, 0) + 1)
            if murcko_scaffold in seen_scaffolds:
                scaffold_duplicate_of = seen_scaffolds[murcko_scaffold]
                if args.reject_scaffold_duplicates:
                    reasons.append(f"scaffold_duplicate_of:{scaffold_duplicate_of}")
            else:
                seen_scaffolds[murcko_scaffold] = candidate_id
            scaffold_counts[murcko_scaffold] = scaffold_counts.get(murcko_scaffold, 0) + 1

        if allowed is not None:
            extras = sorted(atom_symbols(mol) - allowed)
            if extras:
                reasons.append("disallowed_elements:" + ",".join(extras))

        if args.min_mw is not None and mol_wt < args.min_mw:
            reasons.append(f"mw_below_min:{mol_wt:.2f}")
        if args.max_mw is not None and mol_wt > args.max_mw:
            reasons.append(f"mw_above_max:{mol_wt:.2f}")
        if args.max_rotatable is not None and rot_bonds > args.max_rotatable:
            reasons.append(f"too_flexible:{rot_bonds}")
        if args.min_qed is not None and qed < args.min_qed:
            reasons.append(f"qed_below_min:{qed:.3f}")
        if args.max_logp is not None and clogp > args.max_logp:
            reasons.append(f"logp_above_max:{clogp:.3f}")
        if args.max_tpsa is not None and tpsa > args.max_tpsa:
            reasons.append(f"tpsa_above_max:{tpsa:.3f}")
        if args.max_hba is not None and hba > args.max_hba:
            reasons.append(f"hba_above_max:{hba}")
        if args.max_hbd is not None and hbd > args.max_hbd:
            reasons.append(f"hbd_above_max:{hbd}")
        if args.min_fsp3 is not None and fraction_csp3 < args.min_fsp3:
            reasons.append(f"fsp3_below_min:{fraction_csp3:.3f}")
        if args.max_fsp3 is not None and fraction_csp3 > args.max_fsp3:
            reasons.append(f"fsp3_above_max:{fraction_csp3:.3f}")
        if args.min_heavy_atoms is not None and heavy_atoms < args.min_heavy_atoms:
            reasons.append(f"heavy_atoms_below_min:{heavy_atoms}")
        if args.max_heavy_atoms is not None and heavy_atoms > args.max_heavy_atoms:
            reasons.append(f"heavy_atoms_above_max:{heavy_atoms}")
        if args.max_sa_score is not None and sa_score is not None and sa_score > args.max_sa_score:
            reasons.append(f"sa_score_above_max:{sa_score:.3f}")
        if args.reject_pains and pains_hits:
            reasons.append("pains_alert")
        if args.reject_brenk and brenk_hits:
            reasons.append("brenk_alert")
        if args.max_medchem_alerts is not None and medchem_alert_count > args.max_medchem_alerts:
            reasons.append(f"medchem_alerts_above_max:{medchem_alert_count}")

        hits = []
        for smarts, pattern in forbidden:
            if mol.HasSubstructMatch(pattern):
                hits.append(smarts)
        if hits:
            reasons.append("forbidden_motif")

        decision = "pass" if not reasons else "reject"
        status = "pass" if not reasons else "fail"

        item.update(
            {
                "valid_smiles": "yes",
                "canonical_smiles": canonical,
                "formula": formula,
                "exact_mass": f"{exact_mass:.6f}",
                "mol_wt": f"{mol_wt:.3f}",
                "formal_charge": str(charge),
                "rotatable_bonds": str(rot_bonds),
                "aromatic_rings": str(aromatic_rings),
                "ring_count": str(ring_count),
                "heavy_atoms": str(heavy_atoms),
                "qed": format_float(qed, 3),
                "clogp": format_float(clogp, 3),
                "tpsa": format_float(tpsa, 3),
                "hba": str(hba),
                "hbd": str(hbd),
                "fraction_csp3": format_float(fraction_csp3, 3),
                "sa_score": format_float(sa_score, 3),
                "murcko_scaffold": murcko_scaffold,
                "scaffold_duplicate_of": scaffold_duplicate_of,
                "scaffold_seen_count": scaffold_seen_count,
                "pains_alerts": ";".join(pains_hits),
                "brenk_alerts": ";".join(brenk_hits),
                "medchem_alert_count": str(medchem_alert_count),
                "forbidden_motif_hit": ";".join(hits),
                "hard_constraint_status": status,
                "filter_decision": decision,
                "filter_reason": ";".join(reasons) if reasons else "ok",
            }
        )
        out_rows.append(item)

    fieldnames = list(out_rows[0].keys())
    for row in out_rows[1:]:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
