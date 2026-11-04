#!/usr/bin/env python3
"""Tests for build_gemini_inputs.py. Run: python3 -m pytest test_build_gemini_inputs.py"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "build_gemini_inputs.py")
REFS = os.path.join(os.path.dirname(HERE), "references")

CANDIDATE_ROWS = [
    {
        "candidate_id": "C1",
        "role": "lead",
        "smiles": "COc1ccc(C)c(C(=O)NC)c1",
        "design_move": "add para methoxy",
        "rationale": "electron-rich ring",
        "expected_proxy_effect": "raises HOMO",
        "risk": "demethylation",
        "synthesis_hypothesis": "amide coupling",
        "surrogate_scope": "finite molecule, no assembly claim",
        "computational_evidence_role": "descriptors only",
    },
    {
        "candidate_id": "C2",
        "role": "control",
        "smiles": "Cc1ccc(C)c(C(=O)NC)c1",
        "design_move": "methyl control",
        "rationale": "baseline",
        "expected_proxy_effect": "none",
        "risk": "none",
        "synthesis_hypothesis": "amide coupling",
        "surrogate_scope": "finite molecule, no assembly claim",
        "computational_evidence_role": "descriptors only",
    },
]

GATE_ROWS = [
    {
        "candidate_id": "C1",
        "synthesis_gate_status": "pass",
        "make_or_buy_status": "buy",
        "route_summary": "one-step amide coupling",
        "synthesis_cost": "low",
        "time_to_first_sample": "days",
        "overall_yield_estimate": "medium",
        "hazard_toxicity_flag": "standard_care",
        "starting_materials_or_building_blocks": "commercial acid + amine",
    },
]


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_round(with_gate=True, with_xtb=False, with_state=False):
    root = tempfile.mkdtemp()
    with open(os.path.join(root, "DESIGN_SPEC_LOCKED.md"), "w", encoding="utf-8") as handle:
        handle.write("# Locked spec\n\nhard_constraints: neutral, C/H/N/O only\n")
    write_csv(os.path.join(root, "ROUND_1_CANDIDATES.csv"), CANDIDATE_ROWS)
    if with_gate:
        write_csv(os.path.join(root, "ROUND_1_SYNTHESIS_FEASIBILITY.csv"), GATE_ROWS)
    if with_xtb:
        write_csv(
            os.path.join(root, "ROUND_1_XTB_RESULTS.csv"),
            [{"candidate_id": "C1", "method": "GFN2-xTB", "optimization_status": "converged",
              "homo_lumo_gap_ev": "3.9"}],
        )
    if with_state:
        with open(os.path.join(root, "DESIGN_LOOP_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({"prior_computational_evidence": {"stage_a": "calc/stage_a/RESULTS.md"}}, handle)
    return root


def run(root, *extra, expect_ok=True):
    out = os.path.join(root, "_gemini_inputs")
    cmd = [sys.executable, SCRIPT, "--round-dir", root, "--skill-refs", REFS, "--out", out]
    proc = subprocess.run(cmd + list(extra), capture_output=True, text=True)
    if expect_ok and proc.returncode != 0:
        raise AssertionError(f"failed:\n{proc.stdout}\n{proc.stderr}")
    return proc, out


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TestPackets(unittest.TestCase):
    def test_writes_all_three_packets(self):
        _, out = run(make_round())
        for name in (
            "step3.5_adversarial_review_input.md",
            "step5.5_prior_art_input.md",
            "step9.5_claim_audit_input.md",
        ):
            self.assertTrue(os.path.exists(os.path.join(out, name)), name)

    def test_selected_steps_only(self):
        _, out = run(make_round(), "--steps", "5.5")
        self.assertEqual(os.listdir(out), ["step5.5_prior_art_input.md"])

    def test_packet_carries_spec_and_raw_rows(self):
        _, out = run(make_round())
        text = read(os.path.join(out, "step3.5_adversarial_review_input.md"))
        self.assertIn("hard_constraints", text)
        self.assertIn("COc1ccc(C)c(C(=O)NC)c1", text)
        self.assertIn("add para methoxy", text)
        self.assertIn("do not summarise", text)

    def test_system_prompt_is_copied_from_the_protocol_file(self):
        _, out = run(make_round())
        text = read(os.path.join(out, "step3.5_adversarial_review_input.md"))
        self.assertIn("## system", text)
        self.assertIn("adversarial", text.lower())
        self.assertNotIn("protocol file not found", text)

    def test_novelty_packet_carries_structure_not_just_words(self):
        # A prior-art check without SMILES is a keyword search wearing a different name.
        _, out = run(make_round())
        text = read(os.path.join(out, "step5.5_prior_art_input.md"))
        self.assertIn("COc1ccc(C)c(C(=O)NC)c1", text)

    def test_adversarial_packet_includes_route_detail(self):
        _, out = run(make_round())
        text = read(os.path.join(out, "step3.5_adversarial_review_input.md"))
        self.assertIn("one-step amide coupling", text)
        self.assertIn("hazard_toxicity_flag", text)

    def test_missing_gate_is_declared_not_faked(self):
        _, out = run(make_round(with_gate=False))
        text = read(os.path.join(out, "step3.5_adversarial_review_input.md"))
        self.assertIn("Not available for this round", text)
        self.assertNotIn("one-step amide coupling", text)

    def test_audit_packet_states_when_no_xtb_ran(self):
        _, out = run(make_round())
        text = read(os.path.join(out, "step9.5_claim_audit_input.md"))
        self.assertIn("No xTB ran this round", text)

    def test_audit_packet_lists_xtb_results_when_present(self):
        _, out = run(make_round(with_xtb=True))
        text = read(os.path.join(out, "step9.5_claim_audit_input.md"))
        self.assertIn("homo_lumo_gap_ev", text)
        self.assertNotIn("No xTB ran this round", text)

    def test_prior_evidence_is_named_not_embedded(self):
        _, out = run(make_round(with_state=True))
        text = read(os.path.join(out, "step9.5_claim_audit_input.md"))
        self.assertIn("calc/stage_a/RESULTS.md", text)
        self.assertIn("not embedded", text)

    def test_absent_columns_are_reported(self):
        root = make_round()
        rows = [{k: v for k, v in row.items() if k != "risk"} for row in CANDIDATE_ROWS]
        write_csv(os.path.join(root, "ROUND_1_CANDIDATES.csv"), rows)
        _, out = run(root)
        text = read(os.path.join(out, "step3.5_adversarial_review_input.md"))
        self.assertIn("Columns absent", text)
        self.assertIn("risk", text)

    def test_missing_spec_is_an_error(self):
        root = make_round()
        os.remove(os.path.join(root, "DESIGN_SPEC_LOCKED.md"))
        proc, _ = run(root, expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
