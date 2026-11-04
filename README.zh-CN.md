# Molecule Design Loop

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Codex Skill](https://img.shields.io/badge/Codex-skill-black)
![Status](https://img.shields.io/badge/status-v0.3.1-blue)

一个面向 agent 的开源分子与聚合物设计 skill，Claude Code 和 Codex 都能用，强调约束驱动设计。把用户的 Zotero 文献库与主动文献检索结合起来，配合对抗性化学审查、新颖性检查和结果→结论审计，以及 RDKit 过滤、看图确认和 xTB 前的人工审批。结构和审查输入包由带测试的脚本生成，不再由模型手写。

[English](README.md) | [中文说明](README.zh-CN.md) | [更新日志](CHANGELOG.zh-CN.md) | [分享包说明](SHARE_PACKAGE.zh-CN.md)

> **当前版本：v0.3.0**（2026-11-04）。这是一次 token 经济性发布：SKILL.md 改成路由（457 → 276 行），`scripts/build_candidates.py` 由一个结构推导出全部机械列并在写出前逐条校验，`scripts/build_gemini_inputs.py` 由轮次文件拼出 Step 3.5 / 5.5 / 9.5 的审查输入包，`scripts/inspect_round.py` 提供大文件的有界视图。契约测试负责让 SKILL.md 保持精简、链接有效、本机路径不进仓库。见 [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)。
> **xTB 前的人类审批仍然是强制的。** **Zotero MCP 和 Gemini MCP 需要配置**才能使用新步骤——不可用时工作流优雅降级。

如果你是 AI agent，请先看 [AGENT_GUIDE.md](AGENT_GUIDE.md)。

> 这是一个"先约束、后计算"的分子设计工作流：先过滤明显不合理结构，再人工看图确认，最后再让 xTB 提供证据，而不是替你做最终科学判断。

## 当前状态

- 当前发布：`v0.3.1` — token 经济性（路由式 SKILL.md、生成候选表与审查输入包、有界文件查看、仓库契约测试），并修正 Step 9.5 输入包的 xTB 列名
- 仓库定位：模块化 Codex skill，Zotero 驱动、对抗性审查的分子设计
- 更新记录：[CHANGELOG.md](CHANGELOG.md) | [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)
- 分享包范围说明：[SHARE_PACKAGE.md](SHARE_PACKAGE.md) | [SHARE_PACKAGE.zh-CN.md](SHARE_PACKAGE.zh-CN.md)

## 版本轨迹

**v0.3.1**（2026-11-04）— 修复：Step 9.5 输入包脚本读 xTB 结果文件用的列名不是 `candidate_schema.md` 规定的那套，按 schema 写的轮次文件因此产出一个没有数字的证据段；而测试数据用的是脚本自己的列名，所以测试一直没抓到。现在以 schema 列名为准，旧列名作为别名接受，缺失的必需列会被点名而不是静默丢掉。

**v0.3.0**（2026-11-04）— token 经济性。一整轮设计的成本远超其化学含量：模型手写派生列、整篇读参考与轮次文件、再把溢出到磁盘的长输出读回来。SKILL.md 改为带明确阅读规则与交接点的步骤路由；`build_candidates.py`、`build_gemini_inputs.py`、`inspect_round.py` 把派生数据、审查输入包和文件查看搬进带测试的代码；`test_skill_contract.py` 强制 SKILL.md 的行数预算、链接有效、脚本有测试、本机路径不进仓库。

**v0.2.6**（2026-11-04）— v0.2.5 的排序诊断变成一个确定性、带测试的脚本（`scripts/ranking_diagnostics.py`）：支配判定、pareto/shadow 排名、具体的排除理由、Kendall τ-b 矩阵、被支配/被评估计数，仅标准库，带 `--benchmark-ids` 已知化合物回收。用代码强制"unknown 不可比、绝不用哨兵值"。

**v0.2.5**（2026-11-03）— 排序开始审计自己。五条排序轴之间的 Kendall τ-b 冗余矩阵（用 τ-b 而非 Pearson——这些轴是并列极多的有序变量）、强制报告 `candidates_dominated / candidates_assessed`（避免"什么都没支配掉"的判据冒充一个在起作用的闸门）、以及仅按性质契合度的 `shadow_rank_property_only` 消融排序，逐一点名被实用性约束排除的候选及其原因。

**v0.2.4**（2026-08-21）— loop 必须说出自己**不知道**什么。当设计目标属于无法提供证据的性质（亲和力、活性、选择性、自组装……）时，即使从未运行 xTB，claim-audit 也会触发并给出 `no_direct_evidence`。新增 `loop_calibration` 块追踪"推荐 vs. 实际成功"与"预测 vs. 实测"，并在 `DESIGN_REPORT.md` 中如实报告。

**v0.2.3**（2026-08-10）— 合成实用性变为多目标且具约束力：闸门新增 `overall_yield_estimate` 与 `hazard_toxicity_flag` 列、可选的 `route_alternatives` 权衡画像；步骤 11 改为在 {性质契合, 成本, 时间, 收率, 危害} 上按 Pareto **支配关系**排序，而非平手判定。被支配的候选不得进入前三。

**v0.2.2**（2026-06-12）— 强制跨轮失败记忆：定义 `DESIGN_LOOP_STATE.json` schema，已杀死母核在步骤 3/4 自动排除。合成成本/取样时间成为一等 Pareto 排序轴（步骤 11），可得原料偏置生成（步骤 1/3），实验与对抗评审的失败信号回流到状态文件（步骤 12）。

**v0.2.1**（2026-06-06）— 结构图像输入（步骤 0.5）和 NMR 预测/验证（步骤 9.7）。重复的 `candidate-generation-schema.md` 合并至 `candidate_schema.md`。AGENT_GUIDE 和 README 同步更新。

**v0.2.0**（2026-05-31）— 完整重构。SKILL.md 从 1041 行精简至 360 行，提取十个协议 reference 文件。双流 Zotero + 主动搜索文献。三个新强制门控：对抗性化学审查（步骤 3.5）、新颖性检查（步骤 5.5）、结果→结论审计（步骤 9.5）。Gemini 和 Zotero MCP 成为一等角色。

**v0.1.3**（2026-05-19）— 聚合物设计文档和分享包说明。

**v0.1.2**（2026-05-18）— 仓库展示刷新，无工作流变化。

**v0.1.1**（2026-05-12）— 脱敏后阶段入口源码包（`molecule-design-stage-src/`）。

**v0.1.0**（2026-05-10）— 首次公开开源包装。

## 这个仓库解决什么问题

很多"LLM 做分子设计"的流程有几个常见问题：

- 生成分子时不锚定领域已知的骨架和 SAR
- 让同一个模型既设计候选又评分——没有对抗性审查
- 把 xTB 数值直接推入设计结论，没有审计这些数值到底能证明什么

`molecule-design-loop` 就是针对这些失败模式的结构化循环。

## 最近更新

- **2026-11-04** — v0.2.6：排序诊断落地为确定性、带测试的脚本（`scripts/ranking_diagnostics.py`）。见 [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)。
- **2026-11-03** — v0.2.5：排序开始审计自己——轴冗余检验、被支配数报告、以及揭示约束实际代价的实用性消融。见 [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)。
- **2026-06-12** — v0.2.2：强制跨轮失败记忆（`DESIGN_LOOP_STATE.json` schema；步骤 3/4 排除已杀死母核）、合成成本排序轴、可得性偏置生成、实验失败回流。见 [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)。
- **2026-06-06** — v0.2.1：结构图像输入和 NMR 预测/验证。Schema 文件整合。见 [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)。
- **2026-05-31** — v0.2.0：完整重构。模块化 reference 文件，双流文献，Gemini 对抗审查，新颖性门控，结果→结论审计。
- **2026-05-19** — v0.1.3：聚合物设计范围和分享包说明。
- **2026-05-12** — v0.1.1：脱敏后 [`molecule-design-stage-src/`](molecule-design-stage-src/) 源码包。
- **2026-05-10** — v0.1.0：首次公开发布。

## 这个 skill 会做什么

**结构图像输入**（步骤 0.5）：用户可以直接提供文献截图、ChemDraw 图片或手绘结构草图，Claude 自动从图像中提取 SMILES，经 RDKit 验证后作为种子结构输入设计规范。

**文献智能**：Zotero 个人文献库（步骤 1.5-A）和主动领域搜索（步骤 1.5-B）并行运行，两流均为必跑。`LIT_PACKET.md` 合并两流，矛盾之处显式标记。

**候选生成**：每个候选必须追溯到 `LIT_PACKET.md` 中的骨架、SAR 规律或设计原则。无来源探索性候选上限 10%。

**对抗性审查**（步骤 3.5）：Gemini 以化学挑剔者视角读取原始候选 CSV，在 RDKit 过滤前审查每个候选的设计逻辑、合成可行性和预期代理效果。Claude 不自我审查。

**确定性筛选**（步骤 4）：RDKit 有效性、MW/logP/TPSA、PAINS/Brenk 警示、Murcko 骨架去重。合成可行性门控（步骤 5）要求候选有合理的制备/购买路线才能晋升。

**新颖性检查**（步骤 5.5）：`prior_art_search` 在可视化画廊前标记已报道结构。`known` 候选自动降级为 control。

**人工审阅**（步骤 6-7）：RDKit 渲染的 HTML 画廊，含结构图、过滤决策和设计理由。xTB 前必须明确用户批准。

**结果→结论审计**（步骤 9.5）：xTB 后，Gemini 为每条计算数值明确其证明范围和局限。`overclaim` 标记阻止步骤 11 打 4/5 分。

**NMR 预测与验证**（步骤 9.7，可选）：Claude 使用其内部化学知识为候选分子预测 1H/13C NMR 谱。有实验 NMR 数据时，进行 predicted vs. experimental 比对并生成结构验证状态。基于 Anthropic "Making Claude a Chemist" 研究（1H 精度 ±0.079 ppm）。

**迭代评分**（步骤 11）：Gemini 在新线程中读取设计规范 + 对抗审查 + 新颖性检查 + 结论审计 + NMR 验证。Pareto 排名跨越硬约束通过、合成可行性、证据水平和软偏好。

**排序诊断**（步骤 11）：排序无法审计自己，所以由两个检查来做。轴冗余矩阵（Kendall τ-b）回答五条排序轴是否真的承载独立信息、权衡是否比看上去更窄，并报告这一轮究竟有多少候选被支配——如果一个都没有，说明实用性闸门根本没起作用，本轮必须明说。实用性消融则仅按性质契合度重排，逐一点名被约束挡在台架外的高分候选及其具体原因。即使答案是"实用性什么都没改变"，两者也照样报告。

同时支持小分子和聚合物/材料设计。聚合物候选使用有限封端寡聚物代理；无法从代理推断的聚合物级属性列为 non-xTB 目标。

## 工作流程

```text
[结构图像 → IMAGE_EXTRACTED_SMILES.csv]              ← 步骤 0.5（可选）
→ design_spec.md
→ [Zotero 提取 (1.5-A) || 主动搜索 (1.5-B)]         ← 并行
→ LIT_PACKET.md（合并）
→ ROUND_N_CANDIDATES.csv
→ ROUND_N_GEMINI_ADVERSARIAL_REVIEW.md              ← 步骤 3.5
→ ROUND_N_FILTERED.csv（RDKit）
→ ROUND_N_SYNTHESIS_FEASIBILITY.csv
→ ROUND_N_NOVELTY_CHECK.md                           ← 步骤 5.5
→ ROUND_N_CANDIDATE_GALLERY.html
→ 用户审批检查点                                      ← 强制
→ ROUND_N_XTB_RESULTS.csv
→ ROUND_N_CLAIM_AUDIT.md                             ← 步骤 9.5
→ ROUND_N_NMR_PREDICTIONS.csv                        ← 步骤 9.7（可选）
→ ROUND_N_DECISION.md（Gemini + Pareto）
→ 下一轮或 DESIGN_REPORT.md
```

## 快速开始

安装主 skill：

```bash
bash install_molecule_design_loop.sh
```

如果想一起安装可选文献辅助 skill：

```bash
bash install_molecule_design_loop.sh --install-research-lit
```

在 Codex 中调用：

```text
/molecule-design-loop "/path/to/design_spec.md"
```

示例输入文件：

- [`examples/example_design_spec.md`](examples/example_design_spec.md)
- [`molecule-design-loop/templates/design_spec_template.md`](molecule-design-loop/templates/design_spec_template.md)

默认安装位置：

```text
$CODEX_HOME/skills/molecule-design-loop
```

如果没有设置 `CODEX_HOME`，则回退到：

```text
~/.codex/skills/molecule-design-loop
```

## 可复用阶段入口

仓库里还有一份来自私有 `molecule-design-stage/` 工作目录的脱敏源码包：

- [`molecule-design-stage-src/`](molecule-design-stage-src/)
- 主入口：[`molecule-design-stage-src/run_design.py`](molecule-design-stage-src/run_design.py)
- Gemini 交接产物保留为 `ROUND_N_GEMINI_INPUT.md`

示例：

```bash
python3 molecule-design-stage-src/run_design.py \
  --config molecule-design-stage-src/inputs/example_run.yaml \
  --step prepare
```

## 仓库包含什么

- `molecule-design-loop/`
- `molecule-design-stage-src/`
- `examples/example_design_spec.md`
- `optional-skills/research-lit/SKILL.md`
- `install_molecule_design_loop.sh`

`molecule-design-loop/` 内置辅助文件：

- `scripts/rdkit_filter_candidates.py`
- `scripts/render_candidate_gallery.py`
- `references/candidate_schema.md` — CSV 契约 + 生成规则
- `references/structure-image-input-protocol.md` — 步骤 0.5
- `references/nmr-prediction-protocol.md` — 步骤 9.7
- `references/` 下另有 10 个协议文件（见 [AGENT_GUIDE.md](AGENT_GUIDE.md)）
- `templates/design_spec_template.md`
- `templates/xtb_approval_template.md`

公开打包范围和本地保留项见 [SHARE_PACKAGE.zh-CN.md](SHARE_PACKAGE.zh-CN.md)。

## 设计原则

- 先满足约束，再谈新颖性
- xTB 是证据，不是最终裁判
- xTB 之前必须先做人类结构审阅
- 保留被拒候选和拒绝原因，便于下一轮迭代
- 每轮候选应测试可解释的设计动作，而不是堆大量近似重复结构

## 环境要求

- Codex，且能访问本地 skills 目录
- Python 3
- 当前 Python 环境已安装 RDKit

可选：

- xTB，用于量化筛选阶段
- `research-lit`，作为配套文献辅助 skill
- `gemini-research`，如果你的 Codex 环境支持

## 仓库结构

```text
.
├── AGENT_GUIDE.md
├── CONTRIBUTING.md
├── CONTRIBUTING_CN.md
├── examples/
├── molecule-design-stage-src/
├── molecule-design-loop/
├── optional-skills/
├── README.md
├── README.zh-CN.md
├── SHARE_PACKAGE.md
├── SHARE_PACKAGE.zh-CN.md
└── install_molecule_design_loop.sh
```

## 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md) 或 [CONTRIBUTING_CN.md](CONTRIBUTING_CN.md)。

## 更新记录

见 [CHANGELOG.md](CHANGELOG.md) 或 [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)。

## 许可证

[MIT](LICENSE)
