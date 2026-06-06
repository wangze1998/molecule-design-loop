# 更新记录

`molecule-design-loop` 的重要变更会记录在这里。

---

## v0.2.1 — 2026-06-06

新功能灵感来自 Anthropic "Making Claude a Chemist" 研究。结构图像输入降低了设计种子的门槛；NMR 预测增加了零依赖的结构合理性检查。同时整理了重复的 schema 文件，AGENT_GUIDE 更新至当前工作流。

### 新增

- **步骤 0.5 — 结构图像输入**：用户可以提供 PNG/JPG/PDF 图像（文献截图、ChemDraw 图片、手绘草图）代替手动输入 SMILES。Claude 直接从图像提取结构，经 RDKit 验证后输入步骤 1。低置信度提取需用户确认。协议：`references/structure-image-input-protocol.md`。
- **步骤 9.7 — NMR 预测与验证**（可选）：Claude 使用内部化学知识为候选分子预测 1H/13C NMR 化学位移、裂分和偶合常数（1H ±0.079 ppm，13C ±1.37 ppm，按 Anthropic 基准）。有实验 NMR 数据时，进行 predicted vs. experimental 比对，为每候选生成 `verification_status`（`confirmed`/`consistent`/`inconclusive`/`mismatch`）。`mismatch` 触发强制结构复核。协议：`references/nmr-prediction-protocol.md`。
- 新产出文件：`IMAGE_EXTRACTED_SMILES.csv`、`ROUND_N_NMR_PREDICTIONS.csv`、`ROUND_N_NMR_VERIFICATION.md`。
- 决策新增列：`nmr_verification_status`。
- 新常量：`NMR_PREDICTION`、`NMR_VALIDATED_SOLVENTS`、`NMR_1H_TOLERANCE`、`NMR_13C_TOLERANCE`、`IMAGE_INPUT`、`IMAGE_LOW_CONFIDENCE_REQUIRES_CONFIRMATION`。
- `design_spec_template.md`：新增"结构图像输入"和"NMR 预测与验证"配置节。

### 调整

- **`candidate-generation-schema.md` 合并至 `candidate_schema.md`**：生成规则（桶分配、突变族、文献溯源）和 CSV 列契约合为一个文件。SKILL.md 引用已更新。
- **`gemini-scoring-protocol.md`**：Gemini 评分输入增加 NMR 验证文件；输出字段新增 `nmr_verification_status`；新增 NMR 证据使用规则。
- **AGENT_GUIDE.md**：工作流图、产出契约和执行清单更新至步骤 0.5、3.5、5.5、9.5、9.7。
- **README.md / README.zh-CN.md**：工作流图和文件清单更新至 v0.2.1。

### 去除

- `references/candidate-generation-schema.md`（已合并至 `candidate_schema.md`）
- v0.2.0 更新日志中的重复段落

### 备注

- NMR 预测无需外部工具——使用 Claude 原生化学知识。预测结果标注"Claude-predicted"，与 xTB 结果共用结论审计规则。
- 结构图像输入使用 Claude 多模态能力，无需 OCR 工具。

---

## v0.2.0 — 2026-05-31

完整重构。原来的单体 SKILL.md（1041 行）拆分为精简的编排器（360 行）加十个专项协议文件。三个新的强制质量门控——对抗性审查、新颖性检查、结果→结论审计——把文献知识、候选生成和评分串联成闭环。Zotero 与主动搜索现在以平等的并行流运行，在任何候选提出之前完成。

### 重构

- **SKILL.md 重构**：从 1041 行缩减至 360 行。所有步骤细节迁移至 `references/` 协议文件。
- **`references/` 目录**：从旧 SKILL.md 中提取出十个协议文件，每个独立成章。

### 新增

- 双流文献：Zotero 提取（步骤 1.5-A）+ 主动搜索（步骤 1.5-B）并行，两流地位平等。
- 步骤 3.5：Gemini 对抗性化学审查。产出 `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`。
- 步骤 5.5：新颖性检查。`known` 候选自动降级为 control。产出 `ROUND_N_NOVELTY_CHECK.md`。
- 步骤 9.5：结果→结论审计。`overclaim` 标记阻止步骤 11 打 4/5 分。产出 `ROUND_N_CLAIM_AUDIT.md`。
- 新产出文件：`ZOTERO_KNOWLEDGE_PACKET.md`、`ZOTERO_SEED_SMILES.csv`、`ACTIVE_SEARCH_PACKET.md`。
- 候选新增列：`zotero_source_key`、`zotero_source_title`、`zotero_grounding`。
- 决策新增列：`prior_art_status`、`claim_audit_flag`、`gemini_adversarial_flag`。
- Zotero MCP 和 Gemini MCP 成为一等角色。Claude 不再自我审查候选。

### 备注

- 需配置 `mcp__zotero-mcp`、`mcp__gemini-review`、`mcp__gemini-research`。不可用时优雅降级。
- xTB 审批门（步骤 7）和核心 RDKit 管线不变。

---

## v0.1.3 - 2026-05-19

这一版把公开仓库整理成更贴近化学科研使用场景的分子与聚合物设计 skill。

### 新增

- `SHARE_PACKAGE.md` 和 `SHARE_PACKAGE.zh-CN.md`，用于说明可安装 skill 包的组成
- README 和中文 README 中明确加入"聚合物设计"定位

### 备注

- 这一版没有修改主工作流逻辑。

## v0.1.2 - 2026-05-18

面向 GitHub 仓库首页的发布说明刷新。无工作流逻辑变化。

## v0.1.1 - 2026-05-12

发布脱敏后的阶段入口源码包 `molecule-design-stage-src/`。

## v0.1.0 - 2026-05-10

首次公开开源包装：主 skill、双语文档、安装脚本、可选文献配套 skill。
