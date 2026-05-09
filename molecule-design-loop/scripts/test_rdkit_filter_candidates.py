#!/usr/bin/env python3
"""Lightweight tests for rdkit_filter_candidates.py."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("rdkit_filter_candidates.py")


class RdkitFilterCandidatesTest(unittest.TestCase):
    def run_filter(
        self,
        rows: list[dict[str, str]],
        extra_args: list[str] | None = None,
    ) -> list[dict[str, str]]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_csv = tmpdir_path / "input.csv"
            output_csv = tmpdir_path / "output.csv"

            with input_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["candidate_id", "smiles"])
                writer.writeheader()
                writer.writerows(rows)

            cmd = [sys.executable, str(SCRIPT_PATH), str(input_csv), str(output_csv)]
            if extra_args:
                cmd.extend(extra_args)

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            with output_csv.open(newline="", encoding="utf-8") as handle:
                return list(csv.DictReader(handle))

    def test_rejects_duplicates_and_pains(self) -> None:
        rows = self.run_filter(
            [
                {"candidate_id": "ethanol_1", "smiles": "CCO"},
                {"candidate_id": "ethanol_2", "smiles": "OCC"},
                {"candidate_id": "catechol_1", "smiles": "Oc1ccccc1O"},
                {"candidate_id": "bad_1", "smiles": "not-a-smiles"},
            ],
            extra_args=["--reject-pains"],
        )
        by_id = {row["candidate_id"]: row for row in rows}

        self.assertEqual(by_id["ethanol_1"]["filter_decision"], "pass")
        self.assertIn("duplicate_of:ethanol_1", by_id["ethanol_2"]["filter_reason"])
        self.assertEqual(by_id["catechol_1"]["filter_decision"], "reject")
        self.assertIn("pains_alert", by_id["catechol_1"]["filter_reason"])
        self.assertTrue(by_id["catechol_1"]["pains_alerts"])
        self.assertEqual(by_id["bad_1"]["valid_smiles"], "no")

    def test_annotates_descriptors_and_scaffold_duplicates(self) -> None:
        rows = self.run_filter(
            [
                {"candidate_id": "toluene_1", "smiles": "Cc1ccccc1"},
                {"candidate_id": "ethylbenzene_1", "smiles": "CCc1ccccc1"},
            ],
            extra_args=["--reject-scaffold-duplicates"],
        )
        by_id = {row["candidate_id"]: row for row in rows}

        self.assertEqual(by_id["toluene_1"]["filter_decision"], "pass")
        self.assertTrue(by_id["toluene_1"]["qed"])
        self.assertTrue(by_id["toluene_1"]["clogp"])
        self.assertTrue(by_id["toluene_1"]["murcko_scaffold"])
        self.assertEqual(by_id["toluene_1"]["scaffold_seen_count"], "1")

        self.assertEqual(by_id["ethylbenzene_1"]["filter_decision"], "reject")
        self.assertEqual(by_id["ethylbenzene_1"]["scaffold_duplicate_of"], "toluene_1")
        self.assertIn(
            "scaffold_duplicate_of:toluene_1",
            by_id["ethylbenzene_1"]["filter_reason"],
        )
        self.assertEqual(by_id["ethylbenzene_1"]["scaffold_seen_count"], "2")


if __name__ == "__main__":
    unittest.main()
