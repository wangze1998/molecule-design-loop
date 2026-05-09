# Molecule Design Spec

## Goal

Design a small candidate series that modifies a photoswitchable aromatic linker to improve a defined xTB-screenable proxy while keeping the molecule chemically interpretable.

## Scientific Hypothesis

Changing the linker rigidity, aromatic surface, or electronic character can tune the preferred geometry and electronic gap proxy without destroying the core photoswitchable motif.

## Seed Structures

| name | SMILES | role | keep / modify / avoid |
|---|---|---|---|
| seed_1 |  | parent scaffold | modify |

## Hard Constraints

- Allowed elements: C,H,N,O,S,F,Cl,Br,I
- Charge range: neutral preferred
- Molecular weight range: define before running xTB
- Required motifs: define the core motif that must remain
- Forbidden motifs: unstable, reactive, or synthetically unrealistic groups
- Required scaffold features: preserve the core recognition/photoswitch module
- Solubility or handling constraints: add if known
- Synthetic accessibility constraints: avoid excessive step count or unstable intermediates

## Soft Preferences

- Electronic character: tune donor/acceptor strength without overpolarizing the molecule
- Rigidity/flexibility: compare rigidified and flexible linker variants
- Pi-surface: tune aromatic contact area
- Steric profile: avoid obvious clashes near the recognition interface
- Hydrogen bonding: add only if it matches the design hypothesis
- Photochemical or redox preference: keep as a qualitative constraint unless real data exist
- Control molecules needed: include conservative and negative-control variants

## Literature Anchors

Use local Zotero papers and recent literature related to the scaffold, photoswitch, host-guest motif, or assembly mechanism.

## xTB Proxy Targets

- geometry convergence and obvious strain;
- HOMO/LUMO/gap proxy;
- dipole moment proxy;
- optional conformer trend within the same molecule.

## Non-xTB Targets

xTB should not be used to prove:

- binding constant;
- self-assembly morphology;
- reaction yield;
- photochemical quantum yield;
- selectivity in solution.

## Iteration Budget

- Max rounds: 2
- Max xTB jobs per round: 8
- Stop condition: at least 3 candidates pass hard constraints and the requested xTB proxy, or no new feasible design motif appears.

## Output Preference

- Number of final candidates: 3-5
- Need ChemDraw drawing checklist: yes
- Need synthesis risk notes: yes
