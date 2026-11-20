#!/usr/bin/env python3
"""Record and check which version of this skill a design round actually ran on.

Why this exists
---------------
During a run the agent has write access to the skill's own files. Nothing stops it
from loosening a filter threshold, editing the dominance code in
`ranking_diagnostics.py`, or softening a protocol in `references/` part-way through a
round, and the test suite only catches that when someone runs it. Self-driving labs
handle the same risk by separating the agent that runs experiments from the code it
runs on, with a human approving every change. This script is the design-loop
equivalent of that separation: it cannot stop an edit, but it makes one visible at the
checkpoints where a human is looking, and it records exactly which code, protocols
and spec produced each round so the result can be reproduced.

Modes
-----
  snapshot : hash every skill file (tests and caches excluded), the locked spec, and
             the environment into ROUND_N_PROVENANCE.json. Prints the snapshot's own
             SHA-256 so the state file can pin it.
  verify   : re-hash and compare against a snapshot. Names every file that was
             modified, added or removed.
  diff     : compare two snapshots, e.g. round 1 vs round 2 after an accepted change.

Exit codes
----------
  0  unchanged
  1  skill files changed (verify) or snapshots differ (diff)
  2  usage error, or a snapshot that is missing, corrupt or not the one pinned
  3  verify only: skill files unchanged but the locked spec changed

Usage
-----
  provenance.py snapshot --skill-dir SKILL --spec DESIGN_SPEC_LOCKED.md --round 2 \\
      --note claude_model=... --note reviewer=codex@agent-hud:<model> --out ROUND_2_PROVENANCE.json
  provenance.py verify --skill-dir SKILL --against ROUND_2_PROVENANCE.json \\
      --spec DESIGN_SPEC_LOCKED.md --expect-sha256 <printed by snapshot>
  provenance.py diff ROUND_1_PROVENANCE.json ROUND_2_PROVENANCE.json

stdlib only.
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import stat
import sys

PROVENANCE_VERSION = "1"

# Never part of the skill's behaviour: test files change how the skill is checked,
# not how a round runs, and caches are regenerated.
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}
SKIP_SUFFIXES = (".pyc", ".pyo")

EXIT_OK, EXIT_DRIFT, EXIT_BAD_INPUT, EXIT_SPEC_DRIFT = 0, 1, 2, 3

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class ProvenanceError(Exception):
    """A snapshot or argument this script cannot trust."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def is_skill_file(rel_path):
    parts = rel_path.split("/")
    name = parts[-1]
    if any(p in SKIP_DIRS or p.startswith(".") for p in parts):
        return False
    if name.endswith(SKIP_SUFFIXES):
        return False
    if parts[0] == "scripts" and name.startswith("test_") and name.endswith(".py"):
        return False
    return True


def skill_files(skill_dir):
    """Relative POSIX path → absolute path, for every file that shapes a run."""
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        raise ProvenanceError(f"{skill_dir} has no SKILL.md; pass the skill folder itself")
    found = {}
    for root, dirs, names in os.walk(skill_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(names):
            path = os.path.join(root, name)
            rel = os.path.relpath(path, skill_dir).replace(os.sep, "/")
            if is_skill_file(rel):
                found[rel] = path
    return found


def hash_skill(skill_dir):
    return {rel: sha256_file(path) for rel, path in sorted(skill_files(skill_dir).items())}


def write_protected(skill_dir):
    """True when no skill file carries a write bit for anyone.

    Mode bits, not os.access: os.access reports every file writable to root, which
    would make a read-only install look unprotected inside a container.
    """
    for path in skill_files(skill_dir).values():
        if os.stat(path).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            return False
    return True


def skill_version(skill_dir):
    with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(r'(?m)^\s*version:\s*"([^"]+)"', text)
    return match.group(1) if match else "unknown"


def git_commit(start_dir):
    """The checked-out commit when the skill runs from a git clone, else None.

    Reads .git directly rather than shelling out. Informational only: the file
    hashes are the record, because an installed copy has no .git at all.
    """
    current = os.path.abspath(start_dir)
    while True:
        dot_git = os.path.join(current, ".git")
        if os.path.exists(dot_git):
            break
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
    try:
        if os.path.isfile(dot_git):  # worktree or submodule: "gitdir: <path>"
            with open(dot_git, encoding="utf-8") as handle:
                pointer = handle.read().strip()
            if not pointer.startswith("gitdir:"):
                return None
            dot_git = os.path.normpath(os.path.join(current, pointer[len("gitdir:"):].strip()))
        with open(os.path.join(dot_git, "HEAD"), encoding="utf-8") as handle:
            head = handle.read().strip()
        if not head.startswith("ref:"):
            return head if HEX40.match(head) else None
        ref = head[len("ref:"):].strip()
        for git_dir in (dot_git, common_dir(dot_git)):
            loose = os.path.join(git_dir, *ref.split("/"))
            if os.path.isfile(loose):
                with open(loose, encoding="utf-8") as handle:
                    value = handle.read().strip()
                return value if HEX40.match(value) else None
            packed = os.path.join(git_dir, "packed-refs")
            if os.path.isfile(packed):
                with open(packed, encoding="utf-8") as handle:
                    for line in handle:
                        fields = line.split()
                        if len(fields) == 2 and fields[1] == ref and HEX40.match(fields[0]):
                            return fields[0]
    except OSError:
        return None
    return None



def common_dir(git_dir):
    """Worktrees keep branch refs in the main repository's git dir."""
    pointer = os.path.join(git_dir, "commondir")
    if os.path.isfile(pointer):
        with open(pointer, encoding="utf-8") as handle:
            return os.path.normpath(os.path.join(git_dir, handle.read().strip()))
    return git_dir


def environment():
    env = {"python": platform.python_version(), "rdkit": None}
    try:
        from importlib import metadata

        env["rdkit"] = metadata.version("rdkit")
    except Exception:  # not installed, or installed without metadata
        pass
    return env


def parse_notes(pairs):
    notes = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip():
            raise ProvenanceError(f"--note expects key=value, got {pair!r}")
        notes[key.strip()] = value.strip()
    return notes


def build_snapshot(skill_dir, spec=None, round_number=None, notes=None, now=None):
    files = hash_skill(skill_dir)
    if spec is not None and not os.path.isfile(spec):
        raise ProvenanceError(f"spec not found: {spec}")
    created = now or datetime.datetime.now(datetime.timezone.utc)
    return {
        "provenance_version": PROVENANCE_VERSION,
        "round": round_number,
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skill_version": skill_version(skill_dir),
        "git_commit": git_commit(skill_dir),
        "write_protected": write_protected(skill_dir),
        "file_count": len(files),
        "files": files,
        "spec": None if spec is None else {
            "name": os.path.basename(spec),
            "sha256": sha256_file(spec),
        },
        "environment": environment(),
        "notes": notes or {},
    }


def dump(snapshot):
    """Canonical bytes: sorted keys, fixed separators, trailing newline."""
    return (json.dumps(snapshot, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_snapshot(path, expect_sha256=None):
    if not os.path.isfile(path):
        raise ProvenanceError(f"snapshot not found: {path}")
    if expect_sha256 is not None:
        actual = sha256_file(path)
        if actual != expect_sha256.lower():
            raise ProvenanceError(
                f"{path} is not the snapshot that was pinned: sha256 {actual} != "
                f"{expect_sha256}. The snapshot itself was edited or replaced."
            )
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, UnicodeDecodeError) as error:
        raise ProvenanceError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ProvenanceError(f"{path} is not a snapshot object")
    missing = [k for k in ("provenance_version", "skill_version", "files") if k not in data]
    if missing:
        raise ProvenanceError(f"{path} is missing {', '.join(missing)}")
    if data["provenance_version"] != PROVENANCE_VERSION:
        raise ProvenanceError(
            f"{path} has provenance_version {data['provenance_version']!r}; "
            f"this script reads {PROVENANCE_VERSION!r}"
        )
    files = data["files"]
    if not isinstance(files, dict) or not files:
        raise ProvenanceError(f"{path} lists no files")
    bad = [k for k, v in files.items() if not isinstance(v, str) or not HEX64.match(v)]
    if bad:
        raise ProvenanceError(f"{path} has malformed hashes for: {', '.join(sorted(bad)[:5])}")
    return data


def compare_files(old, new):
    modified = sorted(k for k in old if k in new and old[k] != new[k])
    removed = sorted(k for k in old if k not in new)
    added = sorted(k for k in new if k not in old)
    return modified, added, removed


def spec_hash(snapshot):
    spec = snapshot.get("spec")
    return spec.get("sha256") if isinstance(spec, dict) else None


def cmd_snapshot(args):
    snapshot = build_snapshot(
        args.skill_dir, spec=args.spec, round_number=args.round, notes=parse_notes(args.note)
    )
    payload = dump(snapshot)
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "wb") as handle:
        handle.write(payload)
    print(f"snapshot: {args.out}")
    print(f"skill_version: {snapshot['skill_version']}  files: {snapshot['file_count']}  "
          f"write_protected: {str(snapshot['write_protected']).lower()}")
    print(f"snapshot_sha256: {hashlib.sha256(payload).hexdigest()}")
    return EXIT_OK


def cmd_verify(args):
    recorded = load_snapshot(args.against, args.expect_sha256)
    current = hash_skill(args.skill_dir)
    modified, added, removed = compare_files(recorded["files"], current)
    drift = bool(modified or added or removed)

    spec_note = None
    spec_drift = False
    if args.spec is not None:
        if not os.path.isfile(args.spec):
            raise ProvenanceError(f"spec not found: {args.spec}")
        before = spec_hash(recorded)
        if before is None:
            spec_note = "spec: not recorded in the snapshot, not checked"
        elif sha256_file(args.spec) != before:
            spec_drift = True
            spec_note = (
                "spec: CHANGED since the snapshot. The spec is the user's; continue only "
                "if the user approved the change and it is recorded in DESIGN_LOOP_STATE.json"
            )
        else:
            spec_note = "spec: unchanged"

    if drift:
        print(f"DRIFT: skill files differ from {args.against} "
              f"(recorded v{recorded['skill_version']})")
        for label, names in (("modified", modified), ("added", added), ("removed", removed)):
            for name in names:
                print(f"  {label}: {name}")
        print("Stop the round. Restore the files, or record an accepted change request "
              "and take a new snapshot. See references/run-integrity-protocol.md.")
    else:
        print(f"OK: {len(current)} skill files unchanged since {args.against} "
              f"(v{recorded['skill_version']})")
    if spec_note:
        print(spec_note)
    if not write_protected(args.skill_dir):
        print("note: skill files are writable; this check detects edits, it does not "
              "prevent them")

    if drift:
        return EXIT_DRIFT
    return EXIT_SPEC_DRIFT if spec_drift else EXIT_OK


def cmd_diff(args):
    old = load_snapshot(args.old)
    new = load_snapshot(args.new)
    lines = []
    if old["skill_version"] != new["skill_version"]:
        lines.append(f"skill_version: {old['skill_version']} -> {new['skill_version']}")
    if old.get("git_commit") != new.get("git_commit"):
        lines.append(f"git_commit: {old.get('git_commit')} -> {new.get('git_commit')}")
    modified, added, removed = compare_files(old["files"], new["files"])
    for label, names in (("modified", modified), ("added", added), ("removed", removed)):
        lines.extend(f"{label}: {name}" for name in names)
    if spec_hash(old) != spec_hash(new):
        lines.append("spec: changed")
    for section in ("environment", "notes"):
        before, after = old.get(section) or {}, new.get(section) or {}
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                lines.append(f"{section}.{key}: {before.get(key)} -> {after.get(key)}")
    if not lines:
        print("identical: same skill files, spec, environment and notes")
        return EXIT_OK
    print("\n".join(lines))
    return EXIT_DRIFT


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    snap = sub.add_parser("snapshot", help="record the skill files, spec and environment")
    snap.add_argument("--skill-dir", required=True, help="the folder holding SKILL.md")
    snap.add_argument("--spec", help="DESIGN_SPEC_LOCKED.md for this run")
    snap.add_argument("--round", type=int, help="round number this snapshot opens")
    snap.add_argument("--note", action="append", metavar="KEY=VALUE",
                      help="free metadata, e.g. model names; repeatable")
    snap.add_argument("--out", required=True, help="ROUND_N_PROVENANCE.json")
    snap.set_defaults(func=cmd_snapshot)

    ver = sub.add_parser("verify", help="check the skill files against a snapshot")
    ver.add_argument("--skill-dir", required=True)
    ver.add_argument("--against", required=True, help="the round's snapshot file")
    ver.add_argument("--spec", help="also check the locked spec")
    ver.add_argument("--expect-sha256",
                     help="the snapshot_sha256 printed at snapshot time; refuses a "
                          "snapshot that was edited afterwards")
    ver.set_defaults(func=cmd_verify)

    dif = sub.add_parser("diff", help="compare two snapshots")
    dif.add_argument("old")
    dif.add_argument("new")
    dif.set_defaults(func=cmd_diff)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ProvenanceError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())
