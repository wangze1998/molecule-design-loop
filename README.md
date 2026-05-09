# Molecule Design Loop

An open Codex skill for constraint-driven molecular design with deterministic RDKit screening, visual candidate review, explicit user approval before xTB, and Gemini-guided iteration.

中文说明见 [README.zh-CN.md](README.zh-CN.md).

## Why this exists

Most "LLM for molecule design" workflows break in one of two ways:

- they generate a lot of molecules but do not make the design logic legible
- they run cheap quantum screening too early, before obvious structural issues are filtered out

`molecule-design-loop` is designed as a practical middle layer:

- literature-informed candidate generation
- deterministic RDKit filtering
- RDKit-rendered HTML candidate gallery
- mandatory human approval before xTB
- Gemini scoring against the locked design brief, with xTB used as evidence rather than the scorer

## Workflow

```text
design_spec.md
→ literature packet
→ SMILES candidates
→ RDKit filtering
→ RDKit HTML gallery
→ user structural approval
→ xTB screening
→ Gemini constraint scoring
→ next design round
```

## What is included

- `molecule-design-loop/`
  - main Codex skill
  - RDKit descriptor and medicinal-chemistry filter helper
  - RDKit HTML gallery renderer
  - xTB approval checkpoint template
- `examples/example_design_spec.md`
- `optional-skills/research-lit/SKILL.md`
- `install_molecule_design_loop.sh`

## Highlights

- Constraint-first rather than novelty-first
- Keeps rejected candidates and rejection reasons for later refinement
- Uses RDKit for structure sanity, alerts, and diversity-aware selection
- Generates a human-readable HTML gallery before any xTB run
- Forces explicit user approval before xTB starts
- Lets Gemini score alignment to the design brief while keeping xTB in an evidence-only role

## Requirements

- Codex with a local skills directory
- Python 3
- RDKit installed in the Python environment

Optional:

- xTB for the quantum screening stage
- `research-lit` if you want a literature helper alongside this skill
- `gemini-research` if your Codex setup supports it

## Installation

```bash
bash install_molecule_design_loop.sh
```

If you also want the optional `research-lit` companion skill:

```bash
bash install_molecule_design_loop.sh --install-research-lit
```

By default this installs to:

```text
$CODEX_HOME/skills/molecule-design-loop
```

If `CODEX_HOME` is not set, it falls back to:

```text
~/.codex/skills/molecule-design-loop
```

## Usage

```text
/molecule-design-loop "/path/to/design_spec.md"
```

Example:

```text
/molecule-design-loop "/path/to/example_design_spec.md"
```

## Key design rule

xTB is not the decision-maker.

This skill treats xTB as a low-cost computational evidence source. Final ranking is driven by the locked design specification plus Gemini's structured scoring, after the user has visually approved candidate structures.

## Repository structure

```text
.
├── molecule-design-loop/
├── examples/
├── optional-skills/
└── install_molecule_design_loop.sh
```

## License

MIT

## If you use this

If this skill helps your workflow, a star on GitHub helps more people find it.
