# Zotero Extraction Protocol (Step 1.5-A)

Extract design knowledge from the user's personal Zotero library. Goal: turn the curated collection into a structured knowledge base — scaffolds studied, SAR context, synthesis routes, failure modes.

Zotero reflects what the user has encountered, not the full field. Absence from Zotero is not evidence of absence.

## A.1 Search the Zotero library

Use `mcp__zotero-mcp__zotero_search_items` with `qmode: "everything"` for:

- the scaffold or compound class (e.g., "cyclic peptide", "photoswitch", "BODIPY", "MOC");
- the target property (e.g., "HOMO-LUMO gap", "self-assembly", "ion transport", "fluorescence");
- the application area (e.g., "drug delivery", "OPV", "antibacterial", "membrane");
- the key reaction type or polymerization route if relevant.

Run **3-5 distinct keyword searches**. De-duplicate results by item key.

If Zotero is unavailable (tool call fails), skip this sub-step silently, log `zotero_status: unavailable` in `DESIGN_LOOP_STATE.json`, and rely on the active search stream (1.5-B) alone.

## A.2 Retrieve metadata

Call `mcp__zotero-mcp__zotero_item_metadata` for each matched paper (up to `ZOTERO_METADATA_LIMIT = 30`).

Extract from metadata: `title`, `authors`, `year`, `journal`, `DOI`, and abstract scan for scaffold names, SMILES/InChI strings, property values, synthesis reactions, known failures.

Score each paper for **structural richness**: papers mentioning specific molecules, SMILES, measured properties, or synthesis yields score highest.

## A.3 Read full text of the most structurally rich papers

Call `mcp__zotero-mcp__zotero_item_fulltext` for the top **5-8 papers** by structural richness score.

Extract:

**Scaffolds and seed structures:**
- Named compound series and structural descriptions
- Explicit SMILES, InChI, or structural formulae
- Core scaffold motifs defining the compound family
- Control/benchmark compounds and their measured properties

**SAR rules:**
- "Modification X at position Y → effect Z on property W"
- Substituent patterns that improved or failed the target property
- Electronic, steric, or geometric design principles

**Synthesis knowledge:**
- Reaction types (named reactions, coupling methods, protecting group strategies)
- Key reagents, solvents, temperatures, yields
- Polymerization routes, monomer sources, DP/dispersity when relevant

**Failed motifs and warnings:**
- Structures or groups that caused instability, poor yield, or unwanted reactivity
- Assay artifacts, promiscuous binders, aggregators

**Experimental benchmarks:**
- Measured property values (IC50, ε, Φ, Tg, conductivity, etc.)
- Characterization methods (NMR, HRMS, X-ray, DLS, TEM, etc.)
- Success thresholds implicit in the paper's conclusions

## A.4 Write ZOTERO_KNOWLEDGE_PACKET.md

Write `molecule-design-stage/ZOTERO_KNOWLEDGE_PACKET.md`:

```markdown
# Zotero Knowledge Packet

## Research Theme Identified
[1-2 sentence summary]

## Papers Consulted
| item_key | title | year | journal | structural_richness |
|---|---|---|---|---|

## Known Scaffolds and Seed Structures
| name | description | smiles_or_formula | source_paper | experimental_status |
|---|---|---|---|---|

## SAR Rules Extracted
| modification | position | effect_on_property | confidence | source_paper |
|---|---|---|---|---|

## Synthesis Knowledge Base
| reaction_type | conditions_summary | yield_range | source_paper | applicable_to |
|---|---|---|---|---|

## Failed Motifs and Warnings
| motif_or_condition | failure_mode | source_paper |
|---|---|---|

## Experimental Benchmarks
| compound | property | value | unit | method | source_paper |
|---|---|---|---|---|---|

## Design Principles from Literature
[Bulleted list of key design principles]

## Gaps and Open Questions
[Topics absent or weakly covered in Zotero — passed to 1.5-B active search]
```

## A.5 Write ZOTERO_SEED_SMILES.csv

Columns: `name`, `smiles`, `source_paper_key`, `source_paper_title`, `experimental_status` (`synthesized_reported` / `commercially_available` / `hypothetical` / `unknown`), `reported_property`, `role` (`seed_scaffold` / `positive_control` / `negative_control` / `benchmark` / `failed_motif`).

If a paper describes a structure but gives no SMILES, generate one from the description and mark `smiles_source: inferred_from_description`. If unreliable, leave blank and mark `smiles_source: unavailable`.

## A.6 Update the locked design spec

After extraction:
- Populate `seed_scaffolds` in `DESIGN_SPEC_LOCKED.md` with structures from `ZOTERO_SEED_SMILES.csv` that match the design goal.
- Add Zotero-sourced `forbidden_motifs` to the spec's forbidden list.
- Note in `DESIGN_SPEC_LOCKED.md` that these were Zotero-sourced, not invented.

If the design spec was empty and Zotero reveals a clear research theme, propose a pre-populated spec and wait for user confirmation before expensive steps.
