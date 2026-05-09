# Molecule Design Spec

## Goal

Describe the target molecule family and the property you want to improve.

## Scientific Hypothesis

State the design hypothesis in one or two sentences.

## Seed Structures

| name | SMILES | role | keep / modify / avoid |
|---|---|---|---|
| seed_1 |  |  |  |

## Hard Constraints

- Allowed elements:
- Charge range:
- Molecular weight range:
- Required motifs:
- Forbidden motifs:
- Required scaffold features:
- Solubility or handling constraints:
- Synthetic accessibility constraints:

## Soft Preferences

- Electronic character:
- Rigidity/flexibility:
- Pi-surface:
- Steric profile:
- Hydrogen bonding:
- Photochemical or redox preference:
- Control molecules needed:

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

## Non-xTB Targets

List claims that xTB must not be used to prove.

Examples:

- binding constant;
- self-assembly morphology;
- reaction yield;
- photochemical quantum yield;
- selectivity in solution.

## Iteration Budget

- Max rounds:
- Max xTB jobs per round:
- Stop condition:

## Output Preference

- Number of final candidates:
- Need ChemDraw drawing checklist: yes/no
- Need synthesis risk notes: yes/no
