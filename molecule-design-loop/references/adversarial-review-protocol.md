# Adversarial Chemistry Review Protocol (Step 3.5)

Mandatory. Runs immediately after candidate generation, before RDKit filtering.

Dispatch through the `review` route resolved at Step 0 ([reviewer-selection-protocol.md](reviewer-selection-protocol.md)). The `mcp__gemini-review__*` tools named below are the default `gemini` route; another backend uses its own tools from that file, with the same prompt, packet and output format.

## Reviewer call

```
system: "You are an expert synthetic chemist and structural chemistry critic reviewing molecular design candidates. Your role is adversarial — find problems, not virtues. You have no knowledge of who designed these candidates. Read the design spec and candidate list directly. For each candidate: (1) Does the stated design move actually test the hypothesis, or is it a superficial change? (2) Is the synthesis hypothesis chemically plausible, or optimistic fiction? (3) Does the expected proxy effect follow from the structural change, with chemical reasoning? (4) What would cause this candidate to fail in the lab — synthesis, stability, assay interference, or aggregation? Be specific and cite chemical reasoning. Do not score candidates — only identify weaknesses and unsupported claims."

prompt: the Step 3.5 packet (see "Building the packet" below) -- locked spec,
        candidate rows, and the route detail the scorer will see.
```

Rules:
- The reviewer must receive raw file content, never a summary or paraphrase. The packet
  script copies it field for field; build the packet rather than retyping rows.
- Use `mcp__gemini-review__review_start` + `mcp__gemini-review__review_status` for async when candidate count > 20.
- Do not retry with a different prompt, or with a different reviewer, if the reviewer raises concerns — record them as legitimate critique.
- To contest a flag, use the rebuttal exchange in the same session (at most `REVIEW_REBUTTAL_ROUNDS`, item by item with file or spec evidence; see the selection protocol). The reviewer's last answer is the record; items it still maintains are `disputed` and go to the user at Step 7.

## Building the packet

Do not retype artifacts into the prompt. Build the packet from the round files and
give the reviewer the path:

```bash
python3 scripts/build_gemini_inputs.py \
  --round-dir molecule-design-stage --skill-refs <skill>/references \
  --out molecule-design-stage/_gemini_inputs --round N --steps 3.5
# -> molecule-design-stage/_gemini_inputs/step3.5_adversarial_review_input.md
```

The packet copies this step's `system:` block verbatim, then the locked spec and the
raw columns this step needs. "Raw artifacts, never a summary" is about what the
reviewer reads; it does not require moving the bytes through the conversation.

## Output: ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md

```markdown
# Round N — Adversarial Chemistry Review

Reviewer: <label> · model <id> (<model_source>) · independence <verdict>

## Review Summary
[The reviewer's overall assessment of the round quality]

## Per-Candidate Critiques
| candidate_id | design_move_challenge | synthesis_challenge | proxy_logic_challenge | likely_lab_failure_mode |
|---|---|---|---|---|

## Systemic Issues
[Problems affecting multiple candidates — e.g., a whole scaffold family with a synthesis blind spot]

## Candidates Flagged for Revision Before RDKit
[candidate IDs the reviewer considers structurally or synthetically implausible]

## Rebuttal exchange
[verbatim, or "none"; per item: executor's evidence → reviewer's concede / maintain / modify; disputed items listed last]
```

## Post-review actions

Add `gemini_adversarial_flag` column to `ROUND_N_CANDIDATES.csv`: `pass`, `warn`, or `revise`.

- `revise`: correct or replace before RDKit filtering if the critique is valid; if disagreed, record the disagreement reason.
- Do not silently discard the reviewer's critique — every flagged candidate must have a documented response.
