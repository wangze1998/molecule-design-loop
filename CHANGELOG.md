# Changelog

All notable changes to `molecule-design-loop` will be tracked in this file.

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
