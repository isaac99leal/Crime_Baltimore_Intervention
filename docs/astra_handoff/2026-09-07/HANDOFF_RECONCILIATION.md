# Foundation continuation — 2026-09-07

Base: `08503d6b91350397daebd0ec3183f243dc8c4a5f` on
`claude/somm-simulator-game-KQpS7`. Work branch:
`foundation/astra-identity-reconciliation-2026-09-07`.

The September 6 Library handoff, reconciliation seed, checkpoint archive, and
live repository were recovered. The prior conversation search did not return
the full progress-chat transcripts. The detailed handoff and actual code are
the basis for this continuation. Do not restart the project.

## Implemented

- The expanded catalog no longer merges newly ingested names by accent or
  punctuation folding. Exact source spellings are retained. A normalized key
  with several candidates cannot return an arbitrary winner.
- Existing base profiles and their declared aliases remain available. An
  accent-folded census match cannot silently add cultivation tags to a base
  profile. This does not certify the older base catalog's identity clusters;
  its legacy union-find remains a separate review task.
- Stable, distinct IDs are assigned to colliding new names. IDs do not depend
  on which colliding source row is processed first. Repeated identical source
  rows remain separate observations, without inventing separate varieties.
- Area queries do not pool different spellings merely because they normalize
  to the same key. Country and source-row provenance are retained.
- All 4,807 country-source rows survive ingestion: 4,705 have a usable country;
  102 are retained in `unresolved_country_area`. They do not establish planting
  in any country. All 1,998 world-source rows remain available.
- `variety_identity.py` provides source-scoped R0–R5 decisions. R4/R5 requires
  a reviewed assertion for the exact source name, canonical identity, relation,
  country scope, and source. Conflicts return no canonical identity. Search
  normalization can only produce a candidate. Identity never supplies GI
  permission. The expanded catalog exposes this through
  `resolve_variety_identity()` independently of profile lookup.
- `reconcile_astra_handoff.py` emits a complete structural Burgundy comparison,
  a first 250-row identity evidence evaluation, all 14 census collision groups,
  the 102 unresolved-country observations, and input hashes.

The expanded catalog contains 2,222 profile/observation records after this
change, versus 2,193 at the base commit. **This is not a claim of 2,222 distinct
botanical varieties.** There are 29 ambiguous catalog search keys. The 14
census collision groups include two groups with identical repeated spellings.

## Repository reconciliation

| Handoff domain | Existing implementation | This continuation |
| --- | --- | --- |
| Identity and census | `catalog.py`, `expanded_catalog.py`, census CSVs | Correct new-name collisions; retain unresolved countries; add reviewed-link resolver |
| Burgundy GC/PC | `vineyard_registry.py`, `legal_specs.py`, `site_claims.py` | Map every handoff row; retain conflicts and gaps |
| Historical legal rules | `legal_specs.py`, legal amendments, exact-date tests | Existing implementation retained; no new law asserted |
| Vineyard, vintage, harvest | `vineyard_engine.py`, `vintage_engine.py`, `harvest_lot.py`, `harvest_must.py` | Existing implementation retained; workbook proposals remain future deltas |
| Fermentation and chemistry | Fermentation, extraction, blend, and fortification modules | Existing implementation retained; no parallel workbook engine |
| Maturation and inventory | Maturation, packaging, bottling, lifecycle, provenance modules | Existing implementation retained |

## Burgundy findings

The JSON report is a structural comparison, not a wine eligibility result.
Every report row has `legal_approval: null`. Full origin, color, vintage,
process, analytical, and release checks remain necessary.

| Premier Cru result | Rows |
| --- | ---: |
| Exact site with a structural claim-rule binding | 593 |
| Duplicate Chablis site records, with one source-qualified claim binding | 38 |
| Exact Rully site without a claim-rule binding | 23 |
| Missing site under the handoff parent and classification | 11 |
| Spelling review required | 3 |
| Total | 668 |

The 11 missing parent-scoped records are seven Blagny claims, one Pouilly-Loché
claim, and three Pouilly-Vinzelles claims. A related site under another AOC
does not automatically authorize a claim under these parents.

The three spelling cases are Chablis `Les Épinottes` versus `les Épinottes`,
Vougeot `Les Cras` versus the current repository spelling, and Beaune
`Clos du roi` versus the current repository spelling. Preserve both source
strings until their legal source chain is checked.

Of 33 Grand Cru AOC rows, 31 have an exact strict-spec name, Chablis has an
explicit spec alias, and `Grands Echezeaux` has a normalized candidate
`Grands-Echezeaux`. These are mapping results, not proof of historical validity.

Of 32 GC suffix rows, 27 have an exact site and structural claim binding.
Corton `La Vigne-au-Saint` needs spelling review. Four Corton suffixes have no
matching parent-scoped site: `En Charlemagne`, `Le Charlemagne`,
`Les Chaumes et la Voierosse`, and `Les Meix`. Their absence does not settle
which source is correct. Recheck the primary effective specification before
adding or rejecting them.

**Burgundy closeout is not complete.** The handoff's workbook count must not
be presented as runtime legal coverage. No new vineyard permissions or legal
names were added by this change.

## VIVC evidence status

Search exposed candidate passport URLs and titles for Cabernet Sauvignon,
Rondo, and Moschofilero. Direct passport and PDF retrieval returned HTTP 403.
These are R2 candidates only. No pedigree, color, species, or confirmed synonym
was inferred from the search title.

The first 250 census rows are selected by current positive area, then
historical positive area, in deterministic order. Evaluation against the
available evidence yields 2 candidates and 248 unknowns; **zero confirmed
links**. This is an offline evaluation and review queue, not 250 completed
live VIVC searches. The third discovered passport candidate falls outside
this first batch. Remaining names still require primary-source verification.

## Validation

- Base repository: 657 tests passed with `python -m unittest discover -s tests -q`.
- September 6 prototype: all 15 fixtures passed.
- Updated repository full suite: 669 tests passed, including the first 12 new tests.
- Final targeted suite: 15 identity tests passed after adding source-order,
  catalog-interface, and repeated-ambiguous-name cases.
- `git diff --check` passed.

The project uses standard-library unittest. Pytest was not installed in the
environment and is not needed to run this suite.

Reproduce the reports:

```bash
python scripts/reconcile_astra_handoff.py --output-dir docs/astra_handoff/2026-09-07
python -m unittest discover -s tests -p test_variety_identity_resolution.py -v
```

## Next work in order

1. Resolve the Burgundy conflict queue using effective primary specifications.
   Check Rully's missing claim bindings, the 11 parent-scoped PC gaps, Corton
   suffix differences, and the duplicate Chablis source records. Do not merge
   physical sites merely because their names match.
2. Obtain readable VIVC/national-catalogue evidence for the identity queue.
   Promote only reviewed assertions. Preserve conflicting or inaccessible
   records and measure resolution coverage.
3. Review the older `catalog.py` union-find clusters. The new resolver and
   collision fix do not retroactively validate those legacy clusters.
4. Extend temporal legal coverage through the existing strict-spec and
   amendment mechanisms, including separate production/release date anchors.
5. Resume vineyard/site expansion and the vintage/fermentation/aging evidence
   work from the September 6 handoff. Keep unknown measurements unknown and
   simulator priors explicitly typed.
