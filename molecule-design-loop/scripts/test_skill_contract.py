#!/usr/bin/env python3
"""Repo contract: the checks that keep this skill cheap to load and safe to publish.

SKILL.md is read in full every time the skill loads, so its size is a running cost
rather than a one-off. These tests fail if it grows back, if a pointer breaks, or if
a local path or secret reaches a public repository.
"""
import ast
import os
import re
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
