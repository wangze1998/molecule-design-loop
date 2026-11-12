#!/usr/bin/env python3
"""Tests for provenance.py. Run: python3 -m pytest test_provenance.py"""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "provenance.py")
sys.path.insert(0, HERE)
import provenance  # noqa: E402

SKILL_MD = '---\nname: "demo"\nmetadata:\n  version: "9.8.7"\n---\n# Demo\n'


def run(*args):
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args], capture_output=True, text=True
    )
    return proc.returncode, proc.stdout, proc.stderr


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class SkillFixture(unittest.TestCase):
    """A small fake skill: SKILL.md, a script, its test, a reference, a template."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.skill = os.path.join(self.root, "skill")
        write(os.path.join(self.skill, "SKILL.md"), SKILL_MD)
        write(os.path.join(self.skill, "scripts", "rank.py"), "THRESHOLD = 0.5\n")
        write(os.path.join(self.skill, "scripts", "test_rank.py"), "# test\n")
        write(os.path.join(self.skill, "references", "protocol.md"), "# rules\n")
        write(os.path.join(self.skill, "templates", "form.md"), "# form\n")
        write(os.path.join(self.skill, "scripts", "__pycache__", "rank.cpython.pyc"), "x")
        self.spec = os.path.join(self.root, "DESIGN_SPEC_LOCKED.md")
        write(self.spec, "MW <= 500\n")
        self.snap = os.path.join(self.root, "ROUND_1_PROVENANCE.json")

    def tearDown(self):
        for root, dirs, names in os.walk(self.root):
            for name in dirs + names:
                path = os.path.join(root, name)
                os.chmod(path, os.stat(path).st_mode | stat.S_IWUSR)
        self.tmp.cleanup()

    def snapshot(self, *extra, out=None):
        return run("snapshot", "--skill-dir", self.skill, "--spec", self.spec,
                   "--out", out or self.snap, *extra)

    def verify(self, *extra):
        return run("verify", "--skill-dir", self.skill, "--against", self.snap, *extra)


class TestSnapshot(SkillFixture):
    def test_records_skill_files_but_not_tests_or_caches(self):
        code, out, _ = self.snapshot("--round", "1")
        self.assertEqual(code, 0, out)
        data = json.load(open(self.snap))
        self.assertEqual(
            sorted(data["files"]),
            ["SKILL.md", "references/protocol.md", "scripts/rank.py", "templates/form.md"],
        )
        self.assertEqual(data["round"], 1)
        self.assertEqual(data["skill_version"], "9.8.7")
        self.assertEqual(data["spec"]["name"], "DESIGN_SPEC_LOCKED.md")

    def test_hashes_are_deterministic(self):
        self.snapshot()
        second = os.path.join(self.root, "again.json")
        self.snapshot(out=second)
        first, again = json.load(open(self.snap)), json.load(open(second))
        self.assertEqual(first["files"], again["files"])
        self.assertEqual(first["spec"], again["spec"])

    def test_prints_its_own_sha256(self):
        _, out, _ = self.snapshot()
        printed = [l.split()[-1] for l in out.splitlines() if l.startswith("snapshot_sha256:")]
        with open(self.snap, "rb") as handle:
            self.assertEqual(printed, [hashlib.sha256(handle.read()).hexdigest()])

    def test_notes_are_recorded(self):
        self.snapshot("--note", "claude_model=a", "--note", "gemini_model=b")
        self.assertEqual(json.load(open(self.snap))["notes"],
                         {"claude_model": "a", "gemini_model": "b"})

    def test_malformed_note_is_rejected(self):
        code, _, err = self.snapshot("--note", "no-equals-sign")
        self.assertEqual(code, 2)
        self.assertIn("key=value", err)

    def test_folder_without_skill_md_is_rejected(self):
        code, _, err = run("snapshot", "--skill-dir", self.root, "--out", self.snap)
        self.assertEqual(code, 2)
        self.assertIn("SKILL.md", err)


class TestVerify(SkillFixture):
    def setUp(self):
        super().setUp()
        code, out, _ = self.snapshot()
        self.assertEqual(code, 0, out)
        self.pinned = [l.split()[-1] for l in out.splitlines()
                       if l.startswith("snapshot_sha256:")][0]

    def test_unchanged_tree_passes(self):
        code, out, _ = self.verify("--spec", self.spec, "--expect-sha256", self.pinned)
        self.assertEqual(code, 0, out)
        self.assertIn("OK: 4 skill files unchanged", out)
        self.assertIn("spec: unchanged", out)

    def test_a_one_byte_edit_to_a_script_is_named(self):
        write(os.path.join(self.skill, "scripts", "rank.py"), "THRESHOLD = 0.6\n")
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("modified: scripts/rank.py", out)
        self.assertIn("Stop the round", out)

    def test_added_and_removed_files_are_named(self):
        write(os.path.join(self.skill, "references", "looser.md"), "# new\n")
        os.remove(os.path.join(self.skill, "templates", "form.md"))
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("added: references/looser.md", out)
        self.assertIn("removed: templates/form.md", out)

    def test_editing_a_test_file_is_not_drift(self):
        write(os.path.join(self.skill, "scripts", "test_rank.py"), "# changed\n")
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)

    def test_spec_change_alone_has_its_own_exit_code(self):
        write(self.spec, "MW <= 650\n")
        code, out, _ = self.verify("--spec", self.spec)
        self.assertEqual(code, 3)
        self.assertIn("spec: CHANGED", out)

    def test_skill_drift_outranks_spec_drift(self):
        write(self.spec, "MW <= 650\n")
        write(os.path.join(self.skill, "SKILL.md"), SKILL_MD + "extra\n")
        code, _, _ = self.verify("--spec", self.spec)
        self.assertEqual(code, 1)

    def test_an_edited_snapshot_is_refused_when_pinned(self):
        data = json.load(open(self.snap))
        data["files"]["scripts/rank.py"] = "0" * 64
        with open(self.snap, "w") as handle:
            json.dump(data, handle)
        code, _, err = self.verify("--expect-sha256", self.pinned)
        self.assertEqual(code, 2)
        self.assertIn("not the snapshot that was pinned", err)

    def test_missing_or_corrupt_snapshot_fails_loudly(self):
        code, _, err = run("verify", "--skill-dir", self.skill,
                           "--against", os.path.join(self.root, "nope.json"))
        self.assertEqual(code, 2)
        self.assertIn("not found", err)
        with open(self.snap, "w") as handle:
            handle.write("{not json")
        code, _, err = self.verify()
        self.assertEqual(code, 2)
        self.assertIn("not valid JSON", err)

    def test_snapshot_without_files_or_with_bad_hashes_is_refused(self):
        for files in ({}, {"SKILL.md": "abc"}):
            data = json.load(open(self.snap))
            data["files"] = files
            with open(self.snap, "w") as handle:
                json.dump(data, handle)
            with self.subTest(files=files):
                code, _, _ = self.verify()
                self.assertEqual(code, 2)

    def test_writable_files_get_a_note_and_read_only_ones_do_not(self):
        _, out, _ = self.verify()
        self.assertIn("does not prevent them", out)
        for root, _, names in os.walk(self.skill):
            for name in names:
                path = os.path.join(root, name)
                os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        _, out, _ = self.verify()
        self.assertNotIn("does not prevent them", out)
        self.assertTrue(provenance.write_protected(self.skill))


class TestDiff(SkillFixture):
    def test_identical_snapshots(self):
        self.snapshot()
        code, out, _ = run("diff", self.snap, self.snap)
        self.assertEqual(code, 0)
        self.assertIn("identical", out)

    def test_names_the_changes_between_rounds(self):
        self.snapshot("--note", "claude_model=a")
        write(os.path.join(self.skill, "scripts", "rank.py"), "THRESHOLD = 0.6\n")
        write(os.path.join(self.skill, "SKILL.md"), SKILL_MD.replace("9.8.7", "9.8.8"))
        write(self.spec, "MW <= 650\n")
        second = os.path.join(self.root, "ROUND_2_PROVENANCE.json")
        self.snapshot("--note", "claude_model=b", out=second)
        code, out, _ = run("diff", self.snap, second)
        self.assertEqual(code, 1)
        for expected in ("skill_version: 9.8.7 -> 9.8.8", "modified: scripts/rank.py",
                         "modified: SKILL.md", "spec: changed", "notes.claude_model: a -> b"):
            self.assertIn(expected, out)


class TestGitCommit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.skill = os.path.join(self.repo, "skill")
        os.makedirs(self.skill)
        self.sha = "a" * 40

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_repository(self):
        self.assertIsNone(provenance.git_commit(self.skill))

    def test_loose_ref(self):
        write(os.path.join(self.repo, ".git", "HEAD"), "ref: refs/heads/main\n")
        write(os.path.join(self.repo, ".git", "refs", "heads", "main"), self.sha + "\n")
        self.assertEqual(provenance.git_commit(self.skill), self.sha)

    def test_packed_ref(self):
        write(os.path.join(self.repo, ".git", "HEAD"), "ref: refs/heads/main\n")
        write(os.path.join(self.repo, ".git", "packed-refs"),
              f"# pack-refs with: peeled\n{self.sha} refs/heads/main\n")
        self.assertEqual(provenance.git_commit(self.skill), self.sha)

    def test_detached_head(self):
        write(os.path.join(self.repo, ".git", "HEAD"), self.sha + "\n")
        self.assertEqual(provenance.git_commit(self.skill), self.sha)


if __name__ == "__main__":
    unittest.main(verbosity=2)
