# Candidate Generation Schema (Step 3)

## Literature grounding

Every candidate must trace back to at least one source in `LIT_PACKET.md`. Record in `zotero_grounding`:

- `scaffold` — derived from a scaffold in `ZOTERO_SEED_SMILES.csv` or found via active search
- `sar_rule` — motivated by an SAR rule from either stream
- `design_principle` — motivated by a design principle from any consulted paper
- `field_consensus` — implementing what the most authoritative recent papers identify as current standard
- `none` — no literature grounding; pure exploratory invention (≤10% of the round)

When a candidate is motivated by active-search findings (not Zotero), record `source: active_search` in the rationale.

## Required columns

- `candidate_id`
- `smiles`
- `parent_or_seed`
- `zotero_source_key` — Zotero item key; `none` if not Zotero-sourced
- `zotero_source_title` — short paper title; `none` if not applicable
- `zotero_grounding` — `scaffold`, `sar_rule`, `design_principle`, `field_consensus`, or `none`
- `design_move`
- `target_constraint`
- `rationale`
- `expected_proxy_effect`
- `risk`
- `source_hint`
- `synthesis_hypothesis`
- `make_or_buy_hint`
- `route_risk`
- `experimental_readout`

## Polymer-specific additional columns

- `repeat_unit_smiles` or `monomer_smiles`
- `oligomer_model_smiles`
- `end_group_model`
- `polymerization_route`
- `target_polymer_property`

## Generation rules

- Every small molecule must have a valid SMILES. For polymers, use a valid monomer, repeat-unit surrogate, or capped oligomer SMILES for RDKit/xTB; BigSMILES or repeat notation are annotations only.
- Every candidate must be tied to at least one design constraint.
- Include control candidates when useful.
- Avoid pure novelty theater: design moves must be chemically interpretable.

## Candidate buckets

- **10-20%** conservative controls close to trusted seeds
- **50-70%** directional edits that each test one primary hypothesis
- **10-30%** bounded exploratory variants that still respect scaffold-level constraints

## Preferred mutation families

- Substituent electronics tuning
- Linker rigidification or flexibilization
- Heteroatom walk or polarity rebalance
- Steric twist introduction
- Motif replacement preserving the core hypothesis
- For polymers: monomer/repeat-unit substitution, comonomer ratio changes, linker/spacer changes, end-group changes, side-chain tuning, tacticity/regioregularity assumptions, capped oligomer model changes

Avoid filling a round with near-isomorphic variants. One candidate should primarily test one interpretable design move.
