# ASTRA HANDOFF — SOMMELIER WORLD REGISTRY / `wine_knowledge_v2`

**handoff_id:** `WKV2-ASTRA-2026-09-06-R1`  
**repository:** `isaac99leal/Crime_Baltimore_Intervention`  
**branch:** `claude/somm-simulator-game-KQpS7`  
**parent observed before handoff:** `c278a052215d8f11abf18ccac2e26638a91c3d08`  
**directive:** CONTINUE. DO NOT RESTART. DO NOT FLATTEN. RECONCILE NEW RESEARCH INTO THE LIVE `sommelier_v2` ARCHITECTURE.

---

# 0. WHY — FOR ISAAC

This is not supposed to become a giant list of wine facts. It is supposed to become a system that can tell the difference between a wine that merely sounds plausible and a wine that could actually exist.

A normal database can say that a grape exists, a region exists, and a technique exists. A weak generator can combine those three things and produce nonsense. Here, the system should also know whether the grape was legally allowed in that exact appellation, whether the rule existed in that vintage, whether the named vineyard can legally appear on the label, whether the weather and site could plausibly produce the stated fruit, whether the cellar process can produce the resulting chemistry, and what evidence supports each part.

That is why the project keeps separating things that ordinary wine databases mix together: grape identity, physical vineyard identity, legal label rights, vintage conditions, fermentation mechanics, commercial observation, simulation priors, and uncertainty.

The goal is to make the simulator capable of producing incredibly obscure wines—tiny commercial varieties, PIWIs, experimental bottlings, unusual countries, tiny named sites—without giving it permission to invent impossible combinations. **Obscurity is desirable; impossibility is not.**

---

# 1. MACHINE OBJECTIVE

Treat this project as a temporally versioned, provenance-aware, jurisdiction-sensitive world-wine knowledge graph coupled to viticultural, cellar, legal, commercial, and bottle-evolution simulators.

Let:

- `K` = coverage breadth;
- `D` = depth;
- `L` = legal precision;
- `P` = physical/process precision;
- `T` = temporal precision;
- `E` = evidence quality;
- `C` = cross-engine consistency;
- `R` = runtime usability;
- `H` = hidden fabricated specificity;
- `FP` = false-positive legality/existence;
- `FN` = false-negative availability.

Optimize roughly:

`U = Σ(w_i * positive_i) - λH*H - λFP*FP - λFN*FN`

with `λFP >> λFN` for protected-origin law and `λH` very high.

This implies:

1. legal validation fails closed;
2. scientific/process uncertainty fails explicit;
3. `UNKNOWN` is a first-class state;
4. commercial absence is not impossibility;
5. a model prior is never silently promoted into a fact;
6. a current rule is never silently back-cast to a historical vintage.

Do not optimize for apparent completeness.

---

# 2. REPOSITORY IS CANONICAL; SEPTEMBER 6 WORKBOOKS ARE DELTAS

The live repository is substantially more mature than the temporary September 6 workbooks. It already has executable, tested knowledge modules. Therefore **do not create a parallel spreadsheet-derived engine**.

High-salience live modules include:

```text
sommelier_v2/
  README.md
  authoritative_catalog.py
  catalog.py
  commercial_provenance.py
  generation.py
  domain.py
  knowledge/
    schema.py
    catalog.py
    expanded_catalog.py
    priors.py
    vineyard_registry.py
    vineyard_engine.py
    legal_vineyard_engine.py
    vineyard_legal_constraints.py
    vineyard_ownership.py
    vineyard_yield_adjustments.py
    site_claims.py
    site_research.py
    site_sources.py
    vintage.py
    vintage_engine.py
    vintage_indices.py
    historical_vintages.py
    harvest_lot.py
    harvest_must.py
    fermentation_engine.py
    fermentation_process.py
    fermentation_chemistry.py
    fermentation_guidance.py
    extraction_process.py
    maturation_process.py
    packaging.py
    finished_wine.py
    bottling_lot.py
    bottle_lifecycle.py
    aging.py
    blend_chemistry.py
    winery_blend_chemistry.py
    winery_provenance.py
    winemaking_decisions.py
    decision_runtime.py
    legal_rules.py
    legal_specs.py
    legal_sources.py
    legal_practice_bridge.py
    machine_legal_constraints.py
    national_varieties.py
    national_overrides.py
    jurisdiction_labels.py
    regional_rules.py
    trade_research.py
    smoke_taint.py
    process_chemistry_evidence.py
scripts/
  sync_legal_spec_sources.py
  extract_legal_spec_constraints.py
  sync_external_knowledge.py
  sync_external_knowledge_ci.py
  catalog_audit.py
  knowledge_audit.py
```

Repository doctrine already encoded and MUST be preserved:

- `knowledge/schema.py`: factual identity/legal data, researched attributes, and simulation priors are separated. Unknowns remain `None`. Missing facts must not become fake facts.
- `knowledge/legal_specs.py`: legacy `primary_grapes` is explicitly not a legal authorization list. Strict legal specs separately evaluate legal blends, production limits, analytical limits, process, aging, release, and temporal validity. Unknown complete-validation rules fail closed.
- `knowledge/decision_runtime.py`: qualitative decisions do not manufacture analytical values. Protected-designation execution fails closed and requires explicit legal confirmation when needed.
- `knowledge/fermentation_engine.py`: deterministic mechanics are simulator priors, not laboratory prediction claims.
- `knowledge/vintage_engine.py`: historical simulation must use observed or explicitly generated weather with provenance; it must not invent historical weather.

Any September 6 row/rule must follow:

```python
if repo_has_equivalent_semantics:
    map_to_existing()
elif repo_is_weaker:
    extend_existing_minimally()
elif repo_conflicts_with_handoff:
    create_conflict_record()
    verify_primary_source()
    add_regression_test()
elif handoff_item_is_model_prior:
    keep_as_prior_only()
else:
    add_typed_provenance_record()
```

No bulk workbook import.

---

# 3. EPISTEMIC TYPE SYSTEM

Every material proposition should be typeable approximately as:

```yaml
subject_id: stable-id
predicate: controlled-predicate
value: typed-value
scope:
  jurisdiction: optional
  geographic_scope: optional
  effective_from: optional
  effective_to: optional
  product_variant: optional
epistemic_class:
  - authoritative_legal
  - authoritative_registry
  - official_statistical
  - peer_reviewed_measurement
  - institutional_technical
  - producer_declared
  - importer_distributor_observed
  - commercial_observed
  - historical_secondary
  - model_prior
  - derived
  - disputed
  - unknown
confidence: authoritative|high|medium|low|unresolved
source_ids: []
retrieved_at: ISO-8601
contradiction_group: optional
```

Recommended internal validation lattice:

```text
ALLOW_STRICT
ALLOW_SCOPE_LIMITED
BLOCK_HARD
BLOCK_TEMPORAL
BLOCK_LABEL_ONLY
WARN_RARE
WARN_RISK
UNKNOWN_REQUIRED_RULE
UNKNOWN_IDENTITY
UNKNOWN_HISTORICAL_RULE
UNKNOWN_SITE_CONTAINMENT
DISPUTED
EVIDENCE_ONLY
MODELED
```

Public UI may collapse these to `ALLOW / BLOCK / WARN / UNKNOWN`; storage must not.

---

# 4. SOURCE PRECEDENCE IS PROPOSITION-SPECIFIC

## Legal propositions

```text
effective statute/regulation/homologated product specification
> competent authority current register
> official consolidated guidance
> interprofessional body / ODG summary
> producer interpretation
> merchant/trade text
> model prior
```

Recency does not override legal force. A new marketing page does not supersede an older still-effective legal instrument.

## Botanical identity

```text
VIVC / curated genetic-passport authority
+ national official catalogue where legal registered names matter
+ PlantGrape / INRAE-IFV for French variety/clone data
> nursery
> producer
> importer
> string normalization
```

String equality has no botanical authority.

## Physical site identity

```text
official cadastral/GIS/deposited delimitation
> competent vineyard register
> official appellation map
> cadastral parcel source
> producer parcel disclosure
> trade map
```

Physical containment and legal label entitlement are separate predicates.

## Commercial occurrence

Use official planting statistics, vineyard registers, direct producer bottlings, importer/distributor records, nursery records, official competitions/certification and other direct observations. These can prove occurrence; they do not automatically prove GI legality.

---

# 5. PRIMARY RESEARCH AUTHORITIES

## VIVC / Julius Kühn-Institut

JKI describes VIVC as documenting worldwide grapevine diversity, including roughly 23,500 varieties, wild species and breeding lines, with passport/description data and bibliography.

- https://www.julius-kuehn.de/en/zr/information-grapevine-and-wine
- https://www.vivc.de/

Use VIVC IDs as preferred global botanical identity anchors. Preserve source spellings and synonyms. Never collapse homonyms.

## PlantGrape / INRAE-IFV

- https://www.plantgrape.fr/

Use for French variety and clone detail: phenology relative to reference material, clone numbers, clone origin/selection, agronomic and technological notes. Collection phenology is not a universal site phenology rule.

## EU eAmbrosia

- https://ec.europa.eu/agriculture/eambrosia/geographical-indications-register/
- https://agriculture.ec.europa.eu/farming/geographical-indications-and-quality-schemes/geographical-indications-registers_en

Use as legal GI/source-document index. Repository already has source indexing, document discovery, deny-safe extraction and strict reviewed specs. Extend those workflows; do not replace them with unreviewed LLM extraction.

## OIV 2026 standards

- https://www.oiv.int/what-we-do/standards

Use as international technical taxonomy and definition source: International Code of Oenological Practices, International Oenological Codex, analytical methods, labeling standards. **OIV admission is not automatic national/GI authorization.**

## United States / TTB

- https://www.ttb.gov/regulated-commodities/beverage-alcohol/wine/american-viticultural-area-ava
- https://www.ttb.gov/regulated-commodities/beverage-alcohol/wine/labeling-wine/wine-labeling-appellation-of-origin

Model AVAs as origin/label systems, not EU-style appellations with assumed grape lists. An AVA claim generally depends on origin percentage and finishing conditions. Also model varietal designation, vintage/origin percentages, estate bottled, state/county claims and foreign-origin interaction.

## Wine Australia

- https://www.wineaustralia.com/labelling/register-of-protected-gis-and-other-terms
- https://www.wineaustralia.com/labelling

Model registered GIs and Label Integrity Program semantics: origin/variety/vintage truthfulness and blending percentages. Do not force EU `allowed_grapes` semantics into Australian GIs.

## New Zealand / IPONZ

- https://www.iponz.govt.nz/get-ip/geographical-indications/register/

Store registration/status, nested local GI relationships, legal conditions and boundaries where available. Again, do not model as EU PDO by default.

## Germany / Rheinland-Pfalz Weinbergsrolle

- https://www.lwk-rlp.de/weinbau/rebflaechen/weinlagen

Official source for narrower geographic wine names including Bereich, Großlage, Einzellage and related boundary/municipality semantics. Preserve Germany-specific types. `Einzellage != climat != Ried` except at a very abstract common superclass.

## Austria / Lower Austria open Ried data

- https://www.noe.gv.at/noe/OGD_Detailseite.html?id=a22e57c2-bbb0-4fb9-a731-b7f675e48476

Fields include Ried/Subriede, cadastral and political municipalities, GIS identifier, implementation status and update information. Source explicitly states coverage is not yet statewide complete. Missing row/geometry therefore does not mean nonexistence.

## Vienna Riedenkarte

- https://www.wien.gv.at/umwelt/weinbaufluren-riedenkarte

Official city map states coverage of all 140 Vienna Weinbaurieden with parcel-level organization. Finite high-value ingest target after higher-priority identity/legal reconciliation.

---

# 6. VARIETY IDENTITY PROGRAM — NEXT HIGH-LEVERAGE DATA WORK

September 6 source workbook observations:

- `1,998` global source-variety rows;
- `4,807` country-variety observations;
- `14` normalization-collision groups discovered in the temporary identity audit.

The source workbook is a **commercial planted-area observation dataset**, not the botanical master.

Target identity object:

```yaml
VarietyIdentity:
  canonical_id:
  vivc_id:
  prime_name:
  source_spellings: []
  synonyms: []
  homonyms: []
  transliterations: []
  color:
  species:
  interspecific:
  pedigree:
  breeder:
  breeding_station:
  breeding_year:
  origin:
  resistance:
    piwi_status:
    loci:
      Rpv: []
      Ren: []
      Run: []
      other: []
  use_roles: []
  clone_ids: []
  national_catalogue_names: {}
  commercial_observations: []
  source_ids: []
```

Resolver sequence:

```text
source name
 -> normalization candidates
 -> exact VIVC match
 -> VIVC synonym match
 -> national-catalogue corroboration
 -> country/context disambiguation
 -> pedigree/color/species consistency checks
 -> confidence class
 -> canonical identity OR unresolved candidate
```

Suggested resolution levels:

```text
R5 authoritative_exact_id
R4 authoritative_synonym_confirmed
R3 multi_source_probable
R2 string_context_candidate
R1 unresolved
R0 conflicting_identity
```

Only R4/R5 may automatically attach to legal rules unless a jurisdictional catalogue independently proves the required relation.

Commercial-area semantics:

```text
positive area -> occurrence evidence
missing/null -> UNKNOWN
zero -> source-specific census zero, not biological impossibility
historical positive/current missing -> historical occurrence, not extinction proof
```

Do not require arbitrary acreage for `commercial`. Tiny positive plantings must survive.

Suggested status tags:

```text
germplasm_only
experimental
microcommercial
commercial_tiny
commercial
historical_decline
reintroduced
unknown
```

### PIWI/resistant varieties

Do not reduce to `PIWI=true`. Store breeder/cross, species contribution where known, resistance loci, national registration, GI eligibility, first plantings, hectares and actual commercial wines. This is needed for disease simulation and legal validation.

---

# 7. GEOGRAPHY / SITE ONTOLOGY

Do not force all named wine geographies into a single `vineyard` type.

Abstract superclass may be `NamedWineGeography`, but preserve concrete semantics:

```text
climat
lieu_dit
premier_cru_climat
grand_cru_AOC
monopole
parcel
block
Einzellage
Gewann
Großlage
Bereich
Ried
Subriede
MGA
UGA
menzione_geografica_aggiuntiva
paraje
quinta
cru
single_vineyard_designation
AVA
sub_AVA
...
```

Separate:

```yaml
PhysicalSite:
  site_id:
  canonical_name:
  jurisdiction_site_type:
  containing_origins: []
  municipality:
  cadastral_ids: []
  geometry:
  geometry_source:
  geometry_version:
  area_ha:
  slope:
  aspect:
  elevation:
  soils:
  ownership_history:
  planted_variety_observations: []
  aliases: []
  source_ids: []

LegalSiteClaim:
  claim_id:
  site_id:
  legal_origin_id:
  label_form:
  classification:
  color_scope:
  variety_scope:
  effective_from:
  effective_to:
  label_conditions:
  status:
  source_ids: []
```

Null physical attributes remain null. Do not copy appellation geology/elevation/ownership to each site.

---

# 8. BURGUNDY CLOSEOUT CONTRACT

User explicitly selected **Grand Cru + Premier Cru** as the current Burgundy completion scope. Do not begin by ingesting every one of the 11,000+ village-level climats/lieux-dits.

September 6 verified temporary tranche:

- 33 Grand Cru AOCs;
- 31 Premier Cru parent AOCs;
- 668 active Premier Cru appellation-climat claim rows;
- 32 Grand Cru legal subdenomination rows;
- all 31 parent count checks passed in the workbook.

These are reconciliation assertions, not license to overwrite repository Burgundy data. The repository already has extensive Burgundy tests and datasets.

Critical edge cases to preserve/test:

### Chablis Grand Cru
One GC AOC with seven legal named climat denominations:

`Blanchot, Bougros, Grenouilles, Les Clos, Preuses, Valmur, Vaudésir`

Legal source spelling encountered was `Preuses`, not common/merchant `Les Preuses`. Search may recognize aliases; exact legal label output must use legal form.

### Corton
Keep physical area, GC AOC, climat label supplements and color scope separate. Red Corton may use authorized climat suffixes under loaded rule; do not generalize that privilege to white Corton.

### Corton-Charlemagne / Charlemagne
Separate legal identities. Do not append component climat names to Corton-Charlemagne unless explicit legal rule permits. Charlemagne may remain legal while commercially dormant; legality and commercial use are distinct fields.

### Charmes-Chambertin / Mazoyères-Chambertin
Shared delimitation can coexist with distinct legal AOC identities. Geometry overlap does not collapse claims.

### Monthélie
September 6 audit found source conflict. Handoff stance:
- canonical active PC set in temporary tranche = 15;
- `Les Hauts Brins` excluded from current active set;
- `Les Crays` quarantined as disputed/non-generatable pending effective primary legal resolution.

Before modifying repository code, re-run primary source and existing test reconciliation.

### Marsannay Premier Cru
2026 committee/classification progress is not equivalent to final effective label law. Keep 14 candidates pending/non-generatable until effective homologated specification + temporal rule exists.

Burgundy GC/PC is done enough when every active claim maps to repository-native IDs, temporal/color/grape/site semantics are typed, aliases are separated from legal strings, edge tests pass and no active claim remains unmapped.

Village-level exhaustive Burgundy is deferred.

---

# 9. LEGAL ENGINE ROADMAP

Preserve repository's three trust levels:

## A — authoritative source index
Proves GI/document existence and status. Does not approve a wine.

## B — deny-safe machine extraction
Can reject clearly unauthorized outsider claims where extraction is bounded and reliable. It does not automatically approve insiders unless completeness for that proposition is proven.

## C — reviewed strict specification
May positively authorize grape/blend/product/yield/maturity/process/aging/release/bottling/site/label claims within exact temporal scope.

Every strict rule should support:

```yaml
effective_from:
effective_to:
source_version:
supersedes:
amendment_chain:
```

Temporal anchors may differ:
- harvest/vintage date;
- production date;
- bottling date;
- release date.

Validation question is not “would this be legal today?” but “was this exact claim legal under the rule applicable to this wine at the relevant time?”

Do not make one universal jurisdiction spec. Prefer strategy objects such as:

```python
LegalJurisdictionStrategy:
    validate_origin()
    validate_variety_claim()
    validate_vintage_claim()
    validate_site_claim()
    validate_process()
    validate_composition()
    validate_label()
    validate_release()
```

Specialize for EU PDO/PGI, US TTB/AVA, Australia LIP/GI, NZ GI, South Africa WO, Argentina, Chile, Canada VQA, etc.

---

# 10. VINTAGE ENGINE TARGET

Current repository daily-weather engine is a sound mechanistic substrate; generic thresholds must progressively become site-/variety-calibrated and provenance-aware.

Target causal chain:

```text
weather(t)
+ physical site
+ soil/water state
+ variety/clone
+ rootstock
+ canopy/viticultural operations
+ disease inoculum/pressure
+ irrigation
+ crop load
 -> phenology(t)
 -> water_status(t)
 -> canopy_status(t)
 -> disease_state(t)
 -> berry_growth(t)
 -> sugar/acid/phenolic/aroma state(t)
 -> fruit health(t)
 -> harvest decision distribution
 -> HarvestLot / MustComposition
 -> fermentation
```

Preserve stage-specific climate, not just annual/seasonal aggregates:

```text
dormancy -> budbreak -> prebloom -> bloom/set -> closure -> veraison -> harvest -> postharvest
```

Required hazards/processors:
- post-budbreak frost;
- hail;
- heatwave/extreme heat;
- hot nights;
- water deficit/drought;
- bloom cold/rain;
- powdery mildew;
- downy mildew;
- Botrytis;
- ripe/sour rot;
- wildfire smoke;
- preharvest rain;
- wind/desiccation where material.

Weather source metadata must include source, spatial resolution/station, temporal resolution, distance/interpolation, and whether observed or generated. City-station data must not masquerade as vineyard weather without uncertainty.

Vintage engine should emit measured or uncertain priors into `HarvestLot` / `MustComposition`:
- Brix/sugars;
- pH;
- TA;
- malic/tartaric;
- YAN;
- potassium;
- anthocyanin/tannin indices;
- rot/damage;
- smoke marker context;
- berry integrity;
- actual receival temperature if observed.

Air temperature is not must temperature.

---

# 11. FERMENTATION ENGINE TARGET

Do not replace executable mechanics with prose heuristics. Extend repository state/process models.

Desired sparse rich state can include:

```text
glucose, fructose, ethanol, microbial biomass by taxon,
YAN components, bulk temp, cap temp, dissolved O2, dissolved CO2,
pressure, pH, TA, malic, lactic, tartaric, K, free/total SO2,
VA, acetic acid, acetaldehyde, glycerol, H2S/reduction,
phenolic extraction, anthocyanin/tannin state, solids/turbidity,
vessel/headspace, lees, microbial risk, fault state
```

Process graph should be composable across:
- receival/sorting;
- destemming/crushing;
- direct press and fractions;
- settling/flotation/centrifuge;
- pre-fermentation skin contact/cold soak;
- hyperoxidation/inert protection;
- SO2, acidification/deacidification, enzyme use;
- must concentration/cryoextraction;
- appassimento/raisining;
- noble-rot selection;
- spontaneous/inoculated/sequential/co-inoculated fermentation;
- Saccharomyces/non-Saccharomyces;
- nutrient type/timing;
- controlled aeration;
- vessel/temperature schedule;
- pump-over/punch-down/delestage/submerged cap;
- carbonic/semi-carbonic;
- thermovinification/warm final/extended maceration;
- fermentation interruption;
- devatting/pressing;
- spontaneous/inoculated/co-inoculated/suppressed MLF;
- lees/batonnage;
- wood/concrete/amphora;
- micro-oxygenation;
- flor/oxidative aging;
- fortification;
- bottle/tank/ancestral sparkling;
- tirage/riddling/disgorgement/dosage;
- stabilization/filtration;
- bottling/closure.

Add microbial-agent typing rather than generic yeast labels:

```yaml
MicrobialAgent:
  taxon:
  strain:
  commercial_name:
  source:
  temperature_tolerance:
  ethanol_tolerance:
  nitrogen_demand:
  fructophilicity:
  killer_status:
  H2S_prior:
  VA_prior:
  glycerol_prior:
  aroma_metabolite_priors:
  MLF_compatibility:
```

Specific performance requires strain evidence. OIV characterization dimensions are taxonomy/technical anchors, not universal numeric performance.

Do not universalize YAN targets, MLF tolerance, “cold fermentation”, oak coefficients, SO2 antimicrobial effect, or extraction response. Prefer response surfaces/distributions and bounded priors with provenance.

---

# 12. AGING / BOTTLE EVOLUTION

Repository already has aging/bottle-lifecycle code. Increase mediation by actual wine state.

Forbidden shortcut:

```python
peak_age = critic_vintage_score / k
```

Target mediation:

```text
harvest chemistry
+ fermentation chemistry
+ extraction
+ MLF
+ SO2
+ oxygen history
+ vessel/lees history
+ filtration
+ packaging TPO
+ closure OTR
+ bottle format
+ storage
+ microbial stability
 -> latent bottle state
 -> probabilistic development curve
```

Internal curve dimensions should include primary retention, tertiary emergence, tannin evolution, freshness, oxidation/reduction risk, microbial divergence, sediment, condition and utility-by-age. User-facing drinking windows may be derived later.

Vintage weather should affect aging primarily through measured/modeled wine composition and process state, not through a direct arbitrary vintage-score channel.

---

# 13. COMMERCIAL OBSERVATION CENSUS

This is discovery/occurrence evidence, not legal authority.

Sources:
- producer portfolios;
- importer books;
- distributor catalogs;
- producer associations;
- nursery catalogs;
- competition/technical sheets;
- customs/trade data where useful;
- restaurant/retail only as weaker discovery evidence.

Record approximately:

```yaml
CommercialObservation:
  observation_id:
  producer_id:
  wine_name:
  vintage:
  country:
  claimed_origin:
  claimed_site:
  claimed_varieties:
  process_claims:
  importer:
  distributor:
  market:
  observed_date:
  source_url:
  evidence_strength:
```

Unusual observation should trigger identity/legal/site research. It never silently upgrades legality.

---

# 14. CROSS-ENGINE VALIDATION PIPELINE

Canonical sequence:

```text
identity
 -> botanical coherence
 -> physical geography containment
 -> temporal validity
 -> legal origin
 -> legal encepagement / color / composition
 -> legal process
 -> vintage coherence
 -> fermentation/process coherence
 -> mass/composition balance
 -> label claims
 -> commercial occurrence / rarity
 -> evidence audit
```

If an upstream required hard rule is `UNKNOWN`, downstream `ALLOW_STRICT` is impossible. The engine may still create an explicitly unresolved exploratory object.

Core regression concepts from September 6 to reconcile into repository-native tests:

1. Chablis Grand Cru + Pinot Noir -> BLOCK.
2. Chablis Grand Cru + Chardonnay + legal `Preuses` -> potentially ALLOW.
3. exact legal output `Les Preuses` -> do not silently treat as legal suffix.
4. red Corton + authorized climat -> potentially ALLOW.
5. white Corton + red-only climat suffix -> BLOCK.
6. Corton-Charlemagne + component climat suffix -> BLOCK.
7. Charlemagne current commercial generation -> WARN/dormant, not illegal.
8. Marsannay Premier Cru pending -> BLOCK current PC label.
9. disputed Monthélie `Les Crays` -> unresolved/BLOCK current pending proof.
10. carbonic with zero whole grapes -> BLOCK.
11. carbonic with whole grapes + CO2 + correct venting -> process-compatible.
12. ancestral bottling after alcoholic fermentation completion -> BLOCK.
13. ordinary ripe-grape harvest before veraison -> BLOCK.
14. country planting presence + unknown GI permission -> UNKNOWN, never legal allow.
15. tiny positive planted area -> retain occurrence evidence.

Every impossible-wine bug becomes a regression test.

---

# 15. TEST STRATEGY

Use:

```text
unit:
  normalization, temporal intervals, composition balance, state transition, legal predicates
fixture:
  obvious valid, obvious invalid, edge appellation, historical rules, rare variety, overlapping site
property:
  no negative blend percentages; sums reconcile; chronology monotonic;
  no legal approval from observation-only evidence;
  no simulation prior exposed as authoritative fact
differential:
  machine-extracted vs reviewed strict specs; current vs historical rules; source revision
fuzz:
  Unicode/diacritics; aliases/homonyms; nulls; contradictory sources
```

Do not weaken repository tests to make new data pass.

---

# 16. CONFLICT PROTOCOL

When sources disagree, persist the conflict:

```yaml
ConflictRecord:
  conflict_id:
  proposition:
  candidates:
    - value:
      source:
      effective_date:
      authority_type:
  resolution:
    status: unresolved|resolved
    selected_value:
    rationale:
  generator_policy: block|unknown|scope_limit
```

Never average legal rules, silently pick the newest webpage, or overwrite one source with another.

---

# 17. PHASED ASTRA EXECUTION PLAN

## PHASE 0 — baseline/reconciliation

1. Fetch current branch head.
2. Run full tests.
3. Read this handoff.
4. Read core repository knowledge modules and sync scripts.
5. Inspect September 6 handoff research seed/artifacts.
6. Produce a reconciliation matrix: represented / missing / contradictory / superseded / candidate migration.
7. Do not add a second ontology.

Acceptance: baseline tests pass; every proposed addition has a destination in existing architecture or a justified minimal schema extension.

## PHASE 1 — Burgundy GC/PC final reconciliation

Map temporary 668 PC rows, 33 GC identities and 32 GC subdenomination records to repository data. Re-research only conflicts/gaps. Add exact-label and temporal regressions. Mark GC/PC scope complete.

## PHASE 2 — variety identity resolution

Process source names in batches of roughly 100–250. Priority:
1. 2023 positive-area varieties;
2. historical positive-area varieties;
3. PIWI/resistant material;
4. commercially observed extras;
5. germplasm tails.

Output canonical IDs, unresolved queue, collision report and tests.

## PHASE 3 — world legal rules

Expand strict/historical GI validation. Suggested initial jurisdiction order by encounter probability and documentation leverage: France, Italy, Spain, Portugal, Germany, Austria, US, Australia, NZ, South Africa, Argentina, Chile, Canada, Greece, Hungary, Georgia, Switzerland, Balkans/Eastern Europe, then remaining wine jurisdictions. Parallelize where eAmbrosia or official machine-readable sources make it efficient.

## PHASE 4 — named-site registries

After legal/identity core: Germany Lage/Gewann; Austria Ried/Subriede; legally defined Italian MGA/UGA and other high-value systems. Do not block global progress on exhaustive low-value site enumeration.

## PHASE 5 — fermentation science

Reconcile September 6 process/risk inventory into executable modules. Add microbial strain/species parameters, nutrient timing, oxygen timing, extraction kinetics, vessel dynamics, MLF interactions, spoilage/fault pathways, sparkling pressure/sugar, fortification/flor/appassimento/botrytis/carbonic. Label every coefficient as empirical, calibrated, institutional guide, or heuristic prior.

## PHASE 6 — vintage calibration/data

Add real weather/site/variety historical observations. Start where commercial relevance, geographic precision, weather access and existing repository vintage records intersect. Preserve uncertainty.

## PHASE 7 — commercial discovery

Continuously ingest producer/importer/distributor/planting observations into a discovery queue for obscure varieties/sites/processes.

## PHASE 8 — aging calibration

Increase bottle-evolution calibration only after upstream chemistry/process state is reliable enough.

---

# 18. PRIORITY FUNCTION

Approximate task priority:

```text
priority =
  encounter_probability
* information_gain
* constraint_value
* legal_risk_reduction
* downstream_reuse
* source_accessibility
/ expected_effort
```

Boost rules that prevent many impossible wines, resolve identity collisions, apply across many appellations, or unlock several engines.

Downweight decorative terroir prose, exhaustive low-value village lieux-dits, owner histories before site identity, and precise sensory values with weak evidence.

---

# 19. DO NOT DO

1. Do not treat `primary_grapes` as legal authorization.
2. Do not treat country planted area as GI authorization.
3. Do not merge identities by lowercase/accent folding/fuzzy match.
4. Do not treat physical named-site existence as label entitlement.
5. Do not apply current law to historical vintages automatically.
6. Do not treat OIV-admitted practice as local permission.
7. Do not copy appellation geology/elevation to every vineyard.
8. Do not copy regional vintage score to every site.
9. Do not derive harvest chemistry from critic scores.
10. Do not derive aging windows directly from weather scores.
11. Do not replace factual `None` with plausible values.
12. Do not store model priors without explicit provenance/type.
13. Do not use EU legal semantics as default US/AU/NZ semantics.
14. Do not overfit famous wines and exclude obscure legal possibilities.
15. Do not spend the next major tranche on all Burgundy village lieux-dits.
16. Do not delete legacy data until adapters/migrations prove redundancy.
17. Do not let importer/merchant data supersede primary law.
18. Do not interpret no importer as no wine.
19. Do not interpret no census row as extinct.
20. Do not conflate clone, mutation, variety, breeding line and synonym.
21. Do not conflate owner/control with site identity.
22. Do not conflate monopole and climat.
23. Do not conflate appellation name and physical vineyard.
24. Do not write a new simulator beside `sommelier_v2`.
25. Do not simplify the stored ontology merely for human readability.

---

# 20. REPRODUCIBILITY / VERSIONING

Every canonical generated wine should eventually be reproducible from:

```text
random seed
+ code commit
+ knowledge snapshot version
+ legal snapshot/source versions
+ identity snapshot
+ site-registry snapshot
+ vintage dataset/model version
+ fermentation parameter/model version
```

Long-term construct: `WineProvenanceFingerprint`.

A generated wine should be able to return structured provenance answering:

```text
WHY this grape?
WHY this origin?
WHY this site?
WHY this vintage state?
WHY this harvest chemistry?
WHY this process?
WHY this legal label?
WHY this rarity?
WHY this aging path?
WHAT is observed vs modeled?
WHICH rules blocked alternatives?
```

This means structured rule/source traces, not hidden chain-of-thought.

---

# 21. RESEARCH TRANCHE COMPLETION GATES

A research tranche is not done because prose was written.

It must end in at least one repository-native artifact: normalized data, code table, tested dataclass records, source ledger, migration or regression suite.

### Identity tranche
- unresolved rate measured;
- collisions retained;
- no ambiguous auto-merge;
- source IDs retained.

### Legal tranche
- authority class known;
- temporal scope known or explicitly unknown;
- completeness typed;
- allow-vs-deny semantics explicit;
- outsider and insider tests.

### Site tranche
- physical identity separated from legal claim;
- source/version/geometry metadata stored;
- coverage completeness declared.

### Vintage tranche
- observed/generated distinction;
- spatial/temporal resolution recorded;
- model/version recorded;
- no critic-score substitution.

### Fermentation tranche
- process executable or explicitly taxonomy-only;
- coefficient provenance typed;
- preconditions/constraints checked;
- legal authorization separate.

---

# 22. SEPTEMBER 6 RESEARCH DELTAS

The ChatGPT checkpoint created these temporary research artifacts. Their operative machine semantics should be reconciled, not treated as parallel canonical databases:

- `Burgundy_GC_PC_Registry_VERIFIED_2026-09-06.xlsx`
- `wine_knowledge_v2_fermentation_engine_v1.xlsx`
- `wine_knowledge_v2_vintage_engine_v1.xlsx`
- `wine_knowledge_v2_cross_engine_validator_v1.xlsx`
- `wine_knowledge_v2_variety_identity_engine_v1.xlsx`
- `wine_knowledge_v2_validator.py`
- `wine_knowledge_v2_validator_regression_results.json`
- `varieties_2000_to_2023.xlsx`
- `VINEYARD_REGISTRY.md`
- `WINE_KNOWLEDGE_V2_CANONICAL_CHECKPOINT_2026-09-06.md`

Temporary workbook inventories:

### Fermentation research delta
- 62 state variables
- 88 process nodes
- 40 constraints
- 26 interaction effects
- 18 fault modes
- 20 pathway templates
- 11 OIV practice mappings
- 14 numerical guide rows

### Vintage research delta
- 75 variables
- 8 phenology windows
- 13 event metrics
- 25 constraints
- 18 output dimensions
- 11 bottle-curve interface fields
- 9 fermentation bridge mappings

### Cross-engine delta
- 1,998 world source observations
- 4,807 country-variety observations
- 13 validation layers
- 40 cross-engine rules
- 15 fixtures

### Prototype validator
15/15 local fixtures passed when created. Mine the tests/invariants; do not replace repository validation runtime.

A machine-readable reconciliation seed should accompany this handoff where available. Its content is research input, not canonical data.

---

# 23. SUCCESS STATE

The mature system should handle requests such as:

> Generate a commercially plausible 2021 white wine from an obscure legally usable variety in a named Austrian Ried, with a process that is legally compatible, physiologically plausible for the vintage, chemically coherent, and rare enough that a serious buyer might actually discover it.

Return structured identity certainty, legal source chain, site source, vintage inputs, process trace, chemistry state, commercial evidence, uncertainty and blocked alternatives.

Or:

> Could a 1998 wine with this exact vineyard, grape and appellation legally exist?

Validate against 1998 law, not 2026 law.

Or:

> Find a commercially planted grape with enormous acid/tannin/structure and minimal fruit expression, then show where a real legal wine using it could exist.

Search structured properties, then constrain with identity, geography and law. Do not invent a fantasy bottling.

---

# 24. ASTRA BOOT SEQUENCE

```text
BOOT-01 fetch current branch head
BOOT-02 run full repository tests
BOOT-03 read this handoff fully
BOOT-04 inspect core knowledge modules and sync pipelines
BOOT-05 reconcile any accompanying September 6 machine seed
BOOT-06 produce HANDOFF_RECONCILIATION.md
BOOT-07 reconcile Burgundy GC/PC deltas
BOOT-08 establish VIVC resolver pipeline
BOOT-09 resolve first priority identity batch
BOOT-10 add tests + canonical records
BOOT-11 continue world legal-rule expansion
```

Do not begin by writing a new architecture or by producing a user-facing summary. Begin with repository/test/reconciliation work.

---

# 25. CHECKPOINT ASSERTIONS

Treat these as assertions requiring preservation or explicit primary-source/repository refutation:

```yaml
repository:
  canonical_architecture: sommelier_v2
  legal_mode: fail_closed
  missing_fact_policy: preserve_unknown
  model_priors: explicitly_typed
burgundy_scope:
  current_completion: GC_and_PC
  exhaustive_village_lieux_dits: deferred
commercial_area_source:
  global_source_rows: 1998
  country_variety_observations: 4807
september6_fermentation_delta:
  state_variables: 62
  process_nodes: 88
  constraints: 40
  interaction_effects: 26
  fault_modes: 18
  pathway_templates: 20
september6_vintage_delta:
  variables: 75
  phenology_windows: 8
  event_metrics: 13
  constraints: 25
prototype_validator:
  passed: 15
  total: 15
```

If contradicted by the current repository or a better primary source: record the contradiction, correct canonical state, add a regression test and document the resolution. Do not preserve a handoff assertion blindly.

---

# 26. FINAL DIRECTIVE

This project is not a wine-facts dataset. It is a **temporally versioned, provenance-aware, jurisdiction-sensitive, physically constrained world-wine registry + legal validator + vineyard/vintage model + cellar-process simulator + commercial observation system**.

Generative principle:

> Generate from the intersection of what exists, what existed then, what law permits, what the site/vintage biology supports, what cellar mechanics can produce, and what evidence justifies.

Epistemic principle:

> Never manufacture certainty merely to complete a wine object.

Coverage principle:

> Obscurity is desirable; impossibility is not.

Engineering principle:

> One canonical architecture; additive researched tranches; regression before expansion.

Project-management principle:

> Prefer high-leverage identity and constraint work over decorative completeness.

Continue aggressively. Do not restart. Do not human-simplify the stored ontology. Do not loosen fail-closed legal behavior. Do not confuse rarity with error, missing data with impossibility, plausibility with evidence, or commercial occurrence with legal authorization.

Build toward a registry capable of surviving adversarial questions from a Master of Wine, appellation lawyer, viticultural scientist, enologist, historian, importer and database engineer simultaneously.
