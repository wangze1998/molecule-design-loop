# ROUND_N_CHANGE_REQUEST — `cr_rN_XX`

Write this instead of editing a skill file during a run. Fill every section, stop at
the current step, and wait for the user. See
[`references/run-integrity-protocol.md`](../references/run-integrity-protocol.md).

- **Request id:** `cr_rN_XX`
- **Raised in:** Round N, Step S
- **Status:** open  <!-- the user sets accepted / rejected -->

## What to change

The file, and the function, threshold or rule inside it. Quote the current text or
value exactly.

## Why

The observed problem, in one or two sentences. Say what the current rule does that
looks wrong, not what you would prefer the result to be.

## Evidence

Pointers to round artifacts that show the problem, e.g.
`ROUND_2_FILTERED.csv:C14` or `ROUND_2_DECISION.md#ranking`. No evidence → no request.

## Invariant touched

Name the integrity rule or protocol rule this change touches (e.g. "no sentinels",
"fixed scoring anchors", "a dominated candidate never enters the top 3",
"user approval before xTB"), or write `none`.

## Effect on this round

Which candidates would change status, rank or evidence label if the change were made,
and in which direction. List them even when the change looks neutral.

**Does any candidate move into the top 3, pass a filter it failed, or gain a stronger
evidence label because of this change?** yes / no — if yes, name them. A change whose
main effect is to rescue a candidate from this round is a spec decision for the user,
not a fix to the skill.

## Proposed test

The test that would lock in the new behaviour, and the existing test it would change
or replace.

## Decision (user)

- **Decision:** accepted / rejected
- **Reason:**
- **Resolved in skill version:**  <!-- e.g. 0.5.1, when accepted and released -->
