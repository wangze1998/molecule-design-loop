# Novelty Check Protocol (Step 5.5)

Mandatory. Runs after synthesis feasibility gate, before the HTML gallery.

## Prior art search call

```
tool: mcp__gemini-research__prior_art_search_start (async)
poll: mcp__gemini-research__literature_search_status

query: [for each candidate: name/SMILES description + design context from ROUND_N_SYNTHESIS_FEASIBILITY.csv]
domain: [scaffold class from design spec, e.g. "cyclic peptide", "BODIPY dye", "DTE photoswitch"]
notes: "Check whether each described structure has been previously reported. Flag exact matches and close structural analogs (scaffold + key substituents identical). Report the original paper DOI when a match is found."
```

## Output: ROUND_N_NOVELTY_CHECK.md

```markdown
# Round N — Novelty Check

| candidate_id | prior_art_status | closest_known_structure | source_doi | novelty_delta | recommendation |
|---|---|---|---|---|---|
```

## prior_art_status values

- `novel` — no close structural match found
- `analog` — similar scaffold reported; the specific modification is new
- `known` — structure matches a reported compound; promote only as a control candidate
- `uncertain` — insufficient information; flag for manual check

Also add `prior_art_status` and `source_doi` columns to `ROUND_N_SYNTHESIS_FEASIBILITY.csv`.

## Rules

- `known` → downgrade to `role: control`; cannot be promoted as a novel candidate.
- `analog` → retain promotion status but cite the prior analog in `source_hint`.
- `uncertain` → flag and let the user decide at the gallery step; do not block.
