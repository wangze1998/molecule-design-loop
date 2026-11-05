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


def row(cid, score, cost, time, yield_, hazard, passes="yes", make="buy", role=None):
    out = {
        "candidate_id": cid,
        "gemini_constraint_score": score,
        "pass_hard_constraints": passes,
        "synthesis_cost": cost,
        "time_to_first_sample": time,
        "overall_yield_estimate": yield_,
        "hazard_toxicity_flag": hazard,
        "make_or_buy_status": make,
    }
    if role is not None:
        out["role"] = role
    return out


class ToolRunnerMixin:
    """Runs the script on an in-memory CSV. Shared by the test cases below; not a
    TestCase itself, so the cases do not re-run each other's tests."""

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


class RankingDiagnosticsTest(ToolRunnerMixin, unittest.TestCase):
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
        # Only 'best' is non-dominated here; what ranks 2 and 3 hold depends on
        # --pareto-rank-mode and is pinned in ShortFrontTest below.

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


class ShortFrontTest(ToolRunnerMixin, unittest.TestCase):
    """The regression this file previously missed: fewer than TOP_N non-dominated rows.

    `positional` numbering hands the free top positions to the best DOMINATED rows, so
    pareto_rank said 2/3 while the report's final top set (in_final_top) left them out.
    Round 1 of loop-v2 hit exactly this: one non-dominated row, two dominated rows at
    pareto_rank 2 and 3.
    """

    # one non-dominated row (best), everything else dominated by it
    ONE_FRONT_ROWS = [
        row("best", 3, "low", "days", "high", "standard_care"),
        row("dom_a", 3, "medium", "weeks", "medium", "standard_care", make="make_on_demand"),
        row("dom_b", 3, "medium", "weeks", "medium", "standard_care", make="custom_synthesis"),
        row("dom_c", 2, "high", "weeks", "low", "standard_care", make="custom_synthesis"),
    ]

    def test_one_non_dominated_row_positional_keeps_ranks_and_warns(self):
        """Default mode is unchanged (old round files stay reproducible) but says so."""
        out, report, stderr = self.run_tool(self.ONE_FRONT_ROWS)
        self.assertEqual(out["best"]["pareto_rank"], "1")
        # the legacy numbering, preserved on purpose
        self.assertEqual(out["dom_a"]["pareto_rank"], "2")
        self.assertEqual(out["dom_b"]["pareto_rank"], "3")
        self.assertTrue(out["dom_a"]["practicality_dominance"].startswith("dominated_by:best"))
        # ... and the conflict is reported, not left for a field check to catch
        self.assertIn("--pareto-rank-mode protocol", stderr)
        self.assertIn("dominated candidate(s) inside the top 3", stderr)
        self.assertIn("pareto_rank / protocol Conflict", report)
        self.assertIn("dom_a", report)

    def test_one_non_dominated_row_protocol_leaves_top_positions_empty(self):
        """Protocol mode: no dominated row inside the top 3, and 2-3 belong to nobody."""
        out, report, stderr = self.run_tool(self.ONE_FRONT_ROWS, extra_args=["--pareto-rank-mode", "protocol"])
        self.assertEqual(out["best"]["pareto_rank"], "1")
        ranks = {cid: r["pareto_rank"] for cid, r in out.items()}
        self.assertNotIn("2", ranks.values())
        self.assertNotIn("3", ranks.values())
        self.assertEqual(ranks["dom_a"], "4")
        self.assertEqual(ranks["dom_b"], "5")
        self.assertEqual(ranks["dom_c"], "6")
        # no dominated row claims a top-3 rank, so nothing to flag
        self.assertNotIn("pareto_rank / protocol Conflict", report)
        self.assertEqual(stderr.strip(), "")
        # the report's final top set and the CSV field now agree: best alone
        self.assertIn("| 1 | best (shadow 1) | best |", report)

    def test_protocol_mode_is_a_no_op_once_the_front_fills_the_top(self):
        """Three non-dominated rows: offset is 0, so both modes agree."""
        rows = [
            row("cheap_slow", 4, "low", "months", "high", "none"),
            row("pricey_fast", 4, "very_high", "same_day", "high", "none"),
            row("mid", 4, "medium", "days", "medium", "none"),
            row("loser", 2, "very_high", "months", "low", "high_hazard"),
        ]
        pos, _, pos_err = self.run_tool(rows)
        pro, _, _ = self.run_tool(rows, extra_args=["--pareto-rank-mode", "protocol"])
        self.assertEqual(
            {k: v["pareto_rank"] for k, v in pos.items()},
            {k: v["pareto_rank"] for k, v in pro.items()},
        )
        self.assertEqual(pro["loser"]["pareto_rank"], "4")
        self.assertEqual(pos_err.strip(), "")

    def test_dominated_rows_tied_on_score_are_ordered_deterministically(self):
        """Dominated rows with identical scores must not jitter, and none may enter the top 3."""
        rows = [
            row("front", 4, "low", "same_day", "high", "none"),
            # same score, same axes, differing only in make/buy then id
            row("tie_c", 3, "medium", "days", "medium", "standard_care", make="custom_synthesis"),
            row("tie_a", 3, "medium", "days", "medium", "standard_care", make="buy"),
            row("tie_b", 3, "medium", "days", "medium", "standard_care", make="buy"),
        ]
        first, _, _ = self.run_tool(rows, extra_args=["--pareto-rank-mode", "protocol"])
        again, _, _ = self.run_tool(list(reversed(rows)), extra_args=["--pareto-rank-mode", "protocol"])
        ranks = {k: v["pareto_rank"] for k, v in first.items()}
        self.assertEqual(ranks, {k: v["pareto_rank"] for k, v in again.items()})
        self.assertEqual(ranks["front"], "1")
        # ties share a shadow rank but get distinct positional ranks, all outside the top 3
        self.assertEqual(ranks["tie_a"], "4")
        self.assertEqual(ranks["tie_b"], "5")
        self.assertEqual(ranks["tie_c"], "6")
        for cid in ("tie_a", "tie_b", "tie_c"):
            self.assertEqual(first[cid]["shadow_rank_property_only"], "2")
            self.assertTrue(first[cid]["practicality_dominance"].startswith("dominated_by:front"))


class ControlRoleTest(ToolRunnerMixin, unittest.TestCase):
    """A control is a reference point, not an offer. Round 1 of loop-v2 had a cap-only
    control as the ONLY non-dominated row, which made the candidate ranking meaningless."""

    ROWS = [
        row("control_cap", 3, "low", "days", "high", "standard_care", make="make_on_demand", role="control"),
        row("cand_a", 3, "medium", "weeks", "medium", "standard_care", make="make_on_demand", role="candidate"),
        row("cand_b", 3, "medium", "weeks", "medium", "standard_care", make="custom_synthesis", role="candidate"),
        row("cand_c", 2, "high", "weeks", "low", "standard_care", make="custom_synthesis", role="candidate"),
    ]

    def test_role_column_is_off_until_asked_for(self):
        """The column alone changes nothing: without --role-column the control is ranked."""
        out, report, _ = self.run_tool(self.ROWS)
        self.assertEqual(out["control_cap"]["pareto_rank"], "1")
        self.assertTrue(out["cand_a"]["practicality_dominance"].startswith("dominated_by:control_cap"))
        self.assertNotIn("Controls (reported separately", report)

    def test_control_is_held_out_of_dominance_and_reported_separately(self):
        out, report, stderr = self.run_tool(
            self.ROWS, extra_args=["--role-column", "role", "--pareto-rank-mode", "protocol"]
        )
        # the control gets no rank and no dominance verdict in either direction
        self.assertEqual(out["control_cap"]["pareto_rank"], "control")
        self.assertEqual(out["control_cap"]["shadow_rank_property_only"], "control")
        self.assertEqual(out["control_cap"]["practicality_dominance"], "control_not_compared")
        self.assertEqual(out["control_cap"]["excluded_by_practicality"], "control")
        # with it held out, the candidates have a real two-member front instead of
        # all being dominated by the thing they are measured against
        self.assertEqual(out["cand_a"]["practicality_dominance"], "non_dominated")
        self.assertEqual(out["cand_b"]["practicality_dominance"], "non_dominated")
        self.assertEqual(out["cand_a"]["pareto_rank"], "1")
        self.assertEqual(out["cand_b"]["pareto_rank"], "2")
        self.assertNotIn("control_cap", out["cand_c"]["practicality_dominance"])
        # reported separately, with its axes, and counted out of the candidate pool
        self.assertIn("Controls (reported separately, not ranked)", report)
        self.assertIn("| control_cap | 3 |", report)
        self.assertIn("Controls held out of the ranking: 1 (control_cap)", report)
        self.assertIn("Hard-constraint passers: 3 of 3 candidates.", report)
        self.assertEqual(stderr.strip(), "")

    def test_control_excluded_from_redundancy_and_dominance_counts(self):
        rows = [row(f"c{i}", (i % 3) + 2, "low", "same_day", "high", "none", role="candidate") for i in range(9)]
        rows.append(row("ctrl", 5, "low", "same_day", "high", "none", role="control"))
        _, report, _ = self.run_tool(rows, extra_args=["--role-column", "role"])
        self.assertIn("Kendall tau-b over 9 hard-constraint passers", report)
        self.assertIn("Controls held out of the ranking: 1 (ctrl)", report)

    def test_unknown_role_aborts(self):
        rows = [row("c1", 5, "low", "same_day", "high", "none", role="reference")]
        _, _, stderr = self.run_tool(rows, extra_args=["--role-column", "role"], expect_rc=2)
        self.assertIn("role='reference'", stderr)
        self.assertIn("candidate, control", stderr)

    def test_missing_role_column_aborts(self):
        rows = [row("c1", 5, "low", "same_day", "high", "none")]
        _, _, stderr = self.run_tool(rows, extra_args=["--role-column", "role"], expect_rc=2)
        self.assertIn("is not a column of the decision CSV", stderr)


if __name__ == "__main__":
    unittest.main()
