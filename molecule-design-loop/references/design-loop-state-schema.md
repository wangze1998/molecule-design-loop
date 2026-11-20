# Design Loop State Schema (`DESIGN_LOOP_STATE.json`)

`DESIGN_LOOP_STATE.json` is the machine-readable cross-round memory of the design loop. It is the only artifact that persists *enforced* knowledge between rounds: what has been killed, what failed in the lab, what worked, and what materials are on hand. Other round files (`ROUND_N_*.csv/.md`) are per-round; this file accumulates.

It is **not** a free-form scratchpad. The fields below are a contract: Step 3 (candidate generation), Step 4 (deterministic filtering), and Step 11 (scoring) read specific keys from it, so improvised field names break the loop.

## Lifecycle

- Created at the end of Round 1; **updated, not overwritten** every subsequent round.
- Append to the list fields; do not drop earlier entries unless a later round actively retracts one (record the retraction in `notes`).
- `killed_motifs[].smarts` is the **authoritative source of historical structural exclusion** — Step 4 feeds these directly into the RDKit filter's `--forbidden-smarts`.

## Top-level keys

- `schema_version`: string, currently `"1.2"`. `1.1` added `provenance` and `change_requests`; `1.2` adds `reviewer_routes`. An older file without them is still valid and gains them at its next round.
- `design_mode`: `"small_molecule"` or `"polymer"`.
- `current_round`: integer, the round just completed.
- `max_rounds`: integer (matches `MAX_ROUNDS`).
- `killed_motifs`: array — structural patterns that must not be re-proposed (see below).
- `failed_reactions`: array — reactions/conditions known to fail.
- `available_building_blocks`: array — in-stock / purchasable / prior-route materials to bias generation toward (Fix C).
- `successful_moves`: array — design moves that improved a candidate.
- `scaffold_families_explored`: array of strings — Murcko scaffold families already covered.
- `evidence_gaps`: array of strings — properties still lacking evidence.
- `hypotheses_to_revisit`: array of strings — ideas parked for a later round.
- `experimental_endpoints`: array — measured endpoints carried from `ROUND_N_EXPERIMENT_RESULTS.csv`.
- `loop_calibration`: object — the loop's own track record: what it promoted vs. what actually worked (see below).
- `provenance`: array — which skill version, spec and environment each round ran on, and every verify (see below).
- `change_requests`: array — requests to change the skill raised during runs, and how each was decided (see below).
- `reviewer_routes`: array — which backend reviewed and searched each round, every attempt including failed ones, and whether the review was independent (see below).
- `notes`: optional free-text string for retractions, approved spec changes, or cross-round caveats.

### `killed_motifs[]` (each object)

- `motif_id`: stable id, e.g. `"km_r1_01"`.
- `smarts`: **mandatory** RDKit-parseable SMARTS for the killed pattern. This is what Step 4 excludes. If a whole scaffold is killed, give the scaffold SMARTS.
- `murcko_scaffold`: canonical Murcko scaffold SMILES when the kill is scaffold-level; `null` otherwise. Enables cross-checking against `scaffold_duplicate_of` / `murcko_scaffold` from the filter output.
- `reason`: short text — why it was killed.
- `failure_source`: one of `rdkit`, `synthesis_gate`, `xtb`, `experiment`, `adversarial_review`, `user`.
- `killed_in_round`: integer.
- `evidence_ref`: pointer to the round artifact that justifies the kill, e.g. `"ROUND_1_EXPERIMENT_RESULTS.csv:cand_07"` or `"ROUND_1_GEMINI_ADVERSARIAL_REVIEW.md"`.

### `failed_reactions[]` (each object)

- `reaction_or_condition`: e.g. `"Suzuki coupling on 2-bromopyridine N-oxide"`.
- `motif_context`: SMARTS or text describing the structural context where it failed; SMARTS preferred so it can also seed a `killed_motifs` entry when a structural pattern is implicated.
- `failure_mode`: e.g. `synthesis_failed`, `unstable`, `purification_failed`.
- `source_round`: integer.
- `evidence_ref`: artifact pointer.

### `available_building_blocks[]` (each object)

- `name_or_smiles`: building block identity (name or SMILES).
- `source`: one of `inventory`, `vendor`, `prior_route`.
- `notes`: optional, e.g. vendor/catalog or shelf location.

### `successful_moves[]` (each object)

- `design_move`: the move that worked.
- `scaffold_family`: Murcko family it applied to.
- `why_it_worked`: short text tied to evidence.
- `round`: integer.

### `experimental_endpoints[]` (each object)

- `candidate_id`, `measured_endpoint`, `measured_value`, `unit`, `success_status`, `source_round`.

### `loop_calibration` (object)

The loop's own track record. Everything here is an aggregation of data the loop already collects — `ROUND_N_DECISION.md` for what was promoted, `ROUND_N_EXPERIMENT_RESULTS.csv` for what actually happened. No new measurement is required.

This exists to answer one question the loop otherwise cannot answer: **of the structures this loop told the chemist to make, what fraction were worth making?** Without it there is no way to tell whether the loop is saving bench time or just producing plausible CSVs.

- `rounds[]`: one record per completed round —
  - `round`: integer.
  - `promoted_count`: candidates the round recommended for synthesis (`decision: keep` / Pareto top-N / `experimental_priority: high`).
  - `attempted_count`: how many the chemist actually made. `null` when unknown.
  - `synthesis_success_count`: how many were successfully made and purified. `null` when unknown.
  - `endpoint_success_count`: how many met the design objective once measured (`success_status: pass`). `null` when unknown.
  - `hit_rate`: `endpoint_success_count / attempted_count` as a decimal, or `not_computable`.
- `prediction_vs_outcome[]`: one record per candidate that has both a prediction and an experimental result —
  - `candidate_id`, `round`.
  - `predicted_score`: the `gemini_constraint_score` it received.
  - `predicted_priority`: the `experimental_priority` it received.
  - `observed_status`: the experimental `success_status`.
  - `agreement`: `confirmed` (high score → worked), `optimistic` (high score → failed), `pessimistic` (low score → worked), or `inconclusive`.
- `known_bias`: array of strings — recurring miscalibration the loop should correct for, e.g. `"over-scores candidates whose only evidence is literature analogy"`.
- `calibration_summary`: short text, written for the chemist, stating the current track record plainly.

**Rules**

- Report the track record honestly, **including when it is unflattering**. A loop that hides its own miss rate is worse than no loop, because it spends bench time on false confidence.
- `not_computable` / `null` are correct answers when no experimental feedback exists. Never estimate a hit rate from predictions alone.
- A hit rate computed from fewer than 5 attempted candidates must be labelled small-sample in `calibration_summary` and must not be presented as a performance figure.
- A repeated `optimistic` pattern in `prediction_vs_outcome[]` should be written into `known_bias` and referenced by the next round's scoring (Step 11) as a reason to lower `confidence`.

### `provenance[]` (each object)

Written by Step 3 and appended to at every verify. Procedure in [run-integrity-protocol.md](run-integrity-protocol.md).

- `round`: integer.
- `snapshot_file`: e.g. `"ROUND_2_PROVENANCE.json"`.
- `snapshot_sha256`: the hash `provenance.py snapshot` printed. Every verify passes it as `--expect-sha256`.
- `skill_version`: from the snapshot.
- `git_commit`: from the snapshot, or `null` for an installed copy.
- `write_protected`: boolean, from the snapshot.
- `verifications[]`: one per check — `step` (`7`, `11`, `12`), `result` (`ok`, `skill_drift`, `spec_drift`, `bad_snapshot`), `detail` (the files named, or `""`).
- `resnapshots[]`: when an accepted change request or an approved spec change required a new snapshot mid-round — `snapshot_file`, `snapshot_sha256`, `reason`, `request_id` (or `null` for a spec change).

### `reviewer_routes[]` (each object)

One per role per round, plus one per attempt after a failure, so a fallback is never invisible. Procedure in [reviewer-selection-protocol.md](reviewer-selection-protocol.md).

- `round`: integer.
- `role`: `review` or `search`.
- `step`: the step that used it (`1.5-B`, `3.5`, `5.5`, `9.5`, `11`), or `0` for the round's resolution.
- `label`: e.g. `"gemini"`, `"codex@agent-hud"`.
- `source`: `invocation`, `project`, `user`, `default` or `fallback`.
- `requested_model`: what the config asked for, or `null`.
- `reported_model`: the model that actually answered, or `null` when unknown.
- `model_source`: `transport`, `agent_hud_default`, `self_report` or `unknown`.
- `session_id`: thread, agent or Agent HUD session id; `null` for `manual`.
- `status`: `ok`, `incomplete` or a failure reason from the protocol (`billing_rejected`, `timeout`, …).
- `independence`: `independent`, `same_family`, `unknown` or `not_applicable` (failed attempt).
- `acceptance`: `accepted`, `provisional` or `none`.
- `rebuttal_rounds`: integer, Steps 3.5 / 9.5; `disputed`: array of candidate ids left contested.
- `raw_file`: path of the saved raw reply, e.g. `"_reviews/ROUND_1_step3.5_codex@agent-hud_raw.md"`.

**Rules**

- Never delete an attempt, failed ones included. A failure after dispatch is recorded with its reason and is not followed by another provider in the same step.
- A `provisional` review cannot clear a `revise` or `overclaim` flag.

### `change_requests[]` (each object)

- `request_id`: stable id, e.g. `"cr_r2_01"`.
- `round`, `step`: where it was raised.
- `file`: `"ROUND_2_CHANGE_REQUEST.md"`.
- `target`: the skill file (and function or threshold) it asks to change.
- `touches_invariant`: the integrity or protocol rule involved, or `"none"`.
- `would_promote`: array of candidate ids that would move into the top 3, pass a filter, or gain a stronger evidence label if the change were made. `[]` when none.
- `status`: `open`, `accepted` or `rejected`.
- `decision_note`: the user's reason.
- `resolved_in_version`: skill version that implements an accepted request, else `null`.

**Rules**

- Never delete a request, including rejected ones. The count of requests, and how many had a non-empty `would_promote`, is part of the loop's track record and goes into the report.
- An `open` request blocks the step it was raised at until the user decides.

## How the loop consumes this file

- **Step 1** writes `available_building_blocks[]` from the locked design spec's known-materials / preferred-vendor fields.
- **Step 3** opens `provenance[]` for the round with a snapshot (see [run-integrity-protocol.md](run-integrity-protocol.md)), then reads `killed_motifs[]` and excludes any candidate matching a killed `smarts` or `murcko_scaffold`, unless the candidate carries an explicit documented rescue hypothesis in its `rationale`. It also biases a portion of the round toward `available_building_blocks[]` (tagged `building_block_source`).
- **Step 4** assembles `--forbidden-smarts` as the union of the design spec's `forbidden_motifs` and every `killed_motifs[].smarts`.
- **Step 11** may read `successful_moves[]` and `evidence_gaps[]` to inform ranking and revision hints.
- **Step 12** writes new `killed_motifs[]` / `failed_reactions[]` entries from experimental `failure_mode` and adversarial `likely_lab_failure_mode`, so the next round excludes them automatically. It also updates `loop_calibration` by comparing what the previous round promoted against what the experiments returned.
- **Steps 7, 11, 12** append a verification to the round's `provenance[]` entry and stop on anything but `ok` (or a `spec_drift` the user approved).
- **Any step** may append to `change_requests[]`; an `open` request stops the run at that step.
- **Step 0** appends the round's resolved routes to `reviewer_routes[]`; **Steps 1.5-B, 3.5, 5.5, 9.5, 11** append each attempt.
- **Step 13** reports `loop_calibration` in `DESIGN_REPORT.md`, unflattering results included, and reports `provenance[]`, `change_requests[]` and `reviewer_routes[]` under *Run integrity*.

## Minimal valid example

```json
{
  "schema_version": "1.2",
  "design_mode": "small_molecule",
  "current_round": 1,
  "max_rounds": 3,
  "killed_motifs": [
    {
      "motif_id": "km_r1_01",
      "smarts": "[N+](=O)[O-]",
      "murcko_scaffold": null,
      "reason": "nitro group flagged unstable under planned reduction route",
      "failure_source": "synthesis_gate",
      "killed_in_round": 1,
      "evidence_ref": "ROUND_1_SYNTHESIS_FEASIBILITY.csv:cand_12"
    }
  ],
  "failed_reactions": [
    {
      "reaction_or_condition": "SNAr on electron-rich aryl chloride",
      "motif_context": "c1ccc(Cl)cc1[OX2]",
      "failure_mode": "synthesis_failed",
      "source_round": 1,
      "evidence_ref": "ROUND_1_EXPERIMENT_RESULTS.csv:cand_05"
    }
  ],
  "available_building_blocks": [
    {
      "name_or_smiles": "4-bromobenzaldehyde",
      "source": "inventory",
      "notes": "on shelf, ~5 g"
    }
  ],
  "successful_moves": [
    {
      "design_move": "added fluorine ortho to linker",
      "scaffold_family": "biphenyl",
      "why_it_worked": "improved metabolic-stability proxy without changing geometry",
      "round": 1
    }
  ],
  "scaffold_families_explored": ["biphenyl", "naphthalene"],
  "evidence_gaps": ["no solubility measurement for any candidate"],
  "hypotheses_to_revisit": ["thiophene-for-phenyl swap if potency stalls"],
  "experimental_endpoints": [
    {
      "candidate_id": "cand_03",
      "measured_endpoint": "IC50",
      "measured_value": "0.42",
      "unit": "uM",
      "success_status": "pass",
      "source_round": 1
    }
  ],
  "loop_calibration": {
    "rounds": [
      {
        "round": 1,
        "promoted_count": 5,
        "attempted_count": 3,
        "synthesis_success_count": 2,
        "endpoint_success_count": 1,
        "hit_rate": 0.33
      }
    ],
    "prediction_vs_outcome": [
      {
        "candidate_id": "cand_03",
        "round": 1,
        "predicted_score": 5,
        "predicted_priority": "high",
        "observed_status": "pass",
        "agreement": "confirmed"
      },
      {
        "candidate_id": "cand_07",
        "round": 1,
        "predicted_score": 4,
        "predicted_priority": "high",
        "observed_status": "fail",
        "agreement": "optimistic"
      }
    ],
    "known_bias": [],
    "calibration_summary": "Round 1: 3 of 5 promoted candidates were attempted, 1 met the endpoint. Small sample — not yet a performance figure."
  },
  "provenance": [
    {
      "round": 1,
      "snapshot_file": "ROUND_1_PROVENANCE.json",
      "snapshot_sha256": "e70f5b25c3cc91bafec02808d4f5d3a5d51f14220c44bf4f37c0734d7889828f",
      "skill_version": "0.5.0",
      "git_commit": null,
      "write_protected": true,
      "verifications": [
        {"step": 7, "result": "ok", "detail": ""},
        {"step": 11, "result": "ok", "detail": ""},
        {"step": 12, "result": "ok", "detail": ""}
      ],
      "resnapshots": []
    }
  ],
  "change_requests": [
    {
      "request_id": "cr_r1_01",
      "round": 1,
      "step": 4,
      "file": "ROUND_1_CHANGE_REQUEST.md",
      "target": "rdkit_filter_candidates.py --max-tpsa default",
      "touches_invariant": "none",
      "would_promote": ["cand_09"],
      "status": "rejected",
      "decision_note": "TPSA limit comes from the spec; raise it there if needed, not in the script",
      "resolved_in_version": null
    }
  ],
  "reviewer_routes": [
    {
      "round": 1,
      "role": "review",
      "step": "3.5",
      "label": "gemini",
      "source": "default",
      "requested_model": "gemini-2.5-flash",
      "reported_model": null,
      "model_source": "unknown",
      "session_id": null,
      "status": "billing_rejected",
      "independence": "not_applicable",
      "acceptance": "none",
      "rebuttal_rounds": 0,
      "disputed": [],
      "raw_file": null
    },
    {
      "round": 1,
      "role": "review",
      "step": "3.5",
      "label": "codex@agent-hud",
      "source": "fallback",
      "requested_model": null,
      "reported_model": "gpt-6.2-astra",
      "model_source": "agent_hud_default",
      "session_id": "example-session-id",
      "status": "ok",
      "independence": "independent",
      "acceptance": "accepted",
      "rebuttal_rounds": 1,
      "disputed": ["cand_11"],
      "raw_file": "_reviews/ROUND_1_step3.5_codex@agent-hud_raw.md"
    }
  ],
  "notes": ""
}
```
