# Changelog

All notable changes to `molecule-design-loop` will be tracked in this file.

---

## v0.2.4 — 2026-08-21

Makes the loop honest about itself: it must now report which design objectives it produced no evidence for, and it must keep score of how often its own recommendations actually worked. Prompted by Min et al., *From Static to Dynamic Structures: Improving Binding Affinity Prediction with Graph-Based Deep Learning* (Adv. Sci. 2024, DOI 10.1002/advs.202405404), whose virtual screen reported a real prospective hit rate — 20 candidates tested, 12 hits, 2 submicromolar — a kind of self-accounting this loop had no way to produce. Documentation-only; no Python changed.

### Added

- **`loop_calibration` block in `DESIGN_LOOP_STATE.json`** (`references/design-loop-state-schema.md`) — the loop's own track record: `rounds[]` (promoted / attempted / made / met-endpoint / hit rate), `prediction_vs_outcome[]` (predicted score and priority vs. observed status, tagged `confirmed` / `optimistic` / `pessimistic`), `known_bias[]`, and `calibration_summary`. This is pure aggregation of data the loop already collects — `ROUND_N_DECISION.md` for what was promoted, `ROUND_N_EXPERIMENT_RESULTS.csv` for what happened. No new measurement required.
- New `auditor_flag` value `no_direct_evidence`, and a mandatory `Un-Evidenced Design Objectives` section in `ROUND_N_CLAIM_AUDIT.md`.
- Two mandatory `DESIGN_REPORT.md` sections: un-evidenced objectives, and loop calibration.

### Changed

- **The claim audit now triggers on two cases, not one.** It was `mandatory when xTB runs`, which left a silent hole: a target-based design that never ran xTB got no audit at all, so a candidate could pass hard constraints, clear the synthesis gate, look clean on descriptors, and score 5 on literature analogy — with the loop having produced **zero evidence about the property the chemist actually cares about**, and nothing saying so. The audit is now also mandatory whenever a design objective is one the loop cannot evidence (binding affinity, potency, selectivity, catalytic activity, self-assembly, permeability, in vivo outcome), **even when xTB did not run**; its output is then the explicit declaration that no direct evidence exists.
- A candidate flagged `no_direct_evidence` may still score well on constraint fit, but its `evidence_level` must be `literature_only` or `hypothesis_only`, and its supported claim must not describe the un-evidenced objective as computationally supported.
- Step 11 lowers `confidence` when a `loop_calibration.known_bias` entry applies to a candidate's evidence type, so measured miscalibration feeds back into scoring.
- Un-evidenced objectives are appended to `evidence_gaps` and named in the report's "what not to claim".

### Honesty boundary

- The calibration track record must be reported **including when it is unflattering**. A loop that hides its own miss rate is worse than no loop, because it spends bench time on false confidence. Hit rates from fewer than 5 attempted candidates must be labelled small-sample and not presented as a performance figure; `not_computable` / `null` are the correct answers when no experimental feedback exists. Never estimate a hit rate from predictions alone.

### Notes

- SKILL.md constants and Steps 9.5, 12, 13 updated; `claim-audit-protocol.md`, `design-loop-state-schema.md`, `gemini-scoring-protocol.md`, `candidate_schema.md`, and `AGENT_GUIDE.md` updated to match.
- No binding-affinity or MD/ensemble prediction layer was added. That would need a protein structure, a docking or affinity model, and MD trajectories — hard dependencies of the same kind deliberately kept out in v0.2.3. The paper's ensemble insight remains a named optional upgrade in the report's recommended-next-calculation section, not a main-loop step.

---

## v0.2.3 — 2026-08-10

Extends the synthesis-economics work of v0.2.2 from a single cost scalar to a multi-objective practicality picture, and promotes practicality from a tiebreaker to a dominance criterion. Motivated by multi-objective synthesis planning work (Hastedt, Zhang & del Rio Chanona, *From Feasible to Practical: Pareto-Optimal Synthesis Planning*, arXiv:2605.07521), whose central point is that a route which merely exists is not a route worth running, and that scalarizing the route choice hides the trade-off. Documentation-only; no Python changed.

### Added

- Synthesis-gate columns `overall_yield_estimate` (`high`/`medium`/`low`/`unknown`) and `hazard_toxicity_flag` (`none`/`standard_care`/`high_hazard`/`unknown`) — the two practicality axes that v0.2.2 lacked. Cost and lead time alone cannot distinguish a cheap high-hazard route from a cheap benign one.
- Recommended synthesis-gate column `route_alternatives` — a compact `route_id | steps | cost | yield_estimate | hazard_flag` profile for 1-3 routes, so the route choice stays visible instead of collapsing into one `synthesis_cost` number. `single_route_only` when evidence supports just one route.
- Gemini scoring output field `practicality_dominance` (`non_dominated` / `dominated_by:<candidate_id>` / `not_assessed`).

### Changed

- **Practicality is now a dominance criterion, not a tiebreaker.** v0.2.2 applied synthesis cost only when candidates were "otherwise tied", which is too weak — a candidate could be worse on *every* practicality axis and still win on a marginally better property score. Step 11 now computes dominance over {property fit, `synthesis_cost`, `time_to_first_sample`, `overall_yield_estimate`, `hazard_toxicity_flag`}; a dominated candidate cannot enter the top 3 of `pareto_rank` whatever its score. Ranking within the non-dominated front keeps the make/buy tiebreak.
- `unknown` is treated as non-comparable on its axis (it can neither dominate nor be dominated there) and lowers `confidence`, so missing data cannot be laundered into a favourable rank.
- Non-dominated candidates are presented as a trade-off set rather than forced into a single rank-1 winner.

### Honesty boundary

- Without a retrosynthesis/CASP engine and a price/toxicity database, `route_alternatives` and the practicality axes are heuristic estimates — **not** an optimality-guaranteed Pareto front over routes in the sense of multi-objective CASP search. They must be labelled as estimates. When a CASP tool is available, prefer its output and record it in `retrosynthesis_tool`. Use `unknown` rather than fabricating a yield or cost. This mirrors the existing `SA score is not a route` boundary.

### Notes

- SKILL.md Steps 5 and 11 updated; `synthesis-gate-schema.md`, `gemini-scoring-protocol.md`, `candidate_schema.md`, and `AGENT_GUIDE.md` updated to match.
- No attempt is made to reimplement a multi-objective retrosynthesis search. That would require a trained single-step model, a price database, and yield/toxicity models — hard dependencies that would break the skill's "xTB itself is optional, report the blocker if it is missing" design.

---

## v0.2.2 — 2026-06-12

Closes the two open loops in the "decide whether to make it" logic: cross-round failure memory and synthesis economics. Previously both mechanisms only *recorded* knowledge — nothing forced the next round to use it. This release makes that knowledge enforced. Documentation-only; no Python changed (the RDKit filter already accepts the list-valued flags relied on here).

### Added

- **`references/design-loop-state-schema.md`** — a real, machine-readable schema for `DESIGN_LOOP_STATE.json`, which was referenced 5+ times across SKILL.md / AGENT_GUIDE.md but had no definition anywhere. Defines `killed_motifs[]` (with mandatory `smarts`), `failed_reactions[]`, `available_building_blocks[]`, `successful_moves[]`, `scaffold_families_explored`, `evidence_gaps`, `hypotheses_to_revisit`, and `experimental_endpoints`, plus a minimal valid JSON example.
- New synthesis-gate columns `synthesis_cost` (`low`/`medium`/`high`/`very_high`) and `time_to_first_sample` (`same_day`/`days`/`weeks`/`months`).
- New candidate column `building_block_source` (`in_stock`/`purchasable`/`custom`/`unknown`) and a shelf-biased building-block candidate bucket.
- New Gemini scoring output fields `synthesis_cost` and `time_to_first_sample`.

### Changed — the four closures

- **(A) Cross-round failure memory is now enforced.** Step 3 must read `DESIGN_LOOP_STATE.json` and exclude any candidate matching a `killed_motifs[]` SMARTS/scaffold (re-proposal allowed only with a documented rescue hypothesis). Step 4's `--forbidden-smarts` must be the union of the spec's `forbidden_motifs` and every historical `killed_motifs[].smarts`. This structurally stops the loop from re-proposing a structure it already killed.
- **(B) Synthesis cost is a first-class ranking axis.** The synthesis gate emits sortable `synthesis_cost`/`time_to_first_sample`; Step 11 Pareto ranking must include them, with a make/buy tiebreak (`buy` < `make_on_demand` < `custom_synthesis`). A strong but 8-step custom synthesis no longer silently outranks a comparable 2-step shelf-available candidate.
- **(C) Availability moved upstream into generation.** Step 1 captures known/purchasable building blocks into `DESIGN_LOOP_STATE.json`; Step 3 biases a portion of the round toward those materials, tagged via `building_block_source`.
- **(D) Lab-failure signals flow back into state.** Step 12 must write experimental `failure_mode` (from `ROUND_N_EXPERIMENT_RESULTS.csv`) and adversarial `likely_lab_failure_mode` (from `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`) back as structured `killed_motifs[]`/`failed_reactions[]` entries, so the next round excludes them automatically.

### Notes

- A and D are the two ends of one feedback loop (write failures → exclude them next round); B and C close the synthesis-economics loop at the ranking (back) and generation (front) ends.
- SKILL.md Steps 1, 3, 4, 5, 11, 12 updated; `synthesis-gate-schema.md`, `gemini-scoring-protocol.md`, `candidate_schema.md`, and `AGENT_GUIDE.md` updated to match.

---

## v0.2.1 — 2026-06-06

New capabilities inspired by Anthropic's "Making Claude a Chemist" research. Structure image input lowers the barrier for seeding designs; NMR prediction adds a zero-dependency structure plausibility check. Housekeeping: duplicate schema files merged, AGENT_GUIDE updated to match current workflow.

### Added

- **Step 0.5 — Structure image input**: users can provide PNG/JPG/PDF images (journal figures, ChemDraw screenshots, hand-drawn sketches) instead of typing SMILES. Claude extracts structures directly, validates with RDKit, and feeds confirmed seeds into Step 1. Low-confidence extractions require user confirmation. Protocol: `references/structure-image-input-protocol.md`.
- **Step 9.7 — NMR prediction and verification** (optional): Claude predicts 1H/13C NMR chemical shifts, multiplicities, and coupling constants for top candidates using its internal chemistry knowledge (±0.079 ppm 1H, ±1.37 ppm 13C per Anthropic benchmarks). When experimental NMR data is available, a predicted-vs-experimental comparison produces a `verification_status` (`confirmed`/`consistent`/`inconclusive`/`mismatch`). A `mismatch` triggers mandatory structural review. Protocol: `references/nmr-prediction-protocol.md`.
- New output files: `IMAGE_EXTRACTED_SMILES.csv`, `ROUND_N_NMR_PREDICTIONS.csv`, `ROUND_N_NMR_VERIFICATION.md`.
- New decision column: `nmr_verification_status` in Gemini scoring output.
- New constants: `NMR_PREDICTION`, `NMR_VALIDATED_SOLVENTS`, `NMR_1H_TOLERANCE`, `NMR_13C_TOLERANCE`, `IMAGE_INPUT`, `IMAGE_LOW_CONFIDENCE_REQUIRES_CONFIRMATION`.
- `design_spec_template.md`: new "Structure Image Input" and "NMR Prediction and Verification" sections.

### Changed

- **`candidate-generation-schema.md` merged into `candidate_schema.md`**: generation rules (buckets, mutation families, literature grounding) now live alongside the CSV column contracts in a single file. All SKILL.md references updated.
- **`gemini-scoring-protocol.md`**: NMR verification file added to Gemini prompt inputs; `nmr_verification_status` added to required output fields; NMR evidence use rule added.
- **AGENT_GUIDE.md**: updated workflow diagram, output contract, and execution checklist to reflect Steps 0.5, 3.5, 5.5, 9.5, 9.7 and all v0.2.x output files.
- **README.md**: workflow diagram and file listings updated for v0.2.1.

### Removed

- `references/candidate-generation-schema.md` (merged into `candidate_schema.md`)
- Duplicate v0.2.0 changelog block

### Notes

- NMR prediction requires no external tools — it uses Claude's native chemistry knowledge. Predictions are labeled "Claude-predicted" and subject to the same claim audit rules as xTB results.
- Structure image input works with Claude's multimodal capabilities; no OCR tool needed.

---

## v0.2.0 — 2026-05-31

Complete redesign. The monolithic SKILL.md is broken into a lean orchestrator (360 lines) plus ten focused protocol files. Three new mandatory quality gates — adversarial review, novelty check, and result-to-claim audit — close the loop between literature knowledge, candidate generation, and scoring. Zotero and active search now run as co-equal parallel streams before any candidate is proposed.

### Redesigned

- **SKILL.md restructured**: dropped from 1041 → 360 lines. All step-level detail moved into `references/` protocol files. The orchestrator now states *what* happens at each step and where to find the *how*.
- **`references/` directory**: ten new protocol files extracted from the old SKILL.md — each is a self-contained spec for one workflow step, readable independently and patchable without touching the orchestrator.

### Added

- Dual literature streams: Zotero extraction (Step 1.5-A) + active search (Step 1.5-B) run in parallel; neither is subordinate.
- Step 3.5: Gemini adversarial chemistry review with chemistry-skeptic prompt. Produces `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`.
- Step 5.5: Novelty check via `prior_art_search`. Produces `ROUND_N_NOVELTY_CHECK.md`.
- Step 9.5: Result-to-claim audit. `overclaim` flag blocks score ≥ 4 in Step 11. Produces `ROUND_N_CLAIM_AUDIT.md`.
- New output files: `ZOTERO_KNOWLEDGE_PACKET.md`, `ZOTERO_SEED_SMILES.csv`, `ACTIVE_SEARCH_PACKET.md`.
- New candidate columns: `zotero_source_key`, `zotero_source_title`, `zotero_grounding`.
- New decision columns: `prior_art_status`, `claim_audit_flag`, `gemini_adversarial_flag`.
- Zotero MCP and Gemini MCP are now named first-class roles. Claude does not self-review its own candidates.

### Notes

- Requires `mcp__zotero-mcp`, `mcp__gemini-review`, `mcp__gemini-research`. Each gate degrades gracefully when unavailable.
- xTB approval gate (Step 7) and core RDKit pipeline unchanged.

## v0.1.3 - 2026-05-19

This release tightens the public package around chemistry-facing molecule and polymer design.

### Added

- `SHARE_PACKAGE.md` and `SHARE_PACKAGE.zh-CN.md` to explain the installable skill package
- explicit polymer-design wording in the README and Chinese README
- clearer description of monomer, headgroup, and motif iteration as part of the design loop

### Changed

- status badge bumped from `v0.1.2` to `v0.1.3`
- README and Chinese README now describe the skill as a molecule/polymer design workflow rather than only a generic molecular-design package
- release notes now focus on user-visible changes instead of internal publishing steps
- share-package docs now describe the main skill, optional literature helper, and sanitized stage runner in one place

### Notes

- The main workflow behavior is unchanged in this release.
- xTB still requires explicit human approval after the RDKit gallery review.
- Gemini handoff remains part of the public workflow via `ROUND_N_GEMINI_INPUT.md`.

## v0.1.2 - 2026-05-18

GitHub-facing release-note refresh for the public repository.

### Added

- README release-track summary covering `v0.1.0 → v0.1.2`
- README `What's New` section with dated public-facing updates
- clearer release-history framing for current users landing directly on the repo homepage

### Changed

- status badge bumped from `v0.1.1` to `v0.1.2`
- README and Chinese README now present updates in a clearer release-summary format
- changelog remains aligned with actual repo history while becoming easier to scan from GitHub

### Notes

- No molecular-design workflow logic changed in this release
- Main skill behavior, stage runner behavior, and Gemini handoff behavior are unchanged from `v0.1.1`

## v0.1.1 - 2026-05-12

Published a sanitized source-only molecular design stage runner while keeping the Gemini handoff path intact.

### Added

- `molecule-design-stage-src/` source package extracted from a private working directory
- generic `run_design.py` reusable workflow entrypoint
- reusable `molecular_design/` modules for config loading, candidate generation, RDKit filtering, gallery rendering, xTB screening, approval, and reporting
- `inputs/example_run.yaml` for a public smoke-testable example run
- `tests/test_molecular_design_workflow.py` for the stage runner package

### Changed

- README and Chinese README now document the reusable stage runner package
- main skill docs now expose `ROUND_N_GEMINI_INPUT.md` as a formal workflow artifact
- public source defaults to `xtb` on `PATH` instead of a private local conda path

### Removed

- private desktop absolute paths from the public runner package
- project-specific generated outputs, xTB job directories, and private round result artifacts from the public release

## v0.1.0 - 2026-05-10

Initial public open-source packaging for the skill.

### Added

- Main Codex skill in `molecule-design-loop/`
- RDKit candidate filtering helper
- HTML candidate gallery renderer
- Design spec and xTB approval templates
- Optional `research-lit` companion skill
- Bilingual repository documentation
- `AGENT_GUIDE.md` for AI agents
- Contribution guides and `.gitignore`

### Changed

- README rewritten into a clearer open-source landing page
- Chinese README expanded into a full project overview

### Fixed

- `install_molecule_design_loop.sh --install-research-lit` now installs the optional skill from the correct directory structure
