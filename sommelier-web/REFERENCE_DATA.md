# Reference-data policy

The game separates **factual wine reference data**, **historical evidence**, **legal/product rules**, **fictional commercial simulation**, and **simulation-derived sensory matrices**.

## Hard rule

The engine must not invent a country, wine region, geographical indication, appellation, commune, formally named vineyard/cru, classification, grape variety, historical weather event, legal ageing rule, old-vine indication, or winemaking permission and present it as real.

Generated producers, estates, cuvées, commercial prices, quantities, allocations, restaurant demand, bottle survival and storage histories may be fictional. They must be marked as fictional and remain plausible for validated geography, grapes, product rules and period.

## Current data layers

1. **Original detailed model.** Hundreds of deeply modeled grapes plus the original region/appellation hierarchy, tasting structure, aromas, viticulture and winemaking affinities. `src/game/reference.ts` adapts this into the generation-safe layer.
2. **Authoritative identity/index layer.** Current normalized indices contain 1,997 prime winegrape records, 60 winegrape-growing countries, 613 statistical planting geographies, 280 U.S. AVAs and 1,665 EU wine GIs. Statistical geography is never relabelled as a legal GI.
3. **Hand-researched legal/appellation overlay.** Legal hierarchy, grapes, product categories, ageing/release rules, classifications, named subzones/sites, yields, analytical limits, production rules and unresolved questions. Twelve provenance-source passes are currently registered.
4. **Environmental layer.** Three research passes currently supply 26 place-specific climate/geology/soil/topography models across at least 12 countries. Numeric matrix effects are explicitly simulation-derived.
5. **Detailed growing-season layer.** Three passes currently supply 17 structured vintage observations plus published categorical authority ratings. Unsourced legacy `VINTAGE_QUALITY` scores are excluded.
6. **Historical vintage evidence ledger.** `historical_vintage_archives.json` can record centuries of documentary evidence without fabricating weather. The IVDP Vintage Port archive currently supplies documented authority years back to 1756; Ontario authority vintage reports are indexed from 2001-2025; Champagne's MATU monitoring history is acknowledged from 1956 without pretending its annual records have all been ingested.
7. **Legal ageing and vine-age layer.** `ageing_old_vine_rules.json` stores current product-specific ageing requirements and jurisdictional vine-age indications separately from sensory ageing. It currently includes Champagne, Rioja, Brunello, Port and Madeira examples plus OIV, South African, Barossa and Rioja vine-age rules.
8. **Winemaking decision layer.** `winemaking_decisions.json` models more than 35 distinct cellar decisions with more than 90 options across harvest, pre-fermentation, fermentation, pressing, post-fermentation, maturation, special-wine production, blending, sparkling production, pre-bottling and bottling. Regulated choices cannot be applied until the exact product/designation legality check passes.
9. **Global designation coverage controller.** `designation_registry_program.json` and `designationProgram.ts` require a coverage status for every one of the 60 currently verified winegrape-growing countries. EU/eAmbrosia and U.S./TTB are live normalized indices. Additional national authorities have been identified for Australia, New Zealand, Japan, Georgia, Argentina, Chile, South Africa, Ontario, British Columbia, Brazil, Mexico and the United Kingdom. Remaining jurisdictions stay visibly `pending-authority-discovery`; they are not silently omitted.

## Vintage, time and tasting notes

Vintage and time are different inputs.

### Vintage

A vintage describes the material produced by a particular growing season. When a sourced year-specific record exists, the simulation may derive bounded effects on:

- acidity and ripeness;
- concentration;
- tannin maturity;
- aromatic freshness;
- disease/selection pressure;
- yield;
- ageability;
- botrytis suitability when appropriate.

`noteEvolution.ts` then converts only sufficiently strong vintage effects into explicitly derived expression terms such as a riper fruit spectrum, concentrated expression or heightened aromatic freshness. Botrytis-linked descriptors are only available to a compatible sweet-botrytis archetype. If no sourced vintage record exists, no historical-weather aroma story is invented.

### Winemaking

Winemaking supplies secondary/process-derived character only after the selected techniques pass the exact designation/product legality gate. Modeled choices include, among others:

- picking maturity, hand/machine harvest and sorting;
- raisining and cryoselection;
- destemming, crushing, whole cluster and skin-contact policy;
- prefermentative cold soak;
- carbonic/semi-carbonic maceration;
- fermentation vessel, temperature, yeast strategy, cap management and oxygen;
- maceration length and press fractions;
- MLF and its timing;
- lees contact and bâtonnage;
- maturation vessel;
- oak origin/species, size, new-oak share, toast and barrel age;
- maturation length, topping/ullage and micro-oxygenation;
- flor/biological ageing;
- fortification and fortification timing;
- fractional and cross-vintage blending;
- traditional/tank/ancestral sparkling methods, lees ageing and dosage;
- clarification, filtration, sulfur management, bottling oxygen, closure and bottle format.

Potential sensory consequences are modeled separately from the technical/legal fact. For example, heavy toast can create a derived roast/smoke note potential; it is not asserted as a guaranteed aroma or a regulator-published measurement.

### Time

`ageing.ts` treats bottle time as a trajectory rather than a generic age score. Current broad phases are youth, development, mature, late-mature and fragile. Time can change the active tasting profile by:

- reducing primary fruit intensity;
- softening tannin;
- increasing savory/earth/tertiary expression;
- producing archetype-dependent mature notes;
- increasing sediment and fragile-bottle service risk.

Ageing speed is style-dependent. Structured dry reds, traditional-method sparkling wines, botrytized sweets, bottle-aged fortified wines and oxidative fortified wines do not share one clock. Storage quality further modifies the trajectory.

The current ageing archetypes are broad simulation categories, not substitutes for exact product rules. A future product resolver must distinguish, for example, dry Tokaj from Tokaji Aszú and Vintage Port from wood-aged Tawny/Colheita before assigning a final ageing pathway.

## Legal ageing is not bottle ageing

Mandatory production/release ageing is a legal constraint. Sensory ageing is a separate physical/simulation process.

Examples already stored include:

- non-vintage versus vintage Champagne minimum maturation;
- Rioja Crianza, Reserva and Gran Reserva red/white/rosé distinctions;
- Rioja quality sparkling levels at 15, 24 and 36 months;
- Brunello versus Brunello Riserva release/ageing requirements;
- Port Colheita and age-indication categories;
- Madeira Estufagem and Canteiro processes.

Current rules must not be projected backward into historical bottles. Historical legal versions need effective, amendment and repeal dates.

## Old vines and named vine-age indications

`Old Vine` is not a universal switch.

- The OIV international definition uses documented vines of at least 35 years, and an old-vineyard definition requiring at least 85% qualifying old vines.
- South Africa's Certified Heritage Vineyard system records qualifying vineyards and planting date information.
- The Barossa Old Vine Charter distinguishes Old Vine, Survivor, Centenarian and Ancestor tiers.
- Rioja `Viñedo Singular` is not treated as a generic old-vine synonym. It is a certified smaller-geographical-unit/product classification with a minimum vineyard age of 35 years plus manual harvest, lower yield limits, a 65% maximum processing yield, same-winery production/ageing/storage/bottling, traceability/exclusive-control requirements and double qualitative tasting.

The generator no longer assigns `Vieilles Vignes` or equivalent language randomly.

## Historical vintages and centuries-old bottles

The generator no longer uses a universal 45-year cap. Broad style-aware simulation horizons now permit archival inventory, but extreme age by itself is not evidence that a historical wine existed under a modern designation.

The preferred model is an authority year ledger:

- **structured-growing-season-ingested** — detailed season data are available;
- **authority-archive-detail-available** — an authority confirms the historical vintage/product entry and more detail can be extracted;
- **authority-report-available** — an official vintage report exists;
- **documentary-bottle-or-harvest-evidence** — existence evidence without a full season record;
- **monitoring-system-confirmed-detail-not-yet-ingested** — an annual monitoring system is known, but its specific year record is not yet captured;
- **unknown** — no claim is made.

A 1756/1790/1815-era Port record therefore can exist as documentary authority evidence without fabricating rainfall, phenology or today's DOP wording.

## Global GI / equivalent program

The target is exhaustive: **every legally recognized wine GI, appellation, denomination of origin, viticultural area and equivalent protected-origin system globally, with no fame or size threshold.**

Each final designation record should eventually include:

- protected identity/spellings/transliterations;
- protection class and legal system;
- registration, effective, amendment and repeal dates;
- hierarchy and parent/child geography;
- official boundaries/geometry where available;
- product categories/colors/styles;
- authorized/principal/prohibited grapes and blend/origin percentages;
- viticultural density, training, pruning, irrigation, yield and harvest rules;
- analytical parameters;
- required/permitted/prohibited winemaking practices;
- enrichment, acidification, sweetening and fortification rules;
- pressing/extraction/fermentation/vessel rules where specified;
- ageing/release requirements by level/style;
- traditional terms and reserved indications;
- old-vine/vine-age requirements;
- formal subzones, communes, crus, climats, MGAs, wards and named vineyards;
- soil, geology, topography and climate;
- historical vintage observations;
- historical legal version applicable to each vintage.

No small GI is intentionally excluded. Incomplete jurisdictions stay visible in the coverage queue until their primary authority and full registry have been ingested.

## Validation

Current automated tests separately validate:

- real geography/grape resolution;
- legal/appellation provenance;
- environmental and growing-season research;
- historical vintage archive evidence;
- legal ageing and vine-age rules;
- detailed winemaking decisions and legality gates;
- global designation coverage accounting;
- vintage/winemaking/time tasting-note layers;
- core service, pairing, inventory and economy behavior.

A factual layer must pass validation before it is allowed to drive generation. Unresolved synonyms, legal ambiguities and missing jurisdictions remain explicit research work rather than guessed data.
