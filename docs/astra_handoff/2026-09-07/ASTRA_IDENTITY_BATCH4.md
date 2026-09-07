# Identity batch 4 — 2026-09-07

Base PR #81 passed GitHub CI at `f742981fb98ec9b506a8fc686b1157f66da31819` (run 34157110564).

This batch adds 22 confirmed source links: 21 R5 mappings and one R4 synonym chain for Tribidrag. There are now 96 confirmed global census rows, covering **79.6767%** of reported positive 2023 hectares. The report records 94 R5, two R4, one R2, one R0 and 1,900 R1 rows. All 1,998 observations remain present.

The [UC Davis Foundation Plant Services record](https://fps.ucdavis.edu/FGRfamilies.cfm?varietyid=1634), selection Zinfandel 42.1, documents the Tribidrag/Zinfandel/Primitivo connection. [GrapeGen Annex 2B](https://openpub.fmach.it/retrieve/e1dbfeaa-5e0a-4ac9-e053-1705fe0a1c61/ANNEX_2B_V3-4.pdf), version 18 March 2011, provides the historical ID 9703. The prime name is retained as that source reports it. Clone differences are not erased.

The other mappings retain exact census spellings and source page numbers. Isabella, Moldova and Bianca retain the source's interspecific-cross classification; they are not changed to Vitis vinifera. Parentage and legal permissions are not inferred.

## First registered conflict

GrapeGen page 45 lists Pamid twice with different IDs and colors: 17323 and 17324. Both assertions are retained at R0. The resolver returns CONFLICT with no canonical ID, and the coverage report emits a blocking conflict entry. This is ambiguity in the retrieved source for the census name, not a claim that all Pamid plantings are unidentifiable.

The regression checks distinguish Pedro Ximénez from Pedro Giménez, Corvina from Corvinone, and white varieties from related colored forms. The older Nebbiolo negative test now checks an unreviewed census namespace; the reviewed Adelaide name has positive coverage.

Catarratto remains under scope review. The publisher search index for [Crespan et al.](https://ojs.openagrar.de/index.php/VITIS/article/view/4185) reports synonymy work with SSR markers, but direct full-text retrieval failed. No new phenotype or registry merger is asserted from that partial retrieval.

## Validation and continuation

All 54 identity and coverage tests pass. The knowledge catalog audit passes. The dated report is `variety_identity_coverage_batch4.json`; older reports remain historical snapshots.

Eight unresolved source rows exceed 10,000 hectares in 2023; this count includes aggregate categories such as “other”. Next research should address the remaining named high-area rows and the Pamid source ambiguity. Botanical identification remains separate from appellation and vintage rules.
