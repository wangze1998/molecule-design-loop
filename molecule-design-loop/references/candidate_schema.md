# Molecule Design Loop Candidate Schema

Use CSV files for round artifacts so they can be filtered, sorted and inspected.

## ROUND_N_CANDIDATES.csv

Required columns:

- `candidate_id`
- `smiles`: RDKit input. For polymer/material rows, this must be a finite valid surrogate molecule, not BigSMILES or `(unit)n` notation.
- `parent_or_seed`
- `zotero_source_key`: Zotero item key of the paper that motivated this candidate; `none` if not Zotero-sourced
- `zotero_source_title`: short paper title; `none` if not applicable
- `zotero_grounding`: `scaffold`, `sar_rule`, `design_principle`, or `none`
- `design_move`
- `target_constraint`
- `rationale`
- `expected_proxy_effect`
- `risk`
- `source_hint`

Recommended columns:

- `design_mode`: `small_molecule` or `polymer`
- `proposal_family`
- `constraint_coverage`
- `novelty_class`
- `synthesis_hypothesis`
- `make_or_buy_hint`
- `route_risk`
- `experimental_readout`

Small-molecule columns, when relevant:

- `small_molecule_design_mode`: `scaffold_optimization`, `de_novo_bounded`, `library_triage`, or `closed_loop_experiment`
- `small_molecule_target_type`: `ligand`, `inhibitor`, `host`, `guest`, `catalyst`, `dye`, `photoswitch`, `supramolecular_building_block`, or `other`
- `mechanism_or_property_hypothesis`
- `scaffold_policy`: `preserve`, `bounded_modification`, or `scaffold_hop_allowed`
- `key_positions`
- `experimental_priority`: `high`, `medium`, `low`, or `control`
- `recommended_experiments`
- `computational_evidence_role`: what RDKit/xTB/ML evidence can and cannot support

Polymer/material columns, when relevant:

- `polymer_design_mode`: `mechanism_first`, `informatics_screen`, or `closed_loop_experiment`
- `structure_property_hypothesis`
- `primary_mechanism_to_tune`
- `synthesis_feasibility_notes`
- `experimental_priority`: `high`, `medium`, `low`, or `control`
- `recommended_experiments`
- `computational_evidence_role`: what RDKit/xTB/ML evidence can and cannot support
- `polymer_html_view`: `embedded_gallery`, `standalone_html`, or `both`
- `target_type`: `monomer`, `repeat_unit`, `oligomer`, `polymer`, or `copolymer`
- `repeat_unit_display_smiles`: primary polymer drawing input; must preserve extension handles as mapped dummy atoms `[*:1]` and `[*:2]`
- `repeat_unit_caption`: compact caption under the repeat-unit drawing, e.g. `{candidate_id} intended repeat unit; [*:1] and [*:2] = polymer chain extension; OEG = solubility side chain; terpy = bundling side patch`
- `sru_bracket_schematic`: primary human polymer view, e.g. `B_start - [p-Ph(O-2EH)-C#C-p-Ph(L_terpy)-C#C]n - B_end`
- `repeat_unit_handles_explanation`: plain-language block explaining `[*:1]`, `[*:2]`, main chain, side chains, solubilizing/steric groups, and that RDKit/xTB structures are finite surrogates
- `polymer_notation`: human-readable repeat notation or BigSMILES, if useful
- `monomer_smiles`
- `repeat_unit_smiles`
- `oligomer_model_smiles`: finite capped structure used for RDKit/xTB
- `rdkit_display_smiles`: explicitly extended capped oligomer used for the human gallery; choose `n = 2-4` when practical so backbone continuation and side chains are visible
- `rdkit_input_smiles`: same structure as `smiles` when the row is polymeric; included to make the surrogate choice explicit
- `xtb_input_model`: `monomer`, `repeat_unit_surrogate`, `capped_oligomer`, or `periodic_cell`
- `xtb_input_geometry_source`: `generated_from_oligomer_model_smiles`, `supplied_xyz`, `supplied_sdf`, or project runner path
- `oligomer_n`
- `end_group_model`
- `backbone_start_atom`: label or atom index for the first repeat-unit extension point
- `backbone_end_atom`: label or atom index for the second repeat-unit extension point
- `backbone_connection_points`: both extension points and their intended connection direction
- `connection_point_atoms`: numeric atom indices for repeat-unit extension points in the display oligomer
- `backbone_path_atoms`: ordered labels/indices for the main-chain path through the repeat unit or display oligomer
- `backbone_direction_label`: human-readable path rendered as `START -> ... -> END` when atom labels alone are not clear
- `backbone_bonds`: optional ordered bond indices for the main-chain path
- `backbone_only_smiles`: optional finite structure containing only the main-chain path
- `side_chain_attachment_atoms`: labels/indices where side chains attach to the main chain
- `side_chain_fragment_smiles`: semicolon-separated `label:SMILES` fragments, one per side chain when possible
- `side_chain_descriptions`: compact text naming each side chain and attachment position
- `polymerization_route`
- `comonomer_ratio`
- `tacticity_or_regioregularity`
- `target_polymer_property`
- `surrogate_scope`: what the finite structure can and cannot support
- `polymer_xtb_preflight_status`: `pass`, `block`, or `not_applicable`
- `polymer_xtb_preflight_notes`: connection, side-chain, end-group, geometry-source, or periodic-cell issues to check before xTB

Do not put polymer-only expressions in `smiles`, `rdkit_input_smiles`, `rdkit_display_smiles`, or `oligomer_model_smiles`: no `(unit)n`, no molecular-weight distribution text, no uncapped `[*]` descriptor model, and no BigSMILES unless a downstream parser explicitly supports it. Use `polymer_notation` for those human-readable forms.

## ROUND_N_FILTERED.csv

Required columns:

- all columns from candidates;
- `valid_smiles`
- `canonical_smiles`
- `rdkit_input_smiles`
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

For polymer/material rows, descriptor columns should refer to the parseable surrogate named in `oligomer_model_smiles`, `repeat_unit_smiles`, or `monomer_smiles`. Keep `surrogate_scope` explicit so later scoring does not confuse oligomer evidence with full-polymer evidence.

## ROUND_N_SYNTHESIS_FEASIBILITY.csv

Use this file after RDKit filtering and before promotion to xTB/final ranking.

Required columns:

- `candidate_id`
- `synthesis_gate_status`: `pass`, `warn`, `fail`, or `not_run`
- `make_or_buy_status`: `buy`, `make_on_demand`, `custom_synthesis`, `unknown`, or `not_applicable`
- `route_summary`
- `route_steps_estimate`
- `starting_materials_or_building_blocks`
- `route_risk`: `low`, `medium`, `high`, or `unknown`
- `synthesis_confidence`: `high`, `medium`, `low`, or `unknown`
- `synthesis_gate_reason`

Recommended columns:

- `retrosynthesis_tool`
- `route_reference`
- `vendor_or_library_hint`
- `forbidden_condition_hit`
- `protecting_group_burden`
- `purification_or_stability_risk`
- `next_route_action`: `promote`, `revise`, `needs_route_work`, `buy`, or `kill`

Rules:

- SA score is descriptor evidence only; it is not a route.
- A `fail` synthesis gate blocks final promotion unless the user explicitly overrides it.
- A `warn` synthesis gate can remain in the design loop if the design hypothesis is strong and the route risk is stated.

## ROUND_N_CANDIDATE_GALLERY.html

Use a standalone HTML file rendered from `ROUND_N_FILTERED.csv`.

It should include:

- RDKit structure depictions for every candidate kept in the filtered CSV;
- `candidate_id`
- rendered or canonical SMILES
- `filter_decision`
- `filter_reason`
- design rationale fields such as `design_move`, `target_constraint`, and `rationale`
- polymer fields such as `target_type`, `repeat_unit_smiles`, `oligomer_model_smiles`, `end_group_model`, and `surrogate_scope` when present
- primary polymer view: `sru_bracket_schematic` must appear above RDKit/xTB surrogate structures for polymer/material rows
- polymer depiction packet fields: `rdkit_display_smiles`, `backbone_start_atom`, `backbone_end_atom`, `backbone_connection_points`, `backbone_path_atoms`, `backbone_only_smiles`, `side_chain_attachment_atoms`, `side_chain_fragment_smiles`, and `side_chain_descriptions`

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

For polymer/material rows, add these recommended columns:

- `model_type`: `monomer`, `repeat_unit_surrogate`, or `capped_oligomer`
- `oligomer_n`
- `end_group_model`
- `xtb_input_geometry_source`
- `polymer_xtb_preflight_status`
- `polymer_xtb_preflight_notes`
- `unsupported_polymer_claims`

## ROUND_N_EXPERIMENT_RESULTS.csv

Use this file only when real synthesis, assay, characterization, or material testing data are available.

Required columns:

- `candidate_id`
- `experiment_type`: `synthesis`, `purification`, `assay`, `spectroscopy`, `microscopy`, `electrochemistry`, `thermal`, `mechanical`, or `other`
- `condition_summary`
- `measured_endpoint`
- `measured_value`
- `unit`
- `success_status`: `pass`, `warn`, `fail`, or `inconclusive`
- `failure_mode`
- `data_quality`: `high`, `medium`, `low`, or `unknown`
- `notes`

Rules:

- Keep failed experiments; they are active-learning signal.
- Do not merge results from different conditions without preserving `condition_summary`.
- Experimental evidence outranks computational proxies for the same endpoint.

## ROUND_N_DECISION.md

Use one table:

| candidate_id | gemini_constraint_score | pareto_rank | confidence | evidence_level | score_reason | pass_hard_constraints | synthesis_gate_status | xtb_status | decision | evidence | unsupported claims | uncertainty_reason | revision_hint | next action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Required notes per row:

- `gemini_constraint_score`: `1-5`, assigned by Gemini against `DESIGN_SPEC_LOCKED.md`
- `pareto_rank`: integer rank among hard-gate-passing candidates, or `not_ranked`
- `confidence`: `high`, `medium`, or `low`
- `evidence_level`: `experimental`, `computed_proxy`, `literature_only`, or `hypothesis_only`
- `score_reason`: short rationale tied to the design constraints
- `pass_hard_constraints`: `yes` or `no`
- `synthesis_gate_status`: `pass`, `warn`, `fail`, or `not_run`
- `xtb_status`: `pass`, `warn`, `fail`, or `not_run`
- `evidence`: may include RDKit and xTB evidence, but xTB is evidence only, not the scorer
- `uncertainty_reason`: why the confidence is limited or why additional evidence is needed
- polymer/material decisions must state whether evidence comes from a monomer, repeat-unit surrogate, or capped oligomer model

Allowed decisions:

- `keep`
- `revise`
- `kill`
- `control`
- `needs_higher_level_calc`
- `needs_route_work`
