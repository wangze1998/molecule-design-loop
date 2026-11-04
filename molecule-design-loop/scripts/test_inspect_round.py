#!/usr/bin/env python3
"""Tests for inspect_round.py. Run: python3 -m pytest test_inspect_round.py"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "inspect_round.py")

ROWS = [
    {
        "candidate_id": "C1",
        "smiles": "COc1ccccc1",
        "role": "lead",
        "filter_decision": "pass",
        "filter_reason": "",
        "rationale": "an unusually long justification " * 8,
        "unused_column": "",
    },
    {
        "candidate_id": "C2",
        "smiles": "Cc1ccccc1",
        "role": "control",
        "filter_decision": "fail",
        "filter_reason": "molecular weight below the minimum",
        "rationale": "baseline",
        "unused_column": "",
    },
    {
        "candidate_id": "C3",
        "smiles": "CCO",
        "role": "lead",
        "filter_decision": "fail",
        "filter_reason": "forbidden motif present",
        "rationale": "exploratory",
        "unused_column": "",
    },
]

GALLERY = """<!doctype html><html><head><title>Round 1 Candidate Gallery</title></head>
<body>
<div class="candidate-card" id="candidate-C1"><svg width="10"></svg><table></table></div>
<div class="candidate-card" id="candidate-C2"><svg width="10"></svg></div>
<img src="data:image/png;base64,AAAA">
</body></html>"""


def make_csv(rows=None):
    path = os.path.join(tempfile.mkdtemp(), "ROUND_1_FILTERED.csv")
    rows = rows if rows is not None else ROWS
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def run(*args, expect_ok=True):
    proc = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)
    if expect_ok and proc.returncode != 0:
        raise AssertionError(f"failed:\n{proc.stdout}\n{proc.stderr}")
    return proc


class TestSummary(unittest.TestCase):
    def test_reports_shape_and_flag_tallies(self):
        out = run("summary", make_csv()).stdout
        self.assertIn("3 rows x 7 columns", out)
        self.assertIn("filter_decision:", out)
        self.assertIn("fail=2", out)
        self.assertIn("pass=1", out)

    def test_names_always_empty_columns(self):
        out = run("summary", make_csv()).stdout
        self.assertIn("always empty", out)
        self.assertIn("unused_column", out)

    def test_does_not_dump_long_values(self):
        out = run("summary", make_csv()).stdout
        self.assertNotIn("an unusually long justification an unusually", out)


class TestCols(unittest.TestCase):
    def test_prints_only_requested_columns(self):
        out = run("cols", make_csv(), "candidate_id", "filter_decision").stdout
        self.assertIn("C1", out)
        self.assertIn("pass", out)
        self.assertNotIn("COc1ccccc1", out)

    def test_clips_long_values_and_says_so(self):
        out = run("--width", "30", "cols", make_csv(), "candidate_id", "rationale").stdout
        self.assertIn("…", out)
        self.assertIn("clipped at 30", out)
        for line in out.splitlines():
            self.assertLessEqual(len(line), 120)

    def test_width_works_on_either_side_of_the_subcommand(self):
        before = run("--width", "30", "cols", make_csv(), "candidate_id", "rationale").stdout
        after = run("cols", make_csv(), "candidate_id", "rationale", "--width", "30").stdout
        self.assertIn("clipped at 30", before)
        self.assertIn("clipped at 30", after)
        self.assertEqual(before, after)

    def test_reports_absent_columns(self):
        out = run("cols", make_csv(), "candidate_id", "no_such_column").stdout
        self.assertIn("absent from this file", out)
        self.assertIn("no_such_column", out)

    def test_all_columns_absent_is_an_error(self):
        proc = run("cols", make_csv(), "nope", expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("available:", proc.stderr)


class TestRow(unittest.TestCase):
    def test_prints_one_row_without_empty_fields(self):
        out = run("row", make_csv(), "C2").stdout
        self.assertIn("filter_reason: molecular weight below the minimum", out)
        self.assertNotIn("unused_column", out)

    def test_unknown_id_is_an_error(self):
        proc = run("row", make_csv(), "nope", expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)


class TestGrep(unittest.TestCase):
    def test_finds_matching_rows(self):
        out = run("grep", make_csv(), "forbidden", "--columns", "candidate_id", "filter_reason").stdout
        self.assertIn("C3", out)
        self.assertNotIn("C2 ", out)
        self.assertIn("1 of 3 rows match", out)

    def test_limit_is_announced(self):
        out = run("grep", make_csv(), "fail", "--limit", "1", "--columns", "candidate_id").stdout
        self.assertIn("showing 1", out)

    def test_no_match_is_reported_not_an_error(self):
        proc = run("grep", make_csv(), "zzzz")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("no row matches", proc.stdout)


class TestCheck(unittest.TestCase):
    def test_passes_a_clean_file(self):
        proc = run("check", make_csv(), "--required", "candidate_id", "smiles")
        self.assertIn("all checks pass", proc.stdout)

    def test_flags_duplicate_ids(self):
        rows = [dict(r) for r in ROWS]
        rows[1]["candidate_id"] = "C1"
        proc = run("check", make_csv(rows), expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("duplicate candidate_id: C1", proc.stdout)

    def test_flags_empty_required_cell(self):
        rows = [dict(r) for r in ROWS]
        rows[2]["smiles"] = ""
        proc = run("check", make_csv(rows), expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("smiles empty for: C3", proc.stdout)

    def test_flags_missing_required_column(self):
        proc = run("check", make_csv(), "--required", "candidate_id", "prior_art_status",
                   expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing columns", proc.stdout)


class TestHtml(unittest.TestCase):
    def gallery(self):
        path = os.path.join(tempfile.mkdtemp(), "ROUND_1_CANDIDATE_GALLERY.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(GALLERY)
        return path

    def test_counts_elements_without_printing_markup(self):
        out = run("html", self.gallery()).stdout
        self.assertIn("Round 1 Candidate Gallery", out)
        self.assertIn("candidate blocks: 2", out)
        self.assertIn("<svg> drawings: 2", out)
        self.assertIn("embedded images: 1", out)
        self.assertNotIn("<div", out)
        self.assertNotIn("base64,AAAA", out)

    def test_lists_candidate_ids(self):
        out = run("html", self.gallery()).stdout
        self.assertIn("C1", out)
        self.assertIn("C2", out)


class TestGeneral(unittest.TestCase):
    def test_missing_file_is_an_error(self):
        proc = run("summary", "/nonexistent/file.csv", expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no such file", proc.stderr)

    def test_empty_csv_is_an_error(self):
        path = os.path.join(tempfile.mkdtemp(), "empty.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("candidate_id,smiles\n")
        proc = run("summary", path, expect_ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no data rows", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
