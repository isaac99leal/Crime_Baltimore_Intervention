# Identity batch 2 — 2026-09-07

Base: PR #79, commit `995325e08bbc6132f48be490d872282bb713a618`. Its GitHub audit run `34155256964` passed before this batch began.

| Literal Adelaide name | VIVC ID | Decision |
| --- | ---: | --- |
| Trebbiano Toscano | 12628 | R5: reviewed exact identity |
| Alicante Henri Bouschet | 304 | R5: reviewed exact identity |
| Prosecco | 9741 | R5: reviewed exact identity |
| Mazuelo | 2098 | R4: reviewed synonym chain |
| Côt | 2889 | R2: candidate; spelling evidence still required |

The first three mappings use the [GrapeGen 06 Annex 2B, version 18 March 2011](https://openpub.fmach.it/retrieve/e1dbfeaa-5e0a-4ac9-e053-1705fe0a1c61/ANNEX_2B_V3-4.pdf), pages 9, 5 and 50. This is a historical registry cross-reference, not a claim of fresh VIVC passport access. Source text was retrieved; the local PDF download returned HTTP 403. Page images could not be inspected through the available tool output. The extracted entries provide explicit names and IDs.

Mazuelo uses a two-document chain: [BOE-A-2023-14681](https://www.boe.es/buscar/doc.php?id=BOE-A-2023-14681), article two, subsection four, lists Mazuelo with Mazuela. GrapeGen page 37 maps Mazuela to ID 2098. This is recorded as a reviewed synonym, not an exact name match. No legal permissions are introduced from the Spanish list.

GrapeGen page 18 maps Cot to ID 2889. The circumflex in the census name is not confirmed by the retrieved registry text, so Côt stays a candidate. No automatic accent-based promotion is permitted.

Related names remain unreviewed in the Adelaide namespace. In particular, this batch does not add generic Trebbiano, Biancame, Ugni Blanc, Alicante Bouschet, Prosecco lungo, Glera, Mazuela or Carignan source links. The historical Prosecco prime name is kept as reported by GrapeGen. Parentage is not inferred.

## Coverage and checks

The new report is `variety_identity_coverage_batch2.json`; the prior integration report remains a historical snapshot. Reproduce with `python scripts/variety_identity_coverage.py --output <path>`.

There are 63 R5 rows, one R4 row, one R2 row and 1,933 R1 rows. The 64 confirmed rows cover 3,122,426.221 of 4,537,455.448 reported positive hectares in 2023: **68.8145%**. This adds 303,140.318 hectares of reviewed coverage. There are now 29 unresolved source rows above 10,000 hectares. Aggregate categories remain in these counts.

All 45 identity and coverage tests pass. Tests check unrelated census namespaces, related names, aggregate categories, the Côt candidate, R4 accounting and the new input hash. The knowledge catalog audit also passes. GitHub runs the complete suite for the published PR.

Next: obtain explicit Côt spelling evidence, then review Muscat Blanc à Petits Grains and the unresolved Catarratto Bianco record. Keep botanical evidence separate from legal appellation rules.
