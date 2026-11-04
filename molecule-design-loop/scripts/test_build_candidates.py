#!/usr/bin/env python3
"""Tests for build_candidates.py. Run: python3 -m pytest test_build_candidates.py"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "build_candidates.py")

# A benzamide scaffold with two substituent slots, and a polyester-like chain.
# Generic textbook chemistry only: the point is the machinery, not the molecules.
BASE_CONFIG = {
    "allowed_elements": ["C", "H", "N", "O"],
    "fragments": {
        "methyl": {"smiles": "C", "desc": "methyl", "label": "Me"},
        "methoxy": {"smiles": "OC", "desc": "methoxy", "label": "OMe"},
        "n_me": {"smiles": "C", "desc": "N-methyl", "label": "NMe"},
        "n_moe": {"smiles": "CCOC", "desc": "N-(2-methoxyethyl)", "label": "NMoe"},
    },
    "scaffolds": {
        # N-methylbenzamide with two ring substituent slots.
        "benzamide": {"template": "{r1}c1ccc({r2})cc1C(=O)NC"},
    },
    "chains": {
        # Peptoid-like N-substituted glycine chain; {x} is the N-substituent.
        "peptoid": {
            "start": "CC(=O)",
            "segment": "N({x})CC(=O)",
            "end": "NC",
            "display_unit": "[*:1]N({x})CC([*:2])=O",
            "path_smarts": "[NX3][CX4H2][CX3]=O",
            "path_keep": [0, 1, 2],
            "sidechain_every": [0, 3],
            "end_group_model": "acetyl / methylamide",
            "polymerization_route": "ring-opening polymerisation",
            "tacticity": "atactic",
            "start_label": "N-terminus",
            "end_label": "C-terminus",
        },
    },
    "text_blocks": {
        "scope": "Finite capped surrogate; says nothing about chain length or morphology.",
    },
    "defaults": {"design_mode": "small_molecule", "zotero_grounding": "none"},
    "candidates": [
        {
            "candidate_id": "C1",
            "scaffold": "benzamide",
            "slots": {"r1": "methyl", "r2": "methoxy"},
            "design_move": "add para methoxy",
            "rationale": "{candidate_id}: electron-rich ring. {{scope}}",
        },
        {
            "candidate_id": "C2",
            "scaffold": "benzamide",
            "slots": {"r1": "methyl", "r2": "methyl"},
            "design_move": "para methyl control",
        },
    ],
}


def write_config(cfg):
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    yaml.safe_dump(cfg, handle, allow_unicode=True)
    handle.close()
    return handle.name


def run(cfg, *extra, expect_ok=True):
    config_path = write_config(cfg)
    out_path = os.path.join(tempfile.mkdtemp(), "ROUND_1_CANDIDATES.csv")
    cmd = [sys.executable, SCRIPT, "--config", config_path]
    if "--check-only" not in extra:
        cmd += ["--out", out_path]
    cmd += list(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if expect_ok and proc.returncode != 0:
        raise AssertionError(f"build failed:\n{proc.stdout}\n{proc.stderr}")
    return proc, out_path


def read_rows(path):
    with open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def deep_copy(cfg):
    return yaml.safe_load(yaml.safe_dump(cfg))


class TestSmallMolecule(unittest.TestCase):
    def test_builds_rows_and_derives_all_smiles_copies(self):
        _, out = run(BASE_CONFIG)
        rows = read_rows(out)
        self.assertEqual([r["candidate_id"] for r in rows], ["C1", "C2"])
        row = rows[0]
        for column in ("smiles", "canonical_smiles", "rdkit_input_smiles", "rdkit_display_smiles"):
            self.assertTrue(row[column], f"{column} is empty")
        # One structure, so every copy agrees. This is the duplication the config no longer carries.
        self.assertEqual(row["smiles"], row["canonical_smiles"])
        self.assertEqual(row["smiles"], row["rdkit_input_smiles"])
        self.assertEqual(row["molecular_formula"], "C10H13NO2")  # 4-methoxy-2,N-dimethylbenzamide

    def test_passthrough_and_defaults_reach_the_csv(self):
        _, out = run(BASE_CONFIG)
        row = read_rows(out)[0]
        self.assertEqual(row["design_move"], "add para methoxy")
        self.assertEqual(row["design_mode"], "small_molecule")

    def test_text_blocks_and_row_fields_expand(self):
        _, out = run(BASE_CONFIG)
        row = read_rows(out)[0]
        self.assertIn("Finite capped surrogate", row["rationale"])
        self.assertTrue(row["rationale"].startswith("C1: "))
        self.assertNotIn("{{", row["rationale"])

    def test_side_chain_columns_describe_the_fragments_used(self):
        _, out = run(BASE_CONFIG)
        row = read_rows(out)[0]
        self.assertIn("OMe", row["side_chain_descriptions"])
        self.assertIn("methoxy", row["side_chain_descriptions"])
        self.assertIn("OMe:[*]OC", row["side_chain_fragment_smiles"])

    def test_check_only_writes_nothing(self):
        proc, out = run(BASE_CONFIG, "--check-only")
        self.assertIn("validated", proc.stdout)
        self.assertFalse(os.path.exists(out))

    def test_print_columns_separates_derived_from_passthrough(self):
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--print-columns"], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("rationale", proc.stdout)
        self.assertIn("rdkit_display_smiles", proc.stdout)


class TestPolymer(unittest.TestCase):
    def polymer_config(self):
        cfg = deep_copy(BASE_CONFIG)
        cfg["candidates"] = [
            {
                "candidate_id": "P1",
                "chain": "peptoid",
                "units": ["n_moe", "n_me", "n_me", "n_me"],
                "design_mode": "polymer",
                "surrogate_scope": "{{scope}}",
            }
        ]
        return cfg

    def test_derives_polymer_columns(self):
        _, out = run(self.polymer_config())
        row = read_rows(out)[0]
        self.assertEqual(row["oligomer_n"], "4")
        self.assertEqual(row["oligomer_model_smiles"], row["smiles"])
        self.assertEqual(row["end_group_model"], "acetyl / methylamide")
        self.assertEqual(row["tacticity_or_regioregularity"], "atactic")
        self.assertIn("[*:1]", row["repeat_unit_display_smiles"])
        self.assertIn("Finite capped surrogate", row["surrogate_scope"])

    def test_backbone_atom_indices_point_into_the_display_structure(self):
        from rdkit import Chem

        _, out = run(self.polymer_config())
        row = read_rows(out)[0]
        atoms = [int(i) for i in row["backbone_path_atoms"].split()]
        self.assertTrue(atoms)
        mol = Chem.MolFromSmiles(row["rdkit_display_smiles"])
        self.assertLess(max(atoms), mol.GetNumAtoms())
        self.assertEqual(row["backbone_start_atom"], str(atoms[0]))
        self.assertEqual(row["backbone_end_atom"], str(atoms[-1]))
        self.assertIn("N-terminus", row["backbone_connection_points"])


class TestValidation(unittest.TestCase):
    def failing(self, mutate):
        cfg = deep_copy(BASE_CONFIG)
        mutate(cfg)
        proc, _ = run(cfg, expect_ok=False)
        self.assertNotEqual(proc.returncode, 0, "expected a non-zero exit")
        return proc.stderr + proc.stdout

    def test_rejects_unparseable_structure(self):
        def mutate(cfg):
            cfg["fragments"]["methyl"]["smiles"] = "C(((("

        self.assertIn("does not parse", self.failing(mutate))

    def test_rejects_element_outside_the_allowed_set(self):
        def mutate(cfg):
            cfg["fragments"]["methoxy"]["smiles"] = "SC"

        self.assertIn("elements outside", self.failing(mutate))

    def counted_config(self, per_unit=1):
        """Peptoid trimer with motif counting switched on.

        Ac-[N(R)CH2C(=O)]x3-NHMe holds one amide per residue plus one for the
        methylamide end group, so the template declares both contributions.
        """
        cfg = deep_copy(BASE_CONFIG)
        cfg["count_smarts"] = {"amide": "C(=O)N"}
        cfg["chains"]["peptoid"]["counts"] = {"amide": 1}
        cfg["chains"]["peptoid"]["counts_per_unit"] = {"amide": per_unit}
        cfg["candidates"] = [
            {"candidate_id": "P1", "chain": "peptoid", "units": ["n_me", "n_me", "n_me"]}
        ]
        return cfg

    def test_accepts_matching_motif_count(self):
        _, out = run(self.counted_config())
        self.assertEqual(len(read_rows(out)), 1)

    def test_rejects_wrong_motif_count(self):
        # Declares two amides per residue but builds one: the kind of assembly
        # error that still parses and would otherwise reach xTB unnoticed.
        proc, _ = run(self.counted_config(per_unit=2), expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("count", proc.stderr + proc.stdout)

    def test_rejects_charged_structure_by_default(self):
        def mutate(cfg):
            cfg["fragments"]["methyl"]["smiles"] = "[NH3+]C"

        self.assertIn("charge", self.failing(mutate))

    def test_rejects_duplicate_candidate_id(self):
        def mutate(cfg):
            cfg["candidates"][1]["candidate_id"] = "C1"

        self.assertIn("duplicate", self.failing(mutate))

    def test_rejects_derived_column_written_in_the_config(self):
        def mutate(cfg):
            cfg["candidates"][0]["smiles"] = "CCO"

        self.assertIn("derived", self.failing(mutate))

    def test_rejects_unknown_fragment(self):
        def mutate(cfg):
            cfg["candidates"][0]["slots"]["r1"] = "nope"

        self.assertIn("unknown fragment", self.failing(mutate))

    def test_rejects_missing_slot(self):
        def mutate(cfg):
            del cfg["candidates"][0]["slots"]["r2"]

        self.assertIn("needs slots", self.failing(mutate))

    def test_stereo_mismatch_is_caught(self):
        cfg = deep_copy(BASE_CONFIG)
        cfg["chains"]["chiral"] = {
            "start": "CC(=O)",
            "segment": "N[C@@H](C)C(=O)",
            "end": "NC",
            "stereo_smarts": "[CX4H1]([NX3])(C)C=O",
            "stereo_cip": ["R"],  # the segment above is S, so this must fail
        }
        cfg["candidates"] = [
            {"candidate_id": "S1", "chain": "chiral", "units": ["n_me", "n_me"]}
        ]
        proc, _ = run(cfg, expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("stereocentre", proc.stderr + proc.stdout)

    def test_stereo_match_passes(self):
        cfg = deep_copy(BASE_CONFIG)
        cfg["chains"]["chiral"] = {
            "start": "CC(=O)",
            "segment": "N[C@@H](C)C(=O)",
            "end": "NC",
            "stereo_smarts": "[CX4H1]([NX3])(C)C=O",
            "stereo_cip": ["S"],
        }
        cfg["candidates"] = [
            {"candidate_id": "S1", "chain": "chiral", "units": ["n_me", "n_me"]}
        ]
        _, out = run(cfg)
        self.assertEqual(len(read_rows(out)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
