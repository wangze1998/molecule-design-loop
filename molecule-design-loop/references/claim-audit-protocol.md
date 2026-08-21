# Result-to-Claim Audit Protocol (Step 9.5)

Runs before Gemini scoring (Step 11). **Mandatory in either of two cases:**

1. **xTB ran** — audit what those numbers do and do not prove.
2. **The design objective is a property this loop cannot evidence at all** — binding affinity, potency, selectivity, catalytic activity, self-assembly behaviour, permeability, or in vivo outcome. This case is mandatory *even when xTB did not run*, and even when there is nothing to audit — the audit's output is then the declaration that no direct evidence exists.

Prevents the core ARIS failure mode: computational results promoted into stronger design claims than the evidence warrants.

Case 2 exists because the more dangerous failure is silent. A candidate can pass hard constraints, clear the synthesis gate, have clean descriptors and a strong literature analogy, and receive a score of 5 — while the loop has produced **zero evidence about the property the chemist actually cares about**. Nothing else in the workflow says so out loud. Bench time then gets spent on confidence the loop never earned.

## Gemini call

```
system: "You are a chemistry claim auditor. Your job is to produce a precise evidence-to-claim map for each computational result. For every xTB or RDKit number: (1) State exactly what this measurement proves about the molecular design. (2) State what it explicitly cannot prove — scope limitations, model approximations, missing validation. (3) State the minimum additional evidence needed to promote this into a synthesis recommendation. Do not allow chemical interpretation to outrun the data. Flag every case where a claim in the candidate rationale exceeds what the computation supports."

prompt: [paste ROUND_N_XTB_RESULTS.csv + ROUND_N_CANDIDATES.csv rationale columns + DESIGN_SPEC_LOCKED.md xTB proxy targets section]
```

Use `mcp__gemini-review__review_start` + `mcp__gemini-review__review_status` for async.

## Output: ROUND_N_CLAIM_AUDIT.md

```markdown
# Round N — Result-to-Claim Audit

## Claims Matrix
| candidate_id | computation | result_value | claim_supported | claim_not_supported | minimum_evidence_to_promote | auditor_flag |
|---|---|---|---|---|---|---|

## Systemic Overclaim Patterns
[Patterns where multiple candidates' rationales exceed what the computation supports]

## Evidence Gaps Blocking Promotion
[What is missing for top candidates before synthesis recommendation]

## Un-Evidenced Design Objectives
[Mandatory in case 2. One line per design objective the loop produced no direct evidence for, stating the objective, what was used as a substitute (literature analogy, descriptor proxy, scaffold precedent), and what measurement would settle it. If every objective has direct evidence, state "none".]
```

## auditor_flag values

- `clean` — claim matches evidence scope
- `overclaim` — rationale exceeds what this computation proves; must be corrected before Step 11
- `underclaim` — computation result is stronger than the stated rationale; flag as upside
- `insufficient_data` — not enough xTB runs to make any directional claim
- `no_direct_evidence` — the loop produced no evidence at all on the design objective (case 2). The candidate may still be worth making on literature grounds, but the rationale must say so and `evidence_level` must be `literature_only` or `hypothesis_only`.

## Rules

- Step 11 (Gemini scoring) must read `ROUND_N_CLAIM_AUDIT.md` before scoring.
- Gemini may not assign a score of 4 or 5 to any candidate with `auditor_flag: overclaim` unless the overclaim is corrected.
- `ROUND_N_DECISION.md` must include a `claim_audit_flag` column sourced from this audit.
- If xTB did not run **and** no design objective falls under case 2, skip this step and mark `claim_audit_status: not_run_xtb_unavailable` in `DESIGN_LOOP_STATE.json`.
- If xTB did not run but case 2 applies, the audit still runs. Its prompt uses the design spec and candidate rationales alone; its job is to produce the `Un-Evidenced Design Objectives` section and assign `no_direct_evidence`.
- A candidate flagged `no_direct_evidence` may still score well on constraint fit, but Step 11 must record `evidence_level: literature_only` or `hypothesis_only` for it and must not describe it as computationally supported on that objective.
- Every un-evidenced objective must also be appended to `evidence_gaps` in `DESIGN_LOOP_STATE.json`, and named in `DESIGN_REPORT.md` under "what not to claim".
