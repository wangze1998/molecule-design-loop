from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STAGE_ROOT))

from molecular_design.candidates import generate_candidates
from molecular_design.config import load_config
from molecular_design.gallery import render_gallery_csv
from molecular_design.rdkit_filter import filter_csv
from molecular_design.workflow import artifact_paths, write_gemini_input
from molecular_design.xtb import parse_xtb_stdout


class MolecularDesignWorkflowTests(unittest.TestCase):
    def test_config_loads_example_schema(self) -> None:
        config = load_config(STAGE_ROOT / "inputs" / "example_run.yaml")
        self.assertEqual(config["run_id"], "example_matrix_run")
        for key in ("scaffold", "axes", "candidate_plan", "filter", "gallery", "approval", "xtb", "backfolding"):
            self.assertIn(key, config)
        self.assertTrue(config["gemini"]["enabled"])

    def test_matrix_candidate_generation(self) -> None:
        config = load_config(STAGE_ROOT / "inputs" / "example_run.yaml")
        rows = generate_candidates(config)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["candidate_id"], "EXAMPLE_01")
        self.assertTrue(all(row.get("headgroup_smiles") for row in rows))

    def test_filter_and_gallery_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_csv = tmp_path / "candidates.csv"
            filtered_csv = tmp_path / "filtered.csv"
            gallery_html = tmp_path / "gallery.html"
            with input_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["candidate_id", "smiles", "design_move"])
                writer.writeheader()
                writer.writerow({"candidate_id": "anisole", "smiles": "COc1ccccc1", "design_move": "smoke"})

            rows = filter_csv(input_csv, filtered_csv, {"allowed_elements": ["C", "H", "O"]})
            self.assertEqual(rows[0]["filter_decision"], "pass")
            render_gallery_csv(filtered_csv, gallery_html, "Smoke Gallery")
            self.assertIn("anisole", gallery_html.read_text(encoding="utf-8"))

    def test_xtb_stdout_parser(self) -> None:
        text = """
        TOTAL ENERGY              -123.456789
        (HOMO)       -7.12 eV
        something
        (LUMO)       -1.23 eV
        HOMO-LUMO GAP        5.89 eV
        molecular dipole:
          full:  2.34
        normal termination of xtb
        """
        parsed = parse_xtb_stdout(text)
        self.assertEqual(parsed["energy_hartree"], "-123.456789")
        self.assertEqual(parsed["gap_ev"], "5.89")
        self.assertEqual(parsed["dipole_debye"], "2.34")
        self.assertEqual(parsed["converged"], "yes")

    def test_gemini_input_writer(self) -> None:
        config = load_config(STAGE_ROOT / "inputs" / "example_run.yaml")
        with tempfile.TemporaryDirectory() as tmp:
            config["_output_dir"] = tmp
            paths = artifact_paths(config)
            paths["output_dir"].mkdir(parents=True, exist_ok=True)
            out = write_gemini_input(
                config,
                [
                    {
                        "candidate_id": "EXAMPLE_01",
                        "parent_or_seed": "example_seed",
                        "design_move": "baseline",
                        "target_constraint": "smoke_test",
                        "rationale": "control",
                        "expected_proxy_effect": "simple aromatic control",
                        "risk": "too simple",
                        "proposal_family": "controls",
                        "constraint_coverage": "smoke_test",
                        "novelty_class": "conservative",
                        "smiles": "COc1ccccc1",
                        "headgroup_smiles": "COc1ccccc1",
                        "hard_constraint_status": "pass",
                        "filter_decision": "pass",
                        "filter_reason": "passes_configured_filters",
                        "formal_charge": "0",
                        "rotatable_bonds": "1",
                        "aromatic_rings": "1",
                        "clogp": "1.23",
                        "tpsa": "9.23",
                    }
                ],
                [
                    {
                        "candidate_id": "EXAMPLE_01",
                        "xtb_status": "pass",
                        "geometry_warning": "",
                        "dimer_centroid_A": "4.321",
                        "dimer_min_aromatic_A": "3.412",
                        "dimer_contacts_lt_4p0A": "32",
                        "dimer_min_heavy_A": "2.876",
                    }
                ],
            )
            text = out.read_text(encoding="utf-8")
            self.assertIn("EXAMPLE_01", text)
            self.assertIn("Treat xTB as a low-cost geometry and stacking proxy only.", text)
            self.assertIn("xTB status: pass", text)


if __name__ == "__main__":
    unittest.main()
