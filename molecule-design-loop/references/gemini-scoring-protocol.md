# Gemini Scoring and Pareto Ranking Protocol (Step 11)

Start a **fresh Gemini thread** — separate from the adversarial review (Step 3.5) and claim audit (Step 9.5) threads — so the scorer reads the full evidence picture without being anchored to prior critique.

## Gemini call

```
system: "You are a scientific design evaluator assessing molecular candidates against a locked design specification. You have access to: the design spec, RDKit filter results, synthesis feasibility assessments (including per-candidate synthesis_cost, time_to_first_sample, overall_yield_estimate, hazard_toxicity_flag, and where available route_alternatives), a prior-art novelty check, xTB results, and a result-to-claim audit that defines exactly what each computation proves. Score each candidate strictly against the design spec. A score of 4 or 5 requires: hard constraints passed, synthesis gate not failed, and no unresolved overclaim flags from the claim audit. Synthesis practicality is a dominance criterion, not a tiebreaker: a candidate that is worse on every practicality axis (cost, time-to-first-sample, yield, hazard) than another candidate of comparable or better property fit is dominated and must not enter the top 3, whatever its score. The goal is to protect the chemist's bench time — rank by what is worth making, not by what scores best on paper."

prompt: [paste DESIGN_SPEC_LOCKED.md + ROUND_N_FILTERED.csv key columns + ROUND_N_SYNTHESIS_FEASIBILITY.csv + ROUND_N_NOVELTY_CHECK.md + ROUND_N_XTB_RESULTS.csv (if run) + ROUND_N_CLAIM_AUDIT.md (if run) + ROUND_N_NMR_VERIFICATION.md (if run) + ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md critique summary]
```

## Scoring rubric

- `5`: passes hard constraints, strongly matches the design brief, available RDKit/xTB evidence aligned.
- `4`: passes hard constraints and looks strong, but has one moderate evidence gap or tradeoff.
- `3`: partially aligned and worth revision, not immediate promotion.
- `2`: weak alignment or meaningful red flags, only keep with a specific rescue hypothesis.
- `1`: fails the design intent; retain only as negative control if at all.

## Evidence use rules

- Gemini scores against `DESIGN_SPEC_LOCKED.md`, not raw xTB numbers.
- xTB numbers can support or weaken a claim, but must not directly assign rank or score.
- If xTB is missing, Gemini scores from the design doc, literature packet, and deterministic filters, marking missing evidence clearly.
- Experimental results outrank computational proxies for the same endpoint.
- NMR verification status (`confirmed` or `consistent`) strengthens the evidence level for a candidate's structural identity. A `mismatch` status requires structural review before final promotion — the synthesized compound may not be the intended target.
- Missing experimental evidence lowers confidence, not automatically kills a candidate.
- Synthesis feasibility can block final promotion even when RDKit/xTB look strong.
- Practicality axes (`synthesis_cost`, `time_to_first_sample`, `overall_yield_estimate`, `hazard_toxicity_flag`) are heuristic estimates unless a retrosynthesis/CASP tool produced them. Use them for ranking, but do not report them as if they were tool-computed route optima.
- A candidate with `claim_audit_flag: no_direct_evidence` may still score well on constraint fit, but its `evidence_level` must be `literature_only` or `hypothesis_only`, and its `supported_design_claim` must not describe the un-evidenced objective as computationally supported.
- If `DESIGN_LOOP_STATE.json` carries a `loop_calibration.known_bias` entry that applies to a candidate's evidence type (e.g. the loop has repeatedly over-scored literature-analogy-only candidates), lower that candidate's `confidence` and say why in `uncertainty_reason`.

## Required output fields per candidate

- `gemini_constraint_score`: 1–5
- `pass_hard_constraints`: yes/no
- `synthesis_gate_status`: pass/warn/fail/not_run
- `synthesis_cost`: low/medium/high/very_high (from the synthesis gate)
- `time_to_first_sample`: same_day/days/weeks/months (from the synthesis gate)
- `overall_yield_estimate`: high/medium/low/unknown (from the synthesis gate)
- `hazard_toxicity_flag`: none/standard_care/high_hazard/unknown (from the synthesis gate)
- `practicality_dominance`: `non_dominated`, `dominated_by:<candidate_id>`, or `not_assessed`
- `prior_art_status`: novel/analog/known/uncertain
- `claim_audit_flag`: clean/overclaim/underclaim/insufficient_data/no_direct_evidence/not_run
- `gemini_adversarial_flag`: pass/warn/revise (from Step 3.5)
- `xTB_status`: pass/warn/fail/not_run
- `nmr_verification_status`: confirmed/consistent/inconclusive/mismatch/not_run
- `pareto_rank`: integer rank or `not_ranked`
- `evidence_level`: experimental / computed_proxy / literature_only / hypothesis_only
- `confidence`: high/medium/low
- `uncertainty_reason`
- `supported_design_claim`
- `unsupported_claims`
- `gemini_score_reason`
- `next_action`: keep / revise / kill / control / needs_higher_level_calc
- `revision_hint`: concrete next modification

## Pareto ranking

Compare only candidates that pass hard constraints. Rank across the design spec's stated objectives — e.g., potency proxy, ADMET/descriptor fit, synthesis feasibility, route confidence, experimental outcome, diversity, risk.

**Synthesis practicality is a dominance criterion, not a tiebreaker.** Earlier versions applied synthesis cost only when candidates were "otherwise tied" — that is too weak, because a candidate can be worse on *every* practicality axis and still win on a marginally better property score. Rank in this order:

1. **Compute practicality dominance.** Candidate A dominates candidate B when A is at least as good as B on every axis in {property fit (`gemini_constraint_score`), `synthesis_cost`, `time_to_first_sample`, `overall_yield_estimate`, `hazard_toxicity_flag`} and strictly better on at least one. Axis ordering: cost `low` < `medium` < `high` < `very_high`; time `same_day` < `days` < `weeks` < `months`; yield `high` > `medium` > `low`; hazard `none` < `standard_care` < `high_hazard`. Treat `unknown` as non-comparable on that axis — it can neither dominate nor be dominated there, and it lowers `confidence`.
2. **Record the verdict** in `practicality_dominance`. A candidate dominated by another must not enter the top 3 of `pareto_rank`, regardless of its score. Say which candidate dominates it.
3. **Rank within the non-dominated front** by design-spec priority, then apply the make/buy ordering `buy` < `make_on_demand` < `custom_synthesis` (lower = preferred) as the final tiebreak.

A high-performing 8-step custom synthesis must not outrank a comparable 2-step shelf-available candidate. Equally, a cheap fast candidate that is clearly worse on the design objective does not win by being cheap — dominance requires being no worse on *every* axis, property fit included.

The front is a set of honest offers, not a single winner: when several candidates are non-dominated, present the trade-off rather than forcing a rank-1 pick.

Do not let a strong xTB output override a violated hard constraint or failed synthesis gate.
