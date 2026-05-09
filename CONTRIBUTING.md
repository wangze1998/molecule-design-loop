# Contributing to Molecule Design Loop

[English](CONTRIBUTING.md) | [中文版](CONTRIBUTING_CN.md)

Thanks for helping improve this repo.

## Ways To Contribute

- Report bugs or unclear workflow behavior
- Improve the main skill or optional companion skills
- Tighten filtering, rendering, or documentation
- Add examples, translations, or validation notes

## Repository Map

- `molecule-design-loop/` — main skill and helper scripts
- `examples/` — example design brief
- `optional-skills/` — optional companion skills

## Local Development

Install the skill locally:

```bash
bash install_molecule_design_loop.sh
```

Install the optional literature companion too:

```bash
bash install_molecule_design_loop.sh --install-research-lit
```

Run the bundled script tests:

```bash
python3 molecule-design-loop/scripts/test_rdkit_filter_candidates.py
python3 molecule-design-loop/scripts/test_render_candidate_gallery.py
```

## Contribution Guidelines

- Keep changes focused and easy to review
- Update `README.md` when user-facing behavior changes
- Update `AGENT_GUIDE.md` when agent-facing invocation or contracts change
- Keep examples aligned with the actual workflow
- Preserve the core guardrail: no xTB before explicit user approval

## Pull Request Checklist

- [ ] Changes are scoped to one clear improvement
- [ ] Documentation is updated when behavior changes
- [ ] Local tests were run when scripts changed
- [ ] Commit messages are clear

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
