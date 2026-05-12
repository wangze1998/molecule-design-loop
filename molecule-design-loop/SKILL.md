---
name: "molecule-design-loop"
description: "Autonomous molecule design loop from a Markdown design constraint file. Reads local literature/Zotero context and recent online literature, proposes SMILES candidates, filters with RDKit-style checks, renders an HTML candidate gallery, requires user structural approval before xTB, runs xTB screening when available as objective evidence, asks Gemini to score candidates against the design constraints, and iterates candidate design."
---

# Molecule Design Loop

Use this skill when the user provides a molecule design constraint file and wants an autonomous loop:

`design_spec.md -> literature packet -> SMILES candidates -> RDKit filtering -> RDKit HTML gallery -> user structural approval -> xTB screening as evidence -> Gemini constraint scoring -> next design round`

This is the molecular-design analogue of `auto-review-loop`.

## Role Split

- Codex orchestrates files, scripts, filters, xTB jobs, tables and iteration.
- Gemini/gemini-research performs literature discovery and external design critique when available.
- RDKit performs deterministic molecule parsing, deduplication and descriptor checks.
- xTB provides low-cost computational proxies only.
- Gemini performs the final candidate scoring against the locked design constraints.
- The user remains the scientific owner of final synthesis decisions.

Do not treat xTB as proof of binding, assembly, reactivity, selectivity, or mechanism.

## Inputs

Primary input:

- a Markdown design constraint file, usually `design_spec.md`

Optional inputs:

- seed SMILES or ChemDraw-selected SMILES;
- local PDFs, notes, Zotero tags, prior design logs;
- known failed motifs;
- desired xTB proxy metrics;
- project-local xTB runner scripts.

If no design file exists, create one from `templates/design_spec_template.md` and ask the user to fill missing hard constraints before launching expensive calculations.

## Output Layout

Use a project-local directory:

- `molecule-design-stage/DESIGN_SPEC_LOCKED.md`
- `molecule-design-stage/LIT_PACKET.md`
- `molecule-design-stage/ROUND_N_CANDIDATES.csv`
- `molecule-design-stage/ROUND_N_FILTERED.csv`
- `molecule-design-stage/ROUND_N_CANDIDATE_GALLERY.html`
- `molecule-design-stage/ROUND_N_XTB_APPROVAL.md`
- `molecule-design-stage/ROUND_N_XTB_RESULTS.csv`
- `molecule-design-stage/ROUND_N_GEMINI_INPUT.md`
- `molecule-design-stage/ROUND_N_DECISION.md`
- `molecule-design-stage/DESIGN_LOOP_STATE.json`
- `molecule-design-stage/DESIGN_REPORT.md`
- `molecule-design-stage/xtb_jobs/`

Bundled helpers:

- `scripts/rdkit_filter_candidates.py` annotates and filters candidate CSV files with RDKit descriptors.
- `scripts/render_candidate_gallery.py` renders candidate CSV rows into a standalone RDKit HTML gallery.
- `references/candidate_schema.md` defines the CSV contracts.
- `templates/design_spec_template.md` is the starting constraint file template.
- `templates/xtb_approval_template.md` is the manual approval checkpoint template before xTB.

If a local `research-wiki/` exists, also update:

- `research-wiki/design-log.md`
- `research-wiki/events.jsonl`

Use the shared event schema in `../shared-references/events-jsonl.md` when logging.

## Helper Script Rules

If the workflow needs a new helper program for auxiliary calculations, preprocessing, postprocessing, or report assembly:

- prefer the pattern `one main entrypoint + reusable modules + per-run input config only` (`一个主入口 + 可复用模块 + 每次只写输入配置`);
- keep the reusable logic needed for later runs of the same workflow;
- do not hard-code the script to one round number, one molecule, one file path, one threshold set, or one temporary local layout unless the user explicitly asks for a one-off throwaway script;
- prefer parameterized inputs, documented CLI flags, and stable CSV/Markdown contracts so the same script can be reused in later rounds;
- when possible, read evolving constraints from workflow files such as `DESIGN_SPEC_LOCKED.md`, `ROUND_N_FILTERED.csv`, or other stage artifacts instead of baking those values into code.

## Constants

- **MAX_ROUNDS = 3**
- **INITIAL_CANDIDATES = 20-50**
- **MAX_XTB_PER_ROUND = 10-20**
- **PRIMARY_LITERATURE_BASE = `Zotero/local papers first`**
- **RECENT_CORRECTION = `3-5 recent papers`**
- **XTB_LEVEL = `GFN2-xTB` unless the design file says otherwise**
- **STOP_IF_NO_NEW_FEASIBLE_MOTIF = true**
- **CHEMDRAW_ROLE = optional visualization/input terminal**

## Workflow

### 1. Lock the design spec

Read the Markdown constraint file and produce `DESIGN_SPEC_LOCKED.md`.

Separate:

- `hard_constraints`: must not be violated;
- `soft_preferences`: optimize if possible;
- `forbidden_motifs`: reject if present;
- `seed_scaffolds`: preserve or modify according to the design goal;
- `allowed_elements`, charge range, size range, solubility and stability limits;
- `xTB_proxy_targets`: what xTB can reasonably test;
- `non_xTB_targets`: properties that must not be inferred from xTB alone.

If a hard constraint is ambiguous, stop and ask a targeted question before running xTB.

### 2. Build a literature packet

Use `/research-lit` or `gemini-research` first.

Prioritize:

- local Zotero/library papers related to the scaffold, recognition motif, photoswitch, host-guest system, self-assembly, or material class;
- local project notes and design logs;
- `3-5` recent external papers not already in the local core set.

Write `LIT_PACKET.md` with:

- useful structural motifs;
- motifs known to fail;
- synthesis or stability warnings;
- computational proxy ideas;
- benchmark molecules and why they matter.

### 3. Generate SMILES candidates

Generate `20-50` candidates in `ROUND_N_CANDIDATES.csv`.

Required columns:

- `candidate_id`
- `smiles`
- `parent_or_seed`
- `design_move`
- `target_constraint`
- `rationale`
- `expected_proxy_effect`
- `risk`
- `source_hint`

Rules:

- Every molecule must have a valid SMILES string.
- Every candidate must be tied to at least one design constraint.
- Include control candidates when useful.
- Avoid pure novelty theater: design moves should be chemically interpretable.

Generate candidates in structured buckets instead of one undifferentiated list:

- `10-20%` conservative controls close to trusted seeds;
- `50-70%` directional edits that test one primary hypothesis each;
- `10-30%` bounded exploratory variants that still respect scaffold-level constraints.

Prefer mutation-style proposal families before free-form invention:

- substituent electronics tuning;
- linker rigidification or flexibilization;
- heteroatom walk or polarity rebalance;
- steric twist introduction;
- motif replacement that preserves the core hypothesis.

Avoid filling a round with many near-isomorphic variants. One candidate should primarily test one interpretable design move.

### 4. Run deterministic filtering

Use RDKit when available.

Prefer the bundled helper:

```bash
python3 "$CODEX_HOME/skills/molecule-design-loop/scripts/rdkit_filter_candidates.py" \
  molecule-design-stage/ROUND_N_CANDIDATES.csv \
  molecule-design-stage/ROUND_N_FILTERED.csv
```

Pass constraints from `DESIGN_SPEC_LOCKED.md` as arguments when applicable, for example `--allowed-elements`, `--min-mw`, `--max-mw`, `--max-rotatable`, and repeated `--forbidden-smarts`.

When the design brief calls for medicinal chemistry style triage, also pass relevant thresholds such as:

- `--min-qed`
- `--max-logp`
- `--max-tpsa`
- `--max-hba`
- `--max-hbd`
- `--min-fsp3`
- `--max-sa-score`
- `--max-medchem-alerts`
- `--reject-pains`
- `--reject-brenk`
- `--reject-scaffold-duplicates`

Filter or annotate:

- invalid SMILES;
- duplicates and near-duplicates;
- formula, exact mass, molecular weight;
- charge and atom composition;
- rotatable bonds and rough flexibility;
- aromatic ring count and pi-surface proxy;
- QED, cLogP, TPSA, HBA/HBD, fractionCSP3, heavy atom count and SA score when available;
- Murcko scaffold identity for diversity-aware selection;
- PAINS and Brenk alerts as medicinal-chemistry warnings or hard filters when requested;
- forbidden SMARTS motifs if specified;
- obvious synthetic or stability red flags.

Write `ROUND_N_FILTERED.csv`.

Keep rejected candidates with a rejection reason; they are useful for later meta-optimization.

### 5. Render an HTML candidate gallery

Before any xTB job selection, render the round candidates into an HTML gallery for quick visual inspection.

Prefer the bundled helper:

```bash
python3 "$CODEX_HOME/skills/molecule-design-loop/scripts/render_candidate_gallery.py" \
  molecule-design-stage/ROUND_N_FILTERED.csv \
  molecule-design-stage/ROUND_N_CANDIDATE_GALLERY.html \
  --title "Round N Candidate Gallery"
```

The gallery should:

- use RDKit depictions, not plain text-only tables;
- show `candidate_id`, structure, SMILES, filter decision, filter reason and key rationale fields;
- preserve rejected candidates so visual review can spot false negatives or duplicate-heavy rounds;
- be produced before any xTB run starts.

If the user wants manual inspection, point them to `ROUND_N_CANDIDATE_GALLERY.html` before launching xTB.

### 6. Get explicit user structural approval before xTB

After generating `ROUND_N_CANDIDATE_GALLERY.html`, stop and ask the user to confirm that the candidate structures do not show obvious structural problems worth blocking xTB.

Write `ROUND_N_XTB_APPROVAL.md` using `templates/xtb_approval_template.md`.

This checkpoint is mandatory:

- do not start xTB until the user explicitly approves the round or a narrowed subset of candidate IDs;
- if the user flags structural issues, record them and revise the candidate list first;
- if only some candidates are approved, xTB may run only on the approved subset;
- if the user gives no approval yet, the workflow pauses here rather than continuing automatically.

The approval request should be short and concrete:

- point the user to `ROUND_N_CANDIDATE_GALLERY.html`;
- summarize any model-detected structural concerns from RDKit output;
- ask whether there are any blocking structural issues before xTB starts.

Update `DESIGN_LOOP_STATE.json` with the approval status and approved candidate IDs before moving on.

### 7. Select xTB jobs

Select at most `MAX_XTB_PER_ROUND` candidates.

Prefer:

- candidates explicitly approved by the user for xTB;
- candidates satisfying all hard constraints;
- chemically diverse design moves and Murcko scaffolds;
- one or two conservative controls;
- candidates with useful disagreement between intuition and descriptor filters.

Before running:

- check `which xtb`;
- search project scripts for existing xTB runners;
- if xTB is not on PATH, report the blocker and still produce candidate/filter files.

Do not silently skip xTB and pretend validation happened.

### 8. Run xTB screening

When xTB is available, run the smallest useful calculation first.

Default proxy outputs:

- optimization status;
- final energy;
- HOMO, LUMO and gap when available;
- dipole moment when available;
- geometry sanity;
- convergence failure reason;
- optional conformer or dimer proxy if specified.

Write `ROUND_N_XTB_RESULTS.csv` and keep raw files under `xtb_jobs/round_N/`.

### 9. Score candidates against constraints with Gemini

Create `ROUND_N_DECISION.md`.

Gemini should read `DESIGN_SPEC_LOCKED.md` first and score candidates against that document, not against raw xTB outputs.

Use xTB only as objective evidence for xTB-addressable constraints:

- xTB numbers can support or weaken a claim;
- xTB must not directly assign the rank or score;
- if xTB is missing, Gemini should still score from the design document, literature packet and deterministic filters, while marking the missing evidence clearly.

Gemini scoring rubric:

- `5`: passes hard constraints, strongly matches the design brief, and available RDKit/xTB evidence is aligned.
- `4`: passes hard constraints and looks strong, but has one moderate evidence gap or tradeoff.
- `3`: partially aligned and worth revision, not immediate promotion.
- `2`: weak alignment or meaningful red flags, only keep with a specific rescue hypothesis.
- `1`: fails the design intent, should be killed or retained only as a negative control.

Gemini should explicitly separate:

- hard-constraint gate;
- soft-preference alignment;
- evidence confidence;
- unsupported claims and remaining uncertainty.

For each candidate, Gemini must produce:

- `gemini_constraint_score`: `1-5`, where `5` means strongest overall alignment to the locked design constraints;
- `pass_hard_constraints`: yes/no;
- `xTB_status`: pass/warn/fail/not_run;
- `supported_design_claim`: what the result actually supports;
- `unsupported_claims`: what must not be inferred;
- `gemini_score_reason`: short explanation tied to the design constraints;
- `next_action`: keep / revise / kill / control / needs_higher_level_calc;
- `revision_hint`: concrete next modification.

Use a result-to-constraint gate. Do not let a pretty xTB output override a violated hard constraint, and do not let xTB become the scorer.

### 10. Iterate

For the next round, generate candidates by modifying failure modes:

- too flexible -> add rigidity or shorten linker;
- too planar -> add steric twist or interrupt conjugation;
- too polar/nonpolar -> adjust substituents or ionizable groups;
- poor gap proxy -> tune donor/acceptor strength;
- geometry collapse -> reduce steric clash or change connection point;
- violates forbidden motif -> replace motif, not just decorate it.

Carry forward:

- kept candidates;
- killed motifs and reasons;
- literature warnings;
- xTB failure modes.

Update `DESIGN_LOOP_STATE.json` with a compact reusable memory:

- successful design moves;
- repeated failure motifs;
- scaffold families already explored;
- evidence gaps that blocked confident scoring;
- hypotheses worth revisiting with better tools.

### 11. Stop and report

Stop when one of these happens:

- at least `3-5` candidates satisfy the hard constraints, receive strong Gemini constraint scores, and have supporting xTB proxy evidence when that proxy is relevant;
- no new feasible motif appears for one full round;
- xTB is unavailable and the user needs to configure the compute backend;
- `MAX_ROUNDS` is reached.

Write `DESIGN_REPORT.md` with:

- top candidates and SMILES;
- why they satisfy the design file;
- xTB proxy summary;
- Gemini constraint scoring summary;
- risks and what not to claim;
- recommended next experiment or higher-level calculation;
- ChemDraw drawing checklist if manual structure drawing is needed.

## xTB Integrity Rules

- Record exact command, version, charge, multiplicity and input geometry source.
- Never compare energies across different stoichiometries as if they were direct stability rankings.
- Treat failed optimizations as evidence, not as missing data.
- Mark conformer sensitivity if only one geometry was tested.
- For host-guest, assembly or dimer proxies, write the proxy definition explicitly.

## Chemistry Design Rules

Prefer chemically interpretable edits:

- electronic tuning;
- steric tuning;
- linker length/rigidity;
- pi-surface modulation;
- heteroatom placement;
- charge-state control;
- solubility handle;
- control molecule design.

Avoid candidates that only look novel but do not test a clear hypothesis.

## ChemDraw Integration

Use ChemDraw as an optional structure input/output layer:

- read selected structure SMILES through `chemdraw-mcp` when useful;
- use ChemDraw to inspect final structures manually;
- do not depend on ChemDraw GUI automation for the core loop.

## Invocation Examples

```text
/molecule-design-loop "/path/to/design_spec.md"
/molecule-design-loop "design_spec.md -- rounds: 2 -- max-xtb: 8"
/molecule-design-loop "design a DTE-naphthyl linker series from design_spec.md"
```

## Success Condition

The skill is successful when it produces:

- valid candidate SMILES;
- a transparent reason for every design move;
- deterministic filter results;
- an RDKit-rendered HTML gallery before xTB selection;
- an explicit user approval checkpoint before any xTB run starts;
- xTB results or a clear xTB availability blocker;
- a Gemini-scored iteration decision that narrows the design space rather than restarting randomly.
