# Gemini Scoring and Pareto Ranking Protocol (Step 11)

Start a **fresh Gemini thread** — separate from the adversarial review (Step 3.5) and claim audit (Step 9.5) threads — so the scorer reads the full evidence picture without being anchored to prior critique.

## Gemini call

```
system: "You are a scientific design evaluator assessing molecular candidates against a locked design specification. You have access to: the design spec, RDKit filter results, synthesis feasibility assessments, a prior-art novelty check, xTB results, and a result-to-claim audit that defines exactly what each computation proves. Score each candidate strictly against the design spec. A score of 4 or 5 requires: hard constraints passed, synthesis gate not failed, and no unresolved overclaim flags from the claim audit."

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

## Required output fields per candidate

- `gemini_constraint_score`: 1–5
- `pass_hard_constraints`: yes/no
- `synthesis_gate_status`: pass/warn/fail/not_run
- `prior_art_status`: novel/analog/known/uncertain
- `claim_audit_flag`: clean/overclaim/underclaim/insufficient_data/not_run
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

Do not let a strong xTB output override a violated hard constraint or failed synthesis gate.
