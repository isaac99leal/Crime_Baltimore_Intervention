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
