#!/usr/bin/env python3
"""Deterministic Step 11 ranking diagnostics for molecule-design-loop.

Reads a decision CSV (one row per candidate) and computes, without any LLM
judgement:

* practicality dominance over {property fit, cost, time, yield, hazard}
* pareto_rank (non-dominated front first, dominated candidates after)
  under one of two explicit modes, see --pareto-rank-mode
* shadow_rank_property_only (property fit alone, the practicality ablation)
* excluded_by_practicality (concrete values, never "practicality concerns")
* a Kendall tau-b redundancy matrix over the five ranking axes
* candidates_dominated / candidates_assessed
* optional benchmark ranks (known compounds scored through the same pass)

Writes an annotated CSV and a Markdown report whose sections map onto the
required ROUND_N_DECISION.md sections in references/ranking-diagnostics-protocol.md.

Integrity rules enforced (references/xtb-integrity-rules.md):
* missing values must be written as ``unknown`` or left empty; they are never
  coerced to a number, and an unrecognised value aborts the run instead of
  being guessed;
* ``unknown`` is non-comparable: a pair of candidates with any unknown axis
  has no dominance relation in either direction;
* a dominated candidate must never hold a ``pareto_rank`` inside the top
  ``TOP_N``. ``--pareto-rank-mode protocol`` enforces that by leaving those
  positions empty; the ``positional`` default keeps the pre-v0.4.0 numbering for
  reproducibility and reports the conflict instead of hiding it.

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Every axis is encoded so that a HIGHER value is BETTER.
AXIS_LEVELS: dict[str, dict[str, int]] = {
    "synthesis_cost": {"low": 3, "medium": 2, "high": 1, "very_high": 0},
    "time_to_first_sample": {"same_day": 3, "days": 2, "weeks": 1, "months": 0},
    "overall_yield_estimate": {"high": 2, "medium": 1, "low": 0},
    "hazard_toxicity_flag": {"none": 2, "standard_care": 1, "high_hazard": 0},
}
SCORE_COLUMN = "gemini_constraint_score"
AXES = [SCORE_COLUMN, *AXIS_LEVELS]
AXIS_LABELS = {
    SCORE_COLUMN: "property_fit",
    "synthesis_cost": "cost",
    "time_to_first_sample": "time",
    "overall_yield_estimate": "yield",
    "hazard_toxicity_flag": "hazard",
}
MAKE_OR_BUY_ORDER = {"buy": 0, "make_on_demand": 1, "custom_synthesis": 2}
UNKNOWN_TOKENS = {"", "unknown", "not_run", "not_assessed", "n/a", "na"}

PARETO_RANK_MODES = ("positional", "protocol")
DEFAULT_PARETO_RANK_MODE = "positional"

ROLE_CANDIDATE = "candidate"
ROLE_CONTROL = "control"
ROLE_VALUES = {"": ROLE_CANDIDATE, ROLE_CANDIDATE: ROLE_CANDIDATE, ROLE_CONTROL: ROLE_CONTROL}

REDUNDANCY_FLOOR = 8
SMALL_SAMPLE_CEILING = 15
REDUNDANT_TAU = 0.8
COUPLED_TAU = 0.6
TOP_N = 3


class InputError(ValueError):
    """Raised when the decision CSV contains a value the script refuses to guess."""


@dataclass
class Candidate:
    candidate_id: str
    row: dict[str, str]
    passes: bool
    values: dict[str, int | None]
    make_or_buy: str
    role: str = ROLE_CANDIDATE
    dominated_by: list[str] = field(default_factory=list)
    pareto_rank: int | None = None
    shadow_rank: int | None = None

    @property
    def is_control(self) -> bool:
        return self.role == ROLE_CONTROL

    def axis_text(self) -> str:
        parts = []
        for axis in AXIS_LEVELS:
            raw = (self.row.get(axis) or "").strip() or "unknown"
            parts.append(f"{AXIS_LABELS[axis]}={raw}")
        return ", ".join(parts)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_csv", help="Decision CSV with candidate_id, gemini_constraint_score and the four practicality axes")
    parser.add_argument("output_csv", help="Annotated CSV (input columns plus diagnostic columns)")
    parser.add_argument("--report", default=None, help="Markdown report path (default: <output_csv stem>_DIAGNOSTICS.md)")
    parser.add_argument(
        "--benchmark-ids",
        default="",
        help="Comma-separated candidate_ids of known reference compounds scored through the same pass",
    )
    parser.add_argument(
        "--pareto-rank-mode",
        choices=PARETO_RANK_MODES,
        default=DEFAULT_PARETO_RANK_MODE,
        help=(
            "positional (default, pre-v0.4.0 behaviour): number every ranked candidate consecutively, "
            "non-dominated first; a dominated candidate can therefore land on rank 2 or 3, which the "
            "scoring protocol forbids, so the run warns and the report records the conflict. "
            "protocol: shift dominated candidates past rank %d so the positions a dominated candidate "
            "would have taken are left empty and no row inside the top %d is dominated. "
            "Step 11 runs must pass protocol." % (TOP_N, TOP_N)
        ),
    )
    parser.add_argument(
        "--role-column",
        default=None,
        help=(
            "Column holding the row's role (candidate/control). Off unless given. When given, rows with "
            "role=control are reported separately, take no part in dominance against candidates and get "
            "no rank, so a control cannot occupy the front it is supposed to be measured against."
        ),
    )
    parser.add_argument(
        "--hard-constraint-column",
        default="pass_hard_constraints",
        help="Column holding yes/no hard-constraint status (missing column = all treated as passing)",
    )
    return parser.parse_args(argv)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_score(raw: str, candidate_id: str) -> int | None:
    text = (raw or "").strip().lower()
    if text in UNKNOWN_TOKENS:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        raise InputError(f"{candidate_id}: {SCORE_COLUMN}={raw!r} is not an integer 1-5 or 'unknown'") from exc
    if not 1 <= value <= 5:
        raise InputError(f"{candidate_id}: {SCORE_COLUMN}={raw!r} is outside 1-5; refusing to treat it as a score")
    return value


def parse_level(axis: str, raw: str, candidate_id: str) -> int | None:
    text = (raw or "").strip().lower()
    if text in UNKNOWN_TOKENS:
        return None
    levels = AXIS_LEVELS[axis]
    if text not in levels:
        allowed = ", ".join([*levels, "unknown"])
        raise InputError(f"{candidate_id}: {axis}={raw!r} is not one of: {allowed}")
    return levels[text]


def parse_role(raw: str | None, candidate_id: str) -> str:
    """Role of a row. Unrecognised values abort rather than being guessed."""
    text = (raw or "").strip().lower()
    if text not in ROLE_VALUES:
        allowed = ", ".join(sorted(v for v in ROLE_VALUES if v))
        raise InputError(f"{candidate_id}: role={raw!r} is not one of: {allowed} (or empty = {ROLE_CANDIDATE})")
    return ROLE_VALUES[text]


def parse_pass(raw: str | None) -> bool:
    if raw is None:
        return True
    return raw.strip().lower() in {"yes", "y", "true", "pass", "1"}


def load_candidates(rows: list[dict[str, str]], hard_column: str, role_column: str | None = None) -> list[Candidate]:
    if not rows:
        raise InputError("decision CSV has no rows")
    missing = [col for col in ["candidate_id", *AXES] if col not in rows[0]]
    if missing:
        raise InputError(f"decision CSV is missing required columns: {', '.join(missing)}")
    if role_column is not None and role_column not in rows[0]:
        raise InputError(f"--role-column {role_column!r} is not a column of the decision CSV")

    candidates: list[Candidate] = []
    seen: set[str] = set()
    errors: list[str] = []
    for row in rows:
        cid = (row.get("candidate_id") or "").strip()
        if not cid:
            errors.append("row with empty candidate_id")
            continue
        if cid in seen:
            errors.append(f"duplicate candidate_id {cid}")
            continue
        seen.add(cid)
        try:
            values: dict[str, int | None] = {SCORE_COLUMN: parse_score(row.get(SCORE_COLUMN, ""), cid)}
            for axis in AXIS_LEVELS:
                values[axis] = parse_level(axis, row.get(axis, ""), cid)
            role = parse_role(row.get(role_column), cid) if role_column is not None else ROLE_CANDIDATE
        except InputError as exc:
            errors.append(str(exc))
            continue
        candidates.append(
            Candidate(
                candidate_id=cid,
                row=row,
                passes=parse_pass(row.get(hard_column)),
                values=values,
                make_or_buy=(row.get("make_or_buy_status") or "").strip().lower(),
                role=role,
            )
        )
    if errors:
        raise InputError("refusing to rank on unparseable input:\n  - " + "\n  - ".join(errors))
    return candidates


def fully_known(candidate: Candidate) -> bool:
    return all(candidate.values[axis] is not None for axis in AXES)


def dominates(a: Candidate, b: Candidate) -> bool:
    """A dominates B: no worse on every axis, strictly better on at least one.

    Any unknown on either side makes the pair non-comparable.
    """
    if not (fully_known(a) and fully_known(b)):
        return False
    at_least_as_good = all(a.values[ax] >= b.values[ax] for ax in AXES)  # type: ignore[operator]
    strictly_better = any(a.values[ax] > b.values[ax] for ax in AXES)  # type: ignore[operator]
    return at_least_as_good and strictly_better


def competition_rank(items: list[Candidate], key) -> dict[str, int]:
    """Standard competition ranking ("1224"): ties share a rank."""
    ordered = sorted(items, key=lambda c: (key(c), c.candidate_id))
    ranks: dict[str, int] = {}
    previous_key = object()
    current_rank = 0
    for position, cand in enumerate(ordered, start=1):
        k = key(cand)
        if k != previous_key:
            current_rank = position
            previous_key = k
        ranks[cand.candidate_id] = current_rank
    return ranks


def score_key(c: Candidate) -> tuple[int, ...]:
    score = c.values[SCORE_COLUMN]
    return (0 if score is not None else 1, -(score or 0))


def rankable(candidates: list[Candidate]) -> list[Candidate]:
    """Rows that enter the ranking: hard-constraint passers that are not controls.

    A control is a reference point the candidates are measured against, not an offer
    to the chemist. With --role-column it is held out of dominance in both directions,
    so it can neither be dominated by a candidate nor occupy the non-dominated front.
    """
    return [c for c in candidates if c.passes and not c.is_control]


def controls(candidates: list[Candidate]) -> list[Candidate]:
    return [c for c in candidates if c.is_control]


def assign_ranks(candidates: list[Candidate], mode: str = DEFAULT_PARETO_RANK_MODE) -> None:
    if mode not in PARETO_RANK_MODES:
        raise InputError(f"unknown pareto rank mode {mode!r}; expected one of: {', '.join(PARETO_RANK_MODES)}")
    ranked = rankable(candidates)
    for b in ranked:
        b.dominated_by = sorted(a.candidate_id for a in ranked if a is not b and dominates(a, b))

    # Shadow ranking: property fit alone, ties shared.
    shadow = competition_rank(ranked, score_key)
    for c in ranked:
        c.shadow_rank = shadow[c.candidate_id]

    # Pareto rank: non-dominated first, then score, then make/buy, then id.
    def pareto_key(c: Candidate):
        return (
            1 if c.dominated_by else 0,
            *score_key(c),
            MAKE_OR_BUY_ORDER.get(c.make_or_buy, len(MAKE_OR_BUY_ORDER)),
        )

    ordered = sorted(ranked, key=lambda c: (pareto_key(c), c.candidate_id))

    # The dominated/non-dominated flag leads pareto_key, so the non-dominated front
    # always occupies the first positions of `ordered`.
    non_dominated = [c for c in ordered if not c.dominated_by]
    # protocol mode: when the front is shorter than TOP_N, the remaining top positions
    # are left EMPTY instead of being handed to the best dominated candidate. No row
    # carries them, and the first dominated candidate starts at TOP_N + 1.
    offset = max(0, TOP_N - len(non_dominated)) if mode == "protocol" else 0

    for position, cand in enumerate(ordered, start=1):
        cand.pareto_rank = position + offset if cand.dominated_by else position


def in_final_top(c: Candidate) -> bool:
    """A candidate is in the presented top set only if it is non-dominated and
    within the first TOP_N by pareto_rank. A dominated candidate is never in it,
    even when fewer than TOP_N candidates are non-dominated (protocol: a dominated
    candidate must not enter the top 3). A control is never in it either."""
    return (
        c.passes
        and not c.is_control
        and not c.dominated_by
        and c.pareto_rank is not None
        and c.pareto_rank <= TOP_N
    )


def top_rank_conflicts(candidates: list[Candidate]) -> list[Candidate]:
    """Ranked candidates that are dominated yet hold a pareto_rank inside the top TOP_N.

    The scoring protocol forbids this. It can only happen in `positional` mode, where
    the ranks are consecutive positions: with fewer than TOP_N non-dominated rows the
    next dominated rows inherit the free positions, so the CSV field says 2 or 3 while
    the report's final top set (in_final_top) correctly leaves them out. Reported
    rather than silently corrected, so an existing round file stays reproducible.
    """
    return sorted(
        (c for c in rankable(candidates) if c.dominated_by and c.pareto_rank is not None and c.pareto_rank <= TOP_N),
        key=lambda c: c.pareto_rank or 0,
    )


def exclusion_reason(c: Candidate) -> str:
    if not c.passes or c.shadow_rank is None or c.pareto_rank is None:
        return "not_ranked"
    if c.shadow_rank > TOP_N or in_final_top(c):
        return "no"
    if c.dominated_by:
        return f"dominated_by:{';'.join(c.dominated_by)} ({c.axis_text()})"
    return f"outranked within the non-dominated front ({c.axis_text()}, make_or_buy={c.make_or_buy or 'unknown'})"


def kendall_tau_b(xs: list[int], ys: list[int]) -> float | None:
    """Kendall tau-b, defined for tied ordinal data. None if an axis is constant."""
    n = len(xs)
    concordant = discordant = ties_x = ties_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = xs[i] - xs[j]
            dy = ys[i] - ys[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif (dx > 0) == (dy > 0):
                concordant += 1
            else:
                discordant += 1
    denominator = ((concordant + discordant + ties_x) * (concordant + discordant + ties_y)) ** 0.5
    if denominator == 0:
        return None
    return (concordant - discordant) / denominator


def redundancy_matrix(candidates: list[Candidate]) -> dict[tuple[str, str], tuple[float | None, int]]:
    ranked = rankable(candidates)
    result: dict[tuple[str, str], tuple[float | None, int]] = {}
    for i, a in enumerate(AXES):
        for b in AXES[i + 1:]:
            pairs = [(c.values[a], c.values[b]) for c in ranked if c.values[a] is not None and c.values[b] is not None]
            xs = [p[0] for p in pairs]  # type: ignore[misc]
            ys = [p[1] for p in pairs]  # type: ignore[misc]
            tau = kendall_tau_b(xs, ys) if len(pairs) >= 2 else None
            result[(a, b)] = (tau, len(pairs))
    return result


def verdict(tau: float | None) -> str:
    if tau is None:
        return "undefined (constant axis or too few pairs)"
    if abs(tau) >= REDUNDANT_TAU:
        return "redundant"
    if abs(tau) >= COUPLED_TAU:
        return "coupled"
    return "independent"


def build_report(
    candidates: list[Candidate],
    benchmark_ids: list[str],
    mode: str = DEFAULT_PARETO_RANK_MODE,
) -> str:
    ranked = rankable(candidates)
    control_rows = controls(candidates)
    n = len(ranked)
    lines: list[str] = ["# Ranking Diagnostics", ""]
    lines.append(f"Hard-constraint passers: {n} of {len(candidates) - len(control_rows)} candidates.")
    if control_rows:
        lines.append(
            f"Controls held out of the ranking: {len(control_rows)} "
            f"({', '.join(c.candidate_id for c in control_rows)}). They take no part in dominance."
        )
    lines.append(f"pareto_rank mode: `{mode}`.")
    lines.append("")

    # Protocol conflict: dominated candidates holding a top-TOP_N rank.
    conflicts = top_rank_conflicts(candidates)
    if conflicts:
        lines += ["## pareto_rank / protocol Conflict", ""]
        lines.append(
            f"**{len(conflicts)} dominated candidate(s) hold a pareto_rank inside the top {TOP_N}**, which the "
            "scoring protocol forbids: "
            + "; ".join(f"{c.candidate_id} (rank {c.pareto_rank}, dominated_by:{';'.join(c.dominated_by)})" for c in conflicts)
        )
        lines.append("")
        non_dominated_count = len([c for c in ranked if not c.dominated_by])
        lines.append(
            f"Only {non_dominated_count} of {n} ranked candidates are non-dominated, so `positional` numbering "
            f"hands the free top positions to the best dominated candidates. The final top set below excludes "
            f"them, so the CSV's pareto_rank field and this report disagree. Re-run with "
            f"`--pareto-rank-mode protocol` to leave those positions empty."
        )
        lines.append("")

    # Axis redundancy
    lines += ["## Axis Redundancy", ""]
    if n < REDUNDANCY_FLOOR:
        lines.append(f"axis_redundancy: not_assessed (n={n}, below floor of {REDUNDANCY_FLOOR})")
    else:
        label = " — small_sample: report only, do not collapse any axis" if n <= SMALL_SAMPLE_CEILING else ""
        lines.append(f"Kendall tau-b over {n} hard-constraint passers{label}. Pairwise deletion of unknown values.")
        lines.append("")
        lines.append("| axis pair | tau-b | usable pairs | verdict |")
        lines.append("|---|---|---|---|")
        flagged: list[str] = []
        for (a, b), (tau, usable) in redundancy_matrix(candidates).items():
            tau_text = "—" if tau is None else f"{tau:+.2f}"
            v = verdict(tau)
            lines.append(f"| {AXIS_LABELS[a]} / {AXIS_LABELS[b]} | {tau_text} | {usable} | {v} |")
            if v in {"redundant", "coupled"}:
                flagged.append(f"{AXIS_LABELS[a]} / {AXIS_LABELS[b]} ({v})")
        lines.append("")
        if flagged:
            lines.append("Flagged pairs: " + "; ".join(flagged) + ". The trade-off narrative must not present these as independent considerations.")
        else:
            lines.append("No axis pair reached the coupled threshold.")
        lines.append("")
        lines.append(
            "Note: redundant axes do not change the Pareto dominance relation; this check exists so the "
            "trade-off is not reported as richer than it is."
        )
    lines.append("")

    # Dominance count
    assessed = [c for c in ranked if fully_known(c)]
    dominated = [c for c in ranked if c.dominated_by]
    lines += ["## Practicality Dominance", ""]
    lines.append(f"candidates_dominated / candidates_assessed: {len(dominated)} / {len(assessed)}")
    not_assessable = [c.candidate_id for c in ranked if not fully_known(c)]
    if not_assessable:
        lines.append(f"Not comparable (an axis is unknown, confidence lowered): {', '.join(not_assessable)}")
    if not dominated:
        lines.append("")
        lines.append(
            f"Practicality dominance: 0 of {len(assessed)} assessed candidates were dominated. "
            "The practicality axes did not constrain the ranking this round."
        )
    lines.append("")

    # Ablation
    lines += ["## Practicality Ablation", ""]
    shadow_top = sorted((c for c in ranked if c.shadow_rank is not None and c.shadow_rank <= TOP_N), key=lambda c: (c.shadow_rank, c.candidate_id))
    final_top = sorted((c for c in ranked if in_final_top(c)), key=lambda c: c.pareto_rank)
    lines.append("| | property-only top | final top |")
    lines.append("|---|---|---|")
    for i in range(max(len(shadow_top), len(final_top))):
        s = f"{shadow_top[i].candidate_id} (shadow {shadow_top[i].shadow_rank})" if i < len(shadow_top) else ""
        f = final_top[i].candidate_id if i < len(final_top) else ""
        lines.append(f"| {i + 1} | {s} | {f} |")
    lines.append("")
    if len(shadow_top) > TOP_N:
        lines.append(f"Property-only top set has {len(shadow_top)} members because of tied scores; ties are shared, not broken arbitrarily.")
        lines.append("")
    shadow_ids = {c.candidate_id for c in shadow_top}
    final_ids = {c.candidate_id for c in final_top}
    pushed_out = [c for c in shadow_top if c.candidate_id not in final_ids]
    pulled_in = [c for c in final_top if c.candidate_id not in shadow_ids]
    if not pushed_out and not pulled_in:
        lines.append(
            "Practicality ablation: the property-only ranking and the final ranking give the same top set. "
            "Practicality did not change the recommendation this round."
        )
    else:
        for c in pushed_out:
            lines.append(f"- Excluded by practicality: **{c.candidate_id}** — {exclusion_reason(c)}")
        for c in pulled_in:
            lines.append(f"- Promoted by practicality: **{c.candidate_id}** (shadow rank {c.shadow_rank}) — {c.axis_text()}")
    lines.append("")

    # Controls
    if control_rows:
        lines += ["## Controls (reported separately, not ranked)", ""]
        lines.append(
            "A control is the reference the candidates are measured against, so it is held out of dominance in "
            "both directions and carries no rank. Read its axes next to the front; do not read it as an offer."
        )
        lines.append("")
        lines.append("| control | property_fit | axes | hard constraints |")
        lines.append("|---|---|---|---|")
        for c in control_rows:
            score = c.values[SCORE_COLUMN]
            lines.append(
                f"| {c.candidate_id} | {score if score is not None else 'unknown'} | {c.axis_text()} | "
                f"{'pass' if c.passes else 'fail'} |"
            )
        lines.append("")

    # Benchmarks
    if benchmark_ids:
        lines += ["## Benchmark Ranks", ""]
        by_id = {c.candidate_id: c for c in candidates}
        lines.append("Known reference compounds scored through the same pass. If a known-good compound ranks low, suspect the scoring before the candidates.")
        lines.append("")
        lines.append("| benchmark | pareto_rank | shadow_rank | dominance |")
        lines.append("|---|---|---|---|")
        for bid in benchmark_ids:
            c = by_id.get(bid)
            if c is None:
                lines.append(f"| {bid} | missing from input | | |")
                continue
            pr = c.pareto_rank if c.pareto_rank is not None else ("control" if c.is_control else "not_ranked")
            sr = c.shadow_rank if c.shadow_rank is not None else ("control" if c.is_control else "not_ranked")
            if c.is_control:
                dom = "control_not_compared"
            elif c.dominated_by:
                dom = f"dominated_by:{';'.join(c.dominated_by)}"
            else:
                dom = "not_comparable" if not fully_known(c) else "non_dominated"
            lines.append(f"| {bid} | {pr} of {n} | {sr} | {dom} |")
        lines.append("")

    lines.append(
        "These diagnostics show what the practicality constraint changed. They do not show the final ranking "
        "is correct; only experimental feedback does that (loop_calibration)."
    )
    lines.append("")
    return "\n".join(lines)


def write_output(path: Path, rows: list[dict[str, str]], candidates: list[Candidate]) -> None:
    by_id = {c.candidate_id: c for c in candidates}
    extra = ["practicality_dominance", "pareto_rank", "shadow_rank_property_only", "excluded_by_practicality"]
    fieldnames = list(rows[0].keys())
    for col in extra:
        if col not in fieldnames:
            fieldnames.append(col)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            c = by_id[row["candidate_id"].strip()]
            out = dict(row)
            if c.is_control:
                out.update({col: "control" for col in extra})
                out["practicality_dominance"] = "control_not_compared"
            elif not c.passes:
                out.update({col: "not_ranked" for col in extra})
                out["practicality_dominance"] = "not_assessed"
            else:
                if c.dominated_by:
                    out["practicality_dominance"] = "dominated_by:" + ";".join(c.dominated_by)
                elif not fully_known(c):
                    out["practicality_dominance"] = "not_assessed"
                else:
                    out["practicality_dominance"] = "non_dominated"
                out["pareto_rank"] = str(c.pareto_rank)
                out["shadow_rank_property_only"] = str(c.shadow_rank)
                out["excluded_by_practicality"] = exclusion_reason(c)
            writer.writerow(out)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)
    report_path = Path(args.report) if args.report else output_path.with_name(output_path.stem + "_DIAGNOSTICS.md")
    benchmark_ids = [b.strip() for b in args.benchmark_ids.split(",") if b.strip()]

    rows = read_rows(input_path)
    try:
        candidates = load_candidates(rows, args.hard_constraint_column, args.role_column)
        assign_ranks(candidates, args.pareto_rank_mode)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    write_output(output_path, rows, candidates)
    report_path.write_text(build_report(candidates, benchmark_ids, args.pareto_rank_mode), encoding="utf-8")
    print(f"wrote {output_path} and {report_path}")

    conflicts = top_rank_conflicts(candidates)
    if conflicts:
        detail = ", ".join(f"{c.candidate_id} (rank {c.pareto_rank})" for c in conflicts)
        print(
            f"warning: --pareto-rank-mode {args.pareto_rank_mode} put {len(conflicts)} dominated candidate(s) "
            f"inside the top {TOP_N}: {detail}. The scoring protocol forbids this and the report's final top set "
            f"excludes them, so pareto_rank and the report disagree. Re-run with --pareto-rank-mode protocol.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
