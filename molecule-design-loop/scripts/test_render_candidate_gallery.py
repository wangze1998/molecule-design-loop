#!/usr/bin/env python3
"""Lightweight tests for render_candidate_gallery.py."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("render_candidate_gallery.py")


class RenderCandidateGalleryTest(unittest.TestCase):
    def test_renders_html_gallery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_csv = tmpdir_path / "filtered.csv"
            output_html = tmpdir_path / "gallery.html"

            with input_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "candidate_id",
                        "canonical_smiles",
                        "filter_decision",
                        "filter_reason",
                        "design_move",
                        "target_constraint",
                        "rationale",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "candidate_id": "cand_1",
                            "canonical_smiles": "CCO",
                            "filter_decision": "pass",
                            "filter_reason": "ok",
                            "design_move": "rigidify_linker",
                            "target_constraint": "reduce flexibility",
                            "rationale": "small alcohol control",
                        },
                        {
                            "candidate_id": "cand_2",
                            "canonical_smiles": "not-a-smiles",
                            "filter_decision": "reject",
                            "filter_reason": "invalid_smiles",
                            "design_move": "negative_control",
                            "target_constraint": "sanity check",
                            "rationale": "kept for review",
                        },
                    ],
                )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    str(input_csv),
                    str(output_html),
                    "--title",
                    "Round 1 Candidate Gallery",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            html_text = output_html.read_text(encoding="utf-8")
            self.assertIn("Round 1 Candidate Gallery", html_text)
            self.assertIn("cand_1", html_text)
            self.assertIn("cand_2", html_text)
            self.assertIn("<svg", html_text)
            self.assertIn("Invalid SMILES", html_text)
            self.assertIn("filter_decision", html_text)


if __name__ == "__main__":
    unittest.main()
