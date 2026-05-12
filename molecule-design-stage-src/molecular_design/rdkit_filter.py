from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, FilterCatalog, Lipinski, QED, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold

try:
    from rdkit.Contrib.SA_Score import sascorer
except ImportError:  # pragma: no cover - depends on RDKit packaging
    sascorer = None


DESCRIPTOR_COLUMNS = [
    "valid_smiles",
    "canonical_smiles",
    "formula",
    "exact_mass",
    "mol_wt",
    "formal_charge",
    "rotatable_bonds",
    "aromatic_rings",
    "ring_count",
    "heavy_atoms",
    "qed",
    "clogp",
    "tpsa",
    "hba",
    "hbd",
    "fraction_csp3",
    "sa_score",
    "murcko_scaffold",
    "scaffold_duplicate_of",
    "scaffold_seen_count",
    "pains_alerts",
    "brenk_alerts",
    "medchem_alert_count",
    "forbidden_motif_hit",
    "hard_constraint_status",
    "filter_decision",
    "filter_reason",
]


def filter_csv(input_csv: Path, output_csv: Path, options: dict[str, Any] | None = None) -> list[dict[str, str]]:
    rows = read_rows(input_csv)
    out_rows = filter_rows(rows, options or {})
    fieldnames = list(rows[0].keys()) if rows else []
    for column in DESCRIPTOR_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    return out_rows


def filter_rows(rows: list[dict[str, str]], options: dict[str, Any]) -> list[dict[str, str]]:
    if not rows:
        raise ValueError("No candidate rows to filter")

    allowed = _allowed_elements(options)
    forbidden = _forbidden_smarts(options)
    pains_catalog = _catalog(
        FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_A,
        FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_B,
        FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_C,
    )
    brenk_catalog = _catalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)

    seen: dict[str, str] = {}
    seen_scaffolds: dict[str, str] = {}
    scaffold_counts: dict[str, int] = {}
    out_rows: list[dict[str, str]] = []

    for row in rows:
        item = dict(row)
        _set_default_rejection(item)
        smiles = (row.get("smiles") or "").strip()
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        if mol is None:
            out_rows.append(item)
            continue

        canonical = Chem.MolToSmiles(mol, canonical=True)
        mol_wt = Descriptors.MolWt(mol)
        exact_mass = Descriptors.ExactMolWt(mol)
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
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
        pains_hits = _catalog_descriptions(mol, pains_catalog)
        brenk_hits = _catalog_descriptions(mol, brenk_catalog)
        forbidden_hits = [smarts for smarts, pattern in forbidden if mol.HasSubstructMatch(pattern)]

        scaffold_counts[scaffold] = scaffold_counts.get(scaffold, 0) + 1
        duplicate_of = seen.get(canonical, "")
        scaffold_duplicate_of = seen_scaffolds.get(scaffold, "") if scaffold else ""
        seen.setdefault(canonical, row.get("candidate_id", canonical))
        if scaffold:
            seen_scaffolds.setdefault(scaffold, row.get("candidate_id", scaffold))

        reasons = _constraint_reasons(
            mol=mol,
            options=options,
            allowed=allowed,
            duplicate_of=duplicate_of,
            scaffold_duplicate_of=scaffold_duplicate_of,
            mol_wt=mol_wt,
            rot_bonds=rot_bonds,
            heavy_atoms=heavy_atoms,
            qed=qed,
            clogp=clogp,
            tpsa=tpsa,
            hba=hba,
            hbd=hbd,
            fraction_csp3=fraction_csp3,
            sa_score=sa_score,
            pains_hits=pains_hits,
            brenk_hits=brenk_hits,
            forbidden_hits=forbidden_hits,
        )

        item.update(
            {
                "valid_smiles": "yes",
                "canonical_smiles": canonical,
                "formula": rdMolDescriptors.CalcMolFormula(mol),
                "exact_mass": _fmt(exact_mass, 4),
                "mol_wt": _fmt(mol_wt, 2),
                "formal_charge": str(charge),
                "rotatable_bonds": str(rot_bonds),
                "aromatic_rings": str(aromatic_rings),
                "ring_count": str(ring_count),
                "heavy_atoms": str(heavy_atoms),
                "qed": _fmt(qed, 3),
                "clogp": _fmt(clogp, 3),
                "tpsa": _fmt(tpsa, 2),
                "hba": str(hba),
                "hbd": str(hbd),
                "fraction_csp3": _fmt(fraction_csp3, 3),
                "sa_score": _fmt(sa_score, 2),
                "murcko_scaffold": scaffold,
                "scaffold_duplicate_of": scaffold_duplicate_of,
                "scaffold_seen_count": str(scaffold_counts[scaffold]) if scaffold else "",
                "pains_alerts": ";".join(pains_hits),
                "brenk_alerts": ";".join(brenk_hits),
                "medchem_alert_count": str(len(pains_hits) + len(brenk_hits)),
                "forbidden_motif_hit": ";".join(forbidden_hits),
                "hard_constraint_status": "fail" if reasons else "pass",
                "filter_decision": "reject" if reasons else "pass",
                "filter_reason": "; ".join(reasons) if reasons else "passes_configured_filters",
            }
        )
        out_rows.append(item)

    return out_rows


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _set_default_rejection(item: dict[str, str]) -> None:
    item.update({column: "" for column in DESCRIPTOR_COLUMNS})
    item.update(
        {
            "valid_smiles": "no",
            "hard_constraint_status": "fail",
            "filter_decision": "reject",
            "filter_reason": "invalid_smiles",
        }
    )


def _constraint_reasons(**kwargs: Any) -> list[str]:
    options = kwargs["options"]
    reasons: list[str] = []
    mol = kwargs["mol"]

    allowed = kwargs["allowed"]
    if allowed is not None:
        symbols = {atom.GetSymbol() for atom in mol.GetAtoms()}
        disallowed = sorted(symbols - allowed)
        if disallowed:
            reasons.append("disallowed_elements:" + ",".join(disallowed))

    checks = [
        ("min_mw", kwargs["mol_wt"], lambda actual, limit: actual < limit),
        ("max_mw", kwargs["mol_wt"], lambda actual, limit: actual > limit),
        ("max_rotatable", kwargs["rot_bonds"], lambda actual, limit: actual > limit),
        ("min_qed", kwargs["qed"], lambda actual, limit: actual < limit),
        ("max_logp", kwargs["clogp"], lambda actual, limit: actual > limit),
        ("max_tpsa", kwargs["tpsa"], lambda actual, limit: actual > limit),
        ("max_hba", kwargs["hba"], lambda actual, limit: actual > limit),
        ("max_hbd", kwargs["hbd"], lambda actual, limit: actual > limit),
        ("min_fsp3", kwargs["fraction_csp3"], lambda actual, limit: actual < limit),
        ("max_fsp3", kwargs["fraction_csp3"], lambda actual, limit: actual > limit),
        ("min_heavy_atoms", kwargs["heavy_atoms"], lambda actual, limit: actual < limit),
        ("max_heavy_atoms", kwargs["heavy_atoms"], lambda actual, limit: actual > limit),
    ]
    if kwargs["sa_score"] is not None:
        checks.append(("max_sa_score", kwargs["sa_score"], lambda actual, limit: actual > limit))

    for key, actual, fails in checks:
        if options.get(key) is not None and fails(actual, options[key]):
            reasons.append(f"{key}:{actual}")

    if kwargs["duplicate_of"]:
        reasons.append("duplicate_smiles:" + kwargs["duplicate_of"])
    if options.get("reject_scaffold_duplicates") and kwargs["scaffold_duplicate_of"]:
        reasons.append("duplicate_scaffold:" + kwargs["scaffold_duplicate_of"])
    if options.get("reject_pains") and kwargs["pains_hits"]:
        reasons.append("pains_alert")
    if options.get("reject_brenk") and kwargs["brenk_hits"]:
        reasons.append("brenk_alert")
    if options.get("max_medchem_alerts") is not None:
        alerts = len(kwargs["pains_hits"]) + len(kwargs["brenk_hits"])
        if alerts > options["max_medchem_alerts"]:
            reasons.append(f"max_medchem_alerts:{alerts}")
    if kwargs["forbidden_hits"]:
        reasons.append("forbidden_motif:" + ",".join(kwargs["forbidden_hits"]))

    return reasons


def _allowed_elements(options: dict[str, Any]) -> set[str] | None:
    allowed = options.get("allowed_elements")
    if isinstance(allowed, str):
        return {item.strip() for item in allowed.split(",") if item.strip()}
    if allowed:
        return {str(item) for item in allowed}
    return None


def _forbidden_smarts(options: dict[str, Any]) -> list[tuple[str, Chem.Mol]]:
    forbidden = []
    for smarts in options.get("forbidden_smarts") or []:
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is None:
            raise ValueError(f"Invalid forbidden SMARTS: {smarts}")
        forbidden.append((smarts, pattern))
    return forbidden


def _catalog(*catalogs: FilterCatalog.FilterCatalogParams.FilterCatalogs) -> FilterCatalog.FilterCatalog:
    params = FilterCatalog.FilterCatalogParams()
    for catalog in catalogs:
        params.AddCatalog(catalog)
    return FilterCatalog.FilterCatalog(params)


def _catalog_descriptions(mol: Chem.Mol, catalog: FilterCatalog.FilterCatalog) -> list[str]:
    return sorted({entry.GetDescription() for entry in catalog.GetMatches(mol)})


def _fmt(value: float | None, digits: int) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter molecular-design candidates with RDKit")
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    parser.add_argument("--allowed-elements")
    parser.add_argument("--max-rotatable", type=int)
    parser.add_argument("--min-mw", type=float)
    parser.add_argument("--max-mw", type=float)
    parser.add_argument("--reject-pains", action="store_true")
    parser.add_argument("--reject-brenk", action="store_true")
    parser.add_argument("--forbidden-smarts", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    options = {key: value for key, value in vars(args).items() if key not in {"input_csv", "output_csv"}}
    try:
        filter_csv(Path(args.input_csv), Path(args.output_csv), options)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
