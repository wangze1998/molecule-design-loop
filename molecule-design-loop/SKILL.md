---
name: "molecule-design-loop"
description: "Constraint-driven design loop for small molecules, polymers and materials. Use when the user asks to design molecules, ligands, inhibitors, hosts, catalysts, dyes, photoswitches, monomers, repeat units or copolymers against a written design spec; for SAR-guided analog series; or for an autonomous design round with literature grounding, RDKit filtering, synthesis-feasibility triage, structural review before calculation, optional xTB evidence, and scored iteration. Mines the user's Zotero library and searches current literature in parallel. Triggers: molecule design loop, design a series, 分子设计, 设计一轮候选物, candidate generation, scaffold optimisation, polymer repeat-unit design."
license: "MIT"
metadata:
  version: "0.4.0"
  requires: "Python 3.9+, RDKit; PyYAML for build_candidates.py"
---

# Molecule Design Loop

Turns a written design spec into reviewable candidate rounds. Literature grounds the
candidates, deterministic code filters them, a human approves the structures, and
scoring decides what the next round changes.

```text
design_spec.md → [Zotero ‖ active search] → LIT_PACKET → candidates → adversarial review
→ RDKit filter → synthesis gate → novelty check → gallery → USER APPROVAL
→ xTB → claim audit → scoring + diagnostics → next round or report
```

Literature comes from two streams that run in parallel and rank equally: the user's
**Zotero library** (what they have read and trust) and an **active search** (recent
and landmark work they may not have). Neither is subordinate; `LIT_PACKET.md` merges
both and flags contradictions rather than silently picking one.

## Modes

Pick from the request and the spec; ask one short question if genuinely ambiguous.

- **Small molecule** — a discrete molecule, ligand, inhibitor, host/guest, catalyst,
  dye, photoswitch, or a scaffold series with no repeat-unit intent.
- **Polymer / material** — mentions polymer, oligomer, monomer, repeat unit,
  copolymer, BigSMILES, DP, Mn, dispersity, tacticity, morphology, film, or a
  polymerisation route. See [references/polymer-design-mode.md](references/polymer-design-mode.md).

These are siblings. Do not run polymer work as a sub-case of small-molecule work.

## Roles

| Actor | Does | Must not |
|---|---|---|
| Claude | orchestrates files, scripts, tables, iteration | review its own candidates |
| Zotero MCP | personal curated knowledge, scaffolds, SAR context | stand in for the field |
| Gemini research | active search, prior-art checks | — |
| Gemini review | independent adversarial critique and claim audit | receive a Claude-written summary |
| RDKit | parsing, dedup, descriptors, depiction | judge synthesisability |
| Synthesis gate | plausible make/buy route before promotion | prove a route works |
| xTB | low-cost proxies on finite capped models | prove binding, assembly or mechanism |
| User | owns every synthesis decision | — |

## Working rules

This loop produces large files. Reading them whole is the main way a run becomes
expensive, and cost here is paid per step for the rest of the session.

**Read narrowly.** Open the one reference the current step names, not the folder.
Never `cat` a candidate CSV, a gallery, or a literature packet — use
`scripts/inspect_round.py` (`summary`, `cols`, `row`, `grep`, `check`, `html`).
If a command's output was too long and got saved to a file, do not read that file
back; re-run the command narrower.

**Generate, don't type.** Derived data belongs to a script. Write the judgement
fields in a config and let `scripts/build_candidates.py` produce the SMILES copies,
atom indices, repeat-unit drawings and per-round boilerplate. Prose repeated across
rows goes in the config's `text_blocks` once.

**Pass paths, not payloads.** Build Gemini packets with
`scripts/build_gemini_inputs.py` and hand over the path. Never retype a CSV into a
prompt — the "raw artifacts, never a summary" rule is about what the reviewer reads,
not about retyping it into the conversation.

**Hand off between stages.** Write `DESIGN_LOOP_STATE.json` and stop at these points,
then continue in a fresh session: after the literature packet (Step 2), at the xTB
approval checkpoint (Step 7), and between rounds (Step 12). State on disk is the
memory; conversation history is not. Delegate Steps 1.5-A and 1.5-B to subagents when
available and take back only the file paths.

## Constants

| | |
|---|---|
| MAX_ROUNDS | 3 |
| INITIAL_CANDIDATES | 20–50 |
| MAX_XTB_PER_ROUND | 10–20 |
| ZOTERO_SEARCH_QUERIES | 3–5 |
| ZOTERO_METADATA_LIMIT | 10 per query |
| ZOTERO_FULLTEXT_PAPERS | 5–8, keyword windows only |
| XTB_LEVEL | GFN2-xTB unless the spec says otherwise |
| SYNTHESIS_GATE_FOR_PROMOTION | route plausible or make-on-demand |
| GEMINI_REVIEW_MODEL | `gemini-2.5-flash` |
| NMR tolerances | ¹H ±0.20 ppm, ¹³C ±2.0 ppm; CDCl₃, DMSO-d₆, D₂O |
| AXIS_REDUNDANCY | \|τ-b\| ≥ 0.8 redundant, 0.6–0.8 coupled; `not_assessed` below 8 candidates |
| STOP_IF_NO_NEW_FEASIBLE_MOTIF | true |

Mandatory every round, never skippable: adversarial review (3.5), novelty check
(5.5), user approval (7), ranking diagnostics (11). The claim audit (9.5) is
mandatory whenever xTB ran **or** an objective is one this loop cannot evidence.

## Workflow

Read the reference when you reach the step. Run the script rather than writing its
output by hand. `--help` on any script lists its flags.

| Step | Do | Read | Run |
|---|---|---|---|
| 0.5 | SMILES from structure images, if any | [structure-image-input-protocol.md](references/structure-image-input-protocol.md) | — |
| 1 | Lock the spec → `DESIGN_SPEC_LOCKED.md` | [templates/design_spec_template.md](templates/design_spec_template.md) | — |
| 1.5-A | Mine Zotero → knowledge packet, seed SMILES | [zotero-extraction-protocol.md](references/zotero-extraction-protocol.md) | — |
| 1.5-B | Search current + landmark work (parallel) | [active-search-protocol.md](references/active-search-protocol.md) | — |
| 2 | Merge both → `LIT_PACKET.md`, flag conflicts | — | — |
| 3 | Generate 20–50 candidates | [candidate_schema.md](references/candidate_schema.md) | `build_candidates.py` |
| 3.5 | Gemini adversarial review | [adversarial-review-protocol.md](references/adversarial-review-protocol.md) | `build_gemini_inputs.py --steps 3.5` |
| 4 | Deterministic filtering | — | `rdkit_filter_candidates.py` |
| 5 | Synthesis-feasibility gate | [synthesis-gate-schema.md](references/synthesis-gate-schema.md) | — |
| 5.5 | Prior-art / novelty check | [novelty-check-protocol.md](references/novelty-check-protocol.md) | `build_gemini_inputs.py --steps 5.5` |
| 6 | Render the HTML gallery | [polymer-design-mode.md](references/polymer-design-mode.md) for polymers | `render_candidate_gallery.py` |
| 7 | **Stop. Get structural approval.** | [templates/xtb_approval_template.md](templates/xtb_approval_template.md) | — |
| 8–9 | Select and run xTB jobs | [xtb-integrity-rules.md](references/xtb-integrity-rules.md) | — |
| 9.5 | Result-to-claim audit | [claim-audit-protocol.md](references/claim-audit-protocol.md) | `build_gemini_inputs.py --steps 9.5` |
| 9.7 | NMR prediction / verification (optional) | [nmr-prediction-protocol.md](references/nmr-prediction-protocol.md) | — |
| 10 | Ingest experimental feedback | [candidate_schema.md](references/candidate_schema.md) | — |
| 11 | Score, rank, run both diagnostics | [gemini-scoring-protocol.md](references/gemini-scoring-protocol.md), [ranking-diagnostics-protocol.md](references/ranking-diagnostics-protocol.md) | `ranking_diagnostics.py` |
| 12 | Write failures back to state; iterate | [design-loop-state-schema.md](references/design-loop-state-schema.md) | — |
| 13 | Stop and report | — | — |

### Step notes

**1 — Lock the spec.** Separate hard constraints, soft preferences, forbidden motifs,
seed scaffolds, element/charge/size limits, synthesis constraints, available building
blocks, Pareto objectives, what xTB may test, and what it may not. Ambiguous hard
constraint → ask before anything expensive.

**3 — Generate.** Every candidate traces to a source in `LIT_PACKET.md`;
unsourced exploratory candidates cap at 10%. Before generating, read
`DESIGN_LOOP_STATE.json`: every `killed_motifs[]` entry is a hard exclusion, and a
killed motif returns only with a written rescue hypothesis in its `rationale`. When
`available_building_blocks[]` is non-empty, spend part of the round on candidates
built from them. One candidate should test one interpretable design move.

**4 — Filter.** Pass `--forbidden-smarts` as the union of the spec's
`forbidden_motifs` and every `killed_motifs[].smarts`, so past structural failures
drop out automatically. Keep rejected rows with their reason. Medchem triage flags
(`--min-qed`, `--max-sa-score`, `--reject-pains`, …) are listed by `--help`.

**5 — Gate.** Emit sortable `synthesis_cost`, `time_to_first_sample`,
`overall_yield_estimate` and `hazard_toxicity_flag`, plus `route_alternatives` when
evidence supports more than one route. A route that merely exists is not a route
worth running: a 3-step high-hazard route and a 6-step benign one are different
offers, and the chemist picks. Use `unknown`, never a made-up number — without a
retrosynthesis engine and a price/toxicity database these are estimates, so label
them as estimates.

**6–7 — Gallery and approval.** The gallery uses RDKit depictions, shows filter
decisions, and keeps rejected candidates. It must exist before any xTB run. Then
stop and ask. Do not start xTB until the user approves; record the approved ids in
`DESIGN_LOOP_STATE.json`.

**9 — xTB.** Smallest useful calculation first. Record optimisation status, energy,
HOMO/LUMO/gap, dipole, geometry sanity, and any convergence failure. For polymers,
report the capped oligomer surrogate only — never extrapolate to Mn, dispersity,
Tg, modulus or morphology.

**11 — Score and rank.** Fresh Gemini thread, separate from Steps 3.5 and 9.5.
Synthesis practicality is a **dominance** criterion, not a tiebreaker: a candidate no
better on any of {property fit, cost, time, yield, hazard} than another is dominated,
is recorded as `dominated_by:<id>`, and stays out of the top 3 whatever it scored.
A high-performing 8-step custom synthesis should not outrank a comparable 2-step
shelf-available candidate — and a cheap candidate that is clearly worse on the
objective does not win by being cheap. When several are non-dominated, present the
trade-off instead of forcing a winner. `unknown` is non-comparable and lowers
confidence. The dominance maths, both ranks and the τ-b matrix are mechanical: run
`ranking_diagnostics.py` rather than computing them by hand. Run it with
`--pareto-rank-mode protocol`, which leaves a top-3 position empty rather than giving it
to a dominated candidate; the default `positional` mode reproduces pre-v0.4.0 round files
and only warns. If the round carries controls or bare baselines, pass `--role-column`:
a control is the reference the candidates are measured against, and a control left in the
pool can be the only non-dominated row, which makes the candidate ranking meaningless.

**12 — Iterate.** Design the next round around the observed failure mode: too
flexible → rigidify; too planar → add twist; gate failed → simplify the route;
experiment failed → identify whether it was synthesis, purification, stability,
assay or measurement. Write both negative signals back as structured state:
experimental `failure_mode` rows and the adversarial review's
`likely_lab_failure_mode` become `killed_motifs[]` / `failed_reactions[]` entries
with a SMARTS whenever a structural pattern is implicated. Update
`loop_calibration` once any experimental feedback exists.

**13 — Report.** Stop when 3–5 candidates clear the constraints with evidence, or no
new feasible motif appears for a full round, or xTB is unavailable, or `MAX_ROUNDS`
is reached. `DESIGN_REPORT.md` must contain three sections that are never softened:
*un-evidenced objectives* (with the substitute used and the measurement that would
settle it), *ranking diagnostics* (redundancy verdict, how many candidates the
practicality criterion actually dominated, and the ablation result), and *loop
calibration* (promoted vs. attempted vs. worked, including when it is unflattering).

## Integrity rules

These exist because each one has produced a wrong conclusion before.

1. **xTB is a proxy.** It is not proof of binding, assembly, reactivity, selectivity
   or mechanism. A heuristic accessibility score is not proof a molecule can be made.
2. **State what has no evidence.** A candidate can pass every constraint, look clean
   on descriptors and score well on literature analogy while the loop has produced
   zero evidence on the property the chemist cares about. Say so out loud, in the
   audit and in the report.
3. **No sentinels.** A failed or missing computation is `fail` / `not_run` /
   `unknown`, never `0` or `-999`. Sentinels sort to the extremes, so a crashed job
   becomes a top-ranked candidate.
4. **Fixed scoring anchors.** Never normalise a descriptor against this round's
   min/max. Anchor to the spec, a physical bound, or a named reference compound, or
   the score means nothing across rounds — and this loop has cross-round memory.
5. **Report diagnostics either way.** A redundancy check that found nothing and a
   dominance gate that dominated nothing are both results. Say when the gate did not
   bind. Correlated axes do not "double-penalise" under dominance; a duplicate axis
   creates no new way to be worse.
6. **Keep the rejects.** Rejected candidates stay in the file with their reason;
   they are how the next round learns.
7. **Label predictions.** NMR predictions are Claude-native plausibility checks, not
   a validated method. Always mark them "Claude-predicted" with the error range. A
   `mismatch` triggers structural review — regioisomer, tautomer or side product.
8. **Low-confidence image extractions need confirmation** before anything downstream.

## Outputs

Everything lands in `molecule-design-stage/`:

`DESIGN_SPEC_LOCKED.md` · `ZOTERO_KNOWLEDGE_PACKET.md` · `ZOTERO_SEED_SMILES.csv` ·
`ACTIVE_SEARCH_PACKET.md` · `LIT_PACKET.md` · `IMAGE_EXTRACTED_SMILES.csv` ·
`ROUND_N_CANDIDATES.csv` · `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md` ·
`ROUND_N_FILTERED.csv` · `ROUND_N_SYNTHESIS_FEASIBILITY.csv` ·
`ROUND_N_NOVELTY_CHECK.md` · `ROUND_N_CANDIDATE_GALLERY.html` ·
`ROUND_N_POLYMER_DESIGN.html` · `ROUND_N_XTB_APPROVAL.md` · `ROUND_N_XTB_RESULTS.csv` ·
`ROUND_N_CLAIM_AUDIT.md` · `ROUND_N_NMR_PREDICTIONS.csv` · `ROUND_N_NMR_VERIFICATION.md` ·
`ROUND_N_EXPERIMENT_RESULTS.csv` · `ROUND_N_DECISION.md` · `DESIGN_LOOP_STATE.json` ·
`DESIGN_REPORT.md` · `xtb_jobs/`

`DESIGN_LOOP_STATE.json` is the cross-round memory and the handoff file. Update it in
place; never overwrite earlier rounds.

## Scripts

| Script | Purpose |
|---|---|
| `build_candidates.py` | config → `ROUND_N_CANDIDATES.csv`, deriving every mechanical column and validating each structure |
| `rdkit_filter_candidates.py` | descriptors, medchem triage, forbidden-SMARTS filtering |
| `render_candidate_gallery.py` | filtered CSV → standalone RDKit HTML gallery |
| `build_gemini_inputs.py` | round files → Steps 3.5 / 5.5 / 9.5 review packets |
| `ranking_diagnostics.py` | dominance, Pareto and shadow ranks, τ-b matrix (stdlib only) |
| `inspect_round.py` | bounded views of any round file (stdlib only) |

When a new helper is needed: one entrypoint, reusable parts, per-run config. Never
hard-code a round number, molecule, path or threshold; read evolving constraints from
`DESIGN_SPEC_LOCKED.md` instead of baking them into code.

## Writing a candidate config

`build_candidates.py --print-columns` separates what you write from what it derives.
Write only the judgement columns; the four SMILES copies, atom indices, repeat-unit
drawings, formula and mass are computed. Structures are assembled from named
`fragments` onto a `scaffolds` template (discrete molecules) or a `chains` template
(polymers), and every one is checked before it is written: it parses, stays within
`allowed_elements`, is neutral, matches the motif counts its pieces declare, and
carries the stereochemistry the template requires. A failure stops the run — a
config that builds the wrong molecule should fail loudly, not reach xTB.

## ChemDraw

Optional input/output only: read selected SMILES through `chemdraw-mcp`, inspect
final structures by hand. The core loop must not depend on GUI automation.

## Invocation

```text
/molecule-design-loop "/path/to/design_spec.md"
/molecule-design-loop "design_spec.md -- rounds: 2 -- max-xtb: 8"
```

If no spec exists, run Zotero extraction first to find the theme, pre-populate
`templates/design_spec_template.md`, and confirm with the user before anything
expensive.
