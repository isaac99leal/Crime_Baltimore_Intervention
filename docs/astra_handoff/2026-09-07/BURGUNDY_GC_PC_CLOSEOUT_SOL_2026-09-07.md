# Burgundy GC/PC closeout — Sol continuation 2026-09-07

This note records the finite reconciliation work performed after Astra's 2026-09-07 handoff. It does **not** expand Burgundy to every village lieu-dit. Grand Cru + Premier Cru remains the intentional project scope boundary.

## Queue closed

Astra's structural report identified:

- 23 Rully Premier Cru sites lacking a positive claim-rule binding;
- 11 missing parent-scoped Premier Cru site identities: 7 Blagny, 1 Pouilly-Loché, 3 Pouilly-Vinzelles;
- three spelling-review rows;
- duplicated Chablis Premier Cru materialization;
- Corton suffix discrepancies.

The continuation resolves those items as follows.

### Rully

Promoted strict current Rully legal paths for red/white standard and red/white Premier Cru. All 23 official Premier Cru climat identities now have a positive, parent-scoped claim rule for both colors. Generic lieux-dits remain fail-closed.

### Blagny

Promoted current 2026 red standard and Premier Cru paths and the seven exact parent-scoped Premier Cru climats. Conditional César authorization and accessory white co-planting are not generalized into ordinary blend permissions.

### Pouilly-Loché / Pouilly-Vinzelles

Promoted only the 2024 Premier Cru paths required by the GC/PC scope:

- Pouilly-Loché: `Les Mûres`;
- Pouilly-Vinzelles: `Les Longeays`, `Les Pétaux`, `Les Quarts`.

Manual-harvest transition provisions are not represented as timeless booleans; they remain for a vintage-aware legal-practice layer.

### Chablis duplicates

The older BIVB expansion file duplicated the current 40-site Chablis Premier Cru set and contained variant spellings. The duplicate materialization group was removed. The BIVB source metadata remains as institutional evidence; `named_sites_chablis_premier_cru_2025.json`, sourced from the current Ministry specification, is the canonical current site set.

### Exact-name review

Current live records already carry the source-preferred forms, so no churn was introduced:

- Chablis: `les Épinottes`;
- Vougeot: `Les Crâs`;
- Beaune: `Clos du Roi`;
- Corton: `La Vigne au Saint`;
- Grand Cru appellation: `Grands-Echezeaux`, with accented legal/search aliases retained.

### Corton

The live repository's 24-name red Corton suffix set is preserved. Four September 6 handoff candidates were false positives for this label-suffix rule and are now negative regression fixtures:

- `En Charlemagne`;
- `Le Charlemagne`;
- `Les Chaumes et la Voierosse`;
- `Les Meix`.

White Corton does not inherit the red climat-suffix privilege.

## Remaining Burgundy items are not closeout blockers

- Marsannay 2026 Premier Cru candidates remain pending/non-generatable until effective homologated law is loaded.
- Monthélie `Les Crays` remains disputed/non-generatable until authoritative current legal evidence resolves the conflict.
- Full village-level Burgundy lieu-dit and parcel ingestion is deferred by explicit project scope decision.
- Historical legal amendments remain a separate temporal-law workstream.

## Completion criterion

Burgundy GC/PC is considered closed for the present foundation phase when the full repository audit passes on PR #77. A later primary legal source may reopen a specific rule through ordinary source-versioning and regression procedures; it should not reopen the entire Burgundy ingestion project.
