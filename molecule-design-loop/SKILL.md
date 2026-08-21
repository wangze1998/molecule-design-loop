---
name: "molecule-design-loop"
description: "Autonomous small-molecule or polymer/materials design loop with dual literature intelligence: mines the user's Zotero library for curated personal knowledge, and independently searches for the latest and most authoritative papers in the field. Both sources inform candidate generation in parallel — Zotero supplies proven scaffolds and personal SAR context, active search supplies recent advances and field consensus. Workflow: Zotero extraction + active literature search (parallel) -> design spec lock -> unified literature packet -> candidates -> RDKit filtering -> synthesis-feasibility gate -> visual gallery -> user approval -> optional xTB -> optional experimental feedback -> Gemini/Pareto scoring -> iterative design."
---

# Molecule Design Loop

Use this skill when the user provides a molecule design constraint file and wants an autonomous loop:

`[optional image extraction] -> design_spec.md -> mode selection -> [Zotero extraction || active literature search] -> unified LIT_PACKET -> candidates -> RDKit filtering -> synthesis-feasibility gate -> HTML gallery -> user structural approval -> optional xTB evidence -> optional NMR prediction/verification -> optional experimental feedback -> Gemini/Pareto decision -> next design round`

**Dual literature philosophy**: Design knowledge comes from two complementary and equally important streams that run in parallel:

- **Zotero stream** — the user's personal curated library: papers they have read, annotated, and considered relevant. Captures personal familiarity, specific scaffolds of interest, and known context. Not complete by design.
- **Active search stream** — independent search for the latest papers (last 1-2 years) and the most authoritative/highly-cited works in the field. Captures recent advances, field consensus, and papers the user may not have encountered yet.

Neither stream is subordinate to the other. The unified `LIT_PACKET.md` synthesizes both.

## Design Mode Hierarchy

Small-molecule design and polymer/material design are sibling modes. Do not nest one under the other.

Automatically select the mode from the user command and `design_spec.md`:

- **Small-Molecule Design Mode**: use when the request is for a discrete molecule, ligand, inhibitor, host/guest molecule, catalyst, dye, photoswitch, supramolecular building block, or a SMILES/scaffold series with no polymer/repeat-unit intent.
- **Polymer Design Mode**: use when the request mentions polymer, oligomer, monomer series, repeat unit, copolymer, material repeat unit, BigSMILES, DP, Mn, dispersity, tacticity, regioregularity, morphology, film, bulk material, or polymerization route.
- If both modes appear or the mode is ambiguous, ask one short targeted question before expensive steps.

## Role Split

- **Zotero MCP** (`mcp__zotero-mcp__*`) supplies personal curated knowledge: scaffolds the user has studied, SAR context from their reading, synthesis routes from papers they collected. Runs in parallel with active search.
- **Gemini research** (`mcp__gemini-research__literature_search`, `prior_art_search`) handles active literature search and novelty checks on candidate structures before gallery promotion.
- **Gemini adversarial reviewer** (`mcp__gemini-review__review`) is an independent cross-model critic that challenges candidate design rationale, synthesis claims, and evidence-to-claim mappings. Receives raw artifacts directly — never a Claude-written summary.
- **Claude** orchestrates files, scripts, filters, xTB jobs, tables, and iteration. Does not self-review its own candidates.
- **RDKit** performs deterministic molecule parsing, deduplication, and descriptor checks.
- **Synthesis-feasibility gate** checks whether a candidate has a plausible make/buy route before promotion.
- **xTB** provides low-cost computational proxies only, usually on finite capped molecules or oligomer models for polymers.
- **Gemini** performs constraint scoring; Pareto/confidence fields make tradeoffs and uncertainty explicit.
- The user remains the scientific owner of final synthesis decisions.

Do not treat xTB as proof of binding, assembly, reactivity, selectivity, or mechanism.
Do not treat heuristic synthetic-accessibility scores as proof that a molecule can actually be made.

## Inputs

Primary inputs:
- a Markdown design constraint file, usually `design_spec.md`;
- the user's Zotero library, accessed via `mcp__zotero-mcp__*` tools.

Optional inputs:
- seed SMILES or ChemDraw-selected SMILES;
- **structure images** (PNG/JPG/PDF of journal figures, ChemDraw screenshots, or hand-drawn structures) — Claude extracts SMILES directly from the image; see [references/structure-image-input-protocol.md](references/structure-image-input-protocol.md);
- Zotero collection name or tags to restrict library search scope;
- local PDFs or notes not yet in Zotero;
- prior design logs;
- known failed motifs;
- known building blocks, vendor-available compounds, prior routes, failed reactions, or route constraints;
- prior experimental results (synthesis success/failure, yield, purity, assay values, characterization);
- desired xTB proxy metrics;
- project-local xTB runner scripts;
- polymer repeat units, monomers, end groups, target DP range, polymerization route, tacticity or morphology constraints when the target is a polymer/material.

If no design file exists, first run Zotero extraction (Step 1.5) to identify the research theme, then create a design spec from `templates/design_spec_template.md` pre-populated with Zotero-extracted scaffolds. Ask the user to confirm before expensive calculations.

## Output Layout

All outputs go in `molecule-design-stage/`:

- `ZOTERO_KNOWLEDGE_PACKET.md` — design knowledge from the Zotero library (personal stream)
- `ZOTERO_SEED_SMILES.csv` — scaffolds and seed structures from Zotero
- `ACTIVE_SEARCH_PACKET.md` — design knowledge from active literature search (field-wide stream)
- `DESIGN_SPEC_LOCKED.md`
- `LIT_PACKET.md` — unified merge of both streams
- `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`
- `ROUND_N_NOVELTY_CHECK.md`
- `ROUND_N_CLAIM_AUDIT.md`
- `ROUND_N_CANDIDATES.csv`
- `ROUND_N_FILTERED.csv`
- `ROUND_N_SYNTHESIS_FEASIBILITY.csv`
- `ROUND_N_CANDIDATE_GALLERY.html`
- `ROUND_N_POLYMER_DESIGN.html` (polymer/material runs)
- `ROUND_N_XTB_APPROVAL.md`
- `ROUND_N_XTB_RESULTS.csv`
- `ROUND_N_NMR_PREDICTIONS.csv` (when NMR prediction is requested or experimental NMR is available)
- `ROUND_N_NMR_VERIFICATION.md` (when experimental NMR data is compared against predictions)
- `ROUND_N_EXPERIMENT_RESULTS.csv` (when user provides experimental feedback)
- `IMAGE_EXTRACTED_SMILES.csv` (when structure images are provided as input)
- `ROUND_N_GEMINI_INPUT.md`
- `ROUND_N_DECISION.md`
- `DESIGN_LOOP_STATE.json` — cross-round memory; structure defined in [references/design-loop-state-schema.md](references/design-loop-state-schema.md)
- `DESIGN_REPORT.md`
- `xtb_jobs/`

Bundled helpers:
- `scripts/rdkit_filter_candidates.py` — annotates and filters candidate CSV files with RDKit descriptors
- `scripts/render_candidate_gallery.py` — renders candidate CSV rows into a standalone RDKit HTML gallery
- `references/candidate_schema.md` — CSV contracts
- `references/design-loop-state-schema.md` — `DESIGN_LOOP_STATE.json` cross-round memory contract
- `templates/design_spec_template.md` — starting constraint file template
- `templates/xtb_approval_template.md` — approval checkpoint template before xTB

If a local `research-wiki/` exists, also update `research-wiki/design-log.md` and `research-wiki/events.jsonl`. Use the shared event schema in `../shared-references/events-jsonl.md`.

## Helper Script Rules

When a new helper program is needed:
- prefer `one main entrypoint + reusable modules + per-run input config only`;
- do not hard-code round number, molecule, file path, threshold set, or temporary local layout;
- prefer parameterized inputs, documented CLI flags, and stable CSV/Markdown contracts;
- read evolving constraints from workflow files (e.g., `DESIGN_SPEC_LOCKED.md`) instead of baking them into code.

## Constants

- **MAX_ROUNDS = 3**
- **INITIAL_CANDIDATES = 20-50**
- **MAX_XTB_PER_ROUND = 10-20**
- **ZOTERO_SEARCH_QUERIES = 3-5**
- **ZOTERO_METADATA_LIMIT = 30**
- **ZOTERO_FULLTEXT_PAPERS = 5-8**
- **LITERATURE_STREAMS = `Zotero (personal curated) || Active search (latest + authoritative) — both mandatory, run in parallel`**
- **ACTIVE_SEARCH_TARGETS = `(1) last 1-2 years on the specific scaffold/topic; (2) top-cited reviews or landmark papers; (3) topics not covered in Zotero`**
- **XTB_LEVEL = `GFN2-xTB` unless the design file says otherwise**
- **SYNTHESIS_GATE_FOR_PROMOTION = `route_plausible_or_make_on_demand`**
- **EXPERIMENTAL_FEEDBACK_REQUIRED = false unless previous wet-lab results are provided**
- **STOP_IF_NO_NEW_FEASIBLE_MOTIF = true**
- **NMR_PREDICTION = `optional; auto-enabled when experimental NMR data is provided`**
- **NMR_VALIDATED_SOLVENTS = `CDCl3, DMSO-d6, D2O`**
- **NMR_1H_TOLERANCE = `±0.20 ppm`**
- **NMR_13C_TOLERANCE = `±2.0 ppm`**
- **IMAGE_INPUT = optional** — Claude extracts SMILES from structure images (journal figures, ChemDraw screenshots, hand-drawn sketches)
- **IMAGE_LOW_CONFIDENCE_REQUIRES_CONFIRMATION = true**
- **CHEMDRAW_ROLE = optional visualization/input terminal**
- **ZOTERO_TRACE_REQUIRED = true** — every generated candidate must reference the Zotero paper(s) that motivated it
- **GEMINI_REVIEW_MODEL = `gemini-2.5-flash`** — default for all `mcp__gemini-review__*` calls
- **GEMINI_ADVERSARIAL_REVIEW = mandatory** — after Step 3, every round; cannot be skipped
- **NOVELTY_CHECK = mandatory** — after Step 5, every round; `prior_art_status` must be populated before gallery
- **CLAIM_AUDIT = mandatory when xTB runs, OR when a design objective is one the loop cannot evidence** (binding affinity, potency, selectivity, catalytic activity, self-assembly, permeability, in vivo outcome) — after Step 9; Gemini scoring in Step 11 must reference the audit
- **LOOP_CALIBRATION = mandatory once experimental feedback exists** — Step 12 records promoted-vs-worked; Step 13 reports it, unflattering results included

---

## Workflow

### 0.5. Extract structures from images (when provided)

If the user provides structure images (journal figures, ChemDraw screenshots, hand-drawn sketches) instead of or alongside SMILES:

1. Read each image with the `Read` tool.
2. Extract molecular structures as canonical SMILES; validate each with RDKit.
3. Write `molecule-design-stage/IMAGE_EXTRACTED_SMILES.csv`.
4. Low-confidence extractions (`extraction_confidence: low`) require user confirmation before proceeding.
5. Confirmed structures feed into `seed_scaffolds` in Step 1.

For full extraction procedure, validation rules, and CSV schema, see [references/structure-image-input-protocol.md](references/structure-image-input-protocol.md).

### 1. Lock the design spec

Read the Markdown constraint file and produce `DESIGN_SPEC_LOCKED.md`. Separate:

- `design_mode`: `small_molecule` or `polymer`
- `hard_constraints`: must not be violated
- `soft_preferences`: optimize if possible
- `forbidden_motifs`: reject if present
- `seed_scaffolds`: preserve or modify per the design goal
- `allowed_elements`, charge range, size range, solubility and stability limits
- `synthesis_feasibility_constraints`: route depth, starting materials, forbidden reactions, make/buy preference, route risk tolerance
- `available_building_blocks`: in-stock, purchasable, and prior-route materials. Capture from the design spec's "Known available starting materials or building blocks" and "Preferred vendors, libraries, or inventory sources" fields. Write these into `DESIGN_LOOP_STATE.json`'s `available_building_blocks[]` so Step 3 can bias generation toward shelf-available materials (Fix C). See [references/design-loop-state-schema.md](references/design-loop-state-schema.md).
- `experimental_feedback_policy`
- `pareto_objectives` and confidence/evidence requirements for promotion
- `xTB_proxy_targets`: what xTB can reasonably test
- `non_xTB_targets`: properties that must not be inferred from xTB alone
- `polymer_constraints`: repeat-unit representation, monomer/end-group assumptions, DP or oligomer model, polymerization route, dispersity/tacticity/morphology requirements, material-property targets

If a hard constraint is ambiguous, stop and ask before running xTB. If design mode is ambiguous, ask before candidate generation.

### 1.5. Build the dual literature intelligence base

**Both sub-steps run in parallel. Neither is subordinate to the other.**

- **1.5-A Zotero extraction** → writes `ZOTERO_KNOWLEDGE_PACKET.md` and `ZOTERO_SEED_SMILES.csv`
  See full protocol: [references/zotero-extraction-protocol.md](references/zotero-extraction-protocol.md)

- **1.5-B Active search** → writes `ACTIVE_SEARCH_PACKET.md`
  See full protocol: [references/active-search-protocol.md](references/active-search-protocol.md)

### 2. Build the unified literature packet

Merge `ZOTERO_KNOWLEDGE_PACKET.md` and `ACTIVE_SEARCH_PACKET.md` into `LIT_PACKET.md`.

- Merge entries that appear in both streams; record both sources.
- Flag contradictions explicitly — do not silently pick one over the other.

`LIT_PACKET.md` must contain: unified scaffold table, SAR rules table, synthesis knowledge, failed motifs, field consensus, and open design questions (to drive bounded-exploratory candidates in Step 3).

### 3. Generate SMILES candidates

Generate 20-50 candidates in `ROUND_N_CANDIDATES.csv`. Every candidate must trace to at least one source in `LIT_PACKET.md`. Bounded-exploratory candidates (`zotero_grounding: none`) capped at 10%.

**Mandatory cross-round exclusion (Fix A).** Before generating, read `DESIGN_LOOP_STATE.json` if it exists. Every `killed_motifs[]` entry is a hard exclusion constraint: no candidate may match a killed `smarts` or `murcko_scaffold`. A killed motif may be re-proposed **only** with an explicit, documented rescue hypothesis recorded in that candidate's `rationale` (e.g., the prior failure was a route problem now solved, not a structural dead end). See [references/design-loop-state-schema.md](references/design-loop-state-schema.md).

**Availability bias (Fix C).** When `DESIGN_LOOP_STATE.json`'s `available_building_blocks[]` is non-empty, devote a portion of the round to candidates built from those in-stock/purchasable materials, tagged via the `building_block_source` column. A lightweight vendor-availability lookup (mirroring the novelty-check structure) may populate `building_block_source`, but this is not a new mandatory gate.

For full column schema, bucket rules (including the shelf-biased building-block bucket), and polymer-specific fields, see [references/candidate_schema.md](references/candidate_schema.md).

### 3.5. Gemini adversarial chemistry review

**Mandatory.** Runs immediately after Step 3, before RDKit filtering. Pass raw `ROUND_N_CANDIDATES.csv` + `DESIGN_SPEC_LOCKED.md` directly — no summaries.

Outputs `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md` and adds `gemini_adversarial_flag` (`pass`/`warn`/`revise`) to the candidates CSV.

For full Gemini prompt, output format, and flag update rules, see [references/adversarial-review-protocol.md](references/adversarial-review-protocol.md).

### 4. Run deterministic filtering

Use the bundled helper:

```bash
python3 "$CODEX_HOME/skills/molecule-design-loop/scripts/rdkit_filter_candidates.py" \
  molecule-design-stage/ROUND_N_CANDIDATES.csv \
  molecule-design-stage/ROUND_N_FILTERED.csv
```

Pass constraints from `DESIGN_SPEC_LOCKED.md` as arguments: `--allowed-elements`, `--min-mw`, `--max-mw`, `--max-rotatable`, `--forbidden-smarts`.

**`--forbidden-smarts` must be the union of two sources (Fix A):** the design spec's `forbidden_motifs` AND every `killed_motifs[].smarts` from `DESIGN_LOOP_STATE.json`. This makes historical structural failures filter out automatically — the flag already accepts a list, so no script change is needed:

```bash
# --forbidden-smarts list = spec forbidden_motifs ∪ DESIGN_LOOP_STATE.json killed_motifs[].smarts
python3 ".../rdkit_filter_candidates.py" ... \
  --forbidden-smarts "<spec_motif_1>" "<spec_motif_2>" "<killed_motif_smarts_1>" "<killed_motif_smarts_2>"
```

For medchem triage, also pass: `--min-qed`, `--max-logp`, `--max-tpsa`, `--max-hba`, `--max-hbd`, `--min-fsp3`, `--max-sa-score`, `--max-medchem-alerts`, `--reject-pains`, `--reject-brenk`, `--reject-scaffold-duplicates`.

Write `ROUND_N_FILTERED.csv`. Keep rejected candidates with a rejection reason.

### 5. Run synthesis-feasibility gate

Write `ROUND_N_SYNTHESIS_FEASIBILITY.csv`. Assess commercial availability, retrosynthetic route, protecting-group burden, purification risk, and known failure modes from the literature packet.

The gate must also emit a directly sortable `synthesis_cost` (`low`/`medium`/`high`/`very_high`) and `time_to_first_sample` (`same_day`/`days`/`weeks`/`months`) estimate per candidate, so Step 11's Pareto ranking can treat synthesis economics as a first-class axis (Fix B), not a footnote.

**Feasible is not practical.** A route that merely exists is not a route worth running, so the gate must also emit `overall_yield_estimate` (`high`/`medium`/`low`/`unknown`) and `hazard_toxicity_flag` (`none`/`standard_care`/`high_hazard`/`unknown`). Where route evidence supports more than one route, record the trade-off in `route_alternatives` rather than collapsing the choice into a single cost number — a 3-step high-hazard route and a 6-step benign one are different offers, and the chemist picks between them.

Use `unknown` rather than a fabricated value. Without a retrosynthesis/CASP engine and a price/toxicity database these axes are heuristic estimates, not an optimality-guaranteed route Pareto front; label them as estimates.

For full column schema, the make/buy preference ordering, and promotion rules, see [references/synthesis-gate-schema.md](references/synthesis-gate-schema.md).

### 5.5. Novelty check

**Mandatory.** Runs after Step 5, before the HTML gallery. Check every promoted candidate against prior art using `mcp__gemini-research__prior_art_search`.

Outputs `ROUND_N_NOVELTY_CHECK.md`. Adds `prior_art_status` and `source_doi` columns to `ROUND_N_SYNTHESIS_FEASIBILITY.csv`.

For full protocol and `prior_art_status` values, see [references/novelty-check-protocol.md](references/novelty-check-protocol.md).

### 6. Render an HTML candidate gallery

Use the bundled helper:

```bash
python3 "$CODEX_HOME/skills/molecule-design-loop/scripts/render_candidate_gallery.py" \
  molecule-design-stage/ROUND_N_FILTERED.csv \
  molecule-design-stage/ROUND_N_CANDIDATE_GALLERY.html \
  --title "Round N Candidate Gallery"
```

The gallery must use RDKit depictions (not text-only tables), show filter decisions and rationale, and preserve rejected candidates. Must be produced before any xTB run starts.

For polymer runs, also render `ROUND_N_POLYMER_DESIGN.html` (or embed it at the top of the gallery) with: SRU bracket schematic, repeat-unit handles, backbone direction strip (`START -> ... -> END`), and three-view depiction packet. See [references/polymer-design-mode.md](references/polymer-design-mode.md) for full display rules.

### 7. Get explicit user structural approval before xTB

After generating the gallery, stop and ask the user to confirm no obvious structural problems exist. Write `ROUND_N_XTB_APPROVAL.md` using `templates/xtb_approval_template.md`.

- Do not start xTB until the user explicitly approves.
- If structural issues are flagged, revise the candidate list first.
- Update `DESIGN_LOOP_STATE.json` with approval status and approved candidate IDs.

### 8. Select xTB jobs

Select at most `MAX_XTB_PER_ROUND` candidates. Prefer: user-approved candidates, hard-constraint passers, synthesis-gate passers, chemically diverse Murcko scaffolds, one or two conservative controls.

Before running: check `which xtb`; search project scripts for existing runners; report the blocker if xTB is not on PATH.

For polymer rows, perform a polymer-map preflight (verify `backbone_start_atom`, `backbone_end_atom`, `backbone_path_atoms`, `oligomer_model_smiles`) and record `polymer_xtb_preflight_status`; block xTB if the map is missing or inconsistent.

### 9. Run xTB screening

Run the smallest useful calculation first (GFN2-xTB by default). Collect: optimization status, final energy, HOMO/LUMO/gap, dipole moment, geometry sanity, convergence failure reason.

Write `ROUND_N_XTB_RESULTS.csv`. Keep raw files under `xtb_jobs/round_N/`.

For polymers, report properties of the stated capped oligomer surrogate only. Do not extrapolate to Mn, dispersity, Tg, modulus, morphology, or conductivity.

See xTB integrity rules: [references/xtb-integrity-rules.md](references/xtb-integrity-rules.md).

### 9.5. Result-to-claim audit

**Mandatory in either of two cases**, before Gemini scoring:

1. **xTB ran** — audit what those numbers do and do not prove.
2. **A design objective is one this loop cannot evidence at all** — binding affinity, potency, selectivity, catalytic activity, self-assembly, permeability, in vivo outcome. Mandatory **even when xTB did not run**: the audit's output is then the explicit declaration that no direct evidence exists.

Case 2 closes a silent hole. A candidate can pass hard constraints, clear the synthesis gate, look clean on descriptors, and score 5 on literature analogy alone — while the loop has produced **zero evidence about the property the chemist actually cares about**, and nothing says so out loud.

Outputs `ROUND_N_CLAIM_AUDIT.md` with an evidence-to-claim matrix, an `Un-Evidenced Design Objectives` section, and `auditor_flag` per candidate. Step 11 must read this file; Gemini may not assign a score ≥ 4 to any candidate with `auditor_flag: overclaim` unless corrected, and any candidate flagged `no_direct_evidence` must carry `evidence_level: literature_only` or `hypothesis_only`.

For full Gemini prompt and output format, see [references/claim-audit-protocol.md](references/claim-audit-protocol.md).

### 9.7. NMR prediction and verification (optional)

**When to run:** when the design spec sets `nmr_prediction: yes`, when the user provides experimental NMR data, or for candidates approaching synthesis recommendation (Gemini score ≥ 4 or Pareto top-3).

Claude predicts 1H and 13C NMR chemical shifts, multiplicities, and coupling constants for selected candidates. No external tool required — this uses Claude's internal chemistry knowledge (validated at ±0.079 ppm for 1H, ±1.37 ppm for 13C per Anthropic benchmarks).

Outputs `ROUND_N_NMR_PREDICTIONS.csv`. When experimental NMR data is available, also outputs `ROUND_N_NMR_VERIFICATION.md` with a peak-by-peak predicted-vs-experimental comparison and a `verification_status` per candidate (`confirmed` / `consistent` / `inconclusive` / `mismatch`).

A `mismatch` status triggers mandatory structural review — the synthesized compound may be a regioisomer, tautomer, or side product.

NMR predictions are a plausibility check, not a replacement for experimental characterization. Always label as "Claude-predicted" and state the expected error range. The claim audit (Step 9.5) scope extends to NMR predictions.

For full protocol, output schemas, matching thresholds, and scope limitations, see [references/nmr-prediction-protocol.md](references/nmr-prediction-protocol.md).

### 10. Ingest experimental feedback when available

Normalize user-provided results into `ROUND_N_EXPERIMENT_RESULTS.csv` before scoring.

Columns: `candidate_id`, `experiment_type`, `condition_summary`, `measured_endpoint`, `measured_value`, `unit`, `success_status` (pass/warn/fail/inconclusive), `failure_mode`, `data_quality`, `notes`.

Keep exact condition summaries; preserve failure rows as useful negative evidence. If no feedback is available, mark `not_provided`.

### 11. Score candidates with Gemini and Pareto ranking

Create `ROUND_N_DECISION.md`. Start a **fresh Gemini thread** (separate from Steps 3.5 and 9.5). Gemini scores against `DESIGN_SPEC_LOCKED.md`, not raw xTB numbers.

**Synthesis practicality is a dominance criterion, not a tiebreaker.** Compute dominance over {property fit, `synthesis_cost`, `time_to_first_sample`, `overall_yield_estimate`, `hazard_toxicity_flag`}: a candidate that is no better on every one of those axes than some other candidate is dominated, is recorded as `dominated_by:<candidate_id>` in `practicality_dominance`, and must not enter the top 3 of `pareto_rank` whatever its score. Rank within the non-dominated front by design-spec priority, then apply the make/buy tiebreak (`buy` < `make_on_demand` < `custom_synthesis`). Treat `unknown` as non-comparable on that axis and lower `confidence`.

A high-performing but 8-step custom synthesis should not outrank a comparable 2-step shelf-available candidate — and a cheap fast candidate that is clearly worse on the design objective does not win by being cheap. When several candidates are non-dominated, present the trade-off instead of forcing a single winner.

For full Gemini prompt, scoring rubric (1-5), all required output fields, and Pareto ranking rules, see [references/gemini-scoring-protocol.md](references/gemini-scoring-protocol.md).

### 12. Iterate

For the next round, generate candidates by modifying observed failure modes:

- Too flexible → add rigidity or shorten linker
- Too planar → add steric twist or interrupt conjugation
- Too polar/nonpolar → adjust substituents or ionizable groups
- Poor gap proxy → tune donor/acceptor strength
- Geometry collapse → reduce steric clash or change connection point
- Synthesis gate fails → simplify route, use available building blocks, reduce protecting-group burden
- Experiment fails → identify whether it was synthesis, purification, stability, assay, or measurement failure; design next round around that failure mode
- Polymer surrogate too bulky/flexible → adjust side chains, spacer length, comonomer, end groups, or oligomer model

Carry forward: kept candidates, killed motifs and reasons, literature warnings, xTB failure modes, synthesis gate outcomes, experimental successes and failures.

Update `DESIGN_LOOP_STATE.json` per the contract in [references/design-loop-state-schema.md](references/design-loop-state-schema.md): `successful_moves`, `killed_motifs`, `failed_reactions`, `scaffold_families_explored`, `evidence_gaps`, `available_building_blocks`, `experimental_endpoints`, and `hypotheses_to_revisit`. Update in place — do not overwrite earlier rounds.

**Close the failure-feedback loop (Fix D).** The two highest-value negative signals must be written back as structured state, not left as prose:

- Experimental `failure_mode` rows from `ROUND_N_EXPERIMENT_RESULTS.csv` → new `killed_motifs[]` and/or `failed_reactions[]` entries (with `failure_source: experiment`).
- The `likely_lab_failure_mode` column from `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md` → new `killed_motifs[]`/`failed_reactions[]` entries (with `failure_source: adversarial_review`).

Whenever a structural pattern is implicated, record a SMARTS in the `killed_motifs[].smarts` field so the next round's Step 3 exclusion and Step 4 `--forbidden-smarts` union remove it automatically.

**Record the loop's own track record.** Once any experimental feedback exists, update `loop_calibration` in `DESIGN_LOOP_STATE.json`: compare what the previous round promoted (`ROUND_N_DECISION.md`) against what the experiments returned (`ROUND_N_EXPERIMENT_RESULTS.csv`). Fill `rounds[]` (promoted / attempted / made / met-endpoint / hit rate) and `prediction_vs_outcome[]` (predicted score and priority vs. observed status, tagged `confirmed` / `optimistic` / `pessimistic`).

This is pure aggregation of data already collected, and it answers the one question the loop otherwise cannot: **of the structures this loop told the chemist to make, what fraction were worth making?** A repeated `optimistic` pattern goes into `known_bias` and lowers `confidence` in the next round's scoring. Use `not_computable`/`null` when feedback is absent — never estimate a hit rate from predictions alone.

### 13. Stop and report

Stop when one of these happens:
- At least 3-5 candidates satisfy hard constraints, pass or warn-only synthesis feasibility, receive strong Gemini/Pareto scores, and have supporting xTB or experimental evidence;
- No new feasible motif appears for one full round;
- xTB is unavailable and the user needs to configure the compute backend;
- `MAX_ROUNDS` is reached.

Write `DESIGN_REPORT.md` with: top candidates and SMILES, why they satisfy the design file, synthesis-feasibility summary, experimental feedback summary, xTB proxy summary, NMR prediction/verification summary (if run), Gemini constraint scoring and Pareto rank, risks and what not to claim, recommended next experiment or higher-level calculation, and for polymers: oligomer-length sensitivity, conformer sampling, MD/CG simulation, polymerization feasibility check, or experimental characterization plan.

**Two sections are mandatory and must not be softened:**

- **Un-evidenced objectives** — every design objective the loop produced no direct evidence for, taken from the claim audit's `Un-Evidenced Design Objectives` section. Name the substitute that was used instead (literature analogy, descriptor proxy, scaffold precedent) and the measurement that would settle it.
- **Loop calibration** — the `loop_calibration` track record from `DESIGN_LOOP_STATE.json`: promoted vs. attempted vs. worked, the hit rate, and any `known_bias`. **Report it honestly, including when it is unflattering.** A loop that hides its own miss rate is worse than no loop, because it spends bench time on false confidence. Label small samples (fewer than 5 attempted) as such and do not present them as a performance figure. When no experimental feedback exists yet, say so plainly rather than omitting the section.

---

## xTB Integrity Rules and Chemistry Design Rules

See [references/xtb-integrity-rules.md](references/xtb-integrity-rules.md).

---

## Small-Molecule Design Mode

Use this mode for a discrete molecule or a small-molecule scaffold series. Do not run it as a polymer/repeat-unit workflow.

`target/use case -> literature/mechanism packet -> seed or scaffold policy -> interpretable analog candidates -> RDKit/medchem filtering -> synthesis-feasibility gate -> optional xTB evidence -> experimental priority list`

Core rules:
- Start from the target use case and hard constraints, not arbitrary SMILES enumeration.
- Identify the likely mechanism or property driver: binding, recognition, electronics, solubility, redox, photophysics, conformation, steric shielding, permeability, stability, or aggregation.
- Preserve the scaffold only when the design spec says to; otherwise allow controlled scaffold hops with clear rationale.
- Keep one design move per candidate so the next round can learn from success/failure.
- Require a make/buy or retrosynthesis plausibility note before final promotion.

Small-molecule outputs must include: `small_molecule_design_mode` (`scaffold_optimization` / `de_novo_bounded` / `library_triage` / `closed_loop_experiment`), `mechanism_or_property_hypothesis`, `scaffold_policy`, `synthesis_feasibility_notes`, `experimental_readout`, `experimental_priority`, `computational_evidence_role`.

---

## Polymer Design Mode

See [references/polymer-design-mode.md](references/polymer-design-mode.md).

---

## ChemDraw Integration

Use ChemDraw as an optional structure input/output layer:
- Read selected structure SMILES through `chemdraw-mcp` when useful.
- Use ChemDraw to inspect final structures manually.
- Do not depend on ChemDraw GUI automation for the core loop.

## Invocation Examples

```text
/molecule-design-loop "/path/to/design_spec.md"
/molecule-design-loop "design_spec.md -- rounds: 2 -- max-xtb: 8"
/molecule-design-loop "design a DTE-naphthyl linker series from design_spec.md"
```

## Success Condition

The skill is successful when it produces:
- valid candidate SMILES with a transparent reason for every design move;
- deterministic filter results;
- synthesis-feasibility status before final promotion;
- an RDKit-rendered HTML gallery before xTB selection;
- an explicit user approval checkpoint before any xTB run starts;
- xTB results or a clear xTB availability blocker;
- optional experimental-feedback intake when results are available;
- a Gemini/Pareto/confidence-scored iteration decision that narrows the design space rather than restarting randomly.
