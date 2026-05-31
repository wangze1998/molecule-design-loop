# Gemini Adversarial Chemistry Review Protocol (Step 3.5)

Mandatory. Runs immediately after candidate generation, before RDKit filtering.

## Gemini call

```
system: "You are an expert synthetic chemist and structural chemistry critic reviewing molecular design candidates. Your role is adversarial — find problems, not virtues. You have no knowledge of who designed these candidates. Read the design spec and candidate list directly. For each candidate: (1) Does the stated design move actually test the hypothesis, or is it a superficial change? (2) Is the synthesis hypothesis chemically plausible, or optimistic fiction? (3) Does the expected proxy effect follow from the structural change, with chemical reasoning? (4) What would cause this candidate to fail in the lab — synthesis, stability, assay interference, or aggregation? Be specific and cite chemical reasoning. Do not score candidates — only identify weaknesses and unsupported claims."

prompt: [paste full ROUND_N_CANDIDATES.csv content + DESIGN_SPEC_LOCKED.md]
```

Rules:
- Pass raw file content directly to Gemini — do not summarize or paraphrase.
- Use `mcp__gemini-review__review_start` + `mcp__gemini-review__review_status` for async when candidate count > 20.
- Do not retry with a different prompt if Gemini raises concerns — record them as legitimate critique.

## Output: ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md

```markdown
# Round N — Gemini Adversarial Chemistry Review

## Review Summary
[Gemini's overall assessment of the round quality]

## Per-Candidate Critiques
| candidate_id | design_move_challenge | synthesis_challenge | proxy_logic_challenge | likely_lab_failure_mode |
|---|---|---|---|---|

## Systemic Issues
[Problems affecting multiple candidates — e.g., a whole scaffold family with a synthesis blind spot]

## Candidates Flagged for Revision Before RDKit
[candidate IDs Gemini considers structurally or synthetically implausible]
```

## Post-review actions

Add `gemini_adversarial_flag` column to `ROUND_N_CANDIDATES.csv`: `pass`, `warn`, or `revise`.

- `revise`: correct or replace before RDKit filtering if the critique is valid; if disagreed, record the disagreement reason.
- Do not silently discard Gemini's critique — every flagged candidate must have a documented response.
