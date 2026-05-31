# xTB Integrity Rules and Chemistry Design Rules

## xTB Integrity Rules

- Record exact command, version, charge, multiplicity, and input geometry source for every run.
- For polymer/material candidates, record the polymer-map preflight status before every xTB run.
- Never compare energies across different stoichiometries as if they were direct stability rankings.
- Treat failed optimizations as evidence, not as missing data.
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
