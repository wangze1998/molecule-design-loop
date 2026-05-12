# Molecule Design Loop

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Codex Skill](https://img.shields.io/badge/Codex-skill-black)
![Status](https://img.shields.io/badge/status-v0.1.1-blue)

Open Codex skill for constraint-driven molecular design with deterministic RDKit filtering, visual candidate review, explicit user approval before xTB, and Gemini-guided iteration.

[English](README.md) | [中文说明](README.zh-CN.md)

AI agents: read [AGENT_GUIDE.md](AGENT_GUIDE.md) first. It is written for LLM consumption rather than human browsing.

> Constraint-first molecular design: filter obvious bad structures early, review molecules visually before xTB, and use xTB as evidence instead of as the final judge.

## Project Status

- Current release line: `v0.1.1`
- Repo focus: publishable Codex skill plus helper scripts and templates
- Release notes: [CHANGELOG.md](CHANGELOG.md) | [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)

## Why this repo exists

Many "LLM for molecule design" workflows fail in predictable ways:

- they generate many molecules but make the design logic hard to audit
- they push cheap quantum screening too early, before basic structural issues are removed
- they blur the line between computational evidence and scientific decision-making

`molecule-design-loop` is a practical middle layer for that gap.

## What the skill does

- Reads a Markdown design brief with hard constraints, soft preferences, and xTB proxy targets
- Builds a literature packet from local context plus recent papers
- Proposes interpretable SMILES candidates instead of novelty-only free-form generations
- Applies deterministic RDKit checks for validity, descriptors, alerts, and scaffold diversity
- Renders an HTML candidate gallery for human review before any xTB run
- Requires explicit user approval before xTB starts
- Uses Gemini to score candidates against the locked design brief after evidence is collected

## Workflow

```text
design_spec.md
→ DESIGN_SPEC_LOCKED.md
→ LIT_PACKET.md
→ ROUND_N_CANDIDATES.csv
→ ROUND_N_FILTERED.csv
→ ROUND_N_CANDIDATE_GALLERY.html
→ user approval checkpoint
→ ROUND_N_XTB_RESULTS.csv
→ ROUND_N_DECISION.md
→ next round or final DESIGN_REPORT.md
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
- `references/candidate_schema.md`
- `templates/design_spec_template.md`
- `templates/xtb_approval_template.md`

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
└── install_molecule_design_loop.sh
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) or [CONTRIBUTING_CN.md](CONTRIBUTING_CN.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) or [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md).

## License

[MIT](LICENSE)
