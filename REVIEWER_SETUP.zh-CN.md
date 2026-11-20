# 审阅者配置

[English](REVIEWER_SETUP.md)

`molecule-design-loop` 从不审自己的候选物。

- 有三步交给外部审阅者：第 3.5 步（对抗审查）、第 9.5 步（结果与结论核对）、第 11 步（打分）。
- 有两步交给检索后端：第 1.5-B 步（主动检索）、第 5.5 步（查新）。

本页讲怎么在你的电脑上配好这些。规则本身见
[`reviewer-selection-protocol.md`](molecule-design-loop/references/reviewer-selection-protocol.md)。

下面的占位符请换成你自己的：

- `<aris>`：你本地 ARIS 仓库的绝对路径。
- `<skill>`：已安装的 `molecule-design-loop` 文件夹。

## 1. 至少选一个与执行者不同家族的审阅者

审阅者不能和跑这个循环的 agent 属于同一模型家族：

| 循环跑在 | 可以审阅 | 不能审阅 |
|---|---|---|
| Claude Code | Gemini、Codex、Antigravity（Gemini 模型）、DeepSeek、manual | 任何形式的 Claude |
| Codex | Gemini、Antigravity、Claude Code、DeepSeek、manual | 任何形式的 Codex / GPT |

有一个审阅者就能跑。再配一个写进 `fallback`，第一个挂了（额度用完、许可被拒、账号所在地区不符合资格）时这一轮还能继续。

## 2. 安装你选的后端

每个 MCP 服务在用户级注册一次，路径用绝对路径，注册后重启客户端。

### Gemini（`gemini`）：默认审阅者

用 ARIS 仓库
（[wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)）
里 `mcp-servers/gemini-review/` 下的 `gemini-review` 桥接。需要一个 Gemini API key（`GEMINI_API_KEY`），
桥接也会读取 `~/.gemini/.env`。

```bash
claude mcp add gemini-review -s user -- python3 <aris>/mcp-servers/gemini-review/server.py
```

```bash
codex mcp add gemini-review -- python3 <aris>/mcp-servers/gemini-review/server.py
```

`gemini` 的**检索**路线需要一个 `gemini-research` MCP 服务，提供 `prior_art_search_start`、
`literature_search_start`、`literature_search_status` 三个工具。本仓库不附带这个服务。没有的话，有两种办法：

- 把 `search` 设成别的后端（见第 3 节）；
- 让第 1.5-B 步改用宿主自带的网页搜索或 `/research-lit`。

### Codex（`codex`）

安装 Codex CLI 并登录。在 Claude Code 里注册 ARIS 的 `codex-exec` 桥接。codex-cli 0.154 删掉了旧的
`codex mcp-server` 入口，所以要注册这个桥接，不要再用旧入口。

```bash
claude mcp add codex -s user -- python3 <aris>/mcp-servers/codex-exec/server.py
```

Codex 能不能上网搜索取决于它自己的配置；只有回答里列出了实际检索到的来源，循环才接受 Codex 的检索结果。在 Codex 宿主里，Codex 就是执行者，不能当审阅者。

### Antigravity（`antigravity`）

安装 Antigravity CLI（`agy`）并登录，然后注册 ARIS 的桥接：

```bash
claude mcp add antigravity -s user -- python3 <aris>/mcp-servers/antigravity-exec/server.py
```

有些账号会被拒绝，提示「所在地区不符合资格」（not eligible in your location）。这种拒绝发生在任何请求运行之前，所以如果配置了后备，会自动接上。

### Claude Code（`claude-code`）：只在循环跑在 Codex 里时用

```bash
codex mcp add claude-review -- python3 <aris>/mcp-servers/claude-review/server.py
```

### Agent HUD（`…@agent-hud`）：用另一个 agent 会话当审阅者

[Agent HUD](https://agenthud.app) 是 macOS 14 以上的应用，需单独授权。它能在你的电脑上打开
Codex、Antigravity、DeepSeek Harness 或 Claude Code 会话，并在会话之间传话。这样审阅者就是一个完整的 agent：

- 它自己读输入包；
- 循环可以在同一个会话里回应它的批评，也就是「反驳对话」。

DeepSeek 只能通过这种方式接入。

```bash
claude mcp add agent-hud -s user -- "/Applications/Agent HUD.app/Contents/MacOS/Agent HUD" --mcp
```

```bash
codex mcp add agent-hud -- "/Applications/Agent HUD.app/Contents/MacOS/Agent HUD" --mcp
```

目标客户端必须已安装、已登录、正在运行：

- Codex：桌面版或 CLI；
- Antigravity：已登录的 Antigravity；
- DeepSeek：装了 Agent HUD 插件的 DeepSeek Harness。

让你的 agent 调一次 `mcp__agent-hud__list_models` 检查：哪个客户端返回的是 `reason` 而不是模型列表，就说明它还用不了。

Agent HUD 打开的会话是能读写文件的完整 agent。循环会要求它只读，事后也会检查，但只在可以接受这一点的项目里用它。

### 手动（`manual`）

什么都不用装。循环写好输入包后停下，你把它交给任意模型，再把回复存成循环指定的文件。

## 3. 写配置

循环按顺序取第一个存在的配置：

1. 本次运行的参数（`-- reviewer: …`）；
2. `molecule-design-stage/reviewer.json`，只对这个项目生效；
3. `~/.config/molecule-design-loop/reviewer.json`（或 `$XDG_CONFIG_HOME/…`），你的长期偏好；
4. 默认 Gemini。

复制 [`examples/reviewer.example.json`](examples/reviewer.example.json) 再改。常见写法：

```json
{"backend": "gemini", "fallback": ["codex", "manual"]}
```

```json
{"review": {"backend": "codex", "via": "agent-hud"},
 "search": {"backend": "gemini"},
 "fallback": ["deepseek@agent-hud", "manual"]}
```

```json
{"review": {"backend": "antigravity", "model": "<你的 agy 账号列出的模型>", "effort": "high"},
 "fallback": ["codex"]}
```

- 平铺写法对两个角色都生效；`review` 或 `search` 块会覆盖它。
- `fallback` 要你主动写才有；只有在失败能证明请求没跑过时才会用到。
- 不需要特定模型就别写 `model`。不管写没写，循环都会记录实际作答的模型。

单次运行时这样指定：

```text
/molecule-design-loop "design_spec.md -- reviewer: codex@agent-hud -- search: gemini"
```

## 4. 检查

```bash
python3 <skill>/scripts/reviewer_route.py show --host claude-code
```

循环跑在 Codex 里时用 `--host codex`。输出会列出：

- 找到了哪些配置文件；
- 每个角色选中了哪个后端；
- 有没有配置错误。

想连工具能不能用也一起检查，就让 agent 加上 `--available`，后面跟它能看到的 `mcp__…` 工具名再跑一次。退出码 0 表示两个角色都有可用后端；3 表示有一个没有。

最后让 agent 对选中的审阅者做一次最小调用。以 Agent HUD 为例：用 `start_session` 发「reply with your model id」，再用 `get_message` 等到 `done`。

## 5. 出错时

| 看到 | 含义 | 会怎样 |
|---|---|---|
| HTTP 402、额度用完 | `billing_rejected` | 有后备就换下一个 |
| 403、没有有效许可 | `auth_rejected` | 换下一个 |
| 「not available in your location」 | `region_unavailable` | 换下一个 |
| agent 的工具列表里没有该工具 | `tool_missing` | 换下一个 |
| Agent HUD 客户端返回 `reason` | `start_failed` | 换下一个 |
| 超时、断线、空回复 | 审阅可能已经跑过 | 这一步停下，报 `REVIEW_UNAVAILABLE`；不换别家 |
| 「is the executor's own family」 | 在 Claude Code 里选了 Claude（或在 Codex 里选了 Codex） | 换一个后端 |
| Agent HUD 提示 pass limit | 没有你介入的来回消息太多 | 你介入一下再继续 |

每一次尝试，包括失败的，都会记在 `DESIGN_LOOP_STATE.json` 的 `reviewer_routes[]` 里，报告的「运行完整性」一节也会列出来。
