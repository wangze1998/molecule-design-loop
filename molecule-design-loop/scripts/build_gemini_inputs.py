#!/usr/bin/env python3
"""Assemble the Gemini input packets for Steps 3.5, 5.5 and 9.5 (one round).

Why this exists
---------------
The three review steps must see raw artifacts, never a model-written summary --
a reviewer handed a summary is reviewing the summary. Pasting whole CSVs into a
prompt satisfies that rule but costs output tokens and leaves the file sitting in
context for the rest of the run. This script writes the packets straight from the
round files instead, so the assistant passes a path rather than retyping the data.

Each packet carries:
  - the `system:` block copied verbatim from the step's protocol reference;
  - DESIGN_SPEC_LOCKED.md;
  - the columns that step actually needs, as CSV.

Step 11 (scoring) is deliberately not built here: it needs the outputs of the
other three first, so it is assembled after they come back.

Usage
-----
  build_gemini_inputs.py --round-dir molecule-design-stage \\
      --skill-refs /path/to/molecule-design-loop/references \\
      --out molecule-design-stage/_gemini_inputs [--round 1] [--steps 3.5 5.5]

Missing optional inputs are skipped with a note rather than faked; a packet that
cannot be built honestly is not written.
"""
import argparse
import csv
import io
import json
import os
import re
import sys

# Per step: the protocol file holding the system prompt, and the columns each
# reviewer needs. Keep these lists narrow -- a reviewer given every column reads
# none of them carefully.
STEPS = {
    "3.5": {
        "title": "Adversarial chemistry review",
        "protocol": "adversarial-review-protocol.md",
        "filename": "step3.5_adversarial_review_input.md",
        "candidate_columns": [
            "candidate_id", "role", "smiles", "design_move", "target_constraint",
            "rationale", "expected_proxy_effect", "risk", "synthesis_hypothesis",
            "make_or_buy_hint", "building_block_source", "source_hint",
        ],
        # The critic should see the route detail the scorer will see, or the
        # synthesis critique is uninformed.
        "gate_columns": [
            "candidate_id", "synthesis_gate_status", "make_or_buy_status",
            "route_summary", "route_steps_estimate", "starting_materials_or_building_blocks",
            "synthesis_cost", "time_to_first_sample", "overall_yield_estimate",
            "hazard_toxicity_flag", "route_alternatives", "synthesis_gate_reason",
        ],
        "gate_required": False,
    },
    "5.5": {
        "title": "Prior-art / novelty check",
        "protocol": "novelty-check-protocol.md",
        "filename": "step5.5_prior_art_input.md",
        # Structure and stereochemistry must be present, or the result is a
        # keyword search being reported as a structure novelty check.
        "candidate_columns": [
            "candidate_id", "role", "smiles", "repeat_unit_display_smiles",
            "sru_bracket_schematic", "tacticity_or_regioregularity", "comonomer_ratio",
            "side_chain_descriptions", "design_move",
        ],
        "gate_columns": [
            "candidate_id", "route_summary", "starting_materials_or_building_blocks",
        ],
        "gate_required": False,
    },
    "9.5": {
        "title": "Result-to-claim audit",
        "protocol": "claim-audit-protocol.md",
        "filename": "step9.5_claim_audit_input.md",
        "candidate_columns": [
            "candidate_id", "rationale", "expected_proxy_effect", "risk",
            "computational_evidence_role", "prior_computational_evidence",
            "surrogate_scope",
        ],
        "gate_columns": [],
        "gate_required": False,
    },
}

NOTE = (
    "> The CSV blocks below are field-for-field copies of the round files. If they\n"
    "> disagree with the `ROUND_*` sources, the sources win.\n"
    "> Review the content as given; do not ask for a summary of it.\n"
)


def system_prompt(path):
    """Copy the `system:` block out of a protocol reference, verbatim."""
    if not os.path.exists(path):
        return f"(protocol file not found: {os.path.basename(path)})"
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(r"^system:.*?(?=\n\s*\n)", text, re.S | re.M)
    if not match:
        return f"(no `system:` block in {os.path.basename(path)})"
    return match.group(0)


def csv_subset(path, columns):
    """Those of `columns` that exist, as CSV text. Returns (text, missing)."""
    with open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return "", columns
    present = [c for c in columns if c in rows[0]]
    missing = [c for c in columns if c not in rows[0]]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(present)
    for row in rows:
        writer.writerow([row.get(c, "") for c in present])
    return buffer.getvalue(), missing


def fence(body, lang="csv"):
    return f"```{lang}\n{body.rstrip()}\n```\n"


def build_packet(step, cfg, paths, round_no):
    """Return the packet text, or None when a required input is missing."""
    parts = [
        f"# Step {step} input packet -- {cfg['title']}\n\n"
        f"Round {round_no}. Paste or attach as given; do not summarise.\n\n{NOTE}",
        "## system\n" + system_prompt(paths["protocol"]),
    ]
    with open(paths["spec"], encoding="utf-8") as handle:
        parts.append("## DESIGN_SPEC_LOCKED.md\n" + handle.read())

    body, missing = csv_subset(paths["candidates"], cfg["candidate_columns"])
    if not body:
        print(f"  step {step}: candidates file is empty, skipped", file=sys.stderr)
        return None
    heading = f"## ROUND_{round_no}_CANDIDATES.csv (selected columns)"
    if missing:
        heading += f"\n\nColumns absent from this round's file: {', '.join(missing)}."
    parts.append(heading + "\n" + fence(body))

    if cfg["gate_columns"]:
        if os.path.exists(paths["gate"]):
            gate_body, _ = csv_subset(paths["gate"], cfg["gate_columns"])
            if gate_body:
                parts.append(
                    f"## ROUND_{round_no}_SYNTHESIS_FEASIBILITY.csv (route and practicality)\n"
                    + fence(gate_body)
                )
        elif cfg["gate_required"]:
            print(f"  step {step}: needs the synthesis gate file, skipped", file=sys.stderr)
            return None
        else:
            parts.append(
                "## Synthesis feasibility\n\nNot available for this round "
                "(the gate had not run when this packet was built).\n"
            )

    if step == "9.5":
        parts.append(evidence_section(paths))
    return "\n".join(parts)


def evidence_section(paths):
    """Name the computational evidence files rather than embedding them.

    The auditor needs to know which raw outputs exist and can ask for them; a
    packet should not carry hundreds of megabytes of xTB or DFT output.
    """
    lines = ["## Computational evidence referenced this round\n"]
    xtb = paths.get("xtb")
    if xtb and os.path.exists(xtb):
        body, _ = csv_subset(
            xtb,
            [
                "candidate_id", "method", "optimization_status", "final_energy",
                "homo_lumo_gap_ev", "dipole_debye", "geometry_sanity",
                "convergence_failure_reason",
            ],
        )
        if body:
            lines.append(f"From `{os.path.basename(xtb)}`:\n" + fence(body))
    else:
        lines.append(
            "No xTB ran this round. This is case 2 of the audit protocol: the packet's\n"
            "job is to state which design objectives have no direct evidence.\n"
        )

    state = paths.get("state")
    if state and os.path.exists(state):
        try:
            with open(state, encoding="utf-8") as handle:
                prior = (json.load(handle) or {}).get("prior_computational_evidence") or {}
        except (json.JSONDecodeError, OSError) as err:
            prior = {}
            lines.append(f"(could not read cross-round state: {err})\n")
        if prior:
            lines.append(
                "Earlier jobs this round's claims lean on. Ask for a file by name; raw\n"
                "outputs are not embedded here.\n\n| stage | results file |\n|---|---|"
            )
            for stage, location in prior.items():
                lines.append(f"| {stage} | `{location}` |")
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--round-dir", required=True, help="folder holding the ROUND_N_* files")
    parser.add_argument("--skill-refs", required=True, help="molecule-design-loop/references")
    parser.add_argument("--out", required=True, help="folder to write the packets into")
    parser.add_argument("--round", default="1", help="round number (default: 1)")
    parser.add_argument(
        "--steps", nargs="*", choices=sorted(STEPS), help="steps to build (default: all)"
    )
    args = parser.parse_args()

    round_dir, round_no = args.round_dir, args.round
    spec = os.path.join(round_dir, "DESIGN_SPEC_LOCKED.md")
    candidates = os.path.join(round_dir, f"ROUND_{round_no}_CANDIDATES.csv")
    for required in (spec, candidates):
        if not os.path.exists(required):
            sys.exit(f"error: missing {required}")

    paths = {
        "spec": spec,
        "candidates": candidates,
        "gate": os.path.join(round_dir, f"ROUND_{round_no}_SYNTHESIS_FEASIBILITY.csv"),
        "xtb": os.path.join(round_dir, f"ROUND_{round_no}_XTB_RESULTS.csv"),
        "state": os.path.join(round_dir, "DESIGN_LOOP_STATE.json"),
    }
    os.makedirs(args.out, exist_ok=True)

    written = 0
    for step in args.steps or sorted(STEPS):
        cfg = STEPS[step]
        paths["protocol"] = os.path.join(args.skill_refs, cfg["protocol"])
        packet = build_packet(step, cfg, paths, round_no)
        if packet is None:
            continue
        target = os.path.join(args.out, cfg["filename"])
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(packet)
        print(f"  step {step}: {target} ({os.path.getsize(target)} bytes)")
        written += 1
    print(f"wrote {written} packet(s) -> {args.out}")
    print("Give Gemini these paths. Do not paste the contents into the conversation.")


if __name__ == "__main__":
    main()
