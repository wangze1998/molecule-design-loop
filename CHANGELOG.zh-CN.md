# 更新记录

`molecule-design-loop` 的重要变更会记录在这里。

## v0.1.3 - 2026-05-19

这次重新核对了公开仓库与当前本地主 skill 源目录的一致性，并补充了分享包范围说明文档。

### 新增

- `SHARE_PACKAGE.md` 和 `SHARE_PACKAGE.zh-CN.md`，用于说明本地分享包里哪些内容进入公开仓库

### 调整

- 状态标识从 `v0.1.2` 更新为 `v0.1.3`
- README 和中文 README 现在写明了本地源目录同步核对结果，链接到分享包范围说明，并明确写出了“聚合物设计”的公开定位
- 公开打包文档现在明确说明 `related-skills/` 下的辅助文件只是本地上下文，不属于公开仓库打包内容

### 备注

- 在同步 GitHub 前，重新核对了 `molecule-design-loop/SKILL.md`、`examples/example_design_spec.md` 和 `research-lit` 与本地工作副本的一致性
- 公开安装脚本继续保留更新后的目录式可选 skill 安装逻辑
- 公开更新日志现在明确说明：这个仓库不仅面向一般分子设计，也覆盖聚合物设计工作流
- 这一版没有修改分子设计工作流逻辑

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
