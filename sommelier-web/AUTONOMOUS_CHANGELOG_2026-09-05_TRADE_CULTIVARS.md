# Autonomous research continuation — trade sources and commercial cultivars

Date: 2026-09-05

This file continues `AUTONOMOUS_CHANGELOG.md` for the large trade-source and commercial-cultivar expansion. The same operating rule applies: sourced facts, legal identity, genetic identity, statistical cultivation, producer observations, historical vintage evidence and simulation-derived behavior remain separate evidence channels.

## Commercial-cultivar evidence layer

- Added `commercialCultivarEvidence.ts` over the full 1,997-record Adelaide authority variety snapshot.
- Preserved global bearing-area series separately for 2000, 2010, 2016 and 2023 rather than collapsing them into one timeless acreage number.
- Promoted the Adelaide geography snapshot into more than 2,500 regional/national cultivar-area observations while every such record remains explicitly `statistical-not-gi`.
- Statistical bearing area alone does not establish protected-origin legality, exact cultivar synonymy, current bottled-wine use or procedural generation permission.
- Added legal wine-use corroboration from researched protected-origin profiles and producer/importer wine-use corroboration from normalized trade observations.
- Added wine-specific technical fields to trade wine-use evidence so actual cellar choices can enrich a cultivar without becoming generic cultivar constants.

## Cultivar × place × vintage context

- Linked the cultivar evidence layer to the sourced historical-vintage observation library.
- A regional vintage observation can attach to a cultivar only when that cultivar has statistical cultivation, legal wine-use or trade wine-use evidence in the matching country/place context.
- Every linked vintage record is explicitly scoped `regional-context-not-universal-cultivar-rating`.
- The system therefore does not create one global Cabernet, Sangiovese, Riesling or other cultivar vintage score from one region's growing season.
- Existing derived vintage matrices remain simulation aids and are never promoted to historical fact.

## Long-tail commercial-cultivar research queue

- Added `commercialCultivarResearchQueue.ts` so the long tail is explicit research work rather than invisible missing data.
- CI requires more than 1,200 cultivars with documented bearing history and more than 1,000 with positive 2023 bearing area.
- Global research gaps include missing commercial wine-use corroboration, regional cultivation depth, legal wine-use profile, trade technical observation and regional vintage context.
- CI deliberately preserves a backlog larger than 500 current-bearing cultivars lacking commercial wine-use corroboration, larger than 800 lacking trade technical observations and larger than 800 lacking regional vintage context.
- Added a separate country × cultivar queue with more than 1,000 country-cultivar research contexts across more than 30 countries. Evidence for a cultivar in one country does not automatically transfer to another.
- Priority scores use documented acreage/geographic evidence and missing-depth fields; they do not make a scientific or quality claim about the cultivar.

## Trade-source discovery and verification funnel

The trade program is now staged rather than binary:

`directory-lead -> website-verified -> portfolio-structured -> tech-sheet-capable -> observation-ingested`

- Added two high-volume discovery-queue passes and deduplication across spelling/company-suffix variants.
- CI requires more than 140 unique specialist importer/distributor candidates and more than 100 candidates to remain explicitly at `directory-lead` until their own sites are inspected.
- Discovery-network membership does not establish that a candidate's portfolio or technical resources have already been researched.
- Added a third verified-source registry pass. The combined verified/curated registry now contains at least 33 importer/distributor/merchant sources.
- Specialist verified sources now include De Maison Selections, Diamond Wine Importers, Haus Alpenz, North Berkeley Imports, Kysela Pere et Fils, Grand Cru Selections, Georgian Wine House, Vias Imports, Martine's Wines, PortoVino, Vom Boden, Brazos Wine Imports and Selection Massale in addition to the earlier core sources.
- Technical-resource qualification is stored separately from mere website verification.

## Niche commercial-wine technical observations

Added a second field-level observation pass emphasizing obscure or under-modeled cultivars and mixed plantings. Examples include:

- Cazin Cour-Cheverny Cuvée Renaissance 2023: 100% Romorantin, 40–90-year vines, native stainless fermentation, no MLF, used 300 L maturation and lees detail.
- Les Vignerons d'Estézargues: 100% Cinsault with vine age, soil, maceration, yeast and tank detail.
- Bloomer Creek: Riesling/Cayuga White pét-nat composition and production method.
- Richard Stávek: Baco Noir with a 450-bottle production observation, old-vine context, carbonic fermentation and barrel maturation.
- Bichi: old Mission planting in Baja California; importer synonym language is preserved only as a producer-channel claim and does not rewrite cultivar genetics.
- El Montañista: old Argentine white and red mixed plantings including Torrontés Sanjuanino, Torrontés Mendocino, Maticha, Greco Nero, Rabosso Veronese, Cardin and Freisa.
- Envínate and Michael Candelario: Canary Islands Listán Blanco, Albillo Criollo and Vijariego Blanco vineyard/cellar observations.
- Nanclares y Prieto: Mencía, Caiño, Espadeiro, Sousón and Brancellao mixed red with parcel and cellar detail.
- Caruso & Minini: Inzolia with vineyard, training, harvest, fermentation, alcohol and production-quantity observations.

These records establish producer/wine/vintage observations only. They cannot independently establish protected-origin law, genetic identity or universal varietal behavior.

## Conflict and provenance policy

- Same-entity/same-vintage contradictions remain competing versioned observations and generate conflict records rather than last-write-wins overwrites.
- Different vintages are not treated as contradictions merely because vineyard source, blend, élevage or analysis changes.
- Legal conflicts defer to regulators/product specifications; genetic/synonym conflicts defer to VIVC or suitable national registration/genetic authorities.
- Undated producer ranges remain undated producer-context evidence and are not converted into exact vintage claims.

## Validation

- Research provenance is now locked at 24 source passes.
- The verified/curated trade-source scale registry is locked at three passes and at least 33 sources.
- CI run `33957037469` passed the complete test suite and production build on code-bearing commit `9c4cde902ff0495c975c028120c4685e284a5787`.
- The preceding integrated run `33956739783` passed 25 test files / 156 tests and the production build before the final specialist-source registry tranche.
- `npm install` continues to report 5 dependency vulnerabilities (3 moderate, 1 high, 1 critical). This research/data expansion does not claim dependency-security remediation.
- Vite continues to warn about a large production chunk; code splitting remains separate engineering debt.

## Next research pressure

- Work through the remaining 100+ specialist directory leads and larger UK/Australia/global directory universes, promoting each source only after website/portfolio/resource verification.
- Harvest vintage-specific tech sheets, PDFs and producer resource folders across verified portfolios at scale, with document dates and conflict queues.
- Use the country-cultivar research queue to target commercially planted grapes that still lack bottle-use evidence, legal context, regional vintage observations or winemaking depth rather than repeatedly enriching famous cultivars.
- Add VIVC/national cultivar-identity normalization around obscure commercial names before using importer synonym language as a lookup alias.
- Expand regional vintage archives in the same cultivar × place × product/style × year model; never create universal grape vintage scores.
