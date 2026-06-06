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
                        "rdkit_display_smiles",
                        "filter_decision",
                        "filter_reason",
                        "design_move",
                        "target_constraint",
                        "rationale",
                        "repeat_unit_display_smiles",
                        "repeat_unit_caption",
                        "sru_bracket_schematic",
                        "repeat_unit_handles_explanation",
                        "polymer_notation",
                        "backbone_start_atom",
                        "backbone_end_atom",
                        "backbone_path_atoms",
                        "side_chain_attachment_atoms",
                        "side_chain_fragment_smiles",
                        "side_chain_descriptions",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "candidate_id": "cand_1",
                            "canonical_smiles": "CCO",
                            "rdkit_display_smiles": "",
                            "filter_decision": "pass",
                            "filter_reason": "ok",
                            "design_move": "rigidify_linker",
                            "target_constraint": "reduce flexibility",
                            "rationale": "small alcohol control",
                            "repeat_unit_display_smiles": "",
                            "repeat_unit_caption": "",
                            "sru_bracket_schematic": "",
                            "repeat_unit_handles_explanation": "",
                            "polymer_notation": "",
                            "backbone_start_atom": "",
                            "backbone_end_atom": "",
                            "backbone_path_atoms": "",
                            "side_chain_attachment_atoms": "",
                            "side_chain_fragment_smiles": "",
                            "side_chain_descriptions": "",
                        },
                        {
                            "candidate_id": "cand_2",
                            "canonical_smiles": "not-a-smiles",
                            "rdkit_display_smiles": "CC(C)CC",
                            "filter_decision": "reject",
                            "filter_reason": "invalid_smiles",
                            "design_move": "negative_control",
                            "target_constraint": "sanity check",
                            "rationale": "kept for review",
                            "repeat_unit_display_smiles": "[*:1]CC([*:2])C",
                            "repeat_unit_caption": "cand_2 intended repeat unit\n[*:1] and [*:2] = polymer chain extension\nmethyl = side chain",
                            "sru_bracket_schematic": "B_start - [CH2-CH(CH3)]n - B_end",
                            "repeat_unit_handles_explanation": "cand_2 repeat unit handles\n[*:1] = connection to previous repeat unit\n[*:2] = connection to next repeat unit\nmain chain = CH2-CH\nside chains = methyl",
                            "polymer_notation": "{[*]CC(C)[*]}",
                            "backbone_start_atom": "0",
                            "backbone_end_atom": "4",
                            "backbone_path_atoms": "0,1,3,4",
                            "side_chain_attachment_atoms": "2",
                            "side_chain_fragment_smiles": "methyl:C",
                            "side_chain_descriptions": "methyl side chain on backbone carbon",
                        },
                        {
                            "candidate_id": "cand_3",
                            "canonical_smiles": "not-a-smiles",
                            "rdkit_display_smiles": "",
                            "filter_decision": "reject",
                            "filter_reason": "invalid_smiles",
                            "design_move": "negative_control",
                            "target_constraint": "sanity check",
                            "rationale": "kept for review",
                            "repeat_unit_display_smiles": "",
                            "repeat_unit_caption": "",
                            "sru_bracket_schematic": "",
                            "repeat_unit_handles_explanation": "",
                            "polymer_notation": "",
                            "backbone_start_atom": "",
                            "backbone_end_atom": "",
                            "backbone_path_atoms": "",
                            "side_chain_attachment_atoms": "",
                            "side_chain_fragment_smiles": "",
                            "side_chain_descriptions": "",
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
            self.assertIn("cand_3", html_text)
            self.assertIn("<svg", html_text)
            self.assertIn("Invalid SMILES", html_text)
            self.assertIn("filter_decision", html_text)
            self.assertIn("Primary polymer view", html_text)
            self.assertIn("repeat-unit-figure", html_text)
            self.assertIn("cand_2 intended repeat unit", html_text)
            self.assertIn("[CH2-CH(CH3)]n", html_text)
            self.assertIn("repeat unit handles", html_text)
            self.assertIn("connection to previous repeat unit", html_text)
            self.assertIn("Polymer depiction packet", html_text)
            self.assertIn("Backbone direction", html_text)
            self.assertIn("START", html_text)
            self.assertIn("END", html_text)
            self.assertIn("Backbone only", html_text)
            self.assertIn("Side chains", html_text)
            self.assertIn("Polymer map", html_text)
            self.assertIn("methyl side chain", html_text)


if __name__ == "__main__":
    unittest.main()
