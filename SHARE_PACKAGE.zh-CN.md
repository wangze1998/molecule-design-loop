# 分享包说明

这份文档说明 `molecule-design-loop` 当前公开分享包的范围，以及它和本地工作目录之间的对应关系。

## 已包含在公开仓库中的内容

- `molecule-design-loop/` —— 主公开 Codex skill
- `examples/example_design_spec.md` —— 公开示例输入
- `optional-skills/research-lit/SKILL.md` —— 可选文献辅助 skill
- `install_molecule_design_loop.sh` —— 公开安装脚本
- `molecule-design-stage-src/` —— 脱敏后的可复用阶段入口源码包
- `README*`、`CHANGELOG*`、`CONTRIBUTING*`、`AGENT_GUIDE.md` 等顶层说明文档

## 已对照本地源目录核对

核对日期：`2026-05-19`

- 仓库中的 `molecule-design-loop/SKILL.md` 与本地主源文件一致
- 仓库中的 `examples/example_design_spec.md` 与本地示例文件一致
- `optional-skills/research-lit/SKILL.md` 与本地 `related-skills/research-lit.SKILL.md` 的内容一致
- 公开安装脚本保留了更新后的目录式 `--install-research-lit` 安装逻辑，没有退回旧的单文件快照方式

## 保留在本地、不进入公开包的内容

- `related-skills/meta-optimize.SKILL.md`
- `related-skills/novelty-check.SKILL.md`
- `related-skills/research-wiki.SKILL.md`
- `dist/` 等本地打包输出
- `__pycache__/`、`.pytest_cache/` 等缓存文件
- `molecule-design-stage/` 这类运行生成产物

## 为什么有些本地文件不公开

- 有些文件只是更大范围本地 Codex skill 库里的上下文辅助，不属于主分享包
- 有些文件是运行时生成物或机器本地打包输出
- 公开仓库的目标是保持可移植、精简、并且适合直接发布
