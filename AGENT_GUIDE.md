# Molecule Design Loop Agent Guide

**For AI agents reading this repo.** If you are a human, start with [README.md](README.md).

`molecule-design-loop` is a Codex skill for constraint-driven molecular design. It turns a Markdown design brief into a reviewable candidate loop:

```text
design_spec.md
→ literature packet
→ candidate SMILES
→ deterministic RDKit filtering
→ HTML structure gallery
→ explicit user approval
→ xTB evidence
→ Gemini constraint scoring
→ next round or final report
```

## Invocation

Codex:

```text
/molecule-design-loop "/path/to/design_spec.md"
```

Optional companion:

```text
/research-lit "topic"
```

If no design brief exists, start from:

- `examples/example_design_spec.md`
- `molecule-design-loop/templates/design_spec_template.md`

## When To Use This Skill

Use it when the user wants a molecule design loop with:

- explicit hard constraints
- interpretable candidate edits
- deterministic RDKit triage
- human review before xTB
- xTB used as low-cost evidence rather than as final judgment

Do not use it when the user wants xTB alone, docking alone, or unconstrained novelty generation.

## Core Files

- `molecule-design-loop/SKILL.md` — main specification
- `molecule-design-loop/scripts/rdkit_filter_candidates.py` — filter and annotate candidate CSV files
- `molecule-design-loop/scripts/render_candidate_gallery.py` — render HTML gallery from filtered CSV
- `molecule-design-loop/references/candidate_schema.md` — candidate CSV contract
- `molecule-design-loop/templates/design_spec_template.md` — design brief template
- `molecule-design-loop/templates/xtb_approval_template.md` — mandatory approval checkpoint template

## Output Contract

Prefer a project-local `molecule-design-stage/` directory with:

- `DESIGN_SPEC_LOCKED.md`
- `LIT_PACKET.md`
- `ROUND_N_CANDIDATES.csv`
- `ROUND_N_FILTERED.csv`
- `ROUND_N_CANDIDATE_GALLERY.html`
- `ROUND_N_XTB_APPROVAL.md`
- `ROUND_N_XTB_RESULTS.csv`
- `ROUND_N_DECISION.md`
- `DESIGN_LOOP_STATE.json`
- `DESIGN_REPORT.md`
- `xtb_jobs/`

## Execution Checklist

1. Lock the design brief into `DESIGN_SPEC_LOCKED.md`.
2. Separate hard constraints, soft preferences, forbidden motifs, and xTB proxy targets.
3. Build a small literature packet from local context plus recent papers.
4. Generate interpretable SMILES candidates tied to specific constraints.
5. Run deterministic RDKit filtering and keep rejection reasons.
6. Render `ROUND_N_CANDIDATE_GALLERY.html`.
7. Pause for explicit user approval before any xTB run.
8. Run xTB only on approved candidates.
9. Ask Gemini to score candidates against the locked brief using xTB as supporting evidence.
10. Either iterate or write the final report.

## Hard Guardrails

- Do not treat xTB as proof of binding, selectivity, mechanism, or synthesis feasibility.
- Do not continue into xTB without explicit user approval.
- Do not collapse all candidates into near-duplicate variants.
- Do not discard rejected candidates silently; keep the rejection reason for later refinement.
- If a hard constraint is ambiguous, stop and ask a targeted question before expensive calculations.

## Local Validation

Useful checks in this repo:

```bash
python3 molecule-design-loop/scripts/test_rdkit_filter_candidates.py
python3 molecule-design-loop/scripts/test_render_candidate_gallery.py
```

Install locally with:

```bash
bash install_molecule_design_loop.sh
```

## Source Of Truth

- Workflow behavior: `molecule-design-loop/SKILL.md`
- Candidate table contract: `molecule-design-loop/references/candidate_schema.md`
- Human-oriented overview: `README.md`
