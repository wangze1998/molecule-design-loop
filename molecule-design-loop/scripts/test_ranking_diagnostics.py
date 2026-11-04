#!/usr/bin/env python3
"""Tests for ranking_diagnostics.py. Standard library only; no RDKit needed."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("ranking_diagnostics.py")

BASE_FIELDS = [
    "candidate_id",
    "gemini_constraint_score",
    "pass_hard_constraints",
    "synthesis_cost",
    "time_to_first_sample",
    "overall_yield_estimate",
    "hazard_toxicity_flag",
    "make_or_buy_status",
]


def row(cid, score, cost, time, yield_, hazard, passes="yes", make="buy"):
    return {
        "candidate_id": cid,
        "gemini_constraint_score": score,
        "pass_hard_constraints": passes,
        "synthesis_cost": cost,
        "time_to_first_sample": time,
        "overall_yield_estimate": yield_,
        "hazard_toxicity_flag": hazard,
        "make_or_buy_status": make,
    }


class RankingDiagnosticsTest(unittest.TestCase):
    def run_tool(self, rows, extra_args=None, expect_rc=0):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_csv = tmp_path / "in.csv"
            out_csv = tmp_path / "out.csv"
            report = tmp_path / "report.md"
            fields = list(BASE_FIELDS)
            for r in rows:
                for k in r:
                    if k not in fields:
                        fields.append(k)
            with in_csv.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            cmd = [sys.executable, str(SCRIPT_PATH), str(in_csv), str(out_csv), "--report", str(report)]
            if extra_args:
                cmd.extend(extra_args)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, expect_rc, msg=proc.stderr)
            if expect_rc != 0:
                return None, None, proc.stderr
            with out_csv.open(newline="", encoding="utf-8") as fh:
                out_rows = {r["candidate_id"]: r for r in csv.DictReader(fh)}
            return out_rows, report.read_text(encoding="utf-8"), proc.stderr

    def test_clear_dominance(self):
        # best is no worse on every axis than worst and strictly better -> worst dominated.
        rows = [
            row("best", 5, "low", "same_day", "high", "none"),
            row("worst", 3, "high", "weeks", "low", "high_hazard"),
            row("mid", 4, "medium", "days", "medium", "standard_care"),
        ]
        out, report, _ = self.run_tool(rows)
        self.assertTrue(out["worst"]["practicality_dominance"].startswith("dominated_by:"))
        self.assertIn("best", out["worst"]["practicality_dominance"])
        self.assertEqual(out["best"]["practicality_dominance"], "non_dominated")
        self.assertEqual(out["best"]["pareto_rank"], "1")
        # worst is dominated, must not be in top 3 ahead of non-dominated ones
        self.assertEqual(out["worst"]["pareto_rank"], "3")

    def test_nothing_dominated_is_reported(self):
        # each better on one axis, worse on another -> a true trade-off, no dominance.
        rows = [
            row("cheap_slow", 4, "low", "months", "high", "none"),
            row("pricey_fast", 4, "very_high", "same_day", "high", "none"),
        ]
        out, report, _ = self.run_tool(rows)
        self.assertEqual(out["cheap_slow"]["practicality_dominance"], "non_dominated")
        self.assertEqual(out["pricey_fast"]["practicality_dominance"], "non_dominated")
        self.assertIn("did not constrain the ranking", report)
        self.assertIn("0 /", report)

    def test_unknown_is_non_comparable_not_zero(self):
        # 'strong' would dominate 'weak' on known axes, but weak has an unknown axis.
        rows = [
            row("strong", 5, "low", "same_day", "high", "none"),
            row("weak", 3, "high", "weeks", "unknown", "high_hazard"),
        ]
        out, report, _ = self.run_tool(rows)
        # weak must NOT be recorded as dominated, because yield is unknown
        self.assertEqual(out["weak"]["practicality_dominance"], "not_assessed")
        self.assertEqual(out["strong"]["practicality_dominance"], "non_dominated")
        self.assertIn("not_assessed", out["weak"]["practicality_dominance"])

    def test_shadow_rank_and_exclusion(self):
        # p_hi has the best score but a terrible route; a cheaper lower-scorer should
        # not be dominated by it (p_hi is worse on every practicality axis), so p_hi
        # can be pushed out of the top by dominance from an equal-or-better profile.
        rows = [
            row("p_hi", 5, "very_high", "months", "low", "high_hazard"),
            row("p_hi_cheap", 5, "low", "same_day", "high", "none"),
            row("mid1", 4, "low", "same_day", "high", "none"),
            row("mid2", 4, "low", "days", "high", "none"),
        ]
        out, report, _ = self.run_tool(rows)
        # p_hi is dominated by p_hi_cheap (same score, worse on everything)
        self.assertIn("dominated_by:p_hi_cheap", out["p_hi"]["practicality_dominance"])
        # shadow rank ranks p_hi and p_hi_cheap tied at 1 on score alone
        self.assertEqual(out["p_hi"]["shadow_rank_property_only"], "1")
        self.assertEqual(out["p_hi_cheap"]["shadow_rank_property_only"], "1")
        # exclusion reason must name concrete values, never a bare phrase
        reason = out["p_hi"]["excluded_by_practicality"]
        self.assertIn("cost=very_high", reason)
        self.assertNotIn("practicality concerns", reason)

    def test_redundancy_floor(self):
        rows = [row(f"c{i}", 5 - (i % 3), "low", "same_day", "high", "none") for i in range(5)]
        _, report, _ = self.run_tool(rows)
        self.assertIn("not_assessed", report)
        self.assertIn("below floor", report)

    def test_redundancy_matrix_emitted(self):
        rows = []
        costs = ["low", "medium", "high", "very_high"]
        times = ["same_day", "days", "weeks", "months"]
        for i in range(10):
            rows.append(row(f"c{i}", (i % 5) + 1, costs[i % 4], times[i % 4], "high", "none"))
        _, report, _ = self.run_tool(rows)
        self.assertIn("Kendall tau-b", report)
        self.assertIn("| cost / time |", report)

    def test_hard_constraint_failers_not_ranked(self):
        rows = [
            row("ok", 5, "low", "same_day", "high", "none"),
            row("failer", 5, "low", "same_day", "high", "none", passes="no"),
        ]
        out, _, _ = self.run_tool(rows)
        self.assertEqual(out["failer"]["pareto_rank"], "not_ranked")
        self.assertEqual(out["failer"]["practicality_dominance"], "not_assessed")

    def test_bad_score_aborts(self):
        rows = [row("c1", 9, "low", "same_day", "high", "none")]
        _, _, stderr = self.run_tool(rows, expect_rc=2)
        self.assertIn("outside 1-5", stderr)

    def test_bad_axis_value_aborts(self):
        rows = [row("c1", 5, "cheap", "same_day", "high", "none")]
        _, _, stderr = self.run_tool(rows, expect_rc=2)
        self.assertIn("synthesis_cost", stderr)

    def test_benchmark_ranks(self):
        rows = [
            row("cand1", 5, "low", "same_day", "high", "none"),
            row("incumbent", 2, "high", "weeks", "low", "high_hazard"),
        ]
        _, report, _ = self.run_tool(rows, extra_args=["--benchmark-ids", "incumbent"])
        self.assertIn("Benchmark Ranks", report)
        self.assertIn("incumbent", report)

    def test_make_buy_tiebreak(self):
        # identical profiles, different make/buy -> buy ranks ahead
        rows = [
            row("buy_one", 5, "low", "same_day", "high", "none", make="buy"),
            row("custom_one", 5, "low", "same_day", "high", "none", make="custom_synthesis"),
        ]
        out, _, _ = self.run_tool(rows)
        self.assertEqual(out["buy_one"]["pareto_rank"], "1")
        self.assertEqual(out["custom_one"]["pareto_rank"], "2")


if __name__ == "__main__":
    unittest.main()
