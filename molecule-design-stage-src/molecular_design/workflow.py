from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

from . import approval, backfolding
from .candidates import generate_candidates, read_csv, validate_candidate_smiles, write_candidates_csv
from .config import round_prefix
from .gallery import render_gallery_csv
from .rdkit_filter import filter_csv
from .xtb import screen_headgroup_dimers, write_xtb_csv


DEFAULT_GEMINI_REVIEW_RULES = [
    "Treat xTB as a low-cost geometry and stacking proxy only.",
    "Do not infer binding, full-assembly retention, synthesis success, or mechanism from xTB alone.",
    "Score candidates against the locked design brief first, then use xTB as supporting evidence.",
]


def prepare(config: dict[str, Any]) -> dict[str, Path]:
    paths = artifact_paths(config)
    paths["output_dir"].mkdir(parents=True, exist_ok=True)

    candidates = generate_candidates(config)
    validate_candidate_smiles(candidates)
    write_candidates_csv(candidates, paths["candidates"])

    filter_csv(paths["candidates"], paths["filtered"], config.get("filter") or {})
    render_gallery_csv(
        paths["filtered"],
        paths["gallery"],
        (config.get("gallery") or {}).get("title") or f"Round {config['round']} Candidate Gallery",
        (config.get("gallery") or {}).get("limit"),
    )
    filtered_rows = read_csv(paths["filtered"])
    concerns = approval.write_approval_file(paths["approval"], config, filtered_rows, paths["gallery"])
    _write_headgroups(paths["headgroups"], candidates)
    _write_state(
        paths["state"],
        config,
        {
            "status": f"round_{config['round']}_pending_xtb_approval",
            "generated_candidates": len(candidates),
            "approval_status": "pending_user_reply",
            "candidate_file": str(paths["candidates"]),
            "filtered_file": str(paths["filtered"]),
            "gallery_file": str(paths["gallery"]),
            "approval_file": str(paths["approval"]),
            "structural_concerns": concerns,
        },
    )
    return paths


def run_xtb_step(config: dict[str, Any]) -> dict[str, Any]:
    paths = artifact_paths(config)
    approval_payload = approval.parse_approval_file(paths["approval"])
    if (config.get("approval") or {}).get("require_explicit", True) and not approval.is_approved(approval_payload):
        return {"status": "blocked_pending_approval", "approval_file": str(paths["approval"])}

    candidates = read_csv(paths["candidates"])
    filtered_rows = read_csv(paths["filtered"]) if paths["filtered"].exists() else []
    filter_map = {row["candidate_id"]: row for row in filtered_rows}
    approved_ids = approval_payload.get("approved_candidate_ids") or []
    if not approved_ids and approval_payload.get("status") in {"approved", "approved_all"}:
        approved_ids = [
            row["candidate_id"]
            for row in candidates
            if filter_map.get(row["candidate_id"], {}).get("filter_decision", "pass") == "pass"
        ]
    max_jobs = (config.get("xtb") or {}).get("max_jobs")
    if max_jobs:
        approved_ids = approved_ids[: int(max_jobs)]

    rows = screen_headgroup_dimers(candidates, approved_ids, paths["xtb_jobs"], config)
    write_xtb_csv(paths["xtb_results"], rows)

    gemini_input_file = ""
    status = f"round_{config['round']}_xtb_complete"
    if (config.get("gemini") or {}).get("enabled", True):
        gemini_input_path = write_gemini_input(config, filtered_rows, rows)
        gemini_input_file = str(gemini_input_path)
        status = f"round_{config['round']}_xtb_complete_pending_gemini_review"

    state_update = {
        "status": status,
        "approved_candidate_ids": approved_ids,
        "xtb_results_file": str(paths["xtb_results"]),
        "xtb_status_summary": _count(rows, "xtb_status"),
    }
    if gemini_input_file:
        state_update["gemini_input_file"] = gemini_input_file
    _write_state(paths["state"], config, state_update)
    return {
        "status": "xtb_complete",
        "xtb_results_file": str(paths["xtb_results"]),
        "gemini_input_file": gemini_input_file,
    }


def run_backfold_step(config: dict[str, Any]) -> dict[str, Any]:
    paths = artifact_paths(config)
    backfold_cfg = config.get("backfolding") or {}
    legacy_module = backfold_cfg.get("legacy_module")
    if legacy_module:
        import sys

        from .candidates import load_module

        module = load_module(legacy_module)
        old_argv = sys.argv[:]
        try:
            sys.argv = [legacy_module]
            result = module.main()
        finally:
            sys.argv = old_argv
        return {"status": "legacy_backfold_complete", "result": result}

    backfolding.write_not_configured_summary(paths["backfold_summary"], config)
    return {"status": "backfold_not_configured", "summary_file": str(paths["backfold_summary"])}


def write_report(config: dict[str, Any]) -> Path:
    paths = artifact_paths(config)
    paths["output_dir"].mkdir(parents=True, exist_ok=True)
    filtered = read_csv(paths["filtered"]) if paths["filtered"].exists() else []
    xtb_rows = read_csv(paths["xtb_results"]) if paths["xtb_results"].exists() else []
    top = [row for row in filtered if row.get("filter_decision") == "pass"][:10]
    xtb_summary = _count(xtb_rows, "xtb_status") if xtb_rows else {}
    lines = [
        f"# Molecular Design Report: {config['run_id']}",
        "",
        f"- round: {config['round']}",
        f"- family: {config['family']}",
        f"- candidates: {len(filtered)}",
        f"- RDKit pass: {sum(1 for row in filtered if row.get('filter_decision') == 'pass')}",
        f"- xTB status: {xtb_summary or 'not_run'}",
        "",
        "## Top RDKit-Passing Candidates",
        "",
    ]
    for row in top:
        lines.append(f"- `{row['candidate_id']}`: {row.get('canonical_smiles') or row.get('smiles', '')}")
    if not top:
        lines.append("- none")
    paths["report"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return paths["report"]


def artifact_paths(config: dict[str, Any]) -> dict[str, Path]:
    output_dir = Path(config["_output_dir"])
    prefix = round_prefix(config)
    jobs_root = output_dir / "xtb_jobs"
    xtb_dir_name = (config.get("xtb") or {}).get("jobs_dir") or f"round_{config['round']}"
    return {
        "output_dir": output_dir,
        "state": output_dir / "DESIGN_LOOP_STATE.json",
        "candidates": output_dir / f"{prefix}_CANDIDATES.csv",
        "filtered": output_dir / f"{prefix}_FILTERED.csv",
        "gallery": output_dir / f"{prefix}_CANDIDATE_GALLERY.html",
        "approval": output_dir / f"{prefix}_XTB_APPROVAL.md",
        "xtb_results": output_dir / f"{prefix}_XTB_RESULTS.csv",
        "gemini_input": output_dir / f"{prefix}_GEMINI_INPUT.md",
        "headgroups": output_dir / f"{prefix}_HEADGROUPS.json",
        "backfold_raw": output_dir / f"{prefix}_BACKFOLDING_RAW.csv",
        "backfold_results": output_dir / f"{prefix}_BACKFOLDING_RESULTS.csv",
        "backfold_summary": output_dir / f"{prefix}_BACKFOLDING_SUMMARY.md",
        "report": output_dir / "DESIGN_REPORT.md",
        "xtb_jobs": jobs_root / xtb_dir_name,
    }


def write_gemini_input(
    config: dict[str, Any],
    filtered_rows: list[dict[str, str]],
    xtb_rows: list[dict[str, str]],
) -> Path:
    paths = artifact_paths(config)
    xtb_map = {row["candidate_id"]: row for row in xtb_rows}
    rules = list((config.get("gemini") or {}).get("review_rules") or DEFAULT_GEMINI_REVIEW_RULES)
    sections: list[str] = []
    for row in filtered_rows:
        xtb = xtb_map.get(row.get("candidate_id", ""), {})
        sections.append(
            textwrap.dedent(
                f"""
                ## {row.get("candidate_id", "unknown")}

                - parent_or_seed: {row.get("parent_or_seed", "")}
                - design_move: {row.get("design_move", "")}
                - target_constraint: {row.get("target_constraint", "")}
                - rationale: {row.get("rationale", "")}
                - expected_proxy_effect: {row.get("expected_proxy_effect", "")}
                - risk: {row.get("risk", "")}
                - proposal_family: {row.get("proposal_family", "")}
                - constraint_coverage: {row.get("constraint_coverage", "")}
                - novelty_class: {row.get("novelty_class", "")}
                - full_smiles: {row.get("smiles", "")}
                - headgroup_smiles: {row.get("headgroup_smiles", "")}
                - RDKit hard_constraint_status: {row.get("hard_constraint_status", "")}
                - RDKit filter_decision: {row.get("filter_decision", "")}
                - RDKit filter_reason: {row.get("filter_reason", "")}
                - RDKit formal_charge: {row.get("formal_charge", "")}
                - RDKit rotatable_bonds: {row.get("rotatable_bonds", "")}
                - RDKit aromatic_rings: {row.get("aromatic_rings", "")}
                - RDKit clogp: {row.get("clogp", "")}
                - RDKit tpsa: {row.get("tpsa", "")}
                - xTB status: {xtb.get("xtb_status", "")}
                - xTB geometry_warning: {xtb.get("geometry_warning", "")}
                - xTB dimer_centroid_A: {xtb.get("dimer_centroid_A", "")}
                - xTB dimer_min_aromatic_A: {xtb.get("dimer_min_aromatic_A", "")}
                - xTB dimer_contacts_lt_4p0A: {xtb.get("dimer_contacts_lt_4p0A", "")}
                - xTB dimer_min_heavy_A: {xtb.get("dimer_min_heavy_A", "")}
                """
            ).strip()
        )

    if not sections:
        sections.append("No filtered candidate rows were available.")

    rule_lines = "\n".join(f"- {rule}" for rule in rules)
    text = textwrap.dedent(
        f"""
        # {round_prefix(config)}_GEMINI_INPUT

        Use the locked constraints from `DESIGN_SPEC_LOCKED.md` in the current stage directory and only the evidence below.

        Hard review rules:
        {rule_lines}

        Candidate evidence follows.

        {"\n\n".join(sections)}
        """
    ).strip() + "\n"
    paths["gemini_input"].write_text(text, encoding="utf-8")
    return paths["gemini_input"]


def _write_headgroups(path: Path, candidates: list[dict[str, str]]) -> None:
    payload = {
        row["candidate_id"]: {
            "headgroup_smiles": row.get("headgroup_smiles", ""),
            "parent_or_seed": row.get("parent_or_seed", ""),
            "proposal_family": row.get("proposal_family", ""),
            "constraint_coverage": row.get("constraint_coverage", ""),
            "novelty_class": row.get("novelty_class", ""),
        }
        for row in candidates
        if row.get("headgroup_smiles")
    }
    if payload:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_state(path: Path, config: dict[str, Any], update: dict[str, Any]) -> None:
    state: dict[str, Any] = {}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    state.update(
        {
            "run_id": config["run_id"],
            "round": config["round"],
            "family": config["family"],
            "config_file": config["_config_path"],
        }
    )
    state.update(update)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _count(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key, "")
        counts[value] = counts.get(value, 0) + 1
    return counts
