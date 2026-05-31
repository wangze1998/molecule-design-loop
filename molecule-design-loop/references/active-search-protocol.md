# Active Search Protocol (Step 1.5-B)

Runs in parallel with Step 1.5-A. Always mandatory, regardless of Zotero results.

Goal: surface papers the user may not have in their library — very recent publications, landmark reviews, highly-cited foundational works, and papers from adjacent fields with transferable methods.

Use `gemini-research`, WebSearch, or `/research-lit`.

## Three Search Targets

**1. Latest papers (last 1-2 years)**
- Search for the specific scaffold class, recognition motif, or material type from the design spec.
- Target venues: Nature, Science, Nature Chemistry, Nature Materials, JACS, Angewandte Chemie, ACS Nano, Chemical Science, Advanced Materials, Chem.
- Goal: 5-8 papers published after the most recent Zotero paper on the same topic.

**2. Authoritative and highly-cited works**
- Search for landmark reviews or perspectives (e.g., "cyclic peptide nanotube review", "OPV morphology design principles").
- Include 1-2 papers with >200 citations that define the field's design consensus.
- If already in Zotero, mark `also_in_zotero: true` and skip re-extraction.

**3. Topics flagged as absent in 1.5-A**
- For each topic in the "Gaps and Open Questions" section of `ZOTERO_KNOWLEDGE_PACKET.md`, run one targeted search.

## Extraction

For each paper found, extract the same structured fields as in 1.5-A.3 (scaffolds, SAR rules, synthesis routes, failed motifs, benchmark values). Mark `source: active_search` to distinguish from Zotero-sourced knowledge. Record `citation_count` or `venue_tier` as a proxy for authority when available.

## Output

Write `molecule-design-stage/ACTIVE_SEARCH_PACKET.md` using the same section structure as `ZOTERO_KNOWLEDGE_PACKET.md`.
