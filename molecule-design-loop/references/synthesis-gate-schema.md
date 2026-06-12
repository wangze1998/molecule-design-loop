# Synthesis Feasibility Gate Schema (Step 5)

Required before promoting candidates. May be evidence-only when no retrosynthesis or inventory tool is available.

## What to assess

- Whether the candidate is commercially available, make-on-demand plausible, or needs custom synthesis
- Plausible retrosynthetic disconnections or a named route family
- Route depth, protecting-group burden, functional-group compatibility, hazardous/forbidden conditions
- Starting-material or building-block availability when the design spec provides sources
- Expected purification or stability problems
- Known failed reactions or motifs from the literature packet or previous rounds

## Required columns

- `candidate_id`
- `synthesis_gate_status`: `pass`, `warn`, `fail`, or `not_run`
- `make_or_buy_status`: `buy`, `make_on_demand`, `custom_synthesis`, `unknown`, or `not_applicable`
- `route_summary`
- `route_steps_estimate`
- `starting_materials_or_building_blocks`
- `route_risk`
- `synthesis_cost`: `low`, `medium`, `high`, or `very_high` — directly sortable estimate of total cost/effort to obtain the first sample (reagent cost + step count + difficulty). This is a first-class ranking axis in Step 11, not a footnote.
- `time_to_first_sample`: `same_day`, `days`, `weeks`, or `months` — lead time to a usable sample, reflecting buy vs make-on-demand vs custom synthesis.
- `synthesis_confidence`: `high`, `medium`, `low`, or `unknown`
- `synthesis_gate_reason`

## Rules

- Do not invent a detailed route when no route evidence exists; mark uncertainty explicitly.
- Treat SA score as a weak heuristic, not a route.
- Do not promote a candidate to final recommendation if `synthesis_gate_status = fail`.
- Keep synthesis-warn candidates when the design hypothesis is valuable, but mark as `revise` or `needs_route_work` unless the user accepts the route risk.
- **Make/buy preference ordering (Fix B):** at equal property fit, prefer candidates by `make_or_buy_status` in the order `buy` < `make_on_demand` < `custom_synthesis` (lower = preferred). `synthesis_cost` and `time_to_first_sample` are mandatory inputs to Step 11 Pareto ranking — a strong but expensive/slow route must not silently outrank a comparable cheap/fast one.
