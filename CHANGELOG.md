# Changelog

All notable changes to `molecule-design-loop` will be tracked in this file.

## v0.1.3 - 2026-05-19

Verified the public repo against the current local skill source tree and refreshed the package-scope docs.

### Added

- `SHARE_PACKAGE.md` and `SHARE_PACKAGE.zh-CN.md` to explain what is bundled from the local share package

### Changed

- status badge bumped from `v0.1.2` to `v0.1.3`
- README and Chinese README now document the local-source sync check, link the share-package scope notes, and explicitly call out polymer-design positioning in the public docs
- public packaging docs now clarify that `related-skills/` helper files are local context only and are not bundled in the public repo

### Notes

- `molecule-design-loop/SKILL.md`, `examples/example_design_spec.md`, and `research-lit` were re-checked against the local working copy before syncing GitHub
- the public installer keeps the newer directory-based optional-skill install logic
- the public update log now explicitly states that this repo also targets polymer-design workflows, not only generic molecular-design packaging
- No molecular-design workflow logic changed in this release

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
