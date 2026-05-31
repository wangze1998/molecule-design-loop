# Changelog

All notable changes to `molecule-design-loop` will be tracked in this file.

---

## v0.2.0 — 2026-05-31

Complete redesign. The monolithic SKILL.md is broken into a lean orchestrator (360 lines) plus ten focused protocol files. Three new mandatory quality gates — adversarial review, novelty check, and result-to-claim audit — close the loop between literature knowledge, candidate generation, and scoring. Zotero and active search now run as co-equal parallel streams before any candidate is proposed.

### Redesigned

- **SKILL.md restructured**: dropped from 1041 → 360 lines. All step-level detail moved into `references/` protocol files. The orchestrator now states *what* happens at each step and where to find the *how*.
- **`references/` directory**: ten new protocol files extracted from the old SKILL.md — each is a self-contained spec for one workflow step, readable independently and patchable without touching the orchestrator.

### New reference files

| File | Covers |
|---|---|
| `zotero-extraction-protocol.md` | Step 1.5-A — how to mine the Zotero library for scaffolds, SAR, routes, failures |
| `active-search-protocol.md` | Step 1.5-B — parallel search for latest + landmark papers |
| `candidate-generation-schema.md` | Step 3 — bucket rules, grounding requirements, polymer-specific fields |
| `adversarial-review-protocol.md` | Step 3.5 — Gemini system prompt, flag logic, output schema |
| `synthesis-gate-schema.md` | Step 5 — column contract, promotion rules |
| `novelty-check-protocol.md` | Step 5.5 — prior-art search, status values, demotion rules |
| `claim-audit-protocol.md` | Step 9.5 — evidence-to-claim matrix, `auditor_flag` values |
| `gemini-scoring-protocol.md` | Step 11 — scoring rubric, Pareto ranking, required output fields |
| `polymer-design-mode.md` | Full polymer/material branch — display rules, surrogate logic, non-xTB targets |
| `xtb-integrity-rules.md` | xTB recording requirements and chemistry design rules |

### Added

- Dual literature streams: Zotero extraction (Step 1.5-A) + active search (Step 1.5-B) run in parallel; neither is subordinate.
- Step 3.5: `mcp__gemini-review__review` with chemistry-skeptic system prompt challenges every candidate batch before RDKit filtering. Produces `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`.
- Step 5.5: `mcp__gemini-research__prior_art_search` flags already-reported structures. `known` candidates are automatically downgraded to control role. Produces `ROUND_N_NOVELTY_CHECK.md`.
- Step 9.5: `mcp__gemini-review__review` with claim-auditor prompt maps each xTB/RDKit result to exactly what it proves. `overclaim` flag blocks score ≥ 4 in Step 11. Produces `ROUND_N_CLAIM_AUDIT.md`.
- New output files: `ZOTERO_KNOWLEDGE_PACKET.md`, `ZOTERO_SEED_SMILES.csv`, `ACTIVE_SEARCH_PACKET.md`, `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`, `ROUND_N_NOVELTY_CHECK.md`, `ROUND_N_CLAIM_AUDIT.md`.
- New candidate columns: `zotero_source_key`, `zotero_source_title`, `zotero_grounding`.
- New decision columns: `prior_art_status`, `claim_audit_flag`, `gemini_adversarial_flag`.
- `design_spec_template.md`: Zotero Library Integration section (search scope, collection, tags).
- Zotero MCP and Gemini MCP are now named first-class roles in the Role Split. Claude does not self-review its own candidates.

### Notes

- Requires `mcp__zotero-mcp`, `mcp__gemini-review`, `mcp__gemini-research` in the Codex MCP config. Each gate degrades gracefully when its server is unavailable.
- xTB approval gate (Step 7) and core RDKit pipeline are unchanged.

---

### Added

- **Dual literature intelligence** (Step 1.5-A + 1.5-B): two parallel streams now run before candidate generation — the user's Zotero library (personal curated knowledge) and an independent active search for the latest and most authoritative papers. Neither is subordinate to the other; `LIT_PACKET.md` merges both. Contradictions between the two streams are flagged explicitly rather than silently resolved.
- **Zotero knowledge extraction** (Step 1.5-A): `mcp__zotero-mcp__*` tools are called first to mine the user's personal paper collection for proven scaffolds, SAR rules, synthesis routes, and known failure modes. Produces `ZOTERO_KNOWLEDGE_PACKET.md` and `ZOTERO_SEED_SMILES.csv`. If Zotero is unavailable the workflow falls back gracefully to active search alone.
- **Active literature search** (Step 1.5-B): `mcp__gemini-research__literature_search` now runs as a parallel mandatory step targeting the last 1-2 years of publications and the most-cited landmark papers in the field — papers the user may not yet have in Zotero. Produces `ACTIVE_SEARCH_PACKET.md`.
- **Gemini adversarial chemistry review** (Step 3.5): `mcp__gemini-review__review` is called immediately after candidate generation with a chemistry-skeptic system prompt. Gemini reads the raw candidate CSV directly — not a Claude summary — and challenges each candidate's design-move logic, synthesis plausibility, and expected proxy effect. Produces `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`; candidates receive a `gemini_adversarial_flag` (`pass`/`warn`/`revise`) before RDKit filtering.
- **Novelty check** (Step 5.5): `mcp__gemini-research__prior_art_search` runs after the synthesis feasibility gate to flag candidates that match already-reported structures. Candidates with `prior_art_status: known` are automatically downgraded to control role; `analog` candidates retain promotion status but must cite the prior analog. Runs async to avoid blocking. Produces `ROUND_N_NOVELTY_CHECK.md`.
- **Result-to-claim audit** (Step 9.5): `mcp__gemini-review__review` runs after xTB with a claim-auditor system prompt. For every xTB/RDKit number, Gemini states what it proves, what it cannot prove, and what additional evidence is needed for synthesis promotion. Candidates flagged `overclaim` cannot receive a score of 4 or 5 in Step 11 until corrected. Produces `ROUND_N_CLAIM_AUDIT.md`.
- New columns in `ROUND_N_CANDIDATES.csv`: `zotero_source_key`, `zotero_source_title`, `zotero_grounding` (`scaffold`/`sar_rule`/`design_principle`/`field_consensus`/`none`).
- New columns in `ROUND_N_DECISION.md`: `prior_art_status`, `claim_audit_flag`, `gemini_adversarial_flag`.
- New output files: `ZOTERO_KNOWLEDGE_PACKET.md`, `ZOTERO_SEED_SMILES.csv`, `ACTIVE_SEARCH_PACKET.md`, `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`, `ROUND_N_NOVELTY_CHECK.md`, `ROUND_N_CLAIM_AUDIT.md`.
- **Zotero Library Integration** section in `design_spec_template.md`: users can configure search keywords, collection scope, and tags; the spec's seed structures section is now pre-populated from Zotero extraction.
- New constants: `ZOTERO_SEARCH_QUERIES`, `ZOTERO_METADATA_LIMIT`, `ZOTERO_FULLTEXT_PAPERS`, `LITERATURE_STREAMS`, `ACTIVE_SEARCH_TARGETS`, `GEMINI_REVIEW_MODEL`, `GEMINI_ADVERSARIAL_REVIEW`, `NOVELTY_CHECK`, `CLAIM_AUDIT`, `ZOTERO_TRACE_REQUIRED`.

### Changed

- **Role split updated**: Zotero MCP, Gemini research, and Gemini adversarial reviewer are now first-class named roles. Codex (Claude) no longer self-reviews its own generated candidates — adversarial review belongs to Gemini.
- **Step 2 (literature packet)** now merges `ZOTERO_KNOWLEDGE_PACKET.md` and `ACTIVE_SEARCH_PACKET.md` rather than running an external search from scratch. External search fills only the gaps identified by the Zotero extraction.
- **Step 3 candidate generation**: 90 % of candidates must trace back to a Zotero or active-search source (`zotero_grounding ≠ none`); unsourced exploratory candidates are capped at 10 %.
- **Step 11 Gemini scoring** now uses `mcp__gemini-review__review` in a fresh thread, reads the adversarial review, novelty check, and claim audit before scoring, and cannot assign 4 or 5 to any candidate with an unresolved `overclaim` flag.
- Status badge bumped from `v0.1.3` to `v0.2.0`.

### Notes

- Zotero MCP (`mcp__zotero-mcp`) and Gemini MCPs (`mcp__gemini-review`, `mcp__gemini-research`) must be configured in the Codex MCP server list for Steps 1.5, 3.5, 5.5, 9.5, and 11 to use their respective tools. The skill falls back gracefully when a server is unavailable.
- xTB still requires explicit human approval after the RDKit gallery review (Step 7 unchanged).
- The core RDKit filtering pipeline and xTB integrity rules are unchanged.

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
