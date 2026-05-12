# 更新记录

`molecule-design-loop` 的重要变更会记录在这里。

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
