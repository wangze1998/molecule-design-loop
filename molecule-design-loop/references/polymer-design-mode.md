# Polymer Design Mode

Use this mode when the target is a polymer, oligomer, material repeat unit, or monomer series.

## Design logic

Do not run polymer design as a small-molecule-style "compute first, rank later" workflow. Use a polymer-specific design loop:

`application target -> literature/mechanism packet -> polymerization chemistry and synthesis feasibility -> SRU bracket candidates -> backbone/side-chain/material-property rationale -> finite surrogate for RDKit/xTB evidence -> experimental priority list`

Core rules:
- Start from target application criteria and hard constraints, not from arbitrary repeat-unit enumeration.
- Identify the likely structure-property mechanism: backbone rigidity, side-chain packing/solubility, donor-acceptor electronics, dynamic bond exchange, degradable linkage, crosslink density, ion transport, morphology, or processability.
- Select a plausible polymerization route before promoting a candidate: ROP, step-growth, radical/RAFT/ATRP, DArP, Suzuki/Stille, click, condensation, network curing, or another route named in the brief.
- Check monomer availability, protecting groups, functional-group tolerance, expected DP/Mn/dispersity, end groups, purification, and characterization feasibility.
- Treat RDKit/xTB/ML as evidence layers that narrow candidates, not as final arbiters of polymer performance.
- Rank final candidates by experimental priority: synthesis feasibility, expected property mechanism, literature precedent, characterization plan, and only then computational proxy support.

## Operating modes

- **mechanism_first**: default for most research polymer design. Literature and chemistry define candidates; computation explains local trends.
- **informatics_screen**: use when there is a dataset/model or virtual forward synthesis library. Compute/ML narrows a large, synthetically constrained space before experiments.
- **closed_loop_experiment**: use when the user has automation or iterative experimental data. Suggest the next experiment from previous synthesis/characterization results.

## Required polymer outputs

- `polymer_design_mode`: `mechanism_first`, `informatics_screen`, or `closed_loop_experiment`
- `structure_property_hypothesis`
- `polymerization_route`
- `synthesis_feasibility_notes`
- `experimental_priority`
- `recommended_experiments`
- `computational_evidence_role`: what RDKit/xTB/ML can and cannot support
- `ROUND_N_POLYMER_DESIGN.html`: standalone HTML view of the polymer subfunction output, or embedded at the top of `ROUND_N_CANDIDATE_GALLERY.html`

## Polymer HTML view (mandatory for polymer runs)

The HTML must present:
- SRU bracket schematic as the first visual block
- Repeat-unit handles explanation (`[*:1]`, `[*:2]`, main chain, side chains, solubilizing/steric groups)
- Structure-property hypothesis and primary mechanism
- Polymerization route and synthesis feasibility notes
- Backbone direction, side-chain panels, and RDKit/xTB finite surrogate
- Experimental priority, recommended experiments, and computational evidence limits

## Representation rules

- Keep a human-readable polymer notation if useful, but always add a finite parseable structure for tools.
- Prefer capped oligomers (`n = 1-3`) for RDKit/xTB unless the design spec requires a different model.
- State end groups and charge state explicitly.
- Do not mix monomer, repeat unit, and oligomer scores without labeling them.

When showing a polymer, explicitly distinguish the RDKit/xTB finite surrogate from the true repeat-unit handles. Use `repeat_unit_handles_explanation`:
- `candidate_id repeat unit handles`
- `RDKit/xTB view = capped repeat-unit surrogate, not the full polymer`
- `[*:1] = connection to previous repeat unit`
- `[*:2] = connection to next repeat unit`
- `main chain = ...`
- `side chains = ...`
- `solubilizing/steric groups = ...`

## Program input rules

- `polymer_notation` is for humans only. Do not pass it directly to RDKit or xTB.
- RDKit `smiles` field must be a valid finite molecule: preferably `oligomer_model_smiles`, otherwise `repeat_unit_smiles` or `monomer_smiles`.
- `rdkit_display_smiles`: explicitly extended capped oligomer (`n = 2-4`) to make backbone and side chains visible; may differ from descriptor-only `smiles`.
- RDKit descriptor input must not contain `(unit)n`, `n=`, dispersity ranges, or uncapped wildcard connection points.
- xTB input must be a 3D geometry generated from the approved finite surrogate with real atoms only, explicit end groups, charge, multiplicity, and oligomer length.
- Use periodic xTB/PBC only when the design spec explicitly selects it and records the cell/model assumptions.
- Record the full mapping: `polymer_notation -> monomer/repeat unit -> capped oligomer -> RDKit/xTB input`.

## Human display rules

- Primary polymer display: repeat-unit structure image with visible `*:1` and `*:2` handles (`repeat_unit_display_smiles`), not a capped oligomer and not text-only.
- `repeat_unit_display_smiles` must keep polymer extension atoms as mapped dummy atoms so the image shows where the repeat module starts and ends.
- `repeat_unit_caption` directly below: `{candidate_id} intended repeat unit`; `[*:1] and [*:2] = polymer chain extension`; side-chain labels and meanings.
- Always provide `sru_bracket_schematic` (e.g., `B_start - [p-Ph(O-2EH)-C#C-p-Ph(L_terpy)-C#C]n - B_end`).
- Always provide `repeat_unit_handles_explanation` near the primary view.
- For complex side chains, keep the backbone readable in `sru_bracket_schematic` using labels like `R_sol` or `L_terpy`; define those labels in `side_chain_descriptions` and `side_chain_fragment_smiles`.
- Treat RDKit depictions as computational surrogate views for checking, not as the primary human explanation.
- State `backbone_start_atom`, `backbone_end_atom`, and `backbone_connection_points` before rendering.
- `backbone_path_atoms`: ordered path `START_LABEL -> segment 1 -> ... -> END_LABEL`.
- List side chains separately in `side_chain_attachment_atoms` and `side_chain_descriptions`.
- Provide `backbone_direction_label` when atom labels are cryptic.
- Provide `backbone_only_smiles` when available; otherwise derive from `backbone_path_atoms`.
- Provide `side_chain_fragment_smiles` as semicolon-separated `label:SMILES` fragments.
- Prefer a three-view polymer depiction: full oligomer (highlighted main chain/side chains/connection points), backbone-only view, and separate side-chain fragment view.

## Design candidates may vary

- Backbone repeat unit
- Side-chain electronics, polarity, sterics, or solubilizing groups
- Comonomer identity or approximate ratio
- Linker/spacer length and rigidity
- End groups or initiator-derived caps
- Polymerization route and protecting-group compatibility

## Non-xTB polymer targets (require external evidence or higher-level simulation)

- Molecular weight, dispersity, yield, and livingness
- Crystallinity, phase separation, film morphology, Tg, modulus, conductivity, and degradation rate
- Self-assembly morphology or device performance
