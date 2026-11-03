# xTB Integrity Rules and Chemistry Design Rules

## xTB Integrity Rules

- Record exact command, version, charge, multiplicity, and input geometry source for every run.
- For polymer/material candidates, record the polymer-map preflight status before every xTB run.
- Never compare energies across different stoichiometries as if they were direct stability rankings.
- Treat failed optimizations as evidence, not as missing data.
- **Never map a failed or missing computation to a numeric sentinel.** A failure is `fail` / `not_run` / `unknown` — never `0`, never `-999`, never an imputed mean. A sentinel silently re-enters every downstream sort, filter and Pareto comparison as if it were a measurement, and because sentinels sit at the extremes of the numeric range, failed runs land at one end of the ranking rather than out of it. The failure mode to picture: a Gaussian or xTB job errors out, the parser writes HOMO `0`, and that candidate now sorts above every real result. Carry failures as their own status value and exclude those rows from numeric comparison explicitly.
- **One parse path per artifact.** When two scripts or two steps read the same results file, they must agree on how failures, units, and precision are handled. Divergent handling — one path dropping error rows while another coerces them to a number — produces two different rankings from one dataset, and nothing in the loop will flag the disagreement.
- Parse numeric fields as numbers, not by string slicing. Truncating a text field to a fixed width (`"-5.76"[:4]` → `-5.7`) silently drops precision and breaks on any value whose sign or magnitude changes its width.
- Mark conformer sensitivity if only one geometry was tested.
- For host-guest, assembly, or dimer proxies, write the proxy definition explicitly before running.
- For polymers, record the exact surrogate: monomer/repeat unit, capped oligomer length, end groups, charge state, tacticity/regioregularity assumption, and which polymer-level claims are unsupported by this surrogate.

## Chemistry Design Rules

Prefer chemically interpretable edits:

- Electronic tuning (donor/acceptor strength, induction, resonance)
- Steric tuning (bulk, twist, shielding)
- Linker length/rigidity
- Pi-surface modulation
- Heteroatom placement
- Charge-state control
- Solubility handle
- Control molecule design

For polymer designs, separate monomer chemistry, repeat-unit structure, finite oligomer proxy, polymerization feasibility, and bulk/material-property claims — do not collapse these layers.

Avoid candidates that only look novel but do not test a clear hypothesis.
