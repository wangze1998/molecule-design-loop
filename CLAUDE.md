# Maintaining this repository

This repository is **public**. It is the single source of the `molecule-design-loop` skill; the maintainer's local Claude Code and Codex both load it straight from a clone of `main`.

## Public-repo rule (本仓库公开 · 只写通用内容)

Never commit, even when the request contains it:

- personal or lab-specific material: home-directory paths (`/Users/<name>/`, `C:\Users\<name>\`), sample or batch IDs, lab-notebook entries, unpublished compounds, spectra, yields or assay data, names or e-mail addresses of people;
- secrets: API keys, tokens, `.env` contents, config files from the maintainer's machine;
- third-party PDFs or long verbatim excerpts from papers.

If a requested change only makes sense with such material, write the generic rule it illustrates instead (e.g. "a protecting group that adds a large hydrophobic group shifts reversed-phase retention later" rather than the specific failed run), and say in the PR description what was generalised.

## Workflow

- Work on a branch and open a PR to `main`; the `privacy-scan` check must pass before merging.
- Keep `README.md` / `README.zh-CN.md` and `CHANGELOG.md` / `CHANGELOG.zh-CN.md` in step when behaviour changes.
- Run `python3 -m pytest molecule-design-loop/scripts` when scripts change.
