# Reference-data policy

The game separates **factual wine reference data** from **fictional simulation content** and from **simulation-derived matrices**.

## Hard rule

The engine must not invent a country, wine region, geographical indication, appellation, commune, formally named vineyard/cru, classification, or grape variety and present it as real. Those entities must resolve to curated reference data before a generated bottle is valid.

Generated producers, estates, cuvées, commercial prices, quantities, allocations, restaurant demand, and bottle histories may be fictional. They are marked as fictional and must remain plausible for their validated real-world geography and grapes.

## Data layers

The reboot deliberately keeps several layers separate instead of flattening all wine information into one database.

1. **Original detailed model.** The original simulator contains hundreds of deeply modeled grape varieties plus a large hierarchy of countries, regions, appellations, communes, vineyards/crus, classifications, grape rules, soils, climate notes, tasting structure, aromas, viticulture and winemaking affinities. `src/game/reference.ts` adapts this into the generation-safe canonical layer.
2. **Authoritative identity/index layer.** Automated source snapshots currently normalize 1,997 prime winegrape variety records, 60 countries, 613 statistical planting geographies, 280 U.S. AVAs and 1,665 EU wine GIs. These records prove identity/geography and improve coverage; they do not automatically imply detailed appellation rules or a tasting profile.
3. **Hand-researched legal/appellation overlay.** `src/data/research/appellation_profiles*.json` stores source-by-source legal hierarchy, grapes, product types, classifications, ageing/release rules, subzones, communes, climats/MGAs, production rules, terroir notes and explicit unresolved research questions. Records remain `reference-only` or `framework-only` until they contain enough detail to become generation candidates.
4. **Environmental research layer.** `environmental_profiles.json` stores sourced place-specific climate, geology, soil and topography. Its numeric matrix modifiers are separately marked `derived: true`; they translate factual research into game behavior and are not claimed as published analytical measurements.
5. **Historical vintage layer.** `vintage_observations.json` stores year-specific growing-season facts, hazards, harvest timing, crop impact, fruit health and sourced style implications. Exact regional observations can produce bounded derived vintage modifiers. Official categorical vintage ratings are retained as categories and are not converted to invented numeric scores.

## Matrix model

The structural model follows the original simulator rather than replacing it:

**grape baseline × place modifier × vintage modifier × winemaking modifier**

The grape baseline remains the existing 1–5 tasting structure: acidity, tannin, body, sweetness, fruit intensity and earth intensity, with alcohol handled as an actual percentage range. Existing grape data also retains viticultural and winemaking attributes such as climate preference, vigor, yield potential, disease/drought/frost tolerance, sparkling/fortified/late-harvest suitability and production-method affinities.

The place layer can modify structural expression from researched climate, soil, geology, elevation, drainage and site exposure. The vintage layer can modify ripeness, concentration, tannin maturity, acidity, aromatic freshness, disease pressure, yield and ageability from sourced year-specific observations. Winemaking remains a separate layer for extraction, oak, lees, oxidative handling, fortification, botrytis handling, skin contact, amphora and other production decisions.

All simulation matrices are bounded and explicitly labeled as derived. A value such as `+0.35 acidity` means a game-model adjustment relative to the grape baseline. It is not a laboratory measurement and must never be presented as one.

## Environmental and vintage coverage

The first environmental pass contains detailed place models for Champagne; the Côte de Nuits/Côte de Beaune; Meursault; Barolo; Rioja Alta, Rioja Alavesa and Rioja Oriental; Napa Valley; and Sauternes. The point is not only broader coverage but meaningful internal differentiation—for example, Rioja Alta, Alavesa and Oriental no longer share one generic Rioja environmental profile.

The first sourced vintage pass contains detailed observations for Champagne 2021/2022, Bourgogne 2021/2022, Bordeaux 2020/2021/2022 and Napa Valley 2021/2022/2023. It also stores the official Rioja DOCa vintage classifications from 2001 through 2025 as categorical authority ratings.

These records are intentionally incomplete. A place without researched environmental data still uses its validated grape/geographic reference model. A vintage without a sourced historical observation does not receive invented weather. The system reports the absence rather than filling it procedurally.

## Legacy vintage scores

The original Python generator contains a useful `VINTAGE_QUALITY` table with simplified 0–1 regional scores. That table is preserved as legacy design history only. The scores are not sourced strongly enough to be authoritative and are **not imported into the new historical-vintage layer**.

The replacement model records the actual growing season first: frost, heat, drought, rainfall, hail, mildew/disease pressure, phenology, harvest dates, berry/fruit condition, crop size and authority assessments where available. Only then may the simulation derive bounded effects. This preserves the old game-design intent without presenting an unsourced score as wine fact.

## Source policy

Research should prefer primary or authoritative sources and retain provenance metadata. Priority sources include:

- OIV vine-variety and global vine/wine statistics databases.
- Vitis International Variety Catalogue (VIVC), Julius Kühn-Institut, for prime variety identity, synonyms, parentage and origin checks.
- European Commission eAmbrosia for EU wine PDO/PGI and protected traditional terms.
- National appellation authorities and official legal specifications for appellation rules.
- Official regional/interprofessional bodies and regulatory councils for terroir, harvest and vintage documentation.
- U.S. Alcohol and Tobacco Tax and Trade Bureau (TTB), 27 CFR Part 9, for American Viticultural Areas.
- Wine Australia Register of Protected Geographical Indications.
- Intellectual Property Office of New Zealand GI Register.
- South African Wine and Spirit Board / Wine of Origin scheme.
- University of Adelaide Wine Economics Research Centre global winegrape datasets for country/region/prime-variety cross-checking and planting relevance.

Secondary descriptive material may enrich sensory or historical context when primary sources do not address it, but it must not override legal or regulatory information.

## Validation

`reference.test.ts` requires generated wines to resolve back to a real reference path and real grape identity. `research.test.ts` checks legal/appellation research and provenance. `environment.test.ts` validates soil/climate/vintage source links, matrix bounds, exact historical observations, geographic mapping and the rule that legacy generic quality scores cannot leak into the sourced vintage layer.

The generator can apply researched place and vintage matrices only after those records pass validation. Unresolved grape synonyms, transliterations and legal ambiguities remain visible research work instead of being silently guessed.
