# Reviewer Selection Protocol (Step 0, used by 1.5-B, 3.5, 5.5, 9.5, 11)

Which model reviews the candidates, and which one searches the literature, is a
choice the user makes once and the loop records. This file says how the choice is
made, how each transport is called, how the executor and the reviewer may argue a
point, and when a review counts.

## Contents

- Why this exists
- Two roles, one resolver
- Choosing: config files and invocation
- Transports
- Agent HUD: calling another agent session
- Rebuttal exchange (Steps 3.5 and 9.5)
- When a backend fails
- Accepting a review
- Search steps
- What goes into the state file

## Why this exists

Every review step was wired to one provider. When it could not be reached — prepaid
credits gone, a CLI licence refused, an account not eligible in its region — the
mandatory steps had two bad options: stop the loop, or switch to whatever else was at
hand without saying so. A silent switch is worse than a stop. The round file still
says who reviewed it, and that is now false. And if the switch went to the executor's
own model family, the review is no longer independent.

## Two roles, one resolver

| Role | Steps | Default |
|---|---|---|
| `review` | 3.5 adversarial review, 9.5 claim audit, 11 scoring | `gemini` (direct MCP, `gemini-2.5-flash`) |
| `search` | 1.5-B active search, 5.5 prior-art check | `gemini` (`gemini-research` MCP) |

At Step 0, before anything else in the run, resolve both roles:

```bash
python3 scripts/reviewer_route.py resolve --role review --host claude-code \
  --stage-dir molecule-design-stage --available "<tool names this host exposes>"
python3 scripts/reviewer_route.py resolve --role search --host claude-code ...
```

`--host` is `claude-code` or `codex`, whichever is running the loop. Pass
`--executor-model` when the executor's model is known and is not the host's usual
family (a Claude Code CLI pointed at another provider). Pass `--available` with the
`mcp__…` tool names actually exposed this session, so a backend whose tools are not
loaded is skipped as `tool_missing` instead of failing mid-step. The script only
parses. It never calls a model and never edits settings.

Exit 0 prints the route as JSON: `backend`, `via`, `label`, `model`, `effort`,
`transport`, `tools`, `source`, `skipped`. Exit 3 means nothing usable:
`REVIEW_UNAVAILABLE`. A mandatory step then stops and the user is asked. Exit 2 is a
config error; show the message to the user.

Resolve once per round. Reuse that route for every step of the round. Re-resolve only
after a failure (see below) or when the user changes the choice.

## Choosing: config files and invocation

Selection order: **this invocation → `molecule-design-stage/reviewer.json` → user
file → default.** The user file is
`$XDG_CONFIG_HOME/molecule-design-loop/reviewer.json`, or
`~/.config/molecule-design-loop/reviewer.json` when `XDG_CONFIG_HOME` is unset. Put a
standing preference there. Put a project's own choice in the stage folder.

```json
{
  "review":   {"backend": "codex", "via": "agent-hud"},
  "search":   {"backend": "gemini"},
  "fallback": ["deepseek@agent-hud", "manual"]
}
```

- A flat `{"backend": …, "via": …, "model": …, "effort": …, "fallback": […]}` applies
  to both roles. A role block overrides it field by field.
- Backends: `gemini`, `codex`, `antigravity` (alias `agy`), `claude-code` (alias
  `claude`), `deepseek`, `manual`. `scripts/reviewer_route.py backends` prints the
  table.
- `"codex@agent-hud"` is short for `{"backend": "codex", "via": "agent-hud"}`.
- `fallback` is **opt-in**. Without it, an unavailable backend stops the step. With
  it, the loop moves down the list only for failures that prove nothing ran.
- `model` and `effort` belong to the backend they were written for. A higher layer that
  switches to a different backend does not inherit them.
- Invocation: `-- reviewer: codex@agent-hud`, `-- reviewer-model: …`,
  `-- search: gemini`, `-- reviewer-fallback: deepseek@agent-hud,manual`. Map these to
  `--backend`, `--model` and `--fallback` for the matching `--role`.

**Never the executor's family.** A backend whose model family matches the executor's
is refused when it is chosen explicitly, and skipped when it is a fallback. Examples:
`claude-code` while Claude runs the loop; `codex` inside Codex; an Antigravity session
serving a Claude model. `--allow-same-family` exists only for a run the user agrees to
label provisional throughout.

## Transports

| `transport` | Backends | First call | Follow-up |
|---|---|---|---|
| `mcp` | gemini | `mcp__gemini-review__review` (`review_start` + `review_status` when > 20 candidates) | `review_reply` with the thread id |
| `mcp` | codex | `mcp__codex__codex` | `mcp__codex__codex-reply`: thread id + prompt only |
| `mcp` | antigravity | `mcp__antigravity__antigravity` | `antigravity-reply`: thread id + prompt only |
| `mcp` | claude-code | `mcp__claude-review__review` | `review_reply` |
| `native` | codex inside Codex | `spawn_agent` with a fresh context (no history fork) | `send_input` |
| `agent-hud` | codex, antigravity, claude-code, deepseek | `mcp__agent-hud__start_session` | `mcp__agent-hud__send_message` (+ `get_message`) |
| `manual` | manual | write the packet path for the user, stop | the user returns the reply as a file |

Tool names may appear with hyphens or underscores. Match them loosely, and use the
names the host actually exposes. Every step that needs a fresh reviewer gets a new
session or thread. Step 11 is never a continuation of 3.5 or 9.5.

The reviewer gets the **packet path** from `build_gemini_inputs.py`, never a
retyped or summarised copy. The packets are reviewer-neutral; the name is historical.

## Agent HUD: calling another agent session

Agent HUD can open a real Codex, Antigravity, DeepSeek Harness or Claude Code session
on this computer and pass messages to it. The reviewer is then a whole agent: it reads
the packet itself, and the executor can answer its critique in the same session.

1. **Check the client.** Call `mcp__agent-hud__list_models` with that client. A
   `reason` in the reply (client not running, not signed in) is the failure
   `start_failed`. Nothing was sent, so a fallback may follow. Record the client's
   `default` model as the expected model. Pass `model` to `start_session` only when the
   config names one **and** that client reports `atStart: true`. Otherwise the session
   runs the client's own choice. Record that, not the configured name.
2. **Start a fresh session.** Call `start_session` with:
   - `client`;
   - `folder`: the project folder that holds `molecule-design-stage/`;
   - `reply_hint: false`;
   - `text`: one whole message. It contains the step's `system:` block, the packet
     path, the output format the step's protocol asks for, and these three lines:
     *Read the files yourself. Do not edit, create or delete any file. State the model
     id you are running as on the first line of your answer.*
3. **Wait for `done`.** Poll `mcp__agent-hud__get_message` with the returned id.
   `queued`, `taken` and `started` are not answers. `done` carries the whole reply and
   the new session's id. `refused` before delivery is `refused`. `expired`, `uncertain`
   or a long silence after `started` is post-dispatch: see below.
4. **Save the raw reply first.** Write it to
   `molecule-design-stage/_reviews/ROUND_N_step<S>_<label>_raw.md` before
   interpreting a word of it. If the client shortened the tool result into a file, copy
   that file.
5. **Check the reviewer wrote nothing.** Compare the stage folder's file list and
   modification times with the ones taken before dispatch, and run
   `provenance.py verify`. An Agent HUD session is a full agent; the brief asks it to
   stay read-only, but nothing enforces that. A review whose reviewer changed a file
   is void. Restore the file and tell the user.

Each message is one pass. Agent HUD refuses further messages after its back-and-forth
limit (10 by default) until the user steps in. A refusal for that reason is
`pass_limit`. It is not switchable, because a different provider would only hide the
limit. The exchange below stays well under it.

## Rebuttal exchange (Steps 3.5 and 9.5)

A reviewer can be wrong, and the executor sometimes knows why: a file the reviewer
misread, or a constraint the spec states explicitly. Steps 3.5 and 9.5 allow a short,
recorded exchange in the **same** reviewer session or thread:

- At most `REVIEW_REBUTTAL_ROUNDS` (2) executor messages per step. Each is one whole
  message covering every contested item. Each item is the candidate id, the flag, and
  the evidence as a file path with a line or row, or a spec clause. Opinion is not
  evidence. Nothing new is introduced: no new candidates, no revised SMILES, no
  summary that replaces a file.
- The reviewer answers each item `concede`, `maintain` or `modify`, with a reason.
  **The reviewer's last answer is the record.** The executor never downgrades a flag on
  its own.
- An item still `maintain` after the last round is `disputed`. It keeps the reviewer's
  flag. It is listed for the user at Step 7, with both positions and their evidence.
- Every exchange goes, verbatim, into the raw file and into a *Rebuttal exchange*
  section of the step's output (`ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`,
  `ROUND_N_CLAIM_AUDIT.md`). Conceded items carry the reviewer's own reason.
- **Step 11 has no rebuttal.** The executor does not argue its candidates' scores up.
  A scoring error is corrected only by a fresh Step 11 thread over corrected inputs.
- Use the transport's follow-up tool. Agent HUD: `send_message` to the session id with
  `reply_hint: false`, then `get_message`. `mcp`: the reply tool with the saved
  thread id. `manual`: the user relays both sides.

## When a backend fails

Classify the failure. Then re-resolve with `--failed <label>:<reason>`.

| Switchable: nothing ran | Not switchable: it may have run |
|---|---|
| `tool_missing`, `start_failed`, `auth_rejected`, `billing_rejected`, `region_unavailable`, `model_unsupported`, `refused` | `timeout`, `disconnected`, `server_error`, `parse_error`, `rate_limited`, `cancelled`, `empty_reply`, `expired`, `uncertain`, `pass_limit` |

Examples, by evidence:
- *credits depleted* (HTTP 402) → `billing_rejected`;
- *no valid licence* (403 before the request is accepted) → `auth_rejected`;
- *not available in your location* → `region_unavailable`;
- the bridge process exits at start → `start_failed`.

A switchable failure moves to the next fallback, if the user configured one. A
non-switchable failure stops the step with `REVIEW_UNAVAILABLE`. That review may have
run, and been billed; trying someone else would double-run it and hide the first
result. Never retry a dispatched call automatically. Never fill a missing review with
the executor's own judgement. Record every attempt, failed ones included.

## Accepting a review

A review counts only when all of these hold:

1. The transport reported completion: no `isError`, a nonempty answer, and Agent HUD
   `done`.
2. The raw reply is saved.
3. The reviewer wrote no file.
4. The answer covers every candidate in the packet.

Missing any of these, the step is incomplete, never a pass.

Then judge independence from the model that actually answered:

```bash
python3 scripts/reviewer_route.py independence \
  --executor-model <executor's model> --reviewer-model <reported model>
```

- Reported model, in order of preference: the transport's own report; the Agent HUD
  client default from step 1; the reviewer's first-line self-report. Record which one
  it was in `model_source`.
- `independent` → accepted.
- `same_family` → `provisional`. The review is kept, but it cannot clear a Step 3.5
  `revise` flag or a Step 9.5 `overclaim`, and Step 13 names it under run integrity.
- `unknown` → also `provisional`, until the user confirms the model.

The output files keep their historical names (`ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`,
`gemini_*` columns) whatever backend ran. Each one opens with a header line:
`Reviewer: <label> · model <id> (<model_source>) · independence <verdict>`.

## Search steps

The `search` role must be able to retrieve. A backend with `search_capability:
needs_check` (Codex, Antigravity, DeepSeek, manual) may serve it only if its answer
lists the sources it retrieved, with a DOI or URL for each. An answer without them is
incomplete:
- Step 5.5 then marks every candidate `prior_art_status: uncertain`; never `novel`.
- Step 1.5-B records the packet as *no retrieval evidence*.

An answer saying it found no match is a `novel` finding only if it says what was
searched. `claude-code` cannot serve this role through its bridge.

## What goes into the state file

`DESIGN_LOOP_STATE.json` → `reviewer_routes[]`. Add one entry per role per round, and
one per attempt, so a fallback is visible.
- Pass the review and search labels and models to `provenance.py snapshot` as
  `--note reviewer=<label>:<model>` and `--note search=<label>:<model>`.
- The fields are listed in
  [design-loop-state-schema.md](design-loop-state-schema.md).
