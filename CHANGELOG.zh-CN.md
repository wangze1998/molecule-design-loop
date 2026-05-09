# 更新记录

`molecule-design-loop` 的重要变更会记录在这里。

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
