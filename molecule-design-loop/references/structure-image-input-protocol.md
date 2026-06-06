# Structure Image Input Protocol

Claude can parse chemical structure images (journal figures, hand-drawn sketches, ChemDraw screenshots, patent drawings) directly into SMILES. This eliminates the requirement for users to manually redraw or export SMILES from external tools.

## When to use

- User provides a PNG/JPG/PDF screenshot containing molecular structures instead of SMILES
- User references "the structure in Figure 2" from a paper
- User pastes a photo of a hand-drawn structure
- User wants to seed the design loop from a literature figure without manual SMILES entry

## Input formats

- PNG, JPG, or PDF containing one or more chemical structures
- ChemDraw screenshot or exported image
- Journal figure crop (single structure or a scheme with multiple structures)
- Hand-drawn structure photo (legible line drawings)

## Extraction procedure

1. Read the image using the `Read` tool (which supports image files natively).
2. For each structure in the image:
   - Identify the molecular graph: atoms, bonds, stereochemistry, charges, isotope labels.
   - Generate a canonical SMILES string.
   - Assign a provisional name from any label in the image (e.g., "compound 3a", "monomer A"), or `image_structure_N` if unlabeled.
   - Note confidence: `high` (unambiguous clean drawing), `medium` (some ambiguity in substituents or stereo), `low` (hand-drawn, partial, or occluded).
3. Write extracted structures to `molecule-design-stage/IMAGE_EXTRACTED_SMILES.csv`.

## IMAGE_EXTRACTED_SMILES.csv columns

- `structure_id`: sequential ID or label from image
- `smiles`: canonical SMILES
- `source_image`: filename of the input image
- `source_description`: "Figure 2 from DOI:10.xxxx" or "hand-drawn sketch" etc.
- `extraction_confidence`: high / medium / low
- `stereochemistry_resolved`: yes / partial / no
- `ambiguity_notes`: any unresolved features (e.g., "R-group not specified", "stereo at C3 unclear")

## Validation

- Parse every extracted SMILES with RDKit (`Chem.MolFromSmiles`) to confirm validity.
- If RDKit rejects a SMILES, flag it and attempt correction (common errors: missing ring closure, wrong valence, aromatic kekulization).
- For structures with R-groups or Markush notation, extract the core scaffold only and note the variable positions.

## Integration with the design loop

- Extracted structures feed into `seed_scaffolds` in `DESIGN_SPEC_LOCKED.md` (same as Zotero seeds or user-supplied SMILES).
- Mark `smiles_source: image_extraction` and `extraction_confidence` in the seed table.
- If confidence is `low`, present the extracted SMILES to the user for confirmation before proceeding to candidate generation.
- Medium-confidence extractions proceed but are flagged in the gallery for user review.

## Limitations

- Complex polymeric structures, metallocenes, or extended MOF/COF nets cannot be fully captured as single SMILES; extract the monomer or building-block unit instead.
- Reaction schemes: extract reactants and products separately, not the arrow notation.
- Low-resolution or heavily annotated images may produce unreliable results; always validate with RDKit.
