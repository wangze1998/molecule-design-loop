# Molecule Design Spec

## Goal

Describe the target molecule or polymer/material family and the property you want to improve.

## Zotero Library Integration

The skill will search your Zotero library first and extract design knowledge automatically. Configure the search scope here if needed.

- Zotero search keywords: (leave blank to auto-detect from Goal and Hypothesis)
- Restrict to Zotero collection: (collection name or leave blank for whole library)
- Restrict to Zotero tags: (comma-separated tags or leave blank)
- Minimum structural richness to read full text: high / medium / low (default: medium)
- Max papers to read full text: (default: 5-8)

> If your Zotero library is not connected, the skill will fall back to web search. Connect Zotero via the zotero-mcp server.

## Design Mode

- Requested mode: auto / small_molecule / polymer
- Auto-detection hints from user command:
- If ambiguous, question to ask before candidate generation:

## Scientific Hypothesis

State the design hypothesis in one or two sentences.

## Structure Image Input

Provide structure images (journal figures, ChemDraw screenshots, hand-drawn sketches) as an alternative to typing SMILES. Claude will extract structures directly from images.

- Structure image files: (paths to PNG/JPG/PDF files, or leave blank)
- Require user confirmation for extracted SMILES: yes (default for low-confidence) / always / no

## Seed Structures

These will be auto-populated from your Zotero library after extraction and/or from structure image input. You can also add or override them manually.

| name | SMILES | role | keep / modify / avoid | source |
|---|---|---|---|---|
| seed_1 |  |  |  | zotero / image / manual |

## Small-Molecule Design Mode

Fill this section only if the target is a discrete small molecule or small-molecule scaffold series.

- Small-molecule design mode: scaffold_optimization / de_novo_bounded / library_triage / closed_loop_experiment
- Target type: ligand / inhibitor / host / guest / catalyst / dye / photoswitch / supramolecular building block / other
- Mechanism or property hypothesis:
- Scaffold policy: preserve / bounded modification / scaffold hop allowed
- Key substituent or motif positions:
- Assay or experimental readout:
- Experimental priority rule:
- Computational evidence role:

## Polymer / Material Design Mode

Fill this section only if the target is a polymer, oligomer, material repeat unit, or monomer series.

- Polymer design mode: mechanism_first / informatics_screen / closed_loop_experiment
- Structure-property hypothesis:
- Primary mechanism to tune:
- Polymerization route:
- Monomer availability or synthesis notes:
- Expected DP / Mn / dispersity target:
- Processing or morphology assumptions:
- Characterization plan:
- Computational evidence role:
- Experimental priority rule:
- Need standalone polymer HTML view: yes/no
- Target type: monomer / repeat unit / oligomer / polymer / copolymer
- Repeat-unit display SMILES with [*:1]/[*:2]:
- Repeat-unit caption:
- SRU bracket schematic:
- Repeat-unit handles explanation:
- Human-readable polymer notation or BigSMILES:
- Monomer SMILES:
- Repeat-unit surrogate SMILES:
- Capped oligomer model SMILES:
- RDKit display oligomer SMILES:
- Oligomer length for screening:
- End-group model:
- Backbone start atom / label:
- Backbone end atom / label:
- Backbone connection points:
- Connection point atom indices:
- Backbone path atoms or labels:
- Human backbone direction label:
- Backbone-only SMILES:
- Side-chain attachment atoms or labels:
- Side-chain fragment SMILES:
- Side-chain descriptions:
- Comonomer ratio or sequence assumptions:
- Tacticity/regioregularity assumptions:
- Target material properties:

## Synthesis Feasibility Gate

Fill this for both small-molecule and polymer/material runs.

- Retrosynthesis or route check required: yes/no
- Minimum synthesis gate for promotion: route_plausible / make_on_demand / commercially_available / user_override
- Make-or-buy preference:
- Known available starting materials or building blocks:
- Preferred vendors, libraries, or inventory sources:
- Maximum acceptable route steps:
- Forbidden reactions, reagents, catalysts, or conditions:
- Protecting-group burden tolerance:
- Purification or stability constraints:
- Route risk tolerance: low / medium / high
- Known failed reactions or motifs:

## Experimental Feedback / Active Learning

Fill this when prior or new experimental data should steer the next round.

- Existing experimental results file:
- Planned experiment type:
- Primary measured endpoint:
- Success threshold:
- Important negative controls:
- Failure labels to track: synthesis_failed / purification_failed / unstable / inactive / insoluble / bad_selectivity / bad_material_property / inconclusive
- Use failed synthesis/test rows as negative examples: yes/no
- Condition metadata required: yes/no

## Candidate Ranking

- Pareto objectives:
- Hard gates before Pareto ranking:
- Evidence priority: experimental > synthesis_route > computed_proxy > literature_only > hypothesis_only
- Minimum confidence for final recommendation:
- Uncertainty reasons to report:

## RDKit / xTB Polymer Inputs

Fill this section for every polymer/material run.

- RDKit input SMILES: finite valid molecule only; usually the capped oligomer model
- xTB input model: capped oligomer / monomer / repeat-unit surrogate / periodic cell
- xTB geometry source: generated from SMILES / supplied XYZ / supplied SDF / project runner
- xTB charge:
- xTB multiplicity:
- Explicit end groups:
- Oligomer `n`:
- Polymer-map preflight required: yes/no
- Polymer-map preflight notes:
- Unsupported polymer-level claims:

## Hard Constraints

- Allowed elements:
- Charge range:
- Molecular weight range:
- Required motifs:
- Forbidden motifs:
- Required scaffold features:
- Required repeat-unit or backbone features:
- Solubility or handling constraints:
- Synthetic accessibility constraints:
- Polymerization feasibility constraints:

## Soft Preferences

- Electronic character:
- Rigidity/flexibility:
- Pi-surface:
- Steric profile:
- Hydrogen bonding:
- Photochemical or redox preference:
- Control molecules needed:
- Polymer controls needed:

## Literature Anchors

List Zotero tags, local PDFs, author names, or known papers to use as anchors.

## xTB Proxy Targets

Specify what xTB should screen.

Examples:

- geometry convergence and obvious strain;
- relative conformer trend within same molecule;
- HOMO/LUMO/gap proxy;
- dipole moment proxy;
- dimer/stacking proxy with explicitly fixed stoichiometry.
- capped oligomer geometry/electronics proxy with stated `n` and end groups.

## Non-xTB Targets

List claims that xTB must not be used to prove.

Examples:

- binding constant;
- self-assembly morphology;
- polymer molecular weight, dispersity, crystallinity, Tg, modulus, morphology, conductivity, or degradation rate;
- reaction yield;
- photochemical quantum yield;
- selectivity in solution.

## NMR Prediction and Verification

- NMR prediction: yes / no (default: no; auto-enabled when experimental NMR data is provided)
- NMR solvent assumption: CDCl3 / DMSO-d6 / D2O / other
- Experimental NMR data file: (path to experimental NMR peak list, or leave blank)
- NMR verification threshold for structural confidence: confirmed / consistent (default: consistent)

## Iteration Budget

- Max rounds:
- Max xTB jobs per round:
- Stop condition:

## Output Preference

- Number of final candidates:
- Need ChemDraw drawing checklist: yes/no
- Need synthesis risk notes: yes/no
