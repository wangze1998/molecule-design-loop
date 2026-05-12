# Molecule Design Stage Source Package

This folder contains a sanitized, source-only version of a reusable molecular design stage runner.

It was extracted from a private `molecule-design-stage/` working directory, but the public package intentionally omits:

- generated candidate/result files
- local desktop absolute paths
- project-specific round scripts
- xTB job outputs
- presentation exports and other private reporting artifacts

## Included

- `run_design.py` — main reusable entrypoint
- `molecular_design/` — workflow modules
- `inputs/example_run.yaml` — public example config
- `tests/test_molecular_design_workflow.py` — smoke tests

## Gemini Handoff

The public runner keeps the Gemini review handoff path. After xTB completes, it can write:

- `ROUND_N_GEMINI_INPUT.md`

That file is intended as a structured handoff for Gemini review against the locked design brief.

## Example

```bash
python3 run_design.py --config inputs/example_run.yaml --step prepare
python3 run_design.py --config inputs/example_run.yaml --step report
```

## Notes

- The runtime artifact directory is still named `molecule-design-stage/`.
- The public source package lives in `molecule-design-stage-src/` so it does not collide with runtime outputs.
- xTB defaults to `xtb` on `PATH` unless overridden in the config.
