# Molecule Design Loop Agent Guide

**For AI agents reading this repo.** If you are a human, start with [README.md](README.md).

`molecule-design-loop` is a Codex skill for constraint-driven molecular design. It turns a Markdown design brief into a reviewable candidate loop:

```text
[optional image extraction (0.5)]
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
→ ROUND_N_NMR_PREDICTIONS.csv (optional)             ← Step 9.7
→ ROUND_N_NMR_VERIFICATION.md (when exp. data)       ← Step 9.7
→ ROUND_N_DECISION.md (Gemini + Pareto)
→ next round or DESIGN_REPORT.md
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
- `molecule-design-loop/references/candidate_schema.md` — candidate CSV contract + generation rules
- `molecule-design-loop/references/design-loop-state-schema.md` — `DESIGN_LOOP_STATE.json` cross-round memory contract
- `molecule-design-loop/templates/design_spec_template.md` — design brief template
- `molecule-design-loop/templates/xtb_approval_template.md` — mandatory approval checkpoint template

Reference protocols in `molecule-design-loop/references/`:

| File | Step |
|---|---|
| `zotero-extraction-protocol.md` | 1.5-A — Zotero library mining |
| `active-search-protocol.md` | 1.5-B — latest + landmark papers |
| `candidate_schema.md` | 3 — CSV contracts, bucket rules, generation rules |
| `adversarial-review-protocol.md` | 3.5 — Gemini adversarial review |
| `synthesis-gate-schema.md` | 5 — synthesis feasibility gate |
| `novelty-check-protocol.md` | 5.5 — prior-art search |
| `structure-image-input-protocol.md` | 0.5 — extracting SMILES from images |
| `nmr-prediction-protocol.md` | 9.7 — NMR prediction and verification |
| `claim-audit-protocol.md` | 9.5 — evidence-to-claim matrix |
| `gemini-scoring-protocol.md` | 11 — scoring rubric, Pareto ranking |
| `design-loop-state-schema.md` | 1/3/4/12 — `DESIGN_LOOP_STATE.json` cross-round memory |
| `polymer-design-mode.md` | polymer/material branch |
| `xtb-integrity-rules.md` | xTB recording requirements |

## Output Contract

Prefer a project-local `molecule-design-stage/` directory with:

- `DESIGN_SPEC_LOCKED.md`
- `IMAGE_EXTRACTED_SMILES.csv` (when structure images provided)
- `ZOTERO_KNOWLEDGE_PACKET.md`
- `ZOTERO_SEED_SMILES.csv`
- `ACTIVE_SEARCH_PACKET.md`
- `LIT_PACKET.md`
- `ROUND_N_CANDIDATES.csv`
- `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`
- `ROUND_N_FILTERED.csv`
- `ROUND_N_SYNTHESIS_FEASIBILITY.csv`
- `ROUND_N_NOVELTY_CHECK.md`
- `ROUND_N_CANDIDATE_GALLERY.html`
- `ROUND_N_XTB_APPROVAL.md`
- `ROUND_N_XTB_RESULTS.csv`
- `ROUND_N_CLAIM_AUDIT.md`
- `ROUND_N_NMR_PREDICTIONS.csv` (optional)
- `ROUND_N_NMR_VERIFICATION.md` (optional)
- `ROUND_N_EXPERIMENT_RESULTS.csv` (when feedback available)
- `ROUND_N_GEMINI_INPUT.md`
- `ROUND_N_DECISION.md`
- `DESIGN_LOOP_STATE.json` (cross-round memory; schema in `references/design-loop-state-schema.md`)
- `DESIGN_REPORT.md`
- `xtb_jobs/`

## Execution Checklist

1. Extract structures from user-provided images if any (Step 0.5).
2. Lock the design brief into `DESIGN_SPEC_LOCKED.md`.
3. Run Zotero extraction (1.5-A) and active search (1.5-B) in parallel.
4. Merge into `LIT_PACKET.md`; flag contradictions.
5. Generate interpretable SMILES candidates tied to specific constraints. Before generating, read `DESIGN_LOOP_STATE.json` and exclude any candidate matching a `killed_motifs[]` SMARTS/scaffold (Step 3, Fix A); bias a portion toward `available_building_blocks[]` (Fix C).
6. Run Gemini adversarial review (Step 3.5) on raw candidates.
7. Run deterministic RDKit filtering with `--forbidden-smarts` = spec `forbidden_motifs` ∪ `DESIGN_LOOP_STATE.json` `killed_motifs[].smarts`; keep rejection reasons.
8. Run synthesis-feasibility gate (Step 5), emitting sortable `synthesis_cost` and `time_to_first_sample`.
9. Run novelty check (Step 5.5).
10. Render `ROUND_N_CANDIDATE_GALLERY.html`.
11. Pause for explicit user approval before any xTB run.
12. Run xTB only on approved candidates.
13. Run result-to-claim audit (Step 9.5).
14. Run NMR prediction/verification if requested (Step 9.7).
15. Ingest experimental feedback if available.
16. Score with Gemini + Pareto ranking; synthesis cost / time-to-first-sample is a mandatory ranking axis (Fix B).
17. Either iterate or write the final report. On iterate, write experimental `failure_mode` and adversarial `likely_lab_failure_mode` back into `DESIGN_LOOP_STATE.json` as structured `killed_motifs[]`/`failed_reactions[]` (Fix D).

## Hard Guardrails

- Do not treat xTB as proof of binding, selectivity, mechanism, or synthesis feasibility.
- Do not continue into xTB without explicit user approval.
- Do not collapse all candidates into near-duplicate variants.
- Do not discard rejected candidates silently; keep the rejection reason for later refinement.
- If a hard constraint is ambiguous, stop and ask a targeted question before expensive calculations.
- NMR predictions are Claude-native plausibility checks, not validated computational methods. Always label as "Claude-predicted."
- Structure image extractions with low confidence require user confirmation before proceeding.

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
