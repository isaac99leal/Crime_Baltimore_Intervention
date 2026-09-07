# ASTRA ADDENDUM — `wine_knowledge_v2` CONTINUATION BRIEFING

**addendum_id:** `WKV2-ASTRA-ADDENDUM-2026-09-07-R1`  
**supersedes:** nothing; this is a delta to `ASTRA_HANDOFF_WINE_KNOWLEDGE_V2_2026-09-06.md`  
**repository:** `isaac99leal/Crime_Baltimore_Intervention`  
**canonical executable architecture:** `sommelier_v2`  
**Astra base branch:** `foundation/astra-identity-reconciliation-2026-09-07`  
**Astra base SHA observed at addendum creation:** `9b22b3637eeb8b911ec86263970cf0748586e5a5`  
**Burgundy closeout PR:** `#77`  
**Variety identity PR:** `#78`  
**identity code checkpoint before this addendum:** `448974ad05a96ab81180b746baaa788f11ad799d`  
**status:** CONTINUE FROM HERE; DO NOT RESTART THE SEPTEMBER 6 HANDOFF WORK

---

# A. WHY THIS ADDENDUM EXISTS — HUMAN-READABLE

Astra already did the important architectural work of making the Adelaide grape census safe to use: it stopped similar-looking names from collapsing into one grape and created a conservative identity resolver. Since then, the work has split into two finite branches.

First, Burgundy Grand Cru and Premier Cru was pushed to the intended stopping point. The remaining Rully, Blagny, Pouilly-Loché, and Pouilly-Vinzelles gaps were researched and encoded; several apparent gaps turned out to be spelling or duplicate-source problems rather than missing wine regions. The Burgundy branch passes the full repository audit. We should therefore stop spending disproportionate effort on every Burgundian lieu-dit and move global.

Second, the grape identity system is now being populated with actual reviewed links between the Adelaide source names and authoritative VIVC identities. The key point is that we are **not** saying that any similar spelling or famous synonym is automatically the same source row. Every strong identity link is tied to the literal Adelaide source name and evidence. That prevents the global census from quietly becoming corrupted as thousands of varieties are added.

The new technical change is that identity evidence is now sharded. This matters because resolving roughly two thousand Adelaide names in one JSON document would become difficult to review, test, and merge. Astra can now add small reviewed batches without rewriting the entire registry every time.

The next job is therefore not to redesign anything. It is to keep filling the identity graph carefully, then use those stable identities to deepen historical GI legality, PIWI/resistance metadata, vineyard/site systems, vintage mechanics, and fermentation science.

---

# B. DELTA FROM THE SEPTEMBER 6 HANDOFF

## B.1 System invariants remain unchanged

Preserve all original handoff invariants:

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

The repository remains fail-closed for legal authorization and fail-explicit for scientific uncertainty.

## B.2 The live repository still outranks temporary handoff spreadsheets

Do not recreate spreadsheet-side engines.

The September 6 workbooks remain research tranches. Integrate useful semantics into:

```text
sommelier_v2/knowledge/schema.py
sommelier_v2/knowledge/legal_specs.py
sommelier_v2/knowledge/vineyard_registry.py
sommelier_v2/knowledge/vineyard_engine.py
sommelier_v2/knowledge/fermentation_engine.py
sommelier_v2/knowledge/vintage_engine.py
sommelier_v2/knowledge/decision_runtime.py
sommelier_v2/knowledge/variety_identity.py
sommelier_v2/knowledge/data/*
tests/*
```

---

# C. BRANCH / PR TOPOLOGY

## C.1 Astra base

```yaml
branch: foundation/astra-identity-reconciliation-2026-09-07
observed_sha: 9b22b3637eeb8b911ec86263970cf0748586e5a5
role: conservative post-Astra reconciliation baseline
```

Do not rewrite this ref to a child-branch head.

## C.2 Burgundy closeout

```yaml
pr: 77
branch: foundation/sol-rully-corton-closeout-2026-09-07-v14
head: 253519bba84c515e0b171735c91685bec5cfc8f4
base: foundation/astra-identity-reconciliation-2026-09-07
ci:
  workflow: Wine catalog audit
  run: 34135572626
  conclusion: success
scope: Burgundy GC/PC closeout only
```

The workflow at that exact head completed successfully, including:

```text
Audit legacy catalog     PASS
Audit v2 knowledge       PASS
Run v2 tests             PASS
```

PR #77 remains a draft. Re-evaluate GitHub mergeability against the current base before integration; CI success is not the same proposition as conflict-free mergeability.

## C.3 Variety identity tranche

```yaml
pr: 78
branch: foundation/sol-variety-identity-batch1-2026-09-07
base: foundation/astra-identity-reconciliation-2026-09-07
code_checkpoint_pre_addendum: 448974ad05a96ab81180b746baaa788f11ad799d
role: evidence-reviewed Adelaide -> canonical botanical identity reconciliation
```

This branch contains the resolver sharding work plus six reviewed evidence tranches.

### Integration recommendation

Do not make PR #78 depend semantically on the Burgundy branch. They are orthogonal workstreams.

Preferred integration:

```text
Astra base
  + Burgundy PR #77
  + identity PR #78
  -> common integration branch
  -> full audit
  -> continue world legal / identity / process expansion
```

If either branch conflicts because the base moved, resolve at the common integration layer rather than deleting one branch's provenance history.

---

# D. BURGUNDY GC/PC CLOSEOUT — TREAT AS A CLOSED SCOPE UNLESS PRIMARY LAW REQUIRES REOPENING

The project owner explicitly chose GC + PC depth as the Burgundy stopping point.

Do not return to exhaustive village-level Burgundy lieux-dits merely because the bulk map contains them.

## D.1 Rully

Implemented:

- four strict legal paths by level/color;
- exact production/maturity/analytical/élevage/release constraints;
- 23 Premier Cru climat claim bindings;
- red and white parent-scoped claims;
- generic lieu-dit claims remain fail-closed.

## D.2 Blagny

Implemented from the effective 2026 cahier:

- red standard path;
- red Premier Cru path;
- seven parent-scoped PC climats;
- exact maturity, yield, alcohol, residual-sugar, malic, élevage, and release constraints.

Important semantic restriction:

- César is conditional and MUST NOT become a generic always-permitted blend component.
- Chardonnay / Pinot Blanc / Pinot Gris accessory/co-planting semantics MUST NOT be widened into generic cellar blend permissions.

## D.3 Pouilly-Loché

Implemented:

- Chardonnay-only Premier Cru strict path;
- `Les Mûres` parent-scoped PC claim.

## D.4 Pouilly-Vinzelles

Implemented:

- Chardonnay-only Premier Cru strict path;
- `Les Longeays`;
- `Les Pétaux`;
- `Les Quarts`.

## D.5 Corton correction

The September 6 temporary handoff contained four false-positive Corton suffix candidates.

Repository policy now fixes Corton's red suffix set to the legally supported canonical set and tests the false positives negatively.

Do not re-import the spreadsheet's larger candidate list as truth.

## D.6 Naming/source cleanup already resolved

Do not churn these records unless a primary source contradicts them:

```text
Chablis PC: les Épinottes
Vougeot: Les Crâs
Beaune: Clos du Roi
Corton: La Vigne au Saint
Grands-Echezeaux: canonical hyphenated appellation identity retained
```

The older redundant BIVB Chablis PC materialization was removed while its institutional source metadata was retained. The Ministry-backed current set remains canonical.

## D.7 Transitional Mâconnais harvest rule

The 2024 Mâconnais specifications contain transitional/manual-harvest provisions.

Do NOT model this as:

```python
manual_harvest_required = True
```

for all vintages forever.

It belongs in the temporal legal-practice layer with effective-date semantics.

---

# E. VARIETY IDENTITY ARCHITECTURE — CURRENT CONTRACT

File:

`sommelier_v2/knowledge/variety_identity.py`

## E.1 Resolution levels

```text
R0 = conflict / competing identity
R1 = unresolved / no source-specific evidence
R2 = normalized-string candidate only
R3 = intermediate evidence state
R4 = reviewed confirmed synonym assertion
R5 = reviewed exact source identity assertion
```

Strong identity:

```python
identity_confirmed == (
    status == "RESOLVED"
    and level in {"R4", "R5"}
)
```

## E.2 Exact name semantics

`exact_name()` is:

- NFC-normalized;
- trimmed;
- case-folded;
- accent-preserving;
- punctuation-preserving.

Therefore:

```text
Airén == airÉn        exact for resolver purposes
Airén != Airen        not exact
Carmenère != Carmenere
Xarello != Xarel·lo
```

The latter forms may become R2 candidates through search normalization, but R2 MUST NOT emit a canonical identity.

## E.3 Source scoping

Every reviewed link is source-specific.

Current source:

```text
source_id = adelaide_2025
```

An R5 assertion for an Adelaide row does not create an R5 assertion for a different census, nursery, importer book, or national catalogue source.

Country-scoped assertions likewise cannot be widened globally.

## E.4 Evidence requirements for R4/R5

An R4/R5 link is accepted only if its registered evidence assertion matches:

```text
review_status == reviewed
authority_type in {botanical_registry, national_catalogue}
canonical_id == link.canonical_id
source_id == link.source_id
exact source_name == link.source_name
country scope == link country scope
url exists
retrieved_on exists
relation == exact_identity for R5
relation == confirmed_synonym for R4
```

A VIVC search-result title or inaccessible passport URL is discovery evidence, not strong identity evidence.

---

# F. EVIDENCE SHARDING — NEW SCALABILITY CONTRACT

Default registry loading now uses:

```text
variety_identity_evidence.json
+ sorted(variety_identity_evidence_shard_*.json)
```

Explicitly passing `data_path` preserves isolated historical single-document behavior.

This is deliberate. Do not remove it.

## F.1 Global invariants across shards

The loader rejects:

- duplicate evidence IDs;
- empty evidence IDs;
- duplicate canonical identity IDs;
- malformed VIVC IDs;
- links to unknown canonical identities;
- links without evidence;
- duplicate exact source/country/canonical/level link tuples;
- R4/R5 links without a qualifying reviewed assertion.

A later shard may link to a canonical identity defined in an earlier document without redefining that identity.

## F.2 Shard size policy

Recommended normal batch:

```text
5–25 strong identity assertions per shard
```

Prefer coherent reviewable batches:

- acreage-priority tranche;
- one authority/source tranche;
- PIWI tranche;
- one national catalogue tranche;
- one conflict-resolution tranche.

Avoid 500-row opaque auto-generated shards.

## F.3 Tests

Each material shard should have regression coverage for:

1. expected exact source-name -> canonical ID;
2. R5 status;
3. source scoping;
4. known alias-widening hazards;
5. adjacent/related source rows that must remain separate;
6. known unresolved conflicts.

Every identity corruption bug becomes a permanent fixture.

---

# G. CURRENT REVIEWED ADELAIDE -> VIVC CHECKPOINT: 48 R5 LINKS

This is the current strong source-specific identity set at the code checkpoint referenced above.

## G.1 Base evidence document — 12

```text
Cabernet Sauvignon -> vivc:1929
Syrah              -> vivc:11748
Rondo              -> vivc:14308
Moschofilero        -> vivc:8068
Merlot              -> vivc:7657
Chardonnay          -> vivc:2455
Tempranillo         -> vivc:12350
Airén               -> vivc:157
Pinot Noir          -> vivc:9279
Pinot Gris          -> vivc:9275
Sangiovese          -> vivc:10680
Sauvignon Blanc     -> vivc:10790
```

## G.2 Shard 0002 — 4

```text
Cabernet Franc -> vivc:1927
Chenin Blanc   -> vivc:2527
Barbera        -> vivc:974
Viognier       -> vivc:13106
```

## G.3 Shard 0003 — 8

```text
Riesling         -> vivc:10077
Rkatsiteli       -> vivc:10116
Monastrell       -> vivc:7915
Pinot Blanc      -> vivc:9272
Gamay Noir       -> vivc:4377
Garnacha Blanca  -> vivc:4457
Garnacha Peluda  -> vivc:4460
Garnacha Tinta   -> vivc:4461
```

## G.4 Shard 0004 — 5

```text
Macabeo          -> vivc:13127   # authority prime: VIURA
Cinsaut           -> vivc:2672
Saperavi          -> vivc:10708
Grüner Veltliner  -> vivc:12930
Vermentino        -> vivc:12989
```

## G.5 Shard 0005 — 9

```text
Bobal             -> vivc:1493
Cayetana Blanca   -> vivc:5648    # authority prime: JAEN BLANCO
Colombard          -> vivc:2771
Graševina          -> vivc:13217   # authority prime: WELSCHRIESLING
Blaufränkisch      -> vivc:1459
Gewürztraminer     -> vivc:12609   # authority prime: TRAMINER ROT
Mencía             -> vivc:7623
Vranac             -> vivc:13179
Marselan           -> vivc:16383
```

## G.6 Shard 0006 — 10

```text
Xarello     -> vivc:13270
Savatiano   -> vivc:10798   # authority prime spelling: SAVVATIANO
Grillo      -> vivc:5021
Zweigelt    -> vivc:13484   # authority prime: ZWEIGELTREBE BLAU
Castelão    -> vivc:9152    # authority prime: PERIQUITA
Baga        -> vivc:885
Pinotage    -> vivc:9286
Chasselas   -> vivc:2473    # authority prime: CHASSELAS BLANC
Caladoc     -> vivc:1989
Carmenère   -> vivc:2109
```

Total:

```text
48 reviewed exact Adelaide source-name identity links at R5
```

Do not reinterpret this as “48 global synonym clusters are complete.”

It means exactly:

> the literal Adelaide source assertion has been reviewed strongly enough to bind to this canonical botanical identity.

---

# H. AUTHORITY SOURCES USED IN THIS TRANCHE

## H.1 CNR/IPSP Vitis Grinzane

Used where a record explicitly reports:

- VIVC number;
- variety identity;
- trueness-to-type / curated accession evidence;
- sometimes species, color, national catalogue code, use.

Do not assume every attribute in the authority record has already been promoted into `GrapeKnowledge`.

Identity evidence and attribute evidence remain separable propositions.

## H.2 European GrapeGen 06 genetic-resource crosswalk

Used where the crosswalk explicitly maps registered collection/source names to a VIVC identity.

This has been especially useful for exact source-name crosswalks where the VIVC prime name differs.

Again:

```text
source-name crosswalk != permission to generate every listed synonym as a source alias
```

## H.3 Direct VIVC retrieval problem

Direct VIVC passport retrieval returned HTTP 403 in the prior environment.

Search-result titles/URLs were retained as candidate/discovery provenance only.

Do not promote those snippets to R5 merely because the ID and title look correct.

If Astra can access VIVC passport records directly, use them—but preserve the same assertion-level provenance model.

---

# I. FAIL-CLOSED IDENTITY CASES TO PRESERVE

These are not nuisances. They are regression boundaries.

## I.1 Diacritic folding

```text
Airén      -> R5
Airen      -> R2 candidate, canonical_id None

Carmenère  -> R5
Carmenere  -> R2 candidate, canonical_id None
```

Do not promote accent-folded strings without a source-specific reviewed assertion.

## I.2 Authority prime-name difference does not widen source namespace

```text
Macabeo -> vivc:13127 / VIURA
Viura as Adelaide source-name link -> UNKNOWN unless separately evidenced

Graševina -> vivc:13217 / WELSCHRIESLING
Welschriesling as Adelaide source-name link -> UNKNOWN unless separately evidenced

Castelão -> vivc:9152 / PERIQUITA
Periquita as Adelaide source-name link -> UNKNOWN unless separately evidenced

Zweigelt -> vivc:13484 / ZWEIGELTREBE BLAU
Rotburger as Adelaide source-name link -> UNKNOWN unless separately evidenced
```

## I.3 Related color/mutation/source rows stay separate

```text
Chasselas       -> R5
Chasselas (R)   -> UNKNOWN

Pinot Blanc != Pinot Gris != Pinot Noir
Garnacha Blanca != Garnacha Peluda != Garnacha Tinta
```

Do not use botanical family intuition as a merge rule.

## I.4 Qualified umbrella/variant row

```text
Garnacha Roja (Gris) -> unresolved
```

The authority crosswalk for a shorter registered name is not enough to delete the Adelaide qualifier.

## I.5 Catarratto

```text
Catarratto Bianco -> UNKNOWN
```

Reason: the Adelaide umbrella name is broader/less precise than authority identities such as Catarratto Bianco Comune / Lucido. Do not guess which identity its acreage belongs to.

## I.6 Petit Verdot / Alicante Bouschet

Current handling:

```text
Petit Verdot       -> UNKNOWN
Alicante Bouschet  -> UNKNOWN
```

Do not promote until the authority conflict/identity evidence is reconciled at the proposition level.

## I.7 Nebbiolo

Current status is simply unresolved in this tranche, not disproven.

```text
Nebbiolo -> UNKNOWN pending reviewed crosswalk
```

Absence from the 48-link set is not evidence of absence.

---

# J. CI / TEST STATE

## J.1 Burgundy

Exact head `253519bba84c515e0b171735c91685bec5cfc8f4`:

```text
Wine catalog audit: SUCCESS
```

Treat this as validated branch state.

## J.2 Identity checkpoint

Exact pre-addendum code checkpoint:

```text
448974ad05a96ab81180b746baaa788f11ad799d
```

At addendum authoring, the workflow had started and both catalog-audit phases had previously been stable; the exact final run conclusion MUST be checked before merge.

Do not replace an incomplete CI state with an assumption.

The code checkpoint includes:

- six evidence tranches totaling 48 R5 Adelaide links;
- default evidence-shard loading;
- global evidence/identity/link duplicate guards;
- isolated `data_path` behavior;
- shard 0005 tests;
- shard 0006 tests;
- source-scoping regressions;
- no-widening regressions.

Before merge/integration, require:

```text
Audit legacy catalog     PASS
Audit v2 knowledge       PASS
Run v2 tests             PASS
```

---

# K. NEXT EXECUTION QUEUE FOR ASTRA

Do not spend the next run restating this addendum.

## K.0 Boot

```text
1. fetch current Astra base
2. inspect PR #77 and PR #78 heads
3. check latest CI for both
4. reconcile any base movement
5. create/common integration branch if appropriate
6. run full suite
7. continue identity batches
```

## K.1 Variety identity — immediate priority

Continue Adelaide resolution using:

```text
priority ~= planted_area_2023
          * exact_authority_match_probability
          * downstream_legal_reuse
          / review_effort
```

Do not prioritize only famous varieties.

High-area unresolved rows should generally come before tiny museum varieties when evidence quality is similar.

### Batch method

For each source row:

```text
A. preserve literal Adelaide source spelling
B. find authoritative canonical identity
C. establish exact crosswalk or confirmed synonym relation
D. inspect homonym/color/mutation conflicts
E. assign R5 exact or R4 confirmed synonym only with reviewed assertion
F. otherwise leave R1/R2/R0
G. add evidence shard
H. add regression
I. run audit
```

### Strong next candidates

Research the high-acreage unresolved universe first, including—but not limited to—major classic, Iberian, Italian, Greek, Georgian, Central/Eastern European, hybrid, and PIWI rows.

Do not preassign IDs in planning notes. Resolve from authority evidence during the tranche.

## K.2 Add R4 confirmed-synonym support deliberately

So far the work has emphasized exact source crosswalks at R5.

The next maturity step is controlled R4 use where:

- the Adelaide source string is explicitly a synonym in VIVC/national catalogue evidence;
- the assertion is source-specific;
- homonyms are excluded;
- country context is represented where necessary.

Do not turn a global synonym dictionary into a universal source rewrite table.

## K.3 Conflict queue

Create a first-class machine conflict queue for rows such as:

```text
umbrella name -> multiple authority identities
same normalized string -> multiple botanical identities
same source name -> mutation/color ambiguity
authority A -> VIVC X
authority B -> VIVC Y
historical name -> changed taxonomy
```

Recommended representation:

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

R0 should become auditable data, not merely an ephemeral resolver result.

## K.4 Identity attributes after canonical linkage

Do not overload the identity-link tranche with every grape fact.

After canonical ID resolution, build proposition-specific attribute tranches:

```text
species
berry color
use role
country of origin
pedigree / parentage
breeder
breeding station
breeding year
clone relationships
PIWI status
Rpv / Ren / Run / other resistance loci
phenology references
agronomic traits
must-chemistry priors
```

Each attribute keeps its own provenance.

## K.5 PIWI / interspecific program

Move resistant varieties into a structured layer rather than a `PIWI=true` tag.

Target:

```yaml
resistance:
  piwi_membership:
  powdery_mildew:
  downy_mildew:
  loci:
    Rpv: []
    Ren: []
    Run: []
  evidence:
```

Keep:

```text
botanical identity
resistance genetics
national registration
GI legality
commercial acreage
```

as separate dimensions.

## K.6 Legal-rule expansion once identity coverage is stable enough

Identity work is an upstream dependency, not the entire project.

Once high-area/common source rows have substantial reviewed coverage, resume country legal-rule expansion in parallel.

Priority remains approximately:

```text
France
Italy
Spain
Portugal
Germany
Austria
United States
Australia
New Zealand
South Africa
Argentina
Chile
Canada
Greece
Hungary
Georgia
Switzerland
Balkans / Eastern Europe
remaining commercial jurisdictions
```

Use jurisdiction-specific strategies; do not force EU encépagement semantics onto AVAs/Australian GIs/NZ GIs.

## K.7 Named-site queue after Burgundy

Burgundy village-level exhaustive named-site ingestion remains deferred.

Higher-leverage next systems:

```text
Rheinland-Pfalz Weinbergsrolle
  - Bereich
  - Großlage
  - Einzellage
  - Gewann

Austria
  - Ried
  - Subriede
  - incomplete-coverage metadata

Vienna
  - finite 140-Ried official map

Italy
  - MGA
  - UGA
  - other legally defined named geographic units
```

Preserve jurisdiction-native semantics.

## K.8 Fermentation / vintage engines

Do not forget the original destination while identity/legal work expands.

After the current identity tranche, resume the existing repository engines—not spreadsheet clones.

Fermentation priorities:

```text
strain/species-specific fermentation parameters
YAN component/timing effects
temperature response surfaces
oxygen timing
SO2 x pH antimicrobial state
extraction kinetics
MLF strain/environment interactions
fault-risk pathways
sparkling pressure/sugar mechanics
fortification/flor/appassimento/botrytis/carbonic pathways
```

Vintage priorities:

```text
daily weather provenance
site/variety phenology calibration
frost/hail/heat/drought/smoke/disease events
stage-specific rain
harvest chemistry bridge
uncertainty
historical rule/version awareness
```

---

# L. RESEARCH AUTOMATION STRATEGY

Astra can accelerate identity resolution, but automated extraction MUST remain bounded by the evidence type system.

Recommended pipeline:

```text
candidate generator
  -> authority retrieval
  -> structured parser
  -> exact-name / synonym proposition
  -> conflict detector
  -> evidence object
  -> shard builder
  -> test generator
  -> human/model review gate
  -> CI
```

Never:

```text
fuzzy join Adelaide CSV to VIVC names
-> bulk mark all as resolved
```

Even a 99% fuzzy-match precision would create unacceptable long-tail corruption across ~2,000 names.

---

# M. METRICS ASTRA SHOULD START REPORTING

Raw count is insufficient.

For identity work, report at least:

```text
source rows total
source rows R5
source rows R4
source rows R2
source rows R1
source rows R0
2023 planted-area coverage by resolved rows
historical planted-area coverage by resolved rows
number of exact spelling collisions
number of homonym conflicts
number of source rows mapping to already-known canonical IDs
number of unresolved >10,000 ha rows
number of unresolved >1,000 ha rows
```

The area-weighted metrics matter because 500 tiny resolved accessions are not equivalent to resolving the major commercial universe.

Do not fabricate area coverage if the necessary sums have not been computed from the source table.

---

# N. PROPOSED IDENTITY COMPLETION GATES

Do not require 100% of 1,998 names before continuing other world-wine work.

Use staged gates.

## Gate I — commercial core

Enough R4/R5 coverage that most current planted-area mass is canonically resolved.

## Gate II — legal dependency core

All varieties referenced by loaded high-priority GI legal specs have canonical identity links.

## Gate III — obscure commercial tail

Tiny but positive current acreage, importer-observed, producer-observed, and PIWI varieties resolved.

## Gate IV — historical/germplasm tail

Historical-positive, breeding-line, experimental, and near-extinct names.

This allows legal/vintage/fermentation work to proceed before the final botanical tail is complete.

---

# O. DO-NOT-REGRESS LIST — ADDENDUM-SPECIFIC

Astra MUST NOT:

1. Remove source scoping from reviewed identity links.
2. Convert R2 normalized matches to canonical IDs.
3. Treat VIVC prime-name differences as automatic Adelaide aliases.
4. Collapse color mutations because they share a root name.
5. Collapse `Catarratto Bianco` to a more specific Catarratto identity without evidence.
6. Promote Petit Verdot/Alicante Bouschet while authority conflict remains unresolved.
7. Mark unresolved rows extinct or invalid.
8. Use botanical identity as GI permission.
9. Reopen all Burgundy village lieux-dits as the highest-priority task.
10. Reintroduce the redundant older Chablis PC materialization as canonical current data.
11. Encode transitional Mâconnais practice as timeless law.
12. Replace evidence shards with an opaque generated monolith.
13. Allow duplicate evidence IDs across shards.
14. Allow canonical identity redefinition in a later shard.
15. Infer pedigree/resistance/clone facts merely because a canonical VIVC ID is now known.
16. Skip regression creation for ambiguous names.
17. Optimize identity count at the expense of acreage-weighted or legal-dependency coverage.

---

# P. ASTRA FIRST-RUN COMMAND SEMANTICS

Conceptual sequence:

```text
CHECKOUT
  Astra base + inspect child PRs

VERIFY
  PR77 CI
  PR78 CI
  mergeability
  source ledgers

INTEGRATE
  common branch if both branches are accepted

TEST
  full Wine catalog audit

MEASURE
  identity level counts
  resolved acreage mass
  unresolved high-area queue

EXPAND
  next exact/R4 identity shard

RETEST

PARALLELIZE
  begin next historical/legal jurisdiction tranche
```

If CI is red:

```text
fix regression or code first
```

Do not continue appending data on a red head unless the failure is conclusively unrelated and explicitly documented.

---

# Q. END-STATE REMINDER

The destination remains:

> a temporally versioned, provenance-aware, jurisdiction-sensitive, physically constrained world-wine knowledge graph and process simulator.

Identity resolution is upstream infrastructure for that destination.

The system should ultimately distinguish:

```text
what grape this is
what names it has in which source/jurisdiction
where it is actually planted
where it is legally permitted
what site it occupies
what happened in the vintage
what happened in the cellar
what chemistry follows
what label is legal
what is commercially observed
what is inferred
what is unknown
```

Continue aggressively, but preserve epistemic type safety.

**Obscurity is desirable. Silent identity corruption is not.**

**Coverage should expand by reviewed propositions, not by plausible-looking joins.**
