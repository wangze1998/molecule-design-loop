# Molecule Design Loop

一个面向 Codex 的开源分子设计 skill，强调约束驱动设计、确定性的 RDKit 初筛、可视化候选审阅、xTB 前必须人工确认，以及 Gemini 引导的迭代优化。

## 这个 skill 解决什么问题

很多“LLM 做分子设计”的流程通常会在两个地方出问题：

- 生成了很多分子，但设计逻辑不够清楚、不方便审阅
- 在明显的结构问题还没排除前，就过早进入廉价量化筛选

`molecule-design-loop` 的定位是一个更实用的中间层：

- 结合文献线索生成候选分子
- 用确定性的 RDKit 规则做初筛
- 生成 RDKit 驱动的 HTML 候选画廊
- 在 xTB 之前强制人工结构确认
- 用 Gemini 按锁定的设计规范打分，把 xTB 作为证据而不是裁判

## 工作流程

```text
design_spec.md
→ 文献资料包
→ SMILES 候选
→ RDKit 过滤
→ RDKit HTML 候选画廊
→ 用户结构确认
→ xTB 筛选
→ Gemini 约束评分
→ 下一轮设计
```

## 包含内容

- `molecule-design-loop/`
  - 主 Codex skill
  - RDKit 描述符与药化过滤脚本
  - RDKit HTML 候选画廊渲染脚本
  - xTB 审批检查点模板
- `examples/example_design_spec.md`
- `optional-skills/research-lit/SKILL.md`
- `install_molecule_design_loop.sh`

## 主要特点

- 优先满足设计约束，而不是优先追求“新颖性”
- 保留被拒绝的候选及拒绝原因，便于后续迭代
- 使用 RDKit 做结构合理性、警示片段和多样性筛选
- 在任何 xTB 运行前先生成人类可读的 HTML 候选画廊
- 强制用户显式批准后才进入 xTB
- 用 Gemini 评估候选对设计规范的符合程度，同时让 xTB 只提供辅助证据

## 环境要求

- Codex，且可访问本地 skills 目录
- Python 3
- 当前 Python 环境中已安装 RDKit

可选：

- xTB，用于量化筛选阶段
- `research-lit`，如果你希望配套使用文献检索辅助 skill
- `gemini-research`，如果你的 Codex 环境支持

## 安装

```bash
bash install_molecule_design_loop.sh
```

如果还想一起安装可选的 `research-lit` 配套 skill：

```bash
bash install_molecule_design_loop.sh --install-research-lit
```

默认安装位置：

```text
$CODEX_HOME/skills/molecule-design-loop
```

如果没有设置 `CODEX_HOME`，则回退到：

```text
~/.codex/skills/molecule-design-loop
```

## 使用方式

```text
/molecule-design-loop "/path/to/design_spec.md"
```

示例：

```text
/molecule-design-loop "/path/to/example_design_spec.md"
```

## 核心设计原则

xTB 不是最终决策者。

这个 skill 把 xTB 视为一种低成本的计算证据来源。最终排序由锁定的设计规范和 Gemini 的结构化评分共同决定，而且前提是用户已经人工审阅并批准候选结构。

## 仓库结构

```text
.
├── molecule-design-loop/
├── examples/
├── optional-skills/
└── install_molecule_design_loop.sh
```

## 许可证

MIT

## 如果它对你有帮助

如果这个 skill 对你的工作流有帮助，欢迎给仓库点个 Star，让更多人能找到它。
