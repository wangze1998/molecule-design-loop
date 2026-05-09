# Molecule Design Loop Candidate Schema

Use CSV files for round artifacts so they can be filtered, sorted and inspected.

## ROUND_N_CANDIDATES.csv

Required columns:

- `candidate_id`
- `smiles`
- `parent_or_seed`
- `design_move`
- `target_constraint`
- `rationale`
- `expected_proxy_effect`
- `risk`
- `source_hint`

Recommended columns:

- `proposal_family`
- `constraint_coverage`
- `novelty_class`

## ROUND_N_FILTERED.csv

Required columns:

- all columns from candidates;
- `valid_smiles`
- `canonical_smiles`
- `formula`
- `exact_mass`
- `mol_wt`
- `formal_charge`
- `rotatable_bonds`
- `aromatic_rings`
- `ring_count`
- `heavy_atoms`
- `qed`
- `clogp`
- `tpsa`
- `hba`
- `hbd`
- `fraction_csp3`
- `sa_score`
- `murcko_scaffold`
- `scaffold_duplicate_of`
- `scaffold_seen_count`
- `pains_alerts`
- `brenk_alerts`
- `medchem_alert_count`
- `forbidden_motif_hit`
- `hard_constraint_status`
- `filter_decision`
- `filter_reason`

## ROUND_N_CANDIDATE_GALLERY.html

Use a standalone HTML file rendered from `ROUND_N_FILTERED.csv`.

It should include:

- RDKit structure depictions for every candidate kept in the filtered CSV;
- `candidate_id`
- rendered or canonical SMILES
- `filter_decision`
- `filter_reason`
- design rationale fields such as `design_move`, `target_constraint`, and `rationale`

This artifact is produced before xTB selection so the round can be visually inspected first.

## ROUND_N_XTB_APPROVAL.md

Use a short Markdown checkpoint written after gallery review and before any xTB run.

Required fields:

- `review_status`: `approved`, `approved_subset`, `blocked`, or `pending_user_reply`
- `reviewer`: usually the user
- `approved_candidate_ids`
- `blocked_candidate_ids`
- `structural_concerns`
- `next_step`

This artifact is mandatory. If it is not approved yet, xTB must not start.

## ROUND_N_XTB_RESULTS.csv

Required columns:

- `candidate_id`
- `canonical_smiles`
- `xtb_status`
- `xtb_command`
- `charge`
- `multiplicity`
- `energy_hartree`
- `homo_ev`
- `lumo_ev`
- `gap_ev`
- `dipole_debye`
- `geometry_warning`
- `raw_output_dir`
- `notes`

## ROUND_N_DECISION.md

Use one table:

| candidate_id | gemini_constraint_score | score_reason | pass_hard_constraints | xtb_status | decision | evidence | unsupported claims | revision_hint | next action |
|---|---|---|---|---|---|---|---|---|---|

Required notes per row:

- `gemini_constraint_score`: `1-5`, assigned by Gemini against `DESIGN_SPEC_LOCKED.md`
- `score_reason`: short rationale tied to the design constraints
- `pass_hard_constraints`: `yes` or `no`
- `xtb_status`: `pass`, `warn`, `fail`, or `not_run`
- `evidence`: may include RDKit and xTB evidence, but xTB is evidence only, not the scorer

Allowed decisions:

- `keep`
- `revise`
- `kill`
- `control`
- `needs_higher_level_calc`
