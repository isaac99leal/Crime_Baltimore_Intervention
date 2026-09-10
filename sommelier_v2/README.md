# Sommelier Simulator v2

This folder is a clean restart of the simulation layer. The old Pygame game remains intact while v2 grows beside it.

## Why restart the architecture

The original project already has useful assets: large grape and region JSON datasets, procedural producer/wine generation, guest archetypes, blind tasting, cellar screens, and service scenes. The weak point is not the existence of wine data. The weak point is that business rules and game rules are tightly coupled to Pygame scenes.

V2 separates the simulation from presentation. A Pygame client, web client, or future native client can call the same engine.

## Implemented in this foundation

- Immutable wine/vintage records with commercial, geographic, sensory, farming, and aging fields.
- Legacy catalog adapter that can turn the existing region/grape generator into 10,000+ v2 wine records without duplicating the old data.
- Cellar lots with sealed bottles, reservations, storage state, and cost value.
- True BTG mechanics: opening bottles, pours by milliliter, remaining open volume, bottle life, and spoilage.
- Bottle and BTG pricing based on target cost percentages and expected waste.
- Distributor/importer/grower relationship state and allocation probability.
- Guest preference, value, prestige, and food-pairing recommendation scoring.
- Staff, equipment, wine-list editions, off-menu placements, career credentials, and daily time blocks in the domain model.
- A ledger and day-close facade that can support operating statements and weekly reviews.
- Provenance-aware wine knowledge, vineyard/vintage simulation, fermentation/MLF mechanics, bottle-aging curves, and protected-origin validation.

## Legal specification ingestion

Protected-origin data has three distinct trust levels. Do not collapse them.

1. **Authoritative source index** — `scripts/sync_legal_spec_sources.py` maps registered EU wine GIs to the European Commission eAmbrosia application record and its official product-specification/single-document attachments. The current snapshot contains 1,649 registered wine GIs across 24 countries; 1,563 have at least one authoritative document and 846 expose a full product-specification attachment. A source record proves that a legal document exists. It does not authorize a wine.
2. **Machine deny constraints** — `scripts/extract_legal_spec_constraints.py` reads official product-specification PDFs for supported jurisdictions and extracts only clearly bounded authorized-variety sections. The current snapshot contains 1,437 parsed/source records and 415 deny-safe constraints across 8 countries. These records are deny-only: an outsider can be rejected, but an insider is not automatically eligible.
3. **Verified strict specifications** — `knowledge/legal_specs.py` contains structured, source-reviewed production specifications. Only this level can positively authorize a protected-origin grape/blend claim and apply detailed yield, alcohol, aging, release, method, bottling, and similar rules.

This asymmetric design is intentional. A false positive creates a legally impossible wine; a false negative only leaves a wine unavailable until the source is parsed and reviewed. The simulator therefore fails closed whenever legal completeness is uncertain.

New World geographical indications must not be forced into the same model as European PDO/PGI specifications. U.S. AVAs and Australian/New Zealand GIs commonly depend on origin-percentage and label-integrity rules rather than an appellation-specific grape list. Those jurisdiction rules should be modeled separately from EU authorized-variety extraction.

The external knowledge workflow is serialized per branch. It refreshes the public wine registries, indexes the official legal documents, derives deny-safe constraints, commits generated snapshots, and prevents concurrent refresh runs from racing each other.

## Playable market buying

The Pygame Wine Market now has a weekly supplier book. Reopening or refreshing the screen keeps the same offers; a new game week changes the selection. Existing supplier stock is not replenished by refresh.

Purchase buttons show totals including freight. Game balance rules give 3% off orders of 6–11 bottles and 5% off orders of 12 or more. Freight is $12 per order below 12 bottles and free from 12 bottles. These are simulation rules. Purchases check cash, cellar space, and stock before making changes. The cellar records the cost including freight and uses a weighted average for repeat purchases.

This feature is connected to the existing Pygame market screen. Supplier-specific terms, invoices, futures, and closeouts remain future work.

## Gameplay systems to build next

1. **Market and buying** — supplier books, vintages, samples, futures, closeouts, minimums, freight, payment terms, and dynamic availability.
2. **Wine list management** — sections, menu reprints, price changes, depletion warnings, off-menu reserves, cellar books, and list aging.
3. **BTG program** — preservation equipment, sparkling loss, oxidation curves, comp pours, staff pours, and waste controls.
4. **Service night** — many simultaneous tables, courses, timing pressure, objections, upsells, decanting, corked bottles, substitutions, VIPs, and recovery.
5. **Pairing system** — dish construction, sauce/method/fat/acid/spice/sweetness, regional pairings, contrast vs complement, and menu changes.
6. **Relationships and allocations** — portfolio support, supplier politics, grower visits, dinners, sample budgets, late invoices, scarce releases, and long-term access.
7. **Inventory operations** — receiving, bin locations, counts, variances, breakage, theft, transfers, vintages, storage zones, and physical capacity.
8. **Economics** — beverage P&L, pour cost, contribution margin, carrying cost, working capital, inventory turns, cash flow, and restaurant-management targets.
9. **People** — hiring, scheduling, server training, junior somms, morale, mistakes, delegation, compensation, and promotion.
10. **Career** — fictional service/theory/tasting credentials inspired by professional wine education, employer reputation, competitions, salary negotiation, and job offers.
11. **Blind tasting** — structured calls, evidence-based deductions, calibration, benchmark flights, vintage variation, faults, and timed exams.
12. **World depth** — expand geographic coverage toward 70+ countries with layered regions, appellations, vineyards, grapes, legal rules, vintages, and producer archetypes.

## Compatibility strategy

Do not delete the old data files. `catalog.load_legacy_catalog()` reuses them. This lets the project improve the game engine first, then replace or enrich individual data layers without a risky all-at-once rewrite.

## Run the vertical slice

```bash
python -m sommelier_v2.demo
```

The demo buys a wine lot, prices it for bottle and BTG, makes a food-aware guest recommendation, opens a bottle for a glass sale, and records the remaining open volume.

## Vineyard water and harvest choices

`DailyWeather.irrigation_mm` now represents root-zone water applied that day. It increases soil water without being counted as rain, leaf wetness, or harvest rainfall. Block irrigation is added to this explicit daily application; callers should use one input path unless the applications are additional. Overhead irrigation and canopy wetting are not modeled by this field.

Daily vintage states now expose irrigation, drainage above field capacity, and actual modeled evapotranspiration limited by available water. These let callers inspect water conservation. The existing evapotranspiration proxy remains a game prior, not a calibrated FAO reference-ET implementation.

Set `VineyardBlock.harvest_day_of_year` or pass `harvest_day_of_year` to `simulate_vintage` to choose the pick date. Simulation stops on that date, so later storms cannot change already-picked fruit. Later picking can change acid retention and disease exposure. Existing automatic harvest remains the default. The resulting vineyard chemistry continues through the existing harvest-to-must conversion; no laboratory measurement is invented.

Explicit picks require a date in the supplied weather. Duplicate dates, negative water, inverted temperatures and non-finite temperature/water inputs are rejected. A daily irrigation input cannot bypass a block's irrigation restriction. An explicit pick date does not guarantee ripe, harvestable or legally eligible fruit.

Water-balance reference: FAO Irrigation and Drainage Paper 56, Chapter 8 (https://www.fao.org/4/x0490e/x0490e0e.htm). Used for the distinction between water inputs, root-zone storage and drainage; the simulation coefficients are not calibrated to this reference.
