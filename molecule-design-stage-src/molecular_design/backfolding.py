from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def summarize_conformer_rows(rows: list[dict[str, str]], low_energy_window_kcal: float) -> dict[str, str]:
    if not rows:
        return {
            "candidate_id": "",
            "n_confs": "0",
            "n_converged": "0",
            "best_conf_id": "",
            "best_energy_hartree": "",
            "low_energy_window_kcal_mol": f"{low_energy_window_kcal:.2f}",
            "n_low_energy_confs": "0",
            "summary_label": "no_conformers",
        }

    candidate_id = rows[0].get("candidate_id", "")
    converged = [row for row in rows if row.get("xtb_status") in {"pass", "warn"} and row.get("energy_hartree")]
    if not converged:
        return {
            "candidate_id": candidate_id,
            "n_confs": str(len(rows)),
            "n_converged": "0",
            "best_conf_id": "",
            "best_energy_hartree": "",
            "low_energy_window_kcal_mol": f"{low_energy_window_kcal:.2f}",
            "n_low_energy_confs": "0",
            "summary_label": "no_converged_xtb",
        }

    best = min(converged, key=lambda row: float(row["energy_hartree"]))
    best_energy = float(best["energy_hartree"])
    low_energy = [
        row
        for row in converged
        if (float(row["energy_hartree"]) - best_energy) * 627.509 <= low_energy_window_kcal
    ]
    labels = [row.get("heuristic_label", "") for row in low_energy]
    summary_label = "mixed"
    if labels and all(label == labels[0] for label in labels):
        summary_label = labels[0] or "unlabeled"

    return {
        "candidate_id": candidate_id,
        "n_confs": str(len(rows)),
        "n_converged": str(len(converged)),
        "best_conf_id": best.get("conf_id", ""),
        "best_energy_hartree": best.get("energy_hartree", ""),
        "low_energy_window_kcal_mol": f"{low_energy_window_kcal:.2f}",
        "n_low_energy_confs": str(len(low_energy)),
        "summary_label": summary_label,
    }


def write_not_configured_summary(path: Path, config: dict[str, Any]) -> None:
    path.write_text(
        f"# Round {config['round']} Backfolding Summary\n\n"
        "Backfolding is not configured for this run. Add `backfolding.legacy_module` or a generic backfolding config before running this step.\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
