# Run Integrity Protocol

How a design round keeps the skill it runs on fixed, and how a needed change to the
skill gets made without the round making it for itself.

## Contents

- Why this exists
- What is frozen and what is the user's
- Change requests
- Provenance: snapshot and verify
- When verify fails
- What goes into the state file and the report
- Limits, and the read-only install

## Why this exists

An agent running a round has write access to the skill's own files. A filter
threshold, the dominance code, or a protocol rule can be loosened part-way through a
round, and a candidate that would have failed then passes. The test suite catches
this only when someone runs it, which is not during a round.

Self-driving labs face the same risk and answer it by separation: the agent that runs
experiments cannot touch the code it runs on; it asks for a feature, and a human
approves it before anyone builds it. This protocol applies that separation to the
design loop. The rules that judge a candidate are not editable by the process being
judged.

## What is frozen and what is the user's

| Thing | Owner | During a run |
|---|---|---|
| `SKILL.md`, `scripts/`, `references/`, `templates/` | the skill maintainer | **read-only** — raise a change request |
| `DESIGN_SPEC_LOCKED.md` (constraints, objectives, limits) | the user | changeable only with the user's explicit approval, recorded in `DESIGN_LOOP_STATE.json` `notes` |
| Round artifacts (`ROUND_N_*`) | the run | written by the steps that own them |

The distinction matters. Widening a project's MW limit is a scientific decision the
user is entitled to make. Changing how dominance is computed changes the rules every
project is judged by, and goes through the maintainer's normal workflow: a branch,
tests, a reviewed merge and a version bump.

## Change requests

When a script looks wrong or a threshold looks miscalibrated:

1. Do **not** edit the file.
2. Copy [`templates/change_request_template.md`](../templates/change_request_template.md)
   to `ROUND_N_CHANGE_REQUEST.md` (one file per round; several requests may share it,
   each with its own `cr_rN_XX` id) and fill every section. The *Effect on this
   round* section is mandatory: say which candidates the change would move. A request
   whose main effect is to rescue a candidate from the current round is a spec
   question for the user, not a skill fix.
3. Append the request to `change_requests[]` in `DESIGN_LOOP_STATE.json` with
   `status: "open"`.
4. Stop at the current step and tell the user a request is open.

The user then:

- **rejects** it — the reason is recorded, the round continues under the current
  rules; or
- **accepts** it — the maintainer makes the change outside the run (branch, test,
  merge, version bump). The round resumes on the new version: take a new snapshot and
  record the request's `resolved_in_version`.

Count the requests. How often the loop asked to change its own rules, and how many of
those asks would have promoted one of its own candidates, is part of the loop's track
record.

## Provenance: snapshot and verify

`scripts/provenance.py` hashes every skill file (test files and caches excluded),
the locked spec, and the environment.

| When | Command | Purpose |
|---|---|---|
| Start of each round, before Step 3 | `provenance.py snapshot --skill-dir <skill> --spec DESIGN_SPEC_LOCKED.md --round N --note claude_model=… --note gemini_model=… --out ROUND_N_PROVENANCE.json` | record the rules this round runs under |
| Before Step 7 (approval) | `provenance.py verify --skill-dir <skill> --against ROUND_N_PROVENANCE.json --spec DESIGN_SPEC_LOCKED.md --expect-sha256 <pinned>` | show the user the rules are the ones the round started with |
| Before Step 11 (scoring) | same | ranking is where a quiet edit changes the outcome most |
| Before Step 12 (write-back) | same | nothing enters cross-round memory from a drifted run |
| Between rounds, optional | `provenance.py diff ROUND_(N-1)_PROVENANCE.json ROUND_N_PROVENANCE.json` | report what changed between rounds, e.g. after an accepted request |

`snapshot` prints `snapshot_sha256`. Write it into the state file straight away
(`provenance[].snapshot_sha256`) and pass it to every `verify` as
`--expect-sha256`, so that editing the snapshot itself is caught too.

Record the model names in `--note`. They are not files and cannot be hashed, but a
round is only reproducible if they are known.

## When verify fails

| Exit | Meaning | Do |
|---|---|---|
| 0 | unchanged | continue |
| 1 | skill files modified, added or removed | **stop**. Show the user the list. Either restore the files, or — if the change is an accepted change request — take a new snapshot and record which request it implements. Never continue on an unexplained change |
| 2 | snapshot missing, corrupt, or not the pinned one | **stop**. Treat as exit 1: the record of what the round ran on is gone |
| 3 | skill unchanged, spec changed | continue only if the user approved the spec change and it is recorded in `notes`; otherwise stop and ask |

A failed verify is reported in `DESIGN_REPORT.md` even after it is resolved.

## What goes into the state file and the report

`DESIGN_LOOP_STATE.json` (see [design-loop-state-schema.md](design-loop-state-schema.md)):

- `provenance[]` — one entry per round: snapshot file, its SHA-256, skill version,
  git commit if known, each verify (step, result), and any re-snapshot with the
  request that caused it.
- `change_requests[]` — one entry per request, open or closed.

`DESIGN_REPORT.md` gets a **Run integrity** section: per round, the skill version, the
verify results, the change requests raised and how each was decided, and whether the
install was write-protected. Report it when nothing happened too; "no drift, no
requests" is a result.

## Limits, and the read-only install

Verification **detects** edits; it does not **prevent** them. An agent that rewrote
`provenance.py`, or rewrote a snapshot and the pinned hash in the state file
together, would get past it. Three layers make that unlikely, in increasing strength:

1. The rule: skill files are read-only during a run, and a needed change is a
   change request.
2. Detection: verify at the checkpoints where a human is looking, with the snapshot
   pinned by its own hash.
3. Prevention: install the skill read-only, so an edit needs a deliberate permission
   change first — `install_molecule_design_loop.sh --read-only`. When the skill is
   loaded straight from a git clone, the same effect comes from removing write
   permission on the skill folder of that clone and restoring it before maintenance.
   `verify` notes when the files are writable.

These guard against drift — a rule quietly loosened because it was in the way — not
against a system deliberately working around its own checks. Say that plainly when
the protocol is described to anyone else.
