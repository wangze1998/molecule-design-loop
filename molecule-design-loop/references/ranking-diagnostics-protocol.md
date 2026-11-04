# Ranking Diagnostics Protocol (Step 11)

Two checks that run alongside Pareto ranking and answer questions the ranking itself cannot answer:

1. **Axis redundancy** — are the practicality axes actually carrying independent information, or is the loop presenting five considerations when there are really three?
2. **Practicality ablation (shadow ranking)** — what did the practicality constraint actually cost? Which high-scoring candidates did it keep off the bench, and why?

Both are diagnostics *about* the ranking, not inputs to it. Neither changes a candidate's score. Both are written into `ROUND_N_DECISION.md` and summarized in `DESIGN_REPORT.md`.

**Compute these with `scripts/ranking_diagnostics.py`, not by hand.** Every number below — the dominance relation, `pareto_rank`, `shadow_rank_property_only`, the exclusion reasons, the τ-b matrix, and the dominated/assessed counts — is mechanical and reproducible, and the integrity rules (unknown is non-comparable, a missing value is never a sentinel) are easy to violate when done in prose. The script takes a decision CSV (`candidate_id`, `gemini_constraint_score`, and the four practicality-axis columns), writes an annotated CSV plus a Markdown report whose sections match the ones required below, and takes `--benchmark-ids` for the known-compound recovery check. Gemini still assigns `gemini_constraint_score`; the script only ranks on it. The prose below is the specification the script implements and the reference for reading its output.

Motivated by Cai et al., *AI-guided discovery of self-assembled monolayers combining synthetic accessibility and interfacial stability for perovskite solar cells* (Nat. Synth. 2026, DOI 10.1038/s44160-026-01203-4), which verified descriptor non-redundancy before trusting its composite score, and re-ranked with the synthesizability term removed to show that the top candidates without it were unmakeable.

---

## 1. Axis redundancy check

### When to run

After the synthesis gate and scoring have populated the practicality axes, before the dominance computation is reported. Every round.

### Inputs

The per-candidate values of the five ranking axes, over all candidates that pass hard constraints:

- `gemini_constraint_score` (1–5)
- `synthesis_cost` (`low` < `medium` < `high` < `very_high`)
- `time_to_first_sample` (`same_day` < `days` < `weeks` < `months`)
- `overall_yield_estimate` (`high` > `medium` > `low`)
- `hazard_toxicity_flag` (`none` < `standard_care` < `high_hazard`)

### Method

These are **ordinal** variables with three or four levels, so ties are frequent. Use **Kendall's τ-b**, which is defined for tied ordinal data. Spearman's ρ is acceptable as a second opinion; **Pearson's r is not appropriate here** — the levels are ordered categories, not measured quantities, and the spacing between them is not meaningful.

Drop `unknown` values pairwise rather than imputing them. Record how many pairs were usable.

Compute τ-b for all ten axis pairs. Report as a compact matrix in `ROUND_N_DECISION.md`.

### Sample-size floor

With fewer than **8** hard-constraint-passing candidates, do not compute the matrix. Record `axis_redundancy: not_assessed (n=<N>, below floor)` and move on. A correlation over five candidates is noise, and acting on it is worse than not having it.

Between 8 and 15 candidates, compute it but label the whole matrix `small_sample` and do not collapse any axis on its basis — report the observation only.

### Thresholds and what to do

| |τ-b| | Verdict | Action |
|---|---|---|
| ≥ 0.8 | `redundant` | Report the pair as carrying one piece of information, not two. With more than 15 candidates, nominate the axis closer to the design spec's stated priority as the representative and mark the other `collapsed_into:<axis>` in the trade-off presentation. Both axes still appear in the per-candidate table. |
| 0.6 – 0.8 | `coupled` | Report the coupling. Do not collapse. The trade-off narrative must not describe the two as independent considerations. |
| < 0.6 | `independent` | No action. |

### What redundancy does and does not mean

Be precise about this; the easy claim here is wrong.

- **Redundancy does not break Pareto dominance.** If two axes are perfectly correlated, adding the second one changes nothing about who dominates whom — a duplicate axis creates no new way for a candidate to be worse. Do not write that correlated axes "double-penalize" candidates under dominance. They do not.
- **Redundancy does misrepresent the trade-off.** When the loop hands the chemist a non-dominated front and says "these differ on five axes", and two of those axes are the same axis wearing different hats, the front looks richer than it is. That is a reporting honesty problem, and it is the reason to run this check.
- **Redundancy would be double-weighting under any scalar composite.** This loop ranks by dominance, not by a weighted sum, so that failure mode does not currently apply. If a future round introduces a composite score, the redundancy matrix is a precondition for choosing weights.

### The failure mode that actually bites: dominance dilution

Separately from redundancy, record and report two counts:

- `candidates_assessed` — hard-constraint passers with enough non-`unknown` axes to be comparable
- `candidates_dominated` — how many were found dominated by at least one other

With five axes of three or four levels each and a typical round of 20–50 candidates narrowed to a handful of passers, ties are common and **it is entirely possible for nothing to be dominated**. When that happens the practicality gate did not bind: it filtered nothing, and the top 3 is the same top 3 it would have been without any practicality reasoning at all.

That must be stated plainly in `ROUND_N_DECISION.md`:

> Practicality dominance: 0 of 7 assessed candidates were dominated. The practicality axes did not constrain the ranking this round.

Not saying it lets a decorative gate pass for a working one. If `candidates_dominated` is 0 for two consecutive rounds, note in `DESIGN_LOOP_STATE.json` `notes` that the axes may be too coarse for this design space.

---

## 2. Practicality ablation (shadow ranking)

### Purpose

The loop claims that ranking by practicality protects bench time. That claim is testable within a single round, for free: rank the same candidates **without** the practicality axes and compare.

### Method

Compute `shadow_rank_property_only` over the same hard-constraint-passing set, using **only** `gemini_constraint_score` and the design spec's stated property priorities. Ignore `synthesis_cost`, `time_to_first_sample`, `overall_yield_estimate`, `hazard_toxicity_flag`, `practicality_dominance`, and the `buy` < `make_on_demand` < `custom_synthesis` tiebreak.

Then compare the two top-3 sets.

### Required output in `ROUND_N_DECISION.md`

A section titled **Practicality Ablation**, containing:

- the property-only top 3 and the final top 3, side by side;
- for every candidate in the property-only top 3 that is **not** in the final top 3: its `candidate_id`, the axis or axes responsible, and the concrete value that excluded it (`custom_synthesis, 8 steps, high_hazard` — not "practicality concerns");
- for every candidate in the final top 3 that is **not** in the property-only top 3: why practicality promoted it;
- one sentence stating what the constraint bought or cost this round.

### When the two rankings are identical

Say so explicitly:

> Practicality ablation: the property-only ranking and the final ranking give the same top 3. Practicality did not change the recommendation this round.

This is an informative result, not a failure, and it must not be silently omitted. A loop that only reports the ablation when it looks impressive is reporting advertising, not diagnostics.

### Feeding calibration

Practicality exclusions are predictions — the loop is asserting those candidates were not worth the bench time. When experimental feedback later arrives:

- If a practicality-excluded candidate was made anyway and met the endpoint, append a `known_bias` entry to `loop_calibration` in `DESIGN_LOOP_STATE.json`, e.g. `"practicality axes excluded cand_12, which later met the endpoint — cost/hazard estimates may be too conservative for this chemistry"`.
- If practicality-excluded candidates were repeatedly attempted and repeatedly failed on route grounds, that is confirmation; record it in `calibration_summary`.

No schema change is required — `known_bias` is already a free-text array.

---

## Honesty boundaries

- The redundancy matrix is computed from this round's candidates only. It describes **this design space at this sample size**, not a general property of the axes. Never carry a redundancy verdict forward as established fact.
- τ-b over 8–15 ordinal points with heavy ties is a weak estimate. Label it `small_sample` and treat it as a hint, never as grounds to drop an axis from the per-candidate table.
- The ablation compares two rankings produced by the same scorer on the same evidence. It shows what the practicality constraint changed. It does **not** show that the final ranking is correct — only experimental feedback does that, which is what `loop_calibration` is for.
- Both diagnostics are reported whether or not they flatter the loop.
