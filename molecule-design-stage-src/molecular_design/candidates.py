from __future__ import annotations

import csv
import importlib.util
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rdkit import Chem

from .config import PROJECT_ROOT, resolve_path


BASE_COLUMNS = [
    "candidate_id",
    "smiles",
    "headgroup_smiles",
    "parent_or_seed",
    "design_move",
    "target_constraint",
    "rationale",
    "expected_proxy_effect",
    "risk",
    "source_hint",
    "proposal_family",
    "constraint_coverage",
    "novelty_class",
]


def load_module(path: str | Path, module_name: str | None = None):
    module_path = resolve_path(path, PROJECT_ROOT)
    name = module_name or f"molecular_design_legacy_{module_path.stem}"
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def generate_candidates(config: dict[str, Any]) -> list[dict[str, str]]:
    plan = config.get("candidate_plan") or {}
    mode = plan.get("mode", "matrix")
    if mode == "legacy_module":
        module = load_module(plan["module_path"], plan.get("module_name"))
        rows = _legacy_rows(module, plan.get("function", "generate_candidates"))
        _add_axis_fields(rows, module, config)
        _add_headgroup_smiles(rows, module, config)
        return rows
    if mode == "matrix":
        return _matrix_rows(config)
    raise ValueError(f"Unsupported candidate_plan.mode: {mode}")


def _legacy_rows(module: Any, function_name: str) -> list[dict[str, str]]:
    generated = getattr(module, function_name)()
    rows: list[dict[str, str]] = []
    for item in generated:
        if is_dataclass(item):
            row = asdict(item)
        elif hasattr(item, "__dict__"):
            row = dict(item.__dict__)
        else:
            row = dict(item)
        rows.append({key: "" if value is None else str(value) for key, value in row.items()})
    return rows


def _matrix_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    templates = (config.get("scaffold") or {}).get("templates") or {}
    plan_items = (config.get("candidate_plan") or {}).get("items") or []
    rows: list[dict[str, str]] = []
    for item in plan_items:
        context = _context_for_axes(item.get("axes") or {}, config.get("axes") or {})
        row = {
            "candidate_id": item["candidate_id"],
            "smiles": _format_template(templates["full"], context),
            "headgroup_smiles": _format_template(templates.get("headgroup", ""), context),
            "parent_or_seed": item.get("parent_or_seed", config.get("scaffold", {}).get("parent_or_seed_default", "")),
            "design_move": item.get("design_move", ""),
            "target_constraint": item.get("target_constraint", config.get("scaffold", {}).get("target_constraint", "")),
            "rationale": item.get("rationale", _join_axis_text(context, "rationale")),
            "expected_proxy_effect": item.get("expected_proxy_effect", _join_axis_text(context, "expected")),
            "risk": item.get("risk", _join_axis_text(context, "risk")),
            "source_hint": item.get("source_hint", config.get("run_id", "")),
            "proposal_family": item.get("proposal_family", ""),
            "constraint_coverage": item.get("constraint_coverage", ""),
            "novelty_class": item.get("novelty_class", ""),
        }
        for axis_name, axis_value in (item.get("axes") or {}).items():
            row[axis_name] = str(axis_value)
        rows.append(row)
    return rows


def _add_axis_fields(rows: list[dict[str, str]], module: Any, config: dict[str, Any]) -> None:
    axes_by_id = _axes_by_candidate_id(module, config)
    for row in rows:
        for axis_name, axis_value in axes_by_id.get(row["candidate_id"], {}).items():
            row[axis_name] = str(axis_value)


def _axes_by_candidate_id(module: Any, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    plan = config.get("candidate_plan") or {}
    axes_by_id: dict[str, dict[str, Any]] = {}
    for item in plan.get("id_axes") or []:
        axes_by_id[item["candidate_id"]] = {key: value for key, value in item.items() if key != "candidate_id"}

    source = plan.get("id_axis_source")
    if source:
        values = getattr(module, source["var"])
        columns = source["columns"]
        for entry in values:
            mapping = dict(zip(columns, entry))
            candidate_id = mapping.pop("candidate_id")
            axes_by_id[str(candidate_id)] = mapping
    return axes_by_id


def _add_headgroup_smiles(rows: list[dict[str, str]], module: Any, config: dict[str, Any]) -> None:
    template = ((config.get("scaffold") or {}).get("templates") or {}).get("headgroup")
    if not template:
        return

    plan = config.get("candidate_plan") or {}
    axis_sources = plan.get("axis_sources") or {}
    axes_by_id = _axes_by_candidate_id(module, config)
    config_axes = config.get("axes") or {}

    for row in rows:
        if row.get("headgroup_smiles"):
            continue
        axis_values = axes_by_id.get(row["candidate_id"], {})
        context: dict[str, Any] = {}
        for axis_name, axis_value in axis_values.items():
            source_name = axis_sources.get(axis_name)
            if source_name and hasattr(module, source_name):
                axis_meta = getattr(module, source_name)[axis_value]
            else:
                axis_meta = config_axes.get(axis_name, {}).get(axis_value, {})
            context[axis_name] = _namespace(axis_meta)
        row["headgroup_smiles"] = _format_template(template, context)


def _context_for_axes(axis_values: dict[str, Any], axes: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for axis_name, axis_value in axis_values.items():
        axis_meta = axes.get(axis_name, {}).get(axis_value, {})
        context[axis_name] = _namespace(axis_meta)
    return context


def _namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace(item) for item in value]
    return value


def _format_template(template: str, context: dict[str, Any]) -> str:
    if not template:
        return ""
    return template.format(**context)


def _join_axis_text(context: dict[str, Any], field: str) -> str:
    values = [getattr(value, field, "") for value in context.values()]
    return " ".join(str(value) for value in values if value)


def validate_candidate_smiles(rows: list[dict[str, str]]) -> None:
    bad: list[str] = []
    for row in rows:
        if Chem.MolFromSmiles(row.get("smiles", "")) is None:
            bad.append(row.get("candidate_id", "unknown"))
        headgroup = row.get("headgroup_smiles", "")
        if headgroup and Chem.MolFromSmiles(headgroup) is None:
            bad.append(row.get("candidate_id", "unknown") + ":headgroup")
    if bad:
        raise ValueError(f"Invalid generated SMILES: {bad}")


def write_candidates_csv(rows: list[dict[str, str]], path: Path) -> None:
    fieldnames = _fieldnames(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        fieldnames = _fieldnames(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fieldnames(rows: list[dict[str, str]]) -> list[str]:
    keys: list[str] = []
    for key in BASE_COLUMNS:
        if any(key in row for row in rows):
            keys.append(key)
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    return keys
