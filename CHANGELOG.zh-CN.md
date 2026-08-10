# 更新记录

`molecule-design-loop` 的重要变更会记录在这里。

---

## v0.2.3 — 2026-08-10

把 v0.2.2 的合成经济性工作从"单一成本标量"扩展为"多目标实用性画像"，并把实用性从**平手判定**升级为**支配判定**。灵感来自多目标合成规划工作（Hastedt, Zhang & del Rio Chanona，*From Feasible to Practical: Pareto-Optimal Synthesis Planning*，arXiv:2605.07521）——其核心论点是：一条仅仅"存在"的路线并不等于"值得走"的路线，而把路线选择标量化会抹掉权衡结构。纯文档改动，未改动 Python。

### 新增

- 合成闸门新增列 `overall_yield_estimate`（`high`/`medium`/`low`/`unknown`）与 `hazard_toxicity_flag`（`none`/`standard_care`/`high_hazard`/`unknown`）—— 这是 v0.2.2 缺失的两根实用性轴。仅有成本与取样时间，无法区分"便宜但高危"与"便宜且温和"的两条路线。
- 合成闸门新增推荐列 `route_alternatives` —— 以 `route_id | steps | cost | yield_estimate | hazard_flag` 紧凑记录 1-3 条候选路线，使路线选择保持可见，而不是被压缩成单个 `synthesis_cost` 数字。若证据只支持一条路线，填 `single_route_only`。
- Gemini 打分新增输出字段 `practicality_dominance`（`non_dominated` / `dominated_by:<candidate_id>` / `not_assessed`）。

### 变更

- **实用性从平手判定升级为支配判定。** v0.2.2 只在候选"其他方面打平"时才使用合成成本，这太弱了——一个候选可能在**每一根**实用性轴上都更差，却因为性质分略高而胜出。Step 11 现在在 {性质契合, `synthesis_cost`, `time_to_first_sample`, `overall_yield_estimate`, `hazard_toxicity_flag`} 上计算支配关系；被支配的候选无论分数多高都不得进入 `pareto_rank` 前三。非支配前沿内部的排序保留 make/buy 平手判定。
- `unknown` 在所属轴上视为不可比较（既不能支配也不能被支配），并降低 `confidence`，避免"数据缺失"被洗成有利排名。
- 多个非支配候选以**权衡集合**呈现，而不是强行挑出唯一的第一名。

### 诚实边界

- 在没有真实逆合成/CASP 引擎与价格/毒性数据库的情况下，`route_alternatives` 与各实用性轴都是**启发式估计**，**不是**多目标 CASP 搜索意义上有最优性保证的路线 Pareto 前沿，必须标注为估计。若环境中有 CASP 工具，优先采用其输出并记入 `retrosynthesis_tool`。宁可填 `unknown`，不要编造收率或成本。此边界与既有的"SA score 不是路线"规则对称。

### 说明

- 更新 SKILL.md 步骤 5 与 11；`synthesis-gate-schema.md`、`gemini-scoring-protocol.md`、`candidate_schema.md`、`AGENT_GUIDE.md` 同步更新。
- 未尝试复现多目标逆合成搜索本身。那需要训练好的单步模型、价格数据库、收率/毒性模型——这些硬依赖会破坏本 skill "连 xTB 都是可选、缺失时明确报阻塞"的轻量设计。

---

## v0.2.2 — 2026-06-12

闭合"决定要不要做"逻辑里两条一直开口的回路：跨轮失败记忆与合成经济性。此前这两套机制都只"记录"知识，没有任何环节强制下一轮去用它。本次发布把这些知识变成强制项。纯文档改动，不改 Python（RDKit 过滤器本就接受这里所依赖的列表型参数）。

### 新增

- **`references/design-loop-state-schema.md`** —— 为 `DESIGN_LOOP_STATE.json` 定义了真正的机器可读 schema。该文件在 SKILL.md / AGENT_GUIDE.md 中被引用 5 次以上，却从无定义。新 schema 规定了 `killed_motifs[]`（`smarts` 为必填）、`failed_reactions[]`、`available_building_blocks[]`、`successful_moves[]`、`scaffold_families_explored`、`evidence_gaps`、`hypotheses_to_revisit`、`experimental_endpoints`，并附最小可用 JSON 示例。
- 合成闸门新增列 `synthesis_cost`（`low`/`medium`/`high`/`very_high`）与 `time_to_first_sample`（`same_day`/`days`/`weeks`/`months`）。
- 候选新增列 `building_block_source`（`in_stock`/`purchasable`/`custom`/`unknown`），以及"偏向货架原料"的候选桶。
- Gemini 打分输出新增字段 `synthesis_cost` 与 `time_to_first_sample`。

### 变更 —— 四处闭合

- **(A) 跨轮失败记忆变为强制。** Step 3 必须读取 `DESIGN_LOOP_STATE.json` 并排除命中 `killed_motifs[]` 的 SMARTS/母核的候选（仅在 `rationale` 中写明 rescue 假设时方可重提）。Step 4 的 `--forbidden-smarts` 必须是 spec 的 `forbidden_motifs` 与全部历史 `killed_motifs[].smarts` 的并集。这从结构上杜绝了重提已杀死结构。
- **(B) 合成成本成为一等排序轴。** 合成闸门产出可直接排序的 `synthesis_cost`/`time_to_first_sample`；Step 11 的 Pareto 排序必须纳入它们，并加 make/buy 平手判定（`buy` < `make_on_demand` < `custom_synthesis`）。性质很好但要 8 步定制合成的分子，不再悄悄排在同等性质、2 步货架可得的分子之前。
- **(C) 可得性前移到生成环节。** Step 1 把已知/可购买原料写入 `DESIGN_LOOP_STATE.json`；Step 3 用 `building_block_source` 标记，并把一部分候选偏向这些原料。
- **(D) 实验失败信号回流到状态文件。** Step 12 必须把实验 `failure_mode`（来自 `ROUND_N_EXPERIMENT_RESULTS.csv`）与对抗评审 `likely_lab_failure_mode`（来自 `ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md`）结构化写回 `killed_motifs[]`/`failed_reactions[]`，使下一轮自动排除。

### 说明

- A 与 D 是同一根回路的两端（写下失败 → 下一轮排除）；B 与 C 在排序端（后）与生成端（前）闭合合成经济性回路。
- 更新了 SKILL.md 的 Step 1、3、4、5、11、12；同步更新 `synthesis-gate-schema.md`、`gemini-scoring-protocol.md`、`candidate_schema.md`、`AGENT_GUIDE.md`。

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
