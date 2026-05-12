from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


STAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = STAGE_ROOT.parent

REQUIRED_KEYS = (
    "run_id",
    "output_dir",
    "round",
    "family",
    "scaffold",
    "axes",
    "candidate_plan",
    "filter",
    "gallery",
    "approval",
    "xtb",
    "backfolding",
)


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    missing = [key for key in REQUIRED_KEYS if key not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")

    config["_config_path"] = str(config_path)
    config["_config_dir"] = str(config_path.parent)
    config["_project_root"] = str(PROJECT_ROOT)
    config["_stage_root"] = str(STAGE_ROOT)

    output_dir = resolve_path(config["output_dir"], PROJECT_ROOT)
    config["_output_dir"] = str(output_dir)
    return config


def resolve_path(value: str | Path, base: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (base or PROJECT_ROOT).joinpath(path).resolve()


def round_prefix(config: dict[str, Any]) -> str:
    return f"ROUND_{config['round']}"
