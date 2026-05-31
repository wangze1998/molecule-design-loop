# 更新记录

`molecule-design-loop` 的重要变更会记录在这里。

---

## v0.2.0 — 2026-05-31

完整重构。原来的单体 SKILL.md（1041 行）拆分为精简的编排器（360 行）加十个专项协议文件。三个新的强制质量门控——对抗性审查、新颖性检查、结果→结论审计——把文献知识、候选生成和评分串联成闭环。Zotero 与主动搜索现在以平等的并行流运行，在任何候选提出之前完成。

### 重构

- **SKILL.md 重构**：从 1041 行缩减至 360 行。所有步骤细节迁移至 `references/` 协议文件。编排器只说"每步做什么"，"怎么做"交给对应协议文件。
- **`references/` 目录**：从旧 SKILL.md 中提取出十个协议文件，每个文件独立成章，覆盖一个工作流步骤，可单独阅读和修改，不影响编排器。

### 新增协议文件

| 文件 | 覆盖内容 |
|---|---|
| `zotero-extraction-protocol.md` | 步骤 1.5-A — 如何从 Zotero 提取骨架、SAR、路线、失败案例 |
| `active-search-protocol.md` | 步骤 1.5-B — 并行搜索最新与 landmark 文献 |
| `candidate-generation-schema.md` | 步骤 3 — 桶规则、文献溯源要求、聚合物专项字段 |
| `adversarial-review-protocol.md` | 步骤 3.5 — Gemini 系统提示、标记逻辑、输出 schema |
| `synthesis-gate-schema.md` | 步骤 5 — 列契约、晋升规则 |
| `novelty-check-protocol.md` | 步骤 5.5 — 先验文献搜索、status 值、降级规则 |
| `claim-audit-protocol.md` | 步骤 9.5 — 证据→结论矩阵、`auditor_flag` 值 |
| `gemini-scoring-protocol.md` | 步骤 11 — 打分标准、Pareto 排名、必填输出字段 |
| `polymer-design-mode.md` | 聚合物/材料完整分支 — 显示规则、有限代理逻辑、非 xTB 目标 |
| `xtb-integrity-rules.md` | xTB 记录要求与化学设计规则 |

### 新增

- 双流文献：Zotero 提取（步骤 1.5-A）+ 主动搜索（步骤 1.5-B）并行，两流地位平等。
- 步骤 3.5：`mcp__gemini-review__review` 以挑剔化学家视角对每批候选发起对抗审查，RDKit 过滤前运行。产出 `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`。
- 步骤 5.5：`mcp__gemini-research__prior_art_search` 标记已报道结构。`known` 候选自动降级为 control。产出 `ROUND_N_NOVELTY_CHECK.md`。
- 步骤 9.5：`mcp__gemini-review__review` 以结论审计员身份为每条 xTB/RDKit 数值划定证明范围。`overclaim` 标记阻止步骤 11 打 4 或 5 分。产出 `ROUND_N_CLAIM_AUDIT.md`。
- 新产出文件：`ZOTERO_KNOWLEDGE_PACKET.md`、`ZOTERO_SEED_SMILES.csv`、`ACTIVE_SEARCH_PACKET.md`、三份 round 审计文件。
- 候选新增列：`zotero_source_key`、`zotero_source_title`、`zotero_grounding`。
- 决策新增列：`prior_art_status`、`claim_audit_flag`、`gemini_adversarial_flag`。
- `design_spec_template.md`：新增 Zotero 文献库集成配置节。
- Zotero MCP 和 Gemini MCP 成为角色分工的一等公民，Claude 不再自我审查候选。

### 备注

- 需在 Codex MCP 配置中注册 `mcp__zotero-mcp`、`mcp__gemini-review`、`mcp__gemini-research`，各门控在服务器不可用时优雅降级。
- xTB 审批门（步骤 7）和核心 RDKit 管线不变。

---

### 新增

- **双流文献智能**（步骤 1.5-A + 1.5-B）：候选生成前先并行跑两条文献流——用户的 Zotero 文献库（个人精选知识）和独立的主动搜索（领域最新与最权威文献）。两流地位平等，`LIT_PACKET.md` 合并两者；两流之间的矛盾会被显式标记。
- **Zotero 知识提取**（步骤 1.5-A）：通过 `mcp__zotero-mcp__*` 工具优先挖掘用户的个人文献库，提取已验证的骨架结构、SAR 规律、合成路线和已知失败模式。产出 `ZOTERO_KNOWLEDGE_PACKET.md` 和 `ZOTERO_SEED_SMILES.csv`。Zotero 不可用时优雅降级。
- **主动文献搜索**（步骤 1.5-B）：`mcp__gemini-research__literature_search` 作为并行必跑步骤，专门搜索近 1-2 年的最新文献和领域高引 landmark 文献。产出 `ACTIVE_SEARCH_PACKET.md`。
- **Gemini 对抗性化学审查**（步骤 3.5）：候选生成后立即调用 `mcp__gemini-review__review`，使用合成化学家挑剔视角的系统提示，直接读取候选 CSV 原始内容逐候选挑战。产出 `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`，每候选获得 `gemini_adversarial_flag`（`pass`/`warn`/`revise`）。
- **新颖性检查**（步骤 5.5）：调用 `mcp__gemini-research__prior_art_search` 检查候选是否已有文献报道。`known` 候选降级为 control，`analog` 候选保留晋升资格但需引用前体。异步运行，产出 `ROUND_N_NOVELTY_CHECK.md`。
- **结果→结论审计**（步骤 9.5）：xTB 后调用 `mcp__gemini-review__review` 使用结论审计员提示，明确每条计算数值能证明什么、不能证明什么。`overclaim` 候选在步骤 11 不能得 4/5 分。产出 `ROUND_N_CLAIM_AUDIT.md`。
- `ROUND_N_CANDIDATES.csv` 新增列：`zotero_source_key`、`zotero_source_title`、`zotero_grounding`。
- `ROUND_N_DECISION.md` 新增列：`prior_art_status`、`claim_audit_flag`、`gemini_adversarial_flag`。
- `design_spec_template.md` 新增 Zotero Library Integration 配置节。

### 调整

- 角色分工更新：Zotero MCP 和 Gemini 对抗审查者成为一等公民角色；Codex 不再自我审查候选。
- 步骤 2 文献包现在合并两流产出，而非从零外部搜索。
- 步骤 3：90% 候选必须有文献来源追溯，无来源探索性候选上限 10%。
- 步骤 11 打分在新 thread 中调用 `mcp__gemini-review__review`，先读三份审计文件再评分。
- 状态标识更新为 `v0.2.0`。

### 备注

- 需在 Codex MCP 服务器列表中配置 `mcp__zotero-mcp`、`mcp__gemini-review`、`mcp__gemini-research`。不可用时优雅降级。
- xTB 仍需人工确认，核心 RDKit 管线不变。

## v0.1.3 - 2026-05-19

这一版把公开仓库整理成更贴近化学科研使用场景的分子与聚合物设计 skill。

### 新增

- `SHARE_PACKAGE.md` 和 `SHARE_PACKAGE.zh-CN.md`，用于说明可安装 skill 包的组成
- README 和中文 README 中明确加入“聚合物设计”定位
- 在设计循环说明中补清楚单体、头基和结构 motif 的可解释迭代

### 调整

- 状态标识从 `v0.1.2` 更新为 `v0.1.3`
- README 和中文 README 现在把这个项目描述为分子/聚合物设计工作流，而不是只写成泛化的分子设计包
- 更新日志改成面向使用者的项目维护记录，重点说明本次公开版本实际带来的变化
- 分享包说明集中介绍主 skill、可选文献辅助和脱敏阶段入口

### 备注

- 这一版没有修改主工作流逻辑。
- RDKit 候选画廊之后，xTB 仍然需要人工确认后才会运行。
- Gemini 交接入口继续通过 `ROUND_N_GEMINI_INPUT.md` 保留在公开工作流中。

## v0.1.2 - 2026-05-18

这次是一次面向 GitHub 仓库首页的发布说明刷新。

### 新增

- README 中的 `v0.1.0 → v0.1.2` 版本轨迹总览
- README 中带日期的“最近更新”展示
- 更适合 GitHub 仓库首页直接阅读的发布历史说明

### 调整

- 状态标识从 `v0.1.1` 更新为 `v0.1.2`
- README 和中文 README 现在用更清晰的版本总结方式展示更新
- 更新日志仍然严格对应实际仓库历史，但在 GitHub 上更容易快速浏览

### 备注

- 这一版没有修改分子设计工作流逻辑
- 主 skill、阶段入口源码包和 Gemini 交接逻辑都与 `v0.1.1` 保持一致

## v0.1.1 - 2026-05-12

发布了一份脱敏后的分子设计阶段源码包，同时保留了 Gemini 交接入口。

### 新增

- 从私有工作目录提取出的 `molecule-design-stage-src/` 源码包
- 通用 `run_design.py` 可复用工作流入口
- 用于配置加载、候选生成、RDKit 过滤、画廊渲染、xTB 筛选、审批和报告的 `molecular_design/` 模块
- 可公开运行的示例配置 `inputs/example_run.yaml`
- 阶段入口包测试 `tests/test_molecular_design_workflow.py`

### 调整

- README 和中文 README 现在说明了可复用阶段入口包
- 主 skill 文档正式暴露 `ROUND_N_GEMINI_INPUT.md` 作为工作流产物
- 公开源码默认使用 `PATH` 上的 `xtb`，不再依赖私有本地 conda 路径

### 去除

- 公开入口包里的桌面绝对路径等私有信息
- 不再把项目专用的生成结果、xTB 作业目录和私有轮次产物带进公开发布内容

## v0.1.0 - 2026-05-10

这是该 skill 的首个公开开源包装版本。

### 新增

- 位于 `molecule-design-loop/` 的主 Codex skill
- RDKit 候选过滤辅助脚本
- HTML 候选画廊渲染脚本
- 设计规范模板与 xTB 审批模板
- 可选的 `research-lit` 配套 skill
- 中英文双语仓库文档
- 面向 AI agent 的 `AGENT_GUIDE.md`
- 贡献指南与 `.gitignore`

### 调整

- 将 README 重写为更完整的开源仓库首页
- 将中文 README 扩展为完整项目说明

### 修复

- 修正 `install_molecule_design_loop.sh --install-research-lit`，现在会从正确的目录结构安装可选 skill
