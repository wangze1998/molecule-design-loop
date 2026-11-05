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

核对日期：`2026-06-06`（v0.2.1）

- 仓库中的 `molecule-design-loop/SKILL.md` 与本地主源文件一致
- `molecule-design-loop/references/` — 全部 12 个协议文件已同步（含新增 `structure-image-input-protocol.md` 和 `nmr-prediction-protocol.md`；`candidate-generation-schema.md` 已合并至 `candidate_schema.md`）
- `molecule-design-loop/templates/design_spec_template.md` 已同步（含新增图像输入和 NMR 配置节）
- 仓库中的 `examples/example_design_spec.md` 与本地示例文件一致
- `optional-skills/research-lit/SKILL.md` 与本地 `related-skills/research-lit.SKILL.md` 的内容一致
- 公开安装脚本保留了更新后的目录式 `--install-research-lit` 安装逻辑

## 尚未与本地源目录核对的变更

上面那次 `2026-06-06` 核对之后仓库里发生的改动，**尚未**与本地源目录对账：

- `v0.4.0` 修复了 `molecule-design-loop/scripts/ranking_diagnostics.py` 的 `pareto_rank`
  （新增 `--pareto-rank-mode protocol`，被支配的候选物不再占据前三的空位），新增
  `--role-column` 以单独处理对照，删掉了把该缺陷写进断言的测试，并修改了 `SKILL.md`、
  `gemini-scoring-protocol.md` 和 `ranking-diagnostics-protocol.md`。
- `v0.3.0` 新增 `build_candidates.py`、`build_gemini_inputs.py`、`inspect_round.py` 和
  `test_skill_contract.py`（各自带测试）、`examples/example_candidates_config.yaml`，以及测试工作流；
  把 `SKILL.md` 重写为路由；修改了 `AGENT_GUIDE.md`、`candidate_schema.md`、
  `zotero-extraction-protocol.md` 和三个 Gemini 协议文件。
- `v0.2.6` 新增了 `molecule-design-loop/scripts/ranking_diagnostics.py` 和 `test_ranking_diagnostics.py`，并修改了 `SKILL.md`、`AGENT_GUIDE.md`、`ranking-diagnostics-protocol.md`。
- `v0.2.5` 新增了第 13 个协议文件 `molecule-design-loop/references/ranking-diagnostics-protocol.md`，并修改了 `SKILL.md`、`gemini-scoring-protocol.md`、`candidate_schema.md`、`xtb-integrity-rules.md`。
- `v0.2.2`–`v0.2.4` 对 `SKILL.md`、`design-loop-state-schema.md`、`synthesis-gate-schema.md`、`claim-audit-protocol.md` 的改动。

重新做一次本地与仓库的对比、并标注新的核对日期之后，上面那份清单才能当作现状使用。

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
