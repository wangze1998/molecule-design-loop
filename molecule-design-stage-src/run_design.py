#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from molecular_design.config import load_config
from molecular_design.workflow import prepare, run_backfold_step, run_xtb_step, write_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reusable molecular-design workflow entrypoint")
    parser.add_argument("--config", required=True, help="YAML run config")
    parser.add_argument(
        "--step",
        required=True,
        choices=["prepare", "xtb", "backfold", "report"],
        help="Workflow step to run",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    if args.step == "prepare":
        paths = prepare(config)
        print(f"prepared: {paths['candidates']}")
        print(f"gallery: {paths['gallery']}")
        print(f"approval: {paths['approval']}")
        return 0
    if args.step == "xtb":
        result = run_xtb_step(config)
        print(result)
        return 0 if result["status"] != "blocked_pending_approval" else 2
    if args.step == "backfold":
        print(run_backfold_step(config))
        return 0
    if args.step == "report":
        print(f"report: {write_report(config)}")
        return 0
    raise AssertionError(args.step)


if __name__ == "__main__":
    raise SystemExit(main())
