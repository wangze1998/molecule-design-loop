# 为 Molecule Design Loop 做贡献

[English](CONTRIBUTING.md) | 中文版

感谢你帮助完善这个仓库。

## 可以怎么贡献

- 报告 Bug 或不清楚的工作流行为
- 改进主 skill 或可选配套 skill
- 完善过滤、渲染脚本或文档
- 补充示例、翻译或验证说明

## 仓库结构

- `molecule-design-loop/` — 主 skill 与辅助脚本
- `examples/` — 示例设计规范
- `optional-skills/` — 可选配套 skill

## 本地开发

先本地安装主 skill：

```bash
bash install_molecule_design_loop.sh
```

如果也要安装可选文献辅助 skill：

```bash
bash install_molecule_design_loop.sh --install-research-lit
```

运行仓库自带脚本测试：

```bash
python3 molecule-design-loop/scripts/test_rdkit_filter_candidates.py
python3 molecule-design-loop/scripts/test_render_candidate_gallery.py
```

## 贡献约定

- 保持改动聚焦，便于审阅
- 用户可见行为变化时，同步更新 `README.md`
- 面向 agent 的调用方式或契约变化时，同步更新 `AGENT_GUIDE.md`
- 示例文件要和实际工作流保持一致
- 保留核心护栏：没有明确人工批准前，不进入 xTB

## Pull Request 检查清单

- [ ] 改动聚焦于一个清晰目标
- [ ] 行为变化时已更新文档
- [ ] 脚本变更后已做本地测试
- [ ] 提交信息清晰

## 许可证

提交贡献即表示你同意这些内容按 [MIT License](LICENSE) 授权。
