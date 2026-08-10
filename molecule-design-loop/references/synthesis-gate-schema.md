# Synthesis Feasibility Gate Schema (Step 5)

Required before promoting candidates. May be evidence-only when no retrosynthesis or inventory tool is available.

## What to assess

- Whether the candidate is commercially available, make-on-demand plausible, or needs custom synthesis
- Plausible retrosynthetic disconnections or a named route family
- Route depth, protecting-group burden, functional-group compatibility, hazardous/forbidden conditions
- Starting-material or building-block availability when the design spec provides sources
- Expected purification or stability problems
- Known failed reactions or motifs from the literature packet or previous rounds
- Where route evidence supports it, **more than one candidate route**, and how those routes trade off against each other (cheap-but-low-yield vs long-but-safe, etc.)

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
- `overall_yield_estimate`: `high` (>60%), `medium` (30-60%), `low` (<30%), or `unknown` — estimated overall yield across the route. `unknown` is the honest answer when no route evidence supports a number; do not invent one.
- `hazard_toxicity_flag`: `none`, `standard_care`, `high_hazard`, or `unknown` — reagent/condition hazard and toxicity burden (e.g. azides, phosgene equivalents, heavy metals, high-pressure hydrogenation, chromatography-only purification of a toxic intermediate).
- `synthesis_confidence`: `high`, `medium`, `low`, or `unknown`
- `synthesis_gate_reason`

## Recommended column: route alternatives

- `route_alternatives`: compact trade-off profile of 1-3 candidate routes, one entry per route, formatted `route_id | steps | cost | yield_estimate | hazard_flag` and separated by `;`. Give more than one route only when route evidence actually supports it; otherwise record the single route and set `single_route_only`.

A single scalar `synthesis_cost` collapses the route choice into one number and hides the trade-off. Recording the alternatives keeps the choice visible — a 3-step high-hazard route and a 6-step benign one are different offers, and the chemist, not the loop, should pick between them.

Example: `r1 | 3 | low | low | high_hazard; r2 | 6 | medium | medium | standard_care`

## Rules

- Do not invent a detailed route when no route evidence exists; mark uncertainty explicitly.
- Treat SA score as a weak heuristic, not a route.
- Do not promote a candidate to final recommendation if `synthesis_gate_status = fail`.
- Keep synthesis-warn candidates when the design hypothesis is valuable, but mark as `revise` or `needs_route_work` unless the user accepts the route risk.
- **Make/buy preference ordering (Fix B):** at equal property fit, prefer candidates by `make_or_buy_status` in the order `buy` < `make_on_demand` < `custom_synthesis` (lower = preferred). `synthesis_cost` and `time_to_first_sample` are mandatory inputs to Step 11 Pareto ranking — a strong but expensive/slow route must not silently outrank a comparable cheap/fast one.
- **Feasible is not practical.** A route that merely exists is not a route worth running. `synthesis_cost`, `time_to_first_sample`, `overall_yield_estimate`, and `hazard_toxicity_flag` are the practicality axes; report them even when only roughly estimable, using `unknown` rather than a fabricated value.
- **These are estimates, not a guaranteed Pareto front.** Without a real retrosynthesis engine and a price/toxicity database, `route_alternatives` and the practicality axes are heuristic judgements — not an optimality-guaranteed Pareto front over routes in the sense of multi-objective CASP search. Label them as estimates. If a CASP/retrosynthesis tool is available in the environment, prefer its output and record it in `retrosynthesis_tool`.
