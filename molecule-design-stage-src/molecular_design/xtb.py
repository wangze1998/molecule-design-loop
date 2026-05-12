from __future__ import annotations

import csv
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem


XTB_COLUMNS = [
    "candidate_id",
    "canonical_smiles",
    "xtb_status",
    "xtb_command",
    "charge",
    "multiplicity",
    "energy_hartree",
    "homo_ev",
    "lumo_ev",
    "gap_ev",
    "dipole_debye",
    "dimer_centroid_A",
    "dimer_min_aromatic_A",
    "dimer_contacts_lt_4p0A",
    "dimer_min_heavy_A",
    "geometry_warning",
    "raw_output_dir",
    "notes",
]


def resolve_xtb_binary(config: dict[str, Any]) -> str | None:
    binary = (config.get("xtb") or {}).get("binary") or "xtb"
    path = Path(binary).expanduser()
    if path.exists():
        return str(path)
    return shutil.which(str(binary))


def screen_headgroup_dimers(
    candidates: list[dict[str, str]],
    selected_ids: list[str],
    jobs_dir: Path,
    config: dict[str, Any],
) -> list[dict[str, str]]:
    xtb_binary = resolve_xtb_binary(config)
    selected = set(selected_ids)
    rows: list[dict[str, str]] = []
    for candidate in candidates:
        base = _base_row(candidate)
        if candidate["candidate_id"] not in selected:
            base["geometry_warning"] = "not_selected_for_xtb"
            rows.append(base)
            continue
        if not candidate.get("headgroup_smiles"):
            base["geometry_warning"] = "missing_headgroup_smiles"
            rows.append(base)
            continue
        if xtb_binary is None:
            base["geometry_warning"] = "xtb_binary_not_found"
            rows.append(base)
            continue
        rows.append(_run_dimer_candidate(candidate, jobs_dir, xtb_binary, config))
    return rows


def write_xtb_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=XTB_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_xtb_stdout(text: str) -> dict[str, str]:
    info = {
        "energy_hartree": "",
        "homo_ev": "",
        "lumo_ev": "",
        "gap_ev": "",
        "dipole_debye": "",
        "converged": "no",
    }
    if "normal termination of xtb" in text:
        info["converged"] = "yes"

    energy_matches = re.findall(r"TOTAL ENERGY\s+(-?\d+\.\d+)", text)
    if energy_matches:
        info["energy_hartree"] = energy_matches[-1]
    gap_matches = re.findall(r"HOMO-LUMO GAP\s+([0-9.]+)\s+eV", text)
    if gap_matches:
        info["gap_ev"] = gap_matches[-1]
    orbital_matches = re.findall(r"\(\s*HOMO\)\s+(-?\d+\.\d+)\s+eV.*?\(\s*LUMO\)\s+(-?\d+\.\d+)\s+eV", text, flags=re.S)
    if orbital_matches:
        info["homo_ev"], info["lumo_ev"] = orbital_matches[-1]
    dipole_matches = re.findall(r"molecular dipole:.*?full:\s+([0-9.]+)", text, flags=re.S)
    if dipole_matches:
        info["dipole_debye"] = dipole_matches[-1]
    return info


def write_xyz(path: Path, symbols: list[str], coords: np.ndarray, comment: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"{len(symbols)}\n{comment}\n")
        for sym, xyz in zip(symbols, coords):
            handle.write(f"{sym:2s} {xyz[0]: .8f} {xyz[1]: .8f} {xyz[2]: .8f}\n")


def read_xyz(path: Path) -> tuple[list[str], np.ndarray]:
    lines = path.read_text(encoding="utf-8").splitlines()
    natoms = int(lines[0].strip())
    symbols: list[str] = []
    coords: list[list[float]] = []
    for line in lines[2 : 2 + natoms]:
        parts = line.split()
        symbols.append(parts[0])
        coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return symbols, np.array(coords, dtype=float)


def embed_headgroup_xyz(smiles: str, out_xyz: Path, random_seed: int = 20260509) -> list[int]:
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    params = AllChem.ETKDGv3()
    params.randomSeed = random_seed
    status = AllChem.EmbedMolecule(mol, params)
    if status != 0:
        raise RuntimeError(f"RDKit embedding failed for {smiles}")
    AllChem.UFFOptimizeMolecule(mol, maxIters=800)
    conf = mol.GetConformer()
    symbols = [atom.GetSymbol() for atom in mol.GetAtoms()]
    coords = np.array(
        [[conf.GetAtomPosition(i).x, conf.GetAtomPosition(i).y, conf.GetAtomPosition(i).z] for i in range(mol.GetNumAtoms())],
        dtype=float,
    )
    write_xyz(out_xyz, symbols, coords, "RDKit ETKDG/UFF seed")
    return [atom.GetIdx() for atom in mol.GetAtoms() if atom.GetIsAromatic()]


def build_dimer(symbols: list[str], coords: np.ndarray, aromatic_idx: list[int]) -> tuple[list[str], np.ndarray]:
    centroid, long_axis, short_axis, normal = _aromatic_axes(coords, aromatic_idx)
    shifted = coords - centroid
    monomer_a = shifted.copy()
    monomer_b = shifted @ _rotation_matrix(long_axis, 180.0).T

    interplanar = 3.5
    slip_long = 1.5
    slip_short = 0.0
    for _ in range(12):
        trial_b = monomer_b + normal * interplanar + long_axis * slip_long + short_axis * slip_short
        if _min_heavy_distance(monomer_a, trial_b, symbols, symbols) >= 2.2:
            monomer_b = trial_b
            break
        slip_short += 0.5
        if slip_short > 2.0:
            interplanar += 0.2
    return symbols + symbols, np.vstack([monomer_a, monomer_b])


def analyze_dimer(symbols: list[str], coords: np.ndarray, monomer_natoms: int, aromatic_idx: list[int]) -> dict[str, float]:
    aro_a = np.array(aromatic_idx, dtype=int)
    aro_b = aro_a + monomer_natoms
    coords_a = coords[:monomer_natoms]
    coords_b = coords[monomer_natoms:]
    centroid_dist = float(np.linalg.norm(coords[aro_a].mean(axis=0) - coords[aro_b].mean(axis=0)))
    dists = np.sqrt(((coords[aro_a][:, None, :] - coords[aro_b][None, :, :]) ** 2).sum(axis=2))
    return {
        "final_centroid_distance_A": centroid_dist,
        "final_min_aromatic_distance_A": float(dists.min()),
        "final_contacts_lt_4p0A": int((dists < 4.0).sum()),
        "final_min_heavy_distance_A": _min_heavy_distance(coords_a, coords_b, symbols[:monomer_natoms], symbols[monomer_natoms:]),
    }


def dimer_status(metrics: dict[str, float], rc_monomer: int, rc_dimer: int) -> tuple[str, str]:
    if rc_monomer != 0 or rc_dimer != 0:
        return "fail", "xTB did not terminate cleanly."
    warnings: list[str] = []
    if metrics["final_min_heavy_distance_A"] < 2.4:
        warnings.append("heavy-atom clash risk")
    if metrics["final_min_aromatic_distance_A"] > 3.6:
        warnings.append("stack too loose")
    if metrics["final_min_aromatic_distance_A"] < 2.9:
        warnings.append("stack too compressed")
    if metrics["final_centroid_distance_A"] > 5.6:
        warnings.append("centroid distance too large")
    if metrics["final_contacts_lt_4p0A"] < 28:
        warnings.append("too few close aromatic contacts")
    return ("warn", "; ".join(warnings)) if warnings else ("pass", "slipped dimer retained without obvious clashes")


def _run_dimer_candidate(candidate: dict[str, str], jobs_dir: Path, xtb_binary: str, config: dict[str, Any]) -> dict[str, str]:
    workdir = jobs_dir / candidate["candidate_id"]
    workdir.mkdir(parents=True, exist_ok=True)
    monomer_seed = workdir / "monomer_seed.xyz"
    aromatic_idx = embed_headgroup_xyz(candidate["headgroup_smiles"], monomer_seed)
    rc_monomer, monomer_stdout = _run_xtb(workdir, xtb_binary, "monomer_seed.xyz", "monomer", charge=2)
    monomer_info = parse_xtb_stdout(monomer_stdout)
    monomer_xyz = workdir / "monomer.xtbopt.xyz"
    if not monomer_xyz.exists():
        return _failed_row(candidate, workdir, "monomer_optimization_failed", monomer_info)

    symbols, coords = read_xyz(monomer_xyz)
    dimer_symbols, dimer_coords = build_dimer(symbols, coords, aromatic_idx)
    dimer_seed = workdir / "dimer_seed.xyz"
    write_xyz(dimer_seed, dimer_symbols, dimer_coords, f"{candidate['candidate_id']} slipped dimer seed")
    xcontrol = workdir / "dimer.xcontrol"
    _write_xcontrol(xcontrol, len(symbols))
    rc_dimer, dimer_stdout = _run_xtb(workdir, xtb_binary, "dimer_seed.xyz", "dimer", charge=4, xcontrol="dimer.xcontrol")
    dimer_info = parse_xtb_stdout(dimer_stdout)
    dimer_xyz = workdir / "dimer.xtbopt.xyz"
    if dimer_xyz.exists():
        final_symbols, final_coords = read_xyz(dimer_xyz)
        metrics = analyze_dimer(final_symbols, final_coords, len(symbols), aromatic_idx)
        status, warning = dimer_status(metrics, rc_monomer, rc_dimer)
    else:
        metrics = {}
        status, warning = "fail", "dimer_optimization_failed"

    row = _base_row(candidate)
    row.update(
        {
            "xtb_status": status,
            "xtb_command": f"{xtb_binary} monomer_seed.xyz ... ; {xtb_binary} dimer_seed.xyz ...",
            "charge": "2/4",
            "multiplicity": str((config.get("xtb") or {}).get("multiplicity", 1)),
            "energy_hartree": dimer_info.get("energy_hartree") or monomer_info.get("energy_hartree", ""),
            "homo_ev": dimer_info.get("homo_ev", ""),
            "lumo_ev": dimer_info.get("lumo_ev", ""),
            "gap_ev": dimer_info.get("gap_ev", ""),
            "dipole_debye": dimer_info.get("dipole_debye", ""),
            "dimer_centroid_A": _metric(metrics, "final_centroid_distance_A"),
            "dimer_min_aromatic_A": _metric(metrics, "final_min_aromatic_distance_A"),
            "dimer_contacts_lt_4p0A": _metric(metrics, "final_contacts_lt_4p0A", digits=0),
            "dimer_min_heavy_A": _metric(metrics, "final_min_heavy_distance_A"),
            "geometry_warning": warning,
            "raw_output_dir": str(workdir),
        }
    )
    return row


def _run_xtb(workdir: Path, xtb_binary: str, input_xyz: str, namespace: str, charge: int, xcontrol: str | None = None) -> tuple[int, str]:
    parts = [xtb_binary, input_xyz, "--opt", "loose", "--alpb", "water", "--chrg", str(charge), "--uhf", "0", "--namespace", namespace]
    if xcontrol:
        parts.extend(["--input", xcontrol])
    out_path = workdir / f"{namespace}.out"
    with out_path.open("w", encoding="utf-8") as handle:
        result = subprocess.run(parts, cwd=workdir, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return result.returncode, out_path.read_text(encoding="utf-8", errors="ignore")


def _base_row(candidate: dict[str, str]) -> dict[str, str]:
    mol = Chem.MolFromSmiles(candidate.get("smiles", ""))
    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True) if mol else "",
        "xtb_status": "not_run",
        "xtb_command": "",
        "charge": "",
        "multiplicity": "",
        "energy_hartree": "",
        "homo_ev": "",
        "lumo_ev": "",
        "gap_ev": "",
        "dipole_debye": "",
        "dimer_centroid_A": "",
        "dimer_min_aromatic_A": "",
        "dimer_contacts_lt_4p0A": "",
        "dimer_min_heavy_A": "",
        "geometry_warning": "",
        "raw_output_dir": "",
        "notes": "",
    }


def _failed_row(candidate: dict[str, str], workdir: Path, warning: str, info: dict[str, str]) -> dict[str, str]:
    row = _base_row(candidate)
    row.update({"xtb_status": "fail", "energy_hartree": info.get("energy_hartree", ""), "geometry_warning": warning, "raw_output_dir": str(workdir)})
    return row


def _write_xcontrol(path: Path, monomer_natoms: int) -> None:
    frozen = f"1-4,{monomer_natoms + 1}-{monomer_natoms + 4}"
    path.write_text("$constrain\n  force constant=1.0\n  atoms: " + frozen + "\n$end\n$opt\n  maxcycle=60\n$end\n", encoding="utf-8")


def _rotation_matrix(axis: np.ndarray, angle_deg: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    angle = math.radians(angle_deg)
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)
    c1 = 1.0 - c
    return np.array(
        [
            [c + x * x * c1, x * y * c1 - z * s, x * z * c1 + y * s],
            [y * x * c1 + z * s, c + y * y * c1, y * z * c1 - x * s],
            [z * x * c1 - y * s, z * y * c1 + x * s, c + z * z * c1],
        ]
    )


def _aromatic_axes(coords: np.ndarray, aromatic_idx: list[int]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    aro = coords[aromatic_idx]
    centroid = aro.mean(axis=0)
    _, _, vh = np.linalg.svd(aro - centroid, full_matrices=False)
    return centroid, vh[0] / np.linalg.norm(vh[0]), vh[1] / np.linalg.norm(vh[1]), vh[2] / np.linalg.norm(vh[2])


def _min_heavy_distance(coords_a: np.ndarray, coords_b: np.ndarray, symbols_a: list[str], symbols_b: list[str]) -> float:
    idx_a = [i for i, sym in enumerate(symbols_a) if sym != "H"]
    idx_b = [i for i, sym in enumerate(symbols_b) if sym != "H"]
    diff = coords_a[idx_a][:, None, :] - coords_b[idx_b][None, :, :]
    return float(np.sqrt((diff * diff).sum(axis=2)).min())


def _metric(metrics: dict[str, float], key: str, digits: int = 3) -> str:
    if key not in metrics:
        return ""
    value = metrics[key]
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)
