#!/usr/bin/env python3
"""Repo contract: the checks that keep this skill cheap to load and safe to publish.

SKILL.md is read in full every time the skill loads, so its size is a running cost
rather than a one-off. These tests fail if it grows back, if a pointer breaks, or if
a local path or secret reaches a public repository.
"""
import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(SKILL_DIR)
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")

# The spec recommends a SKILL.md body under ~5000 tokens; 350 lines leaves headroom
# for a step or two without inviting the 450-line version back.
MAX_SKILL_LINES = 350
MAX_DESCRIPTION_CHARS = 1024
MAX_REFERENCE_BYTES = 20_000

PRIVATE_PATTERNS = [
    (r"/Users/[A-Za-z0-9_-]+", "a macOS home directory"),
    (r"/home/[A-Za-z0-9_-]+/", "a Linux home directory"),
    (r"[A-Za-z]:\\Users\\[A-Za-z0-9_-]+", "a Windows home directory"),
    (r"sk-(?:ant-)?[A-Za-z0-9_-]{20,}", "an API key"),
    (r"AIza[0-9A-Za-z_-]{30,}", "a Google API key"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "a GitHub token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
]


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def tracked_text_files():
    """Text files in the skill folder, plus the repo's top-level Markdown."""
    for root, dirs, names in os.walk(SKILL_DIR):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".pytest_cache"}]
        for name in names:
            if name.endswith((".md", ".py", ".yaml", ".yml", ".txt")):
                yield os.path.join(root, name)
    for name in os.listdir(REPO):
        if name.endswith(".md"):
            yield os.path.join(REPO, name)


class TestSkillMd(unittest.TestCase):
    def test_stays_under_the_line_budget(self):
        lines = read(SKILL_MD).splitlines()
        self.assertLessEqual(
            len(lines),
            MAX_SKILL_LINES,
            f"SKILL.md is {len(lines)} lines. Move detail into references/ rather than "
            "raising this limit; it is loaded in full on every run.",
        )

    def test_frontmatter_has_name_and_description(self):
        text = read(SKILL_MD)
        self.assertTrue(text.startswith("---\n"), "SKILL.md must open with YAML frontmatter")
        block = text.split("---", 2)[1]
        self.assertRegex(block, r"(?m)^name:", "frontmatter needs a name")
        self.assertRegex(block, r"(?m)^description:", "frontmatter needs a description")

    def test_description_fits_and_carries_triggers(self):
        match = re.search(r'description: "(.*?)"\n', read(SKILL_MD), re.S)
        self.assertIsNotNone(match, "description must be a double-quoted string")
        description = match.group(1)
        self.assertLessEqual(len(description), MAX_DESCRIPTION_CHARS)
        # The description is the only text the model sees before deciding to load the
        # skill, so it has to say when to use it, not just what it is.
        self.assertIn("Use when", description)

    def test_every_relative_link_resolves(self):
        broken = [
            target
            for target in re.findall(r"\]\(([^)]+)\)", read(SKILL_MD))
            if not target.startswith(("http://", "https://", "#"))
            and not os.path.exists(os.path.join(SKILL_DIR, target))
        ]
        self.assertEqual(broken, [], f"SKILL.md points at missing files: {broken}")

    def test_every_reference_is_reachable(self):
        text = read(SKILL_MD)
        linked = {
            os.path.basename(t) for t in re.findall(r"\]\((references/[^)]+)\)", text)
        }
        on_disk = {
            n for n in os.listdir(os.path.join(SKILL_DIR, "references")) if n.endswith(".md")
        }
        orphans = sorted(on_disk - linked)
        self.assertEqual(
            orphans, [], f"references nothing points to (dead weight or a missing step): {orphans}"
        )

    def test_every_script_is_named(self):
        text = read(SKILL_MD)
        scripts = {
            n
            for n in os.listdir(os.path.join(SKILL_DIR, "scripts"))
            if n.endswith(".py") and not n.startswith("test_")
        }
        missing = sorted(s for s in scripts if s not in text)
        self.assertEqual(missing, [], f"scripts SKILL.md never mentions: {missing}")


class TestReferences(unittest.TestCase):
    def test_references_stay_one_level_deep(self):
        root = os.path.join(SKILL_DIR, "references")
        nested = [n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))]
        self.assertEqual(nested, [], "keep references/ flat so a pointer is one hop")

    def test_long_references_have_a_table_of_contents(self):
        root = os.path.join(SKILL_DIR, "references")
        for name in sorted(os.listdir(root)):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            text = read(path)
            if len(text.splitlines()) <= 300:
                continue
            with self.subTest(reference=name):
                self.assertTrue(
                    re.search(r"(?mi)^#{2,3} (contents|table of contents)", text)
                    or len(re.findall(r"(?m)^#{2,3} ", text)) >= 5,
                    f"{name} is long; give it section headings or a contents list",
                )

    def test_no_reference_is_oversized(self):
        root = os.path.join(SKILL_DIR, "references")
        oversized = {
            n: os.path.getsize(os.path.join(root, n))
            for n in os.listdir(root)
            if n.endswith(".md") and os.path.getsize(os.path.join(root, n)) > MAX_REFERENCE_BYTES
        }
        self.assertEqual(oversized, {}, f"split these references: {oversized}")


class TestScripts(unittest.TestCase):
    def script_paths(self):
        """Every script but this one, which holds the forbidden names as literals."""
        root = os.path.join(SKILL_DIR, "scripts")
        this_file = os.path.basename(__file__)
        return [
            os.path.join(root, n)
            for n in sorted(os.listdir(root))
            if n.endswith(".py") and n != this_file
        ]

    def test_all_scripts_parse(self):
        for path in self.script_paths():
            with self.subTest(script=os.path.basename(path)):
                ast.parse(read(path))

    def test_scripts_have_module_docstrings(self):
        for path in self.script_paths():
            with self.subTest(script=os.path.basename(path)):
                self.assertTrue(
                    ast.get_docstring(ast.parse(read(path))),
                    "say what the script is for and why it exists",
                )

    def test_no_shell_out_to_eval_or_system(self):
        for path in self.script_paths():
            with self.subTest(script=os.path.basename(path)):
                tree = ast.parse(read(path))
                called = {
                    node.func.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                }
                self.assertEqual(called & {"eval", "exec"}, set())
                self.assertNotIn("os.system", read(path))

    def test_every_non_test_script_has_tests(self):
        root = os.path.join(SKILL_DIR, "scripts")
        names = {n for n in os.listdir(root) if n.endswith(".py")}
        untested = sorted(
            n for n in names if not n.startswith("test_") and f"test_{n}" not in names
        )
        self.assertEqual(untested, [], f"scripts without a test file: {untested}")


class TestPublicRepoHygiene(unittest.TestCase):
    def test_no_local_paths_or_secrets(self):
        this_file = os.path.abspath(__file__)
        for path in tracked_text_files():
            if os.path.abspath(path) == this_file:
                continue  # holds the patterns themselves
            text = read(path)
            for pattern, label in PRIVATE_PATTERNS:
                with self.subTest(file=os.path.relpath(path, REPO), looking_for=label):
                    found = re.search(pattern, text)
                    self.assertIsNone(
                        found,
                        f"{os.path.relpath(path, REPO)} contains {label}: "
                        f"{found.group(0)[:40] if found else ''}",
                    )


class TestRunIntegrity(unittest.TestCase):
    """The checks that keep a run from editing the rules it is judged by. These guard
    the guard: removing a verify checkpoint or the change-request route fails here."""

    def workflow_row(self, step):
        for line in read(SKILL_MD).splitlines():
            if line.startswith(f"| {step} |"):
                return line
        self.fail(f"SKILL.md workflow table has no row for Step {step}")

    def test_round_opens_with_a_snapshot(self):
        self.assertIn("provenance.py snapshot", self.workflow_row("3"))

    def test_verify_runs_at_approval_scoring_and_write_back(self):
        for step in ("7", "11", "12"):
            with self.subTest(step=step):
                self.assertIn("provenance.py verify", self.workflow_row(step))

    def test_skill_md_freezes_the_skill_and_names_the_change_route(self):
        text = read(SKILL_MD)
        self.assertIn("The skill is read-only during a run", text)
        self.assertIn("templates/change_request_template.md", text)
        self.assertIn("ROUND_N_CHANGE_REQUEST.md", text)
        self.assertIn("ROUND_N_PROVENANCE.json", text)

    def test_change_request_template_has_every_section(self):
        text = read(os.path.join(SKILL_DIR, "templates", "change_request_template.md"))
        for heading in ("## What to change", "## Why", "## Evidence", "## Invariant touched",
                        "## Effect on this round", "## Proposed test", "## Decision (user)"):
            with self.subTest(heading=heading):
                self.assertIn(heading, text)
        # The question that exposes a rule change made to rescue a candidate.
        self.assertIn("move into the top 3", text)

    def test_state_schema_documents_both_records(self):
        text = read(os.path.join(SKILL_DIR, "references", "design-loop-state-schema.md"))
        for key in ("provenance", "change_requests"):
            with self.subTest(key=key):
                self.assertIn(f"- `{key}`:", text)
                self.assertIn(f"### `{key}[]`", text)
        example = json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))
        self.assertIn("provenance", example)
        self.assertIn("change_requests", example)

    def test_read_only_install_leaves_no_write_bits(self):
        if not (shutil.which("bash") and shutil.which("rsync")):
            self.skipTest("installer needs bash and rsync")
        with tempfile.TemporaryDirectory() as home:
            try:
                proc = subprocess.run(
                    ["bash", os.path.join(REPO, "install_molecule_design_loop.sh"), "--read-only"],
                    env={**os.environ, "CODEX_HOME": home},
                    capture_output=True, text=True,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                installed = os.path.join(home, "skills", "molecule-design-loop")
                writable = [
                    os.path.relpath(os.path.join(root, name), installed)
                    for root, dirs, names in os.walk(installed)
                    for name in dirs + names
                    if os.stat(os.path.join(root, name)).st_mode & 0o222
                ]
                self.assertEqual(writable, [], "read-only install left writable files")
            finally:
                for root, dirs, names in os.walk(home):
                    for name in dirs + names:
                        path = os.path.join(root, name)
                        os.chmod(path, os.stat(path).st_mode | 0o200)

    def test_installer_rejects_unknown_options(self):
        if not shutil.which("bash"):
            self.skipTest("installer needs bash")
        proc = subprocess.run(
            ["bash", os.path.join(REPO, "install_molecule_design_loop.sh"), "--no-such-flag"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--read-only", proc.stderr)


class TestReviewerSelection(unittest.TestCase):
    """A review step wired to one provider either stops the loop or gets switched
    without a record. These keep the selection step, its record and its rules."""

    def test_step_zero_resolves_the_route(self):
        rows = [l for l in read(SKILL_MD).splitlines() if l.startswith("| 0 |")]
        self.assertTrue(rows, "SKILL.md workflow table has no Step 0")
        self.assertIn("reviewer_route.py resolve", rows[0])

    def test_review_protocols_dispatch_through_the_route(self):
        root = os.path.join(SKILL_DIR, "references")
        for name in ("adversarial-review-protocol.md", "claim-audit-protocol.md",
                     "gemini-scoring-protocol.md", "novelty-check-protocol.md",
                     "active-search-protocol.md"):
            with self.subTest(reference=name):
                self.assertIn("reviewer-selection-protocol.md", read(os.path.join(root, name)))

    def test_selection_protocol_keeps_its_safety_rules(self):
        text = read(os.path.join(SKILL_DIR, "references", "reviewer-selection-protocol.md"))
        for phrase in ("Never the executor's family", "REVIEW_UNAVAILABLE",
                       "The reviewer's last answer is the record", "Step 11 has no rebuttal",
                       "Save the raw reply first", "mcp__agent-hud__start_session"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_state_schema_records_routes(self):
        text = read(os.path.join(SKILL_DIR, "references", "design-loop-state-schema.md"))
        self.assertIn("- `reviewer_routes`:", text)
        self.assertIn("### `reviewer_routes[]`", text)
        example = json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))
        self.assertIn("reviewer_routes", example)


class TestVersionsAgree(unittest.TestCase):
    """The README is the repo's front page; a release that bumps SKILL.md but not the
    README leaves visitors reading an old version number (v0.4.0 shipped that way)."""

    def skill_version(self):
        match = re.search(r'(?m)^\s*version:\s*"([0-9][^"]*)"', read(SKILL_MD))
        self.assertIsNotNone(match, "SKILL.md frontmatter needs version: \"x.y.z\"")
        return match.group(1)

    def test_readmes_and_changelogs_name_the_skill_version(self):
        version = self.skill_version()
        checks = {
            "README.md": [r"badge/status-v([0-9.]+)-", r"\*\*Current release: v([0-9.]+)\*\*",
                          r"- Current release: `v([0-9.]+)`"],
            "README.zh-CN.md": [r"badge/status-v([0-9.]+)-", r"\*\*当前版本：v([0-9.]+)\*\*",
                                r"- 当前发布：`v([0-9.]+)`"],
            "CHANGELOG.md": [r"(?m)^## v([0-9.]+)"],
            "CHANGELOG.zh-CN.md": [r"(?m)^## v([0-9.]+)"],
        }
        for name, patterns in checks.items():
            text = read(os.path.join(REPO, name))
            for pattern in patterns:
                match = re.search(pattern, text)
                self.assertIsNotNone(match, f"{name}: no version found for {pattern!r}")
                self.assertEqual(
                    match.group(1).rstrip("."),
                    version,
                    f"{name} says v{match.group(1)} but SKILL.md is {version}; "
                    "update it in the same release commit",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
