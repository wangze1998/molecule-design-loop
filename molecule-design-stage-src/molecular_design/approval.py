from __future__ import annotations

import re
from pathlib import Path
from typing import Any


APPROVED_STATUSES = {"approved", "approved_all", "approved_subset"}


def write_approval_file(
    path: Path,
    config: dict[str, Any],
    filtered_rows: list[dict[str, str]],
    gallery_path: Path,
) -> list[str]:
    concerns = list((config.get("approval") or {}).get("structural_concerns") or [])
    rejected = [row["candidate_id"] for row in filtered_rows if row.get("filter_decision") == "reject"]
    if rejected:
        concerns.append("RDKit rejected: " + ", ".join(rejected))
    else:
        concerns.append("RDKit found no invalid SMILES under configured filters.")

    rel_gallery = _display_path(gallery_path)
    lines = [
        f"# Round {config['round']} xTB Approval",
        "",
        "- review_status: pending_user_reply",
        "- reviewer:",
        "- approved_candidate_ids: []",
        "- blocked_candidate_ids: []",
        "- structural_concerns:",
        "- next_step: wait_for_user_confirmation_before_xtb",
        "",
        "## Notes",
        "",
        f"- Reference gallery: `{rel_gallery}`",
        "- xTB must not start until `review_status` becomes `approved` or `approved_subset`.",
        "- Model-detected structural concerns:",
    ]
    lines.extend(f"  - {concern}" for concern in concerns)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return concerns


def parse_approval_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "approved_candidate_ids": [], "blocked_candidate_ids": []}
    text = path.read_text(encoding="utf-8")
    return {
        "status": _field(text, "review_status") or "pending_user_reply",
        "approved_candidate_ids": _list_field(text, "approved_candidate_ids"),
        "blocked_candidate_ids": _list_field(text, "blocked_candidate_ids"),
    }


def is_approved(payload: dict[str, Any]) -> bool:
    return payload.get("status") in APPROVED_STATUSES


def _field(text: str, name: str) -> str:
    match = re.search(rf"^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text, flags=re.M)
    return match.group(1).strip() if match else ""


def _list_field(text: str, name: str) -> list[str]:
    raw = _field(text, name)
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [item.strip().strip("'\"`") for item in re.split(r"[,;\s]+", raw) if item.strip().strip("'\"`")]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)
