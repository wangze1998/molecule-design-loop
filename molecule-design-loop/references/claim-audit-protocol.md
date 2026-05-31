# Result-to-Claim Audit Protocol (Step 9.5)

Mandatory when xTB runs. Runs after xTB results are written, before Gemini scoring (Step 11).

Prevents the core ARIS failure mode: computational results promoted into stronger design claims than the evidence warrants.

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
```

## auditor_flag values

- `clean` — claim matches evidence scope
- `overclaim` — rationale exceeds what this computation proves; must be corrected before Step 11
- `underclaim` — computation result is stronger than the stated rationale; flag as upside
- `insufficient_data` — not enough xTB runs to make any directional claim

## Rules

- Step 11 (Gemini scoring) must read `ROUND_N_CLAIM_AUDIT.md` before scoring.
- Gemini may not assign a score of 4 or 5 to any candidate with `auditor_flag: overclaim` unless the overclaim is corrected.
- `ROUND_N_DECISION.md` must include a `claim_audit_flag` column sourced from this audit.
- If xTB did not run, skip this step and mark `claim_audit_status: not_run_xtb_unavailable` in `DESIGN_LOOP_STATE.json`.
