# Share Package

This document records the current shareable package scope for `molecule-design-loop` and how it maps back to the local working tree.

## Included In The Public Repo

- `molecule-design-loop/` — main public Codex skill
- `examples/example_design_spec.md` — public example input
- `optional-skills/research-lit/SKILL.md` — optional literature companion
- `install_molecule_design_loop.sh` — public installer
- `molecule-design-stage-src/` — sanitized reusable stage-runner source package
- top-level docs such as `README*`, `CHANGELOG*`, `CONTRIBUTING*`, and `AGENT_GUIDE.md`

## Verified Against The Local Source Tree

Checked on `2026-06-06` (v0.2.1):

- `molecule-design-loop/SKILL.md` in this repo matches the local source copy
- `molecule-design-loop/references/` — all 12 protocol files synced (including new `structure-image-input-protocol.md` and `nmr-prediction-protocol.md`; `candidate-generation-schema.md` merged into `candidate_schema.md`)
- `molecule-design-loop/templates/design_spec_template.md` synced (new image input and NMR sections)
- `examples/example_design_spec.md` in this repo matches the local source copy
- `optional-skills/research-lit/SKILL.md` matches the local context copy from `related-skills/research-lit.SKILL.md`
- the public installer intentionally keeps the newer directory-based `--install-research-lit` behavior

## Not Yet Verified Against The Local Source Tree

Changes made in the repo since the `2026-06-06` check above, which have **not** been reconciled with the local source tree:

- `v0.2.5` added a 13th protocol file, `molecule-design-loop/references/ranking-diagnostics-protocol.md`, and edited `SKILL.md`, `gemini-scoring-protocol.md`, `candidate_schema.md`, and `xtb-integrity-rules.md`.
- `v0.2.2`–`v0.2.4` edits to `SKILL.md`, `design-loop-state-schema.md`, `synthesis-gate-schema.md`, and `claim-audit-protocol.md`.

Re-run the local-vs-repo comparison and date a fresh check before treating the list above as current.

## Local-Only Items Not Bundled

- `related-skills/meta-optimize.SKILL.md`
- `related-skills/novelty-check.SKILL.md`
- `related-skills/research-wiki.SKILL.md`
- local packaging outputs such as `dist/`
- cache files such as `__pycache__/` and `.pytest_cache/`
- generated run artifacts such as `molecule-design-stage/` outputs

## Why Some Local Files Stay Local

- some files are context helpers from the broader local Codex skill library, not part of the main share package
- some files are generated artifacts or machine-local packaging outputs
- the public repo is meant to stay portable, minimal, and safe to publish
