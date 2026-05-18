# Molecule Design Loop

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Codex Skill](https://img.shields.io/badge/Codex-skill-black)
![Status](https://img.shields.io/badge/status-v0.1.2-blue)

一个面向 Codex 的开源分子设计 skill，强调约束驱动设计、确定性的 RDKit 过滤、候选结构可视化审阅、xTB 前必须人工确认，以及 Gemini 引导的迭代优化。

[English](README.md) | [中文说明](README.zh-CN.md) | [更新日志](CHANGELOG.zh-CN.md)

> **Molecule Design Loop v0.1.0 → v0.1.2**（2026-05）—— 三步公开包装更新序列。**v0.1.2** 这次补上了更接近 ARIS 的 GitHub 发布说明和仓库更新展示。**v0.1.1** 发布了脱敏后的 `molecule-design-stage-src/` 源码包。**v0.1.0** 则完成了主 skill、双语文档、安装脚本和可选文献配套 skill 的首次公开发布。
> **xTB 前的人类审批仍然是强制的。** **Gemini 交接入口也保留为一等产物**：`ROUND_N_GEMINI_INPUT.md`。

如果你是 AI agent，请先看 [AGENT_GUIDE.md](AGENT_GUIDE.md)。这份文档是给模型读的，不是给人类快速浏览的。

> 这是一个“先约束、后计算”的分子设计工作流：先过滤明显不合理结构，再人工看图确认，最后再让 xTB 提供证据，而不是替你做最终科学判断。

## 当前状态

- 当前发布线：`v0.1.2`
- 仓库定位：可直接发布的 Codex skill，加上辅助脚本与模板
- 更新记录：[CHANGELOG.md](CHANGELOG.md) | [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)
- 最近一次面向 GitHub 的更新：补齐了更像 ARIS 的发布总览、`What's New` 风格更新说明和更清晰的公开更新日志

## 版本轨迹

**v0.1.2**（2026-05-18）—— 仓库发布展示刷新。README 改成更像 ARIS 的版本链路和更新说明形式，并补了更清晰的公开更新日志。这一版没有改工作流逻辑。

**v0.1.1**（2026-05-12）—— 发布脱敏后的阶段入口源码包。新增 `molecule-design-stage-src/`、可复用 `run_design.py`、模块化 `molecular_design/`、示例配置、测试，并把 `ROUND_N_GEMINI_INPUT.md` 正式纳入 Gemini 交接产物。

**v0.1.0**（2026-05-10）—— 首次公开开源包装。发布主 Codex skill、可选 `research-lit` 配套 skill、双语 README、安装脚本、贡献文档和 GitHub 展示结构。

## 这个仓库解决什么问题

很多“LLM 做分子设计”的流程有几个常见问题：

- 会生成很多分子，但设计逻辑不清楚，不方便审阅
- 在明显结构问题还没排除前，就过早进入廉价量化筛选
- 把计算结果误当成最终结论，而不是辅助证据

`molecule-design-loop` 的定位，就是把这些环节变得更可控、更可解释。

## 最近更新

- **2026-05-18** — ![NEW](https://img.shields.io/badge/NEW-red?style=flat-square) README 改成更接近 ARIS 的发布/更新说明形式，补上版本链路、版本轨迹和公开更新日志入口。
- **2026-05-12** — ![NEW](https://img.shields.io/badge/NEW-red?style=flat-square) 新增脱敏后的 [`molecule-design-stage-src/`](molecule-design-stage-src/) 源码包，包含可复用主入口、模块化流程代码、测试，以及保留的 Gemini 交接产物。
- **2026-05-10** — ![NEW](https://img.shields.io/badge/NEW-red?style=flat-square) 完成首次公开仓库包装：主 skill、可选文献辅助、安装脚本、双语文档和 GitHub 展示结构。

## 这个 skill 会做什么

- 读取 Markdown 设计规范，解析硬约束、软偏好和 xTB 可测试代理指标
- 结合本地上下文与近期文献生成文献资料包
- 生成可解释的 SMILES 候选，而不是只追求“新颖”
- 用 RDKit 做有效性、描述符、警示片段和骨架多样性过滤
- 在任何 xTB 运行前先生成 HTML 候选画廊供人工审阅
- 强制用户显式批准后才进入 xTB
- 在收集到证据后，再让 Gemini 按锁定设计规范做结构化打分

## 工作流程

```text
design_spec.md
→ DESIGN_SPEC_LOCKED.md
→ LIT_PACKET.md
→ ROUND_N_CANDIDATES.csv
→ ROUND_N_FILTERED.csv
→ ROUND_N_CANDIDATE_GALLERY.html
→ 用户审批检查点
→ ROUND_N_XTB_RESULTS.csv
→ ROUND_N_DECISION.md
→ 下一轮或最终 DESIGN_REPORT.md
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

仓库里还补了一份来自私有 `molecule-design-stage/` 工作目录的脱敏源码包：

- [`molecule-design-stage-src/`](molecule-design-stage-src/)
- 主入口：[`molecule-design-stage-src/run_design.py`](molecule-design-stage-src/run_design.py)
- 仍然保留 Gemini 交接产物：`ROUND_N_GEMINI_INPUT.md`

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
- `references/candidate_schema.md`
- `templates/design_spec_template.md`
- `templates/xtb_approval_template.md`

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
└── install_molecule_design_loop.sh
```

## 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md) 或 [CONTRIBUTING_CN.md](CONTRIBUTING_CN.md)。

## 更新记录

见 [CHANGELOG.md](CHANGELOG.md) 或 [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md)。

## 许可证

[MIT](LICENSE)
