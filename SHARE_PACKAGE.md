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

Checked on `2026-05-19`:

- `molecule-design-loop/SKILL.md` in this repo matches the local source copy
- `examples/example_design_spec.md` in this repo matches the local source copy
- `optional-skills/research-lit/SKILL.md` matches the local context copy from `related-skills/research-lit.SKILL.md`
- the public installer intentionally keeps the newer directory-based `--install-research-lit` behavior

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
