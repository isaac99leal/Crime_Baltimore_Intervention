# ASTRA ADDENDUM — `wine_knowledge_v2` CONTINUATION BRIEFING

**addendum_id:** `WKV2-ASTRA-ADDENDUM-2026-09-07-R2`  
**role:** delta to `ASTRA_HANDOFF_WINE_KNOWLEDGE_V2_2026-09-06.md`  
**repository:** `isaac99leal/Crime_Baltimore_Intervention`  
**canonical executable architecture:** `sommelier_v2`  
**Astra base branch:** `foundation/astra-identity-reconciliation-2026-09-07`  
**Astra base SHA observed:** `9b22b3637eeb8b911ec86263970cf0748586e5a5`  
**Burgundy closeout PR:** `#77`  
**Variety identity PR:** `#78`  
**current identity code checkpoint before this documentation update:** `e2093394f67ec7de90a99ac347c22be0585e3f73`  
**status:** CONTINUE; DO NOT RESTART OR REBUILD THE ONTOLOGY

---

# 1. WHY — HUMAN-READABLE

Astra already did the most important safety work on the global grape census: it stopped similar-looking names from silently collapsing into one grape and created a conservative R0–R5 identity resolver. Since then, Burgundy Grand Cru/Premier Cru has been closed at the intended scope and the variety resolver has been converted into a scalable, evidence-sharded system.

The grape-identity work is now real data integration rather than architecture design. Sixty literal Adelaide source names have authoritative, reviewed links to canonical VIVC identities. The system deliberately does **not** infer that every familiar synonym, accentless spelling, color mutation, or related source row is the same thing. That caution is the point: the simulator needs obscure coverage without silently corrupting its botanical graph.

The next job is therefore straightforward: keep resolving the high-impact global commercial grape universe with strong evidence, model conflicts explicitly, then use stable identities to deepen legal rules, PIWI/resistance data, site systems, vintage mechanics, and fermentation science.

---

# 2. NON-NEGOTIABLE INVARIANTS

Preserve:

```text
botanical identity != source spelling
botanical identity != GI permission
commercial planting != GI permission
physical site != legal site claim
current law != historical law
OIV-admitted practice != local legal permission
regional prior != site observation
model prior != observed fact
UNKNOWN != FALSE
UNKNOWN != ALLOW
```

The live repository outranks temporary spreadsheet architecture.

Do not recreate a parallel wine engine from the September 6 workbooks.

---

# 3. BRANCH / PR TOPOLOGY

## 3.1 Astra base

```yaml
branch: foundation/astra-identity-reconciliation-2026-09-07
sha: 9b22b3637eeb8b911ec86263970cf0748586e5a5
role: conservative post-Astra reconciliation baseline
```

Do not move this ref to a child-branch head.

## 3.2 Burgundy closeout

```yaml
pr: 77
branch: foundation/sol-rully-corton-closeout-2026-09-07-v14
head: 253519bba84c515e0b171735c91685bec5cfc8f4
ci_run: 34135572626
ci_conclusion: success
```

At that exact head:

```text
Audit legacy catalog     PASS
Audit v2 knowledge       PASS
Run v2 tests             PASS
```

Treat Burgundy GC/PC as closed scope unless primary law requires reopening.

## 3.3 Variety identity

```yaml
pr: 78
branch: foundation/sol-variety-identity-batch1-2026-09-07
base: foundation/astra-identity-reconciliation-2026-09-07
code_checkpoint: e2093394f67ec7de90a99ac347c22be0585e3f73
reviewed_R5_adelaide_links: 60
```

PR #77 and #78 are orthogonal. Integrate them through a common integration branch after checking current mergeability and CI.

Do not make the identity architecture depend semantically on Burgundy.

---

# 4. BURGUNDY CLOSEOUT CONTRACT

Do not spend the next run ingesting every village-level Burgundy lieu-dit.

The intended boundary is GC + PC.

Implemented and tested:

- Rully: four strict color/level paths and all 23 PC claim bindings.
- Blagny: current 2026 red standard/PC paths and seven parent-scoped PC climats.
- Pouilly-Loché PC: Chardonnay-only strict path + `Les Mûres`.
- Pouilly-Vinzelles PC: Chardonnay-only strict path + `Les Longeays`, `Les Pétaux`, `Les Quarts`.
- Corton: legally supported canonical red suffix set; false-positive handoff candidates blocked by regressions.
- Chablis duplicate-source cleanup: old redundant BIVB materialization removed, source metadata retained, current Ministry-backed set canonical.

Already-correct names that should not be churned without primary contradiction:

```text
Chablis PC: les Épinottes
Vougeot: Les Crâs
Beaune: Clos du Roi
Corton: La Vigne au Saint
Grands-Echezeaux: canonical hyphenated identity retained
```

Do not generalize Blagny conditional César/accessory-variety rules.

Do not encode transitional Mâconnais manual-harvest provisions as timeless booleans; they belong in temporal legal-practice rules.

---

# 5. VARIETY IDENTITY RESOLVER CONTRACT

File:

`sommelier_v2/knowledge/variety_identity.py`

Resolution lattice:

```text
R0 = conflict
R1 = unresolved
R2 = normalized-string candidate only
R3 = intermediate evidence state
R4 = reviewed confirmed synonym
R5 = reviewed exact source identity
```

Strong identity requires:

```python
status == "RESOLVED" and level in {"R4", "R5"}
```

`exact_name()` is NFC-normalized, trimmed, case-folded, accent-preserving, punctuation-preserving.

Therefore:

```text
Airén != Airen
Carmenère != Carmenere
Xarello != Xarel·lo
```

Folded variants may be R2 candidates but MUST NOT emit canonical IDs.

Every strong link is source-specific. Current source scope is `adelaide_2025`.

A link for Adelaide does not create a link for another census, importer, nursery, producer, or legal catalogue.

R4/R5 requires a reviewed evidence assertion whose canonical ID, source ID, literal source name, country scope, relation type, URL, and retrieval date match the link.

Search snippets are not R5 evidence.

---

# 6. EVIDENCE SHARDING — PRESERVE THIS

Default loading:

```text
variety_identity_evidence.json
+ sorted(variety_identity_evidence_shard_*.json)
```

Explicit `data_path` keeps isolated single-document behavior for tests/callers.

Across shards, reject:

- duplicate/empty evidence IDs;
- duplicate canonical identity IDs;
- malformed VIVC authority IDs;
- links to unknown identities;
- links without registered evidence;
- duplicate source/country/canonical/level links;
- R4/R5 without qualifying reviewed evidence.

A later shard may reference an earlier canonical identity but must not redefine it.

Recommended shard size: roughly 5–25 reviewed assertions, grouped by reviewable evidence logic.

Each material shard gets dedicated regression coverage for exact resolution, source scope, alias widening, adjacent related rows, and known unresolved cases.

---

# 7. CURRENT REVIEWED ADELAIDE -> VIVC CHECKPOINT: 60 R5 LINKS

## Base evidence — 12

```text
Cabernet Sauvignon -> 1929
Syrah -> 11748
Rondo -> 14308
Moschofilero -> 8068
Merlot -> 7657
Chardonnay -> 2455
Tempranillo -> 12350
Airén -> 157
Pinot Noir -> 9279
Pinot Gris -> 9275
Sangiovese -> 10680
Sauvignon Blanc -> 10790
```

## Shard 0002 — 4

```text
Cabernet Franc -> 1927
Chenin Blanc -> 2527
Barbera -> 974
Viognier -> 13106
```

## Shard 0003 — 8

```text
Riesling -> 10077
Rkatsiteli -> 10116
Monastrell -> 7915
Pinot Blanc -> 9272
Gamay Noir -> 4377
Garnacha Blanca -> 4457
Garnacha Peluda -> 4460
Garnacha Tinta -> 4461
```

## Shard 0004 — 5

```text
Macabeo -> 13127 / VIURA
Cinsaut -> 2672
Saperavi -> 10708
Grüner Veltliner -> 12930
Vermentino -> 12989
```

## Shard 0005 — 9

```text
Bobal -> 1493
Cayetana Blanca -> 5648 / JAEN BLANCO
Colombard -> 2771
Graševina -> 13217 / WELSCHRIESLING
Blaufränkisch -> 1459
Gewürztraminer -> 12609 / TRAMINER ROT
Mencía -> 7623
Vranac -> 13179
Marselan -> 16383
```

## Shard 0006 — 10

```text
Xarello -> 13270
Savatiano -> 10798 / SAVVATIANO
Grillo -> 5021
Zweigelt -> 13484 / ZWEIGELTREBE BLAU
Castelão -> 9152 / PERIQUITA
Baga -> 885
Pinotage -> 9286
Chasselas -> 2473 / CHASSELAS BLANC
Caladoc -> 1989
Carmenère -> 2109
```

## Shard 0007 — 12

```text
Montepulciano -> 7949
Nero d'Avola -> 1986 / CALABRESE
Aligoté -> 312
Touriga Franca -> 12593
Touriga Nacional -> 12594
Alvarinho -> 15689
Aglianico -> 121
Ancellotta -> 447 / ANCELOTTA
Furmint -> 4292
Agiorgitiko -> 102
Godello -> 4840 / GODELHO
Assyrtiko -> 726
```

Total strong Adelaide source-specific identity assertions:

```text
60 R5 links
```

This does **not** mean 60 global synonym clusters are complete.

It means the literal Adelaide source assertion is strongly bound to the listed canonical identity.

---

# 8. AUTHORITY SOURCES CURRENTLY USED

## CNR/IPSP Vitis Grinzane

Useful where it explicitly reports VIVC number and trueness-to-type / curated accession evidence.

## European GrapeGen 06 Annex 2B

Primary crosswalk between official/registered source names and VIVC prime identities/IDs.

This is especially useful when the registered source name differs from the VIVC prime name.

Direct VIVC passport retrieval was previously blocked with HTTP 403. Do not elevate search-result snippets to R5. If Astra can access VIVC directly, add that provenance rather than weakening the evidence rules.

---

# 9. FAIL-CLOSED CASES TO PRESERVE

## Orthography

```text
Airén -> R5; Airen -> R2
Carmenère -> R5; Carmenere -> R2
Aligoté -> R5; Aligote -> R2
```

## Prime-name differences do not widen Adelaide

```text
Macabeo -> VIURA ID; Viura Adelaide link remains absent unless separately evidenced
Graševina -> WELSCHRIESLING ID; Welschriesling source link not invented
Castelão -> PERIQUITA ID; Periquita source link not invented
Nero d'Avola -> CALABRESE ID; Calabrese source link not invented
Godello -> GODELHO ID; Godelho source link not invented
Zweigelt -> ZWEIGELTREBE BLAU ID; Rotburger source link not invented
```

## Related rows remain separate

```text
Chasselas != Chasselas (R)
Assyrtiko != Asirtiko Red
Aglianico != Aglianicone
Touriga Franca != Touriga Nacional != Touriga Femea
Pinot Blanc != Pinot Gris != Pinot Noir
Garnacha Blanca != Garnacha Peluda != Garnacha Tinta
```

## Known unresolved/quarantined rows

```text
Garnacha Roja (Gris)
Catarratto Bianco
Petit Verdot
Alicante Bouschet
Nebbiolo   # unresolved in this tranche, not disproven
```

Do not convert UNKNOWN into falsehood or legality.

---

# 10. NEXT ASTRA EXECUTION QUEUE

## Boot

```text
1. read September 6 handoff
2. read this R2 addendum
3. inspect PR #77 and PR #78
4. check latest CI and mergeability
5. create a common integration branch if accepting both
6. run full Wine catalog audit
7. continue identity resolution
```

## Variety priority

Use approximately:

```text
priority = current planted area
         * exact-authority-match probability
         * downstream legal reuse
         / review effort
```

Do not optimize for famous-name count.

For each source row:

```text
preserve literal source spelling
-> retrieve authority evidence
-> identify canonical candidate(s)
-> detect homonym/color/mutation ambiguity
-> R5 exact or R4 reviewed synonym only with assertion-level evidence
-> otherwise R0/R1/R2
-> add shard
-> add regression
-> run audit
```

Begin reporting:

```text
R5 count
R4 count
R2 count
R1 count
R0 count
2023 planted-area mass resolved
historical planted-area mass resolved
unresolved >10k ha rows
unresolved >1k ha rows
conflict count
```

Do not invent area-weighted percentages before computing them from the source table.

---

# 11. BUILD A FIRST-CLASS CONFLICT QUEUE

Current ambiguity should become auditable data rather than informal notes.

Recommended object:

```yaml
VarietyIdentityConflict:
  source_id:
  source_name:
  country:
  candidate_ids: []
  evidence_ids: []
  conflict_class:
  status:
  generator_policy: block_identity_promotion
```

Use it for umbrella names, homonyms, mutation/color ambiguity, and contradictory authority mappings.

R0 should be inspectable and source-backed.

---

# 12. AFTER IDENTITY: DO NOT LOSE THE REST OF THE PROJECT

Identity is upstream infrastructure, not the final product.

Once the commercial core has strong canonical coverage, resume in parallel:

## Historical / jurisdiction-specific legality

France, Italy, Spain, Portugal, Germany, Austria, US, Australia, NZ, South Africa, Argentina, Chile, Canada, Greece, Hungary, Georgia, Switzerland, Balkans/Eastern Europe, remaining commercial jurisdictions.

Do not use one legal ontology strategy for all jurisdictions.

## PIWI / resistant varieties

Separate botanical identity, resistance loci, breeding data, national registration, GI eligibility, and commercial acreage.

## Named sites

Prioritize official German Lage/Gewann and Austrian Ried/Subriede systems; Burgundy exhaustive village lieux-dits remain deferred.

## Fermentation engine

Deepen strain/species behavior, YAN timing, temperature surfaces, oxygen, SO2×pH, extraction, MLF, fault pathways, sparkling mechanics, fortification/flor/appassimento/botrytis/carbonic pathways.

## Vintage engine

Deepen daily-weather provenance, site/variety phenology, frost/hail/heat/drought/smoke/disease, stage-specific rain, harvest chemistry, and uncertainty.

---

# 13. DO-NOT-REGRESS LIST

Astra MUST NOT:

1. remove source scoping;
2. convert R2 fuzzy/normalized matches into canonical IDs;
3. widen VIVC prime names into unreviewed Adelaide aliases;
4. collapse color mutations/related varieties by root name;
5. guess through Catarratto/Petit Verdot/Alicante conflicts;
6. use botanical identity as GI authorization;
7. infer pedigree/resistance merely because VIVC ID is known;
8. reopen exhaustive Burgundy village lieu-dit ingestion as top priority;
9. encode transitional legal rules as timeless law;
10. replace evidence shards with an opaque generated monolith;
11. allow duplicate evidence or canonical identity redefinition;
12. continue appending data on a red CI head without first resolving the failure.

---

# 14. END-STATE REMINDER

The target remains a:

> temporally versioned, provenance-aware, jurisdiction-sensitive, physically constrained world-wine knowledge graph + process simulator.

It must distinguish:

```text
what grape this is
what names it has in which source/jurisdiction
where it is planted
where it is legally permitted
what site it occupies
what happened in the vintage
what happened in the cellar
what chemistry follows
what label is legal
what is commercially observed
what is modeled
what is unknown
```

Continue aggressively, but preserve epistemic type safety.

**Obscurity is desirable. Silent identity corruption is not.**
