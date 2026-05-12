# Changelog

All notable changes to `molecule-design-loop` will be tracked in this file.

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
