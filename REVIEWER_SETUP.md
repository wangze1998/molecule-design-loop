# Reviewer setup

[中文](REVIEWER_SETUP.zh-CN.md)

`molecule-design-loop` never reviews its own candidates. Three steps go to an outside
reviewer: Step 3.5 (adversarial review), Step 9.5 (claim audit) and Step 11 (scoring).
Two steps go to a search backend: Step 1.5-B (active search) and Step 5.5 (prior-art
check). This page sets those up on your machine. The rules behind them are in
[`reviewer-selection-protocol.md`](molecule-design-loop/references/reviewer-selection-protocol.md).

Placeholders below, replace with your own values:
- `<aris>`: the absolute path of your clone of the ARIS repository.
- `<skill>`: the installed `molecule-design-loop` folder.

## 1. Pick at least one reviewer from another model family

The reviewer must not be the same model family as the agent running the loop:

| The loop runs in | Can review | Cannot review |
|---|---|---|
| Claude Code | Gemini, Codex, Antigravity (Gemini model), DeepSeek, manual | Claude in any form |
| Codex | Gemini, Antigravity, Claude Code, DeepSeek, manual | Codex / GPT in any form |

One reviewer is enough to run. A second one, listed as `fallback`, keeps a round going
when the first is down: credits run out, a licence is refused, or an account is not
eligible in its region.

## 2. Install the backends you chose

Register each MCP server once, at user scope. Use absolute paths. Restart the client
afterwards.

### Gemini (`gemini`): the default reviewer

Uses the `gemini-review` MCP bridge from the ARIS repository
([wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep),
`mcp-servers/gemini-review/`). Give it a Gemini API key (`GEMINI_API_KEY`). The bridge
also reads `~/.gemini/.env`.

```bash
claude mcp add gemini-review -s user -- python3 <aris>/mcp-servers/gemini-review/server.py
```

```bash
codex mcp add gemini-review -- python3 <aris>/mcp-servers/gemini-review/server.py
```

The `gemini` **search** route expects a `gemini-research` MCP server exposing
`prior_art_search_start`, `literature_search_start` and `literature_search_status`.
This repository does not ship one. If you do not have it, set `search` to another
backend (section 3), or let Step 1.5-B use the host's web search or `/research-lit`.

### Codex (`codex`)

Install the Codex CLI and sign in. From Claude Code, register ARIS's `codex-exec`
bridge. codex-cli 0.154 removed the old `codex mcp-server` entry point, so register the
bridge, not that.

```bash
claude mcp add codex -s user -- python3 <aris>/mcp-servers/codex-exec/server.py
```

Whether Codex can search the web depends on its own configuration. The loop accepts a
Codex search only when the answer lists the sources it retrieved. Inside Codex itself,
Codex is the executor and cannot review.

### Antigravity (`antigravity`)

Install the Antigravity CLI (`agy`) and sign in. Then register ARIS's bridge:

```bash
claude mcp add antigravity -s user -- python3 <aris>/mcp-servers/antigravity-exec/server.py
```

Some accounts are refused as "not eligible in your location". That refusal happens
before anything runs, so a configured fallback takes over.

### Claude Code (`claude-code`): only when the loop runs in Codex

```bash
codex mcp add claude-review -- python3 <aris>/mcp-servers/claude-review/server.py
```

### Agent HUD (`…@agent-hud`): another agent session as the reviewer

[Agent HUD](https://agenthud.app) is a macOS 14+ app, licensed separately. It can open
a Codex, Antigravity, DeepSeek Harness or Claude Code session on your machine and pass
messages to it. The reviewer is then a whole agent: it reads the packet itself, and
the loop can answer its critique in the same session (the rebuttal exchange).
DeepSeek is reachable only this way.

```bash
claude mcp add agent-hud -s user -- "/Applications/Agent HUD.app/Contents/MacOS/Agent HUD" --mcp
```

```bash
codex mcp add agent-hud -- "/Applications/Agent HUD.app/Contents/MacOS/Agent HUD" --mcp
```

The target client must be installed, signed in and running:
- Codex: the desktop app or the CLI.
- Antigravity: a signed-in Antigravity.
- DeepSeek: a DeepSeek Harness with Agent HUD's plugin.

Ask your agent to call `mcp__agent-hud__list_models`. A client that shows a `reason`
instead of models is not usable yet.

Agent HUD sessions are full agents with file access. The loop tells them to stay
read-only and checks afterwards, but run them only in projects where that is
acceptable.

### Manual (`manual`)

Nothing to install. The loop writes the review packet and stops. You give the packet
to any model you like and save its reply as the file the loop names.

## 3. Write the configuration

The loop takes the first of these that exists:
1. this run's flags (`-- reviewer: …`);
2. `molecule-design-stage/reviewer.json`, for this project;
3. `~/.config/molecule-design-loop/reviewer.json` (or `$XDG_CONFIG_HOME/…`), for your
   standing preference;
4. the Gemini default.

Copy [`examples/reviewer.example.json`](examples/reviewer.example.json) and edit it.
Typical setups:

```json
{"backend": "gemini", "fallback": ["codex", "manual"]}
```

```json
{"review": {"backend": "codex", "via": "agent-hud"},
 "search": {"backend": "gemini"},
 "fallback": ["deepseek@agent-hud", "manual"]}
```

```json
{"review": {"backend": "antigravity", "model": "<a model your agy account lists>", "effort": "high"},
 "fallback": ["codex"]}
```

- A flat object applies to both roles. A `review` or `search` block overrides it.
- `fallback` is opt-in. The loop uses it only when the failure proves nothing ran.
- Leave `model` out unless you need a specific one. The loop records the model that
  actually answered either way.

For one run:

```text
/molecule-design-loop "design_spec.md -- reviewer: codex@agent-hud -- search: gemini"
```

## 4. Check it

```bash
python3 <skill>/scripts/reviewer_route.py show --host claude-code
```

Use `--host codex` when the loop runs in Codex. The output lists:
- which config files were found;
- the backend each role resolves to;
- any configuration error.

To also check that the tools are reachable, have your agent run it with `--available`,
followed by the `mcp__…` tool names it can see. Exit 0 means both roles have a usable
backend; exit 3 means one does not.

Then have your agent make one tiny call to the chosen reviewer. For Agent HUD:
`start_session` with "reply with your model id", then `get_message` until `done`.

## 5. When something fails

| You see | It means | What happens |
|---|---|---|
| HTTP 402, "credits depleted" | `billing_rejected` | next fallback, if configured |
| 403, "no valid licence" | `auth_rejected` | next fallback |
| "not available in your location" | `region_unavailable` | next fallback |
| tool not in the agent's tool list | `tool_missing` | next fallback |
| Agent HUD client shows a `reason` | `start_failed` | next fallback |
| timeout, dropped connection, empty reply | the review may have run | the step stops: `REVIEW_UNAVAILABLE`; no other provider is tried |
| "is the executor's own family" | you picked Claude while running in Claude Code (or Codex in Codex) | pick another backend |
| Agent HUD "pass limit" | too many messages without you | step in, then continue |

Every attempt, failed ones included, is recorded in `DESIGN_LOOP_STATE.json` under
`reviewer_routes[]`. The report lists them under *Run integrity*.
