# Reference-data policy

The game separates **factual wine reference data** from **fictional simulation content**.

## Hard rule

The engine must not invent a country, wine region, geographical indication, appellation, commune, formally named vineyard/cru, classification, or grape variety and present it as real. Those entities must resolve to the curated reference layer before a generated bottle is valid.

Generated producers, estates, cuvées, commercial prices, quantities, allocations, restaurant demand, and bottle histories may be fictional. They are marked as fictional and must remain plausible for their validated real-world geography and grapes.

## Existing project data

The original simulator already contains a substantial hand-curated dataset with hundreds of grape varieties and a large nested hierarchy of regions, appellations, communes, crus/vineyards, classifications, authorized grapes, soils, climate notes, and style notes. `src/game/reference.ts` now adapts that data into a canonical validation layer instead of replacing it with a small launch catalog.

## Expansion sources

Future reference expansion should prefer primary or authoritative sources and retain source/provenance metadata. The source plan includes:

- OIV vine-variety and global vine/wine statistics databases.
- Vitis International Variety Catalogue (VIVC), Julius Kühn-Institut, for prime variety identity, synonyms, parentage, and origin checks.
- European Commission eAmbrosia for EU wine PDO/PGI and protected traditional terms.
- National appellation authorities and official legal specifications for appellation rules.
- U.S. Alcohol and Tobacco Tax and Trade Bureau (TTB), 27 CFR Part 9, for American Viticultural Areas.
- Wine Australia Register of Protected Geographical Indications.
- Intellectual Property Office of New Zealand GI Register.
- South African Wine and Spirit Board / Wine of Origin scheme.
- University of Adelaide Wine Economics Research Centre global winegrape datasets for country/region/prime-variety cross-checking and planting relevance.

## Historical vintages

Past vintage weather and quality notes must be curated historical data. The procedural generator may model bottle age and a hypothetical future vintage, but it must not fabricate historical weather and state it as fact. Generated wines therefore say when vintage-specific historical notes are not yet curated.

## Validation

`reference.test.ts` requires generated wines to resolve back to a real reference path and real grape identity. Data-quality audits also surface unresolved grape names in appellation records so aliases and spelling differences can be normalized instead of silently accepted.
