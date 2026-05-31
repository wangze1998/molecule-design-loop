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
- `synthesis_confidence`: `high`, `medium`, `low`, or `unknown`
- `synthesis_gate_reason`

## Rules

- Do not invent a detailed route when no route evidence exists; mark uncertainty explicitly.
- Treat SA score as a weak heuristic, not a route.
- Do not promote a candidate to final recommendation if `synthesis_gate_status = fail`.
- Keep synthesis-warn candidates when the design hypothesis is valuable, but mark as `revise` or `needs_route_work` unless the user accepts the route risk.
