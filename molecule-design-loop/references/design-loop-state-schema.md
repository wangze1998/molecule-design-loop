# Design Loop State Schema (`DESIGN_LOOP_STATE.json`)

`DESIGN_LOOP_STATE.json` is the machine-readable cross-round memory of the design loop. It is the only artifact that persists *enforced* knowledge between rounds: what has been killed, what failed in the lab, what worked, and what materials are on hand. Other round files (`ROUND_N_*.csv/.md`) are per-round; this file accumulates.

It is **not** a free-form scratchpad. The fields below are a contract: Step 3 (candidate generation), Step 4 (deterministic filtering), and Step 11 (scoring) read specific keys from it, so improvised field names break the loop.

## Lifecycle

- Created at the end of Round 1; **updated, not overwritten** every subsequent round.
- Append to the list fields; do not drop earlier entries unless a later round actively retracts one (record the retraction in `notes`).
- `killed_motifs[].smarts` is the **authoritative source of historical structural exclusion** — Step 4 feeds these directly into the RDKit filter's `--forbidden-smarts`.

## Top-level keys

- `schema_version`: string, currently `"1.0"`.
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
- `notes`: optional free-text string for retractions or cross-round caveats.

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

## How the loop consumes this file

- **Step 1** writes `available_building_blocks[]` from the locked design spec's known-materials / preferred-vendor fields.
- **Step 3** reads `killed_motifs[]` and excludes any candidate matching a killed `smarts` or `murcko_scaffold`, unless the candidate carries an explicit documented rescue hypothesis in its `rationale`. It also biases a portion of the round toward `available_building_blocks[]` (tagged `building_block_source`).
- **Step 4** assembles `--forbidden-smarts` as the union of the design spec's `forbidden_motifs` and every `killed_motifs[].smarts`.
- **Step 11** may read `successful_moves[]` and `evidence_gaps[]` to inform ranking and revision hints.
- **Step 12** writes new `killed_motifs[]` / `failed_reactions[]` entries from experimental `failure_mode` and adversarial `likely_lab_failure_mode`, so the next round excludes them automatically.

## Minimal valid example

```json
{
  "schema_version": "1.0",
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
  "notes": ""
}
```
