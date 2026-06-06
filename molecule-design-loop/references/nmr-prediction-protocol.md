# NMR Prediction and Verification Protocol (Step 9.7)

Optional step after xTB screening (Step 9) and before Gemini scoring (Step 11). Claude predicts 1H and 13C NMR spectra for top candidates using its internal chemistry knowledge, and optionally compares predictions against experimental NMR data when available.

## Basis

Anthropic research ("Making Claude a Chemist", 2026) demonstrated that Claude Opus achieves:
- 1H NMR: ±0.079 ppm average error (below ±0.20 ppm tolerance)
- 13C NMR: ±1.37 ppm average error (competitive with MestReNova)
- Splitting patterns: ~80% match rate for sub-peak spacing within 0.5 Hz

This is sufficient for structure plausibility checks and predicted-vs-experimental comparison, not for de novo structure elucidation of unknowns without additional data.

## When to run

- **Always available** when the design spec requests NMR prediction (`nmr_prediction: yes`)
- **Triggered automatically** when the user provides experimental NMR data in Step 10
- **Recommended** for candidates approaching synthesis recommendation (Gemini score ≥ 4 or Pareto top-3)

## What Claude predicts

For each candidate SMILES, predict:

### 1H NMR
- Chemical shift (δ, ppm) for each chemically distinct proton environment
- Multiplicity (s, d, t, q, dd, dt, m, br s, etc.)
- Coupling constants (J, Hz) for resolved splittings
- Integration (relative number of protons)
- Solvent assumption (default: CDCl3 unless design spec specifies otherwise)

### 13C NMR
- Chemical shift (δ, ppm) for each chemically distinct carbon
- DEPT classification (CH3, CH2, CH, C) when requested

## Output: ROUND_N_NMR_PREDICTIONS.csv

Columns:
- `candidate_id`
- `nucleus`: `1H` or `13C`
- `atom_environment`: description of the chemical environment (e.g., "aromatic H ortho to NO2", "methyl on N")
- `predicted_shift_ppm`: predicted chemical shift
- `multiplicity`: splitting pattern (1H only)
- `coupling_hz`: coupling constant (1H only)
- `integration`: relative H count (1H only)
- `dept`: CH3/CH2/CH/C (13C only)
- `solvent`: assumed solvent
- `confidence`: high / medium / low
- `notes`: any caveats (e.g., "exchange-broadened NH", "rotamers may cause peak doubling")

## Experimental comparison (when data available)

When the user provides experimental NMR data (in Step 10 or as a separate input), run a predicted-vs-experimental comparison:

### Matching procedure
1. Align predicted peaks to experimental peaks by proximity (within ±0.20 ppm for 1H, ±2.0 ppm for 13C).
2. For each predicted peak, record: `matched` (experimental peak found), `unmatched` (no corresponding experimental peak), or `extra` (experimental peak with no prediction).
3. Compute: mean absolute error across matched peaks, number of unmatched/extra peaks, multiplicity match rate.

### Output: ROUND_N_NMR_VERIFICATION.md

```markdown
# Round N — NMR Verification

## Summary
| candidate_id | nucleus | peaks_predicted | peaks_matched | peaks_unmatched | peaks_extra | mae_ppm | multiplicity_match_rate | verification_status |
|---|---|---|---|---|---|---|---|---|

## Detailed Comparison
[Per-candidate peak-by-peak table]

## Structural Confidence Assessment
[For each candidate: does the NMR comparison support or challenge the proposed structure?]

## Red Flags
[Cases where predicted and experimental NMR diverge significantly — may indicate wrong structure, unexpected tautomer, or impurity]
```

### verification_status values
- `confirmed`: ≥90% peaks matched, MAE < 0.15 ppm (1H) or < 2.0 ppm (13C), no major extra peaks
- `consistent`: ≥75% peaks matched, MAE < 0.25 ppm (1H) or < 3.0 ppm (13C)
- `inconclusive`: 50-75% matched or moderate MAE
- `mismatch`: <50% matched or large systematic deviation — flag for structural review

## Integration with scoring

- `verification_status` feeds into Step 11 (Gemini scoring) as an additional evidence field.
- `confirmed` status strengthens `evidence_level` to `experimental` for that candidate.
- `mismatch` status triggers a mandatory review: is the synthesized compound actually the target, or is it a regioisomer, tautomer, or side product?
- NMR verification cannot override hard constraint violations or synthesis gate failures.

## Scope limitations

Per the Anthropic benchmarks, predictions are validated for:
- Solvents: DMSO-d6, CDCl3, D2O
- Scaffold coverage: limited scaffold families tested (~20 compounds)
- Not validated for: 2D NMR (COSY, HSQC, HMBC), stereochemistry determination, complex natural products, many heteroaromatic classes

Treat NMR predictions as a plausibility check, not a replacement for experimental characterization. Always state the solvent and note when the scaffold class is outside the validated range.

## Claim integrity

- NMR prediction is a Claude-native capability, not a validated computational chemistry method. Do not treat predicted NMR as equivalent to DFT-computed NMR or experimental NMR.
- When reporting NMR predictions, always label them as "Claude-predicted" and state the expected error range.
- The claim audit (Step 9.5) scope extends to NMR predictions: overclaiming NMR match quality is flagged the same way as overclaiming xTB results.
