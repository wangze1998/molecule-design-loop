# Molecule Design Loop

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Codex Skill](https://img.shields.io/badge/Codex-skill-black)
![Status](https://img.shields.io/badge/status-v0.2.4-blue)

Open Codex skill for constraint-driven molecule and polymer design. Integrates the user's Zotero library and local Gemini MCP for dual-stream literature intelligence, adversarial chemistry review, novelty checking, and result-to-claim auditing — alongside RDKit filtering, visual candidate review, and explicit user approval before xTB. Now supports structure image input and Claude-native NMR prediction.

[English](README.md) | [中文说明](README.zh-CN.md) | [Changelog](CHANGELOG.md) | [Share Package](SHARE_PACKAGE.md)

> **Current release: v0.2.4** (2026-08-21). New: the loop is now honest about itself. It must declare which design objectives it produced **no evidence** for — the claim audit now runs even without xTB whenever the objective is affinity, potency, selectivity, self-assembly or similar — and it keeps a `loop_calibration` track record of how often its own recommendations actually worked, reported unflattering results included. See [CHANGELOG.md](CHANGELOG.md).
> **Human approval stays mandatory before xTB.** **Zotero MCP and Gemini MCP must be configured** for the new steps — the skill falls back gracefully when they are unavailable.

AI agents: read [AGENT_GUIDE.md](AGENT_GUIDE.md) first. It is written for LLM consumption rather than human browsing.

> Constraint-first molecular design: filter obvious bad structures early, review molecules visually before xTB, and use xTB as evidence instead of as the final judge.

## Project Status

- Current release: `v0.2.4` — evidence-gap declaration + loop self-calibration
- Repo focus: modular Codex skill for Zotero-grounded, adversarially reviewed molecular design
- Release notes: [CHANGELOG.md](CHANGELOG.md) | [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)
- Share-package scope: [SHARE_PACKAGE.md](SHARE_PACKAGE.md) | [SHARE_PACKAGE.zh-CN.md](SHARE_PACKAGE.zh-CN.md)

## Release Track

**v0.2.4** (2026-08-21) — The loop must now say what it does *not* know. Claim audit triggers on un-evidenceable objectives (affinity, potency, selectivity, self-assembly…) even when xTB never ran, emitting `no_direct_evidence`. New `loop_calibration` block tracks promoted-vs-worked and prediction-vs-outcome, reported honestly in `DESIGN_REPORT.md`.

**v0.2.3** (2026-08-10) — Synthesis practicality became multi-objective and enforcing: new `overall_yield_estimate` and `hazard_toxicity_flag` gate columns, optional `route_alternatives` trade-off profile, and Step 11 ranking by Pareto *dominance* over {property fit, cost, time, yield, hazard} instead of a tiebreak. Dominated candidates cannot enter the top 3.

**v0.2.2** (2026-06-12) — Enforced cross-round failure memory: `DESIGN_LOOP_STATE.json` schema defined, killed motifs excluded at Steps 3/4. Synthesis cost / time-to-first-sample is now a first-class Pareto axis (Step 11), building-block availability biases generation (Steps 1/3), and experimental + adversarial lab failures flow back into state (Step 12).

**v0.2.1** (2026-06-06) — Structure image input (Step 0.5) and NMR prediction/verification (Step 9.7). Duplicate `candidate-generation-schema.md` merged into `candidate_schema.md`. AGENT_GUIDE and README updated.

**v0.2.0** (2026-05-31) — Complete redesign. SKILL.md restructured from 1041 → 360 lines; ten protocol reference files extracted. Dual Zotero + active-search literature streams. Three new mandatory gates: adversarial chemistry review (Step 3.5), novelty check (Step 5.5), result-to-claim audit (Step 9.5). Gemini and Zotero MCPs are now named first-class roles.

**v0.1.3** (2026-05-19) — Polymer-design documentation and package notes.

**v0.1.2** (2026-05-18) — Repository landing-page refresh. No workflow logic changed.

**v0.1.1** (2026-05-12) — Sanitized stage-runner source package (`molecule-design-stage-src/`).

**v0.1.0** (2026-05-10) — Initial public open-source packaging.

## Why this repo exists

Many "LLM for molecule design" workflows fail in predictable ways:

- they generate molecules without grounding them in the field's known scaffolds and SAR
- they let the same model that designed a candidate also score it — no adversarial check
- they push xTB numbers into design conclusions without auditing what the numbers actually prove

`molecule-design-loop` is a structured loop against those failure modes.

## What's New

- **2026-08-21** — v0.2.4: un-evidenced design objectives must be declared (claim audit no longer requires xTB to fire), and the loop keeps score of its own hit rate. See [CHANGELOG.md](CHANGELOG.md).
- **2026-08-10** — v0.2.3: synthesis practicality is a dominance criterion, not a tiebreaker; yield and hazard axes added; route trade-offs recorded instead of collapsed into one cost number. See [CHANGELOG.md](CHANGELOG.md).
- **2026-06-12** — v0.2.2: enforced cross-round failure memory (`DESIGN_LOOP_STATE.json` schema; killed motifs excluded at Steps 3/4), synthesis-cost ranking axis, availability-biased generation, and lab-failure feedback. See [CHANGELOG.md](CHANGELOG.md).
- **2026-06-06** — v0.2.1: structure image input and NMR prediction/verification. Schema files consolidated. See [CHANGELOG.md](CHANGELOG.md).
- **2026-05-31** — v0.2.0: complete redesign. Modular reference files, dual literature streams, Gemini adversarial reviewer, novelty gate, result-to-claim audit.
- **2026-05-19** — v0.1.3: polymer-design scope and share-package notes.
- **2026-05-12** — v0.1.1: sanitized [`molecule-design-stage-src/`](molecule-design-stage-src/) package.
- **2026-05-10** — v0.1.0: initial public release.

## What the skill does

**Structure image input** (Step 0.5): Users can provide journal figures, ChemDraw screenshots, or hand-drawn sketches instead of typing SMILES. Claude extracts structures directly from images, validates with RDKit, and feeds confirmed seeds into the design spec.

**Literature intelligence**: Zotero personal library (Steps 1.5-A) and active field search (Step 1.5-B) run in parallel. Both are mandatory. `LIT_PACKET.md` merges the two streams; contradictions are flagged, not silently resolved.

**Candidate generation**: Every proposal must trace to a scaffold, SAR rule, or design principle from `LIT_PACKET.md`. Unsourced exploratory candidates are capped at 10% of each round.

**Adversarial review** (Step 3.5): Gemini reads the raw candidate CSV with a chemistry-skeptic prompt before RDKit filtering. Challenges each candidate's design logic, synthesis plausibility, and expected proxy effect. Claude does not review its own candidates.

**Deterministic triage** (Step 4): RDKit validity, MW/logP/TPSA, PAINS/Brenk alerts, Murcko scaffold deduplication. Synthesis feasibility gate (Step 5) requires a plausible make/buy route before gallery promotion.

**Novelty check** (Step 5.5): `prior_art_search` flags already-reported structures before the visual gallery. `known` candidates are automatically demoted to control role.

**Human-in-the-loop** (Step 6–7): RDKit-rendered HTML gallery with structure depictions, filter decisions, and design rationale. Explicit user approval required before any xTB run.

**Result-to-claim audit** (Step 9.5): After xTB, Gemini maps each computed number to exactly what it proves and what it cannot prove. `overclaim` flag blocks a score ≥ 4 in Step 11.

**NMR prediction and verification** (Step 9.7, optional): Claude predicts 1H/13C NMR spectra for top candidates using its internal chemistry knowledge. When experimental NMR data is available, a predicted-vs-experimental comparison produces a structural verification status. Based on Anthropic's "Making Claude a Chemist" research (±0.079 ppm 1H accuracy).

**Iterative scoring** (Step 11): Gemini reads design spec + adversarial review + novelty check + claim audit + NMR verification in a fresh thread. Pareto ranking across hard-constraint pass, synthesis feasibility, evidence level, and soft preferences.

Both small-molecule and polymer/material design are supported. Polymer candidates use finite capped oligomers for RDKit/xTB; polymer-level properties that cannot be inferred from surrogates are listed as non-xTB targets.

## Workflow

```text
[structure images → IMAGE_EXTRACTED_SMILES.csv]       ← Step 0.5 (optional)
→ design_spec.md
→ [Zotero extraction (1.5-A) || active search (1.5-B)]  ← parallel
→ LIT_PACKET.md (merged)
→ ROUND_N_CANDIDATES.csv
→ ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md              ← Step 3.5
→ ROUND_N_FILTERED.csv (RDKit)
→ ROUND_N_SYNTHESIS_FEASIBILITY.csv
→ ROUND_N_NOVELTY_CHECK.md                           ← Step 5.5
→ ROUND_N_CANDIDATE_GALLERY.html
→ user approval checkpoint                           ← mandatory
→ ROUND_N_XTB_RESULTS.csv
→ ROUND_N_CLAIM_AUDIT.md                             ← Step 9.5
→ ROUND_N_NMR_PREDICTIONS.csv                       ← Step 9.7 (optional)
→ ROUND_N_DECISION.md (Gemini + Pareto)
→ next round or DESIGN_REPORT.md
```

## Quick Start

Install the main skill:

```bash
bash install_molecule_design_loop.sh
```

Install the main skill plus the optional literature helper:

```bash
bash install_molecule_design_loop.sh --install-research-lit
```

Invoke the skill in Codex:

```text
/molecule-design-loop "/path/to/design_spec.md"
```

Example input files:

- [`examples/example_design_spec.md`](examples/example_design_spec.md)
- [`molecule-design-loop/templates/design_spec_template.md`](molecule-design-loop/templates/design_spec_template.md)

Default install target:

```text
$CODEX_HOME/skills/molecule-design-loop
```

Fallback when `CODEX_HOME` is unset:

```text
~/.codex/skills/molecule-design-loop
```

## Reusable Stage Runner

This repo also includes a sanitized source-only stage runner extracted from a private `molecule-design-stage/` working directory:

- [`molecule-design-stage-src/`](molecule-design-stage-src/)
- main entrypoint: [`molecule-design-stage-src/run_design.py`](molecule-design-stage-src/run_design.py)
- Gemini handoff artifact preserved as `ROUND_N_GEMINI_INPUT.md`

Example:

```bash
python3 molecule-design-stage-src/run_design.py \
  --config molecule-design-stage-src/inputs/example_run.yaml \
  --step prepare
```

## What is included

- `molecule-design-loop/`
- `molecule-design-stage-src/`
- `examples/example_design_spec.md`
- `optional-skills/research-lit/SKILL.md`
- `install_molecule_design_loop.sh`

Bundled helpers inside `molecule-design-loop/`:

- `scripts/rdkit_filter_candidates.py`
- `scripts/render_candidate_gallery.py`
- `references/candidate_schema.md` — CSV contracts + generation rules
- `references/structure-image-input-protocol.md` — Step 0.5
- `references/nmr-prediction-protocol.md` — Step 9.7
- 10 additional protocol files in `references/` (see [AGENT_GUIDE.md](AGENT_GUIDE.md))
- `templates/design_spec_template.md`
- `templates/xtb_approval_template.md`

Packaging details are documented in [SHARE_PACKAGE.md](SHARE_PACKAGE.md).

## Design Principles

- Constraints first, novelty second
- xTB is evidence, not the final decision-maker
- Human structural review happens before xTB
- Rejected candidates and rejection reasons are kept for later refinement
- Candidate rounds should test interpretable design moves, not near-duplicate noise

## Requirements

- Codex with access to a local skills directory
- Python 3
- RDKit installed in the Python environment

Optional:

- xTB for the quantum-screening stage
- `research-lit` as a companion literature skill
- `gemini-research` if your Codex setup supports it

## Repository Layout

```text
.
├── AGENT_GUIDE.md
├── CONTRIBUTING.md
├── CONTRIBUTING_CN.md
├── examples/
├── molecule-design-stage-src/
├── molecule-design-loop/
├── optional-skills/
├── README.md
├── README.zh-CN.md
├── SHARE_PACKAGE.md
├── SHARE_PACKAGE.zh-CN.md
└── install_molecule_design_loop.sh
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) or [CONTRIBUTING_CN.md](CONTRIBUTING_CN.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) or [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md).

## License

[MIT](LICENSE)
