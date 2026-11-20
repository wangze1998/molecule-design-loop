#!/usr/bin/env python3
"""Tests for reviewer_route.py: selection order, safe fallback, and independence.

The rules worth guarding: an explicit choice beats a file, a file beats the default;
a provider is never swapped after a review may have run; and the executor's own
model family never quietly reviews its own candidates.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reviewer_route as rr  # noqa: E402

SCRIPT = os.path.join(HERE, "reviewer_route.py")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = os.path.join(self.tmp.name, "reviewer.json")
        self.user = os.path.join(self.tmp.name, "user.json")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, data):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def resolve(self, role="review", host="claude-code", **kwargs):
        return rr.resolve(role, host, project_file=self.project, user_file=self.user, **kwargs)


class TestSelectionOrder(Base):
    def test_default_is_gemini_direct(self):
        route = self.resolve()
        self.assertEqual((route["backend"], route["via"], route["source"]),
                         ("gemini", "direct", "default"))
        self.assertEqual(route["model"], "gemini-2.5-flash")
        self.assertEqual(route["tools"]["fresh"], "mcp__gemini-review__review")

    def test_search_role_uses_research_tools(self):
        route = self.resolve(role="search")
        self.assertEqual(route["tools"]["fresh"], "mcp__gemini-research__prior_art_search_start")

    def test_user_beats_default_and_project_beats_user(self):
        self.write(self.user, {"backend": "antigravity"})
        self.assertEqual(self.resolve()["source"], "user")
        self.write(self.project, {"review": {"backend": "codex"}})
        route = self.resolve()
        self.assertEqual((route["backend"], route["source"]), ("codex", "project"))

    def test_invocation_beats_files(self):
        self.write(self.project, {"backend": "codex"})
        route = self.resolve(inline={"backend": "antigravity"})
        self.assertEqual((route["backend"], route["source"]), ("antigravity", "invocation"))

    def test_role_block_overrides_flat_fields(self):
        self.write(self.project, {"backend": "codex", "search": {"backend": "gemini"}})
        self.assertEqual(self.resolve()["backend"], "codex")
        self.assertEqual(self.resolve(role="search")["backend"], "gemini")

    def test_other_backends_model_is_not_inherited(self):
        self.write(self.project, {"backend": "codex", "model": "gpt-x", "effort": "high"})
        route = self.resolve(inline={"backend": "antigravity"})
        self.assertIsNone(route["model"])
        self.assertIsNone(route["effort"])

    def test_inline_model_applies_to_chosen_backend(self):
        self.write(self.project, {"backend": "codex", "model": "gpt-x"})
        self.assertEqual(self.resolve(inline={"model": "gpt-y"})["model"], "gpt-y")
        self.assertEqual(self.resolve()["model"], "gpt-x")

    def test_aliases(self):
        self.assertEqual(self.resolve(inline={"backend": "agy"})["backend"], "antigravity")


class TestAgentHud(Base):
    def test_suffix_and_via_field_agree(self):
        a = self.resolve(inline={"backend": "codex@agent-hud"})
        b = self.resolve(inline={"backend": "codex", "via": "agent-hud"})
        for route in (a, b):
            self.assertEqual(route["transport"], "agent-hud")
            self.assertEqual(route["tools"]["fresh"], "mcp__agent-hud__start_session")
            self.assertEqual(route["tools"]["client"], "codex")
            self.assertEqual(route["label"], "codex@agent-hud")

    def test_deepseek_defaults_to_agent_hud(self):
        route = self.resolve(inline={"backend": "deepseek"})
        self.assertEqual((route["via"], route["tools"]["client"]), ("agent-hud", "deepseek"))

    def test_deepseek_has_no_direct_bridge(self):
        with self.assertRaises(rr.ConfigError):
            self.resolve(inline={"backend": "deepseek", "via": "direct"})

    def test_gemini_cannot_go_through_agent_hud(self):
        with self.assertRaises(rr.ConfigError):
            self.resolve(inline={"backend": "gemini@agent-hud"})

    def test_failure_is_tracked_per_transport(self):
        self.write(self.project, {"backend": "codex", "fallback": ["codex@agent-hud"]})
        route = self.resolve(failed={("codex", "direct"): "tool_missing"})
        self.assertEqual(route["label"], "codex@agent-hud")


class TestFallback(Base):
    def test_no_fallback_means_unavailable(self):
        route = self.resolve(failed=rr.parse_failed(["gemini:billing_rejected"]))
        self.assertEqual(route["status"], "unavailable")

    def test_pre_dispatch_failure_moves_down_the_chain(self):
        self.write(self.project, {"fallback": ["codex@agent-hud", "manual"]})
        route = self.resolve(failed=rr.parse_failed(["gemini:region_unavailable"]))
        self.assertEqual((route["label"], route["source"]), ("codex@agent-hud", "fallback"))
        self.assertEqual(route["skipped"], [{"backend": "gemini", "reason": "region_unavailable"}])

    def test_post_dispatch_failure_never_switches(self):
        self.write(self.project, {"fallback": ["codex"]})
        for reason in ("timeout", "disconnected", "uncertain", "pass_limit"):
            with self.subTest(reason=reason):
                route = self.resolve(failed=rr.parse_failed([f"gemini:{reason}"]))
                self.assertEqual(route["status"], "unavailable")
                self.assertIn("may have run", route["message"])

    def test_missing_tool_is_skipped_when_tools_are_listed(self):
        self.write(self.project, {"fallback": ["codex@agent-hud"]})
        route = self.resolve(available=["mcp__agent-hud__start_session"])
        self.assertEqual(route["label"], "codex@agent-hud")
        self.assertEqual(route["skipped"][0]["reason"], "tool_missing")

    def test_tool_names_match_across_hyphens_and_dots(self):
        route = self.resolve(available=["mcp__gemini_review__review"])
        self.assertEqual(route["backend"], "gemini")

    def test_manual_needs_no_tool(self):
        self.write(self.project, {"backend": "manual"})
        self.assertEqual(self.resolve(available=[])["transport"], "manual")

    def test_unknown_failure_reason_is_rejected(self):
        with self.assertRaises(rr.ConfigError):
            rr.parse_failed(["gemini:it_broke"])


class TestIndependence(Base):
    def test_executor_family_is_refused_when_chosen(self):
        self.write(self.project, {"backend": "claude-code"})
        with self.assertRaises(rr.ConfigError):
            self.resolve()

    def test_same_family_allowed_only_on_request(self):
        self.write(self.project, {"backend": "claude-code"})
        route = self.resolve(allow_same_family=True)
        self.assertTrue(route["same_family_allowed"])

    def test_same_family_fallback_is_skipped(self):
        self.write(self.project, {"fallback": ["claude@agent-hud", "codex@agent-hud"]})
        route = self.resolve(failed=rr.parse_failed(["gemini:auth_rejected"]))
        self.assertEqual(route["label"], "codex@agent-hud")
        self.assertIn({"backend": "claude-code@agent-hud", "reason": "same_family_as_executor"},
                      route["skipped"])

    def test_codex_host_cannot_pick_codex(self):
        with self.assertRaises(rr.ConfigError):
            self.resolve(host="codex", inline={"backend": "codex"})

    def test_executor_model_overrides_host_family(self):
        # A Claude Code CLI pointed at another provider is not an Anthropic executor.
        self.write(self.project, {"backend": "claude-code"})
        route = self.resolve(executor_model="deepseek-v4")
        self.assertEqual(route["executor_family"], "deepseek")

    def test_model_named_family_beats_backend_family(self):
        # Antigravity can serve a Claude model; that is the executor's family.
        with self.assertRaises(rr.ConfigError):
            self.resolve(inline={"backend": "antigravity", "model": "claude-opus-x"})

    def test_independence_verdicts(self):
        self.assertEqual(rr.independence("claude-opus-5-5", "gpt-6.2-astra")["verdict"],
                         "independent")
        self.assertEqual(rr.independence("claude-opus-5-5", "sonnet")["verdict"], "same_family")
        self.assertFalse(rr.independence("claude-opus-5-5", None)["accepted"])


class TestSearchRole(Base):
    def test_claude_bridge_cannot_search(self):
        self.write(self.project, {"search": {"backend": "claude-code"}})
        with self.assertRaises(rr.ConfigError):
            self.resolve(role="search", host="codex")

    def test_conditional_search_is_reported(self):
        route = self.resolve(role="search", inline={"backend": "codex@agent-hud"})
        self.assertEqual(route["search_capability"], "needs_check")


class TestConfigErrors(Base):
    def test_unknown_field_is_rejected(self):
        self.write(self.project, {"backend": "codex", "reviewr": "x"})
        with self.assertRaises(rr.ConfigError):
            self.resolve()

    def test_unknown_backend_is_rejected(self):
        self.write(self.project, {"backend": "bard"})
        with self.assertRaises(rr.ConfigError):
            self.resolve()


class TestCli(Base):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)

    def test_resolve_prints_json_and_exit_codes(self):
        stage = self.tmp.name
        ok = self.run_cli("resolve", "--role", "review", "--host", "claude-code",
                          "--stage-dir", stage, "--no-user-config")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["backend"], "gemini")
        down = self.run_cli("resolve", "--role", "review", "--host", "claude-code",
                            "--stage-dir", stage, "--no-user-config",
                            "--failed", "gemini:timeout")
        self.assertEqual(down.returncode, 3)
        bad = self.run_cli("resolve", "--role", "review", "--host", "claude-code",
                           "--stage-dir", stage, "--no-user-config", "--backend", "bard")
        self.assertEqual(bad.returncode, 2)

    def test_user_config_honours_xdg(self):
        xdg = os.path.join(self.tmp.name, "xdg")
        os.makedirs(os.path.join(xdg, "molecule-design-loop"))
        self.write(os.path.join(xdg, "molecule-design-loop", "reviewer.json"),
                   {"backend": "codex@agent-hud"})
        proc = subprocess.run(
            [sys.executable, SCRIPT, "resolve", "--role", "review", "--host", "claude-code",
             "--stage-dir", self.tmp.name],
            capture_output=True, text=True, env={**os.environ, "XDG_CONFIG_HOME": xdg},
        )
        self.assertEqual(json.loads(proc.stdout)["label"], "codex@agent-hud")

    def test_show_reports_files_and_both_roles(self):
        stage = os.path.join(self.tmp.name, "stage")
        os.makedirs(stage)
        self.write(os.path.join(stage, "reviewer.json"),
                   {"review": {"backend": "codex@agent-hud"}})
        proc = self.run_cli("show", "--host", "claude-code", "--stage-dir", stage,
                            "--user-config", self.user)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["config_files"]["project"]["found"])
        self.assertFalse(report["config_files"]["user"]["found"])
        self.assertEqual(report["routes"]["review"]["label"], "codex@agent-hud")
        self.assertEqual(report["routes"]["search"]["label"], "gemini")
        self.assertIn("note", report)

    def test_show_exits_3_when_a_role_is_unreachable(self):
        proc = self.run_cli("show", "--host", "claude-code", "--stage-dir", self.tmp.name,
                            "--user-config", self.user, "--available", "")
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(json.loads(proc.stdout)["routes"]["review"]["status"], "unavailable")

    def test_show_reports_config_errors_per_role(self):
        self.write(self.user, {"backend": "claude-code"})
        proc = self.run_cli("show", "--host", "claude-code", "--stage-dir", self.tmp.name,
                            "--user-config", self.user)
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(json.loads(proc.stdout)["routes"]["review"]["status"], "config_error")

    def test_shipped_example_config_is_valid(self):
        example = os.path.join(os.path.dirname(os.path.dirname(HERE)), "examples",
                               "reviewer.example.json")
        if not os.path.exists(example):
            self.skipTest("examples/ not shipped with this install")
        route = rr.resolve("review", "claude-code", project_file=example)
        self.assertEqual(route["label"], "codex@agent-hud")

    def test_backends_table(self):
        table = json.loads(self.run_cli("backends").stdout)
        self.assertFalse(table["deepseek"]["direct"])
        self.assertEqual(table["codex"]["agent_hud_client"], "codex")


if __name__ == "__main__":
    unittest.main(verbosity=2)
