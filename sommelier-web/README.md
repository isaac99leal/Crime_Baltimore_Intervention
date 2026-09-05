# Sommelier Web — reboot

This folder is a browser-first reboot of the original Pygame sommelier simulator.

## Why this exists

The original prototype contains substantial domain work: a large grape database, detailed wine regions, guest archetypes, pairing rules, generators, cellar management, service, blind tasting and event concepts. Its main constraint is product architecture. It is a local Pygame application inside an unrelated repository, with no clean browser launch path.

This reboot keeps the original game untouched and reuses its data as source material. The new application is designed for a web launch and for incremental, source-backed wine research.

## Current playable loop

- Dining-room service with full menu, preparation, sauce and aromatic pairing logic.
- Cellar inventory, bins, par levels, bottle condition, list pricing and off-menu stock.
- By-the-glass program with pour size, glass pricing and open-bottle handling.
- Large deterministic wholesale market built from validated real geography/grapes and fictional commercial producers/cuvées.
- Blind tasting from structural and aromatic clues.
- Supplier relationships, staff training, equipment and certification-style progression.
- Weekly office/economy loop and browser local save.

## Wine-data architecture

The reboot does not flatten all wine data into one source.

1. **Original detailed model** — hundreds of hand-modeled grapes and detailed geography, tasting structure, aromas and production context.
2. **Authoritative identity indices** — 1,997 prime winegrape records, 60 countries, 613 statistical planting geographies, 280 U.S. AVAs and 1,665 EU wine GIs.
3. **Hand-researched legal/appellation overlay** — source-by-source rules, hierarchy, grapes, styles, classifications, subzones, climats/MGAs, ageing and production requirements.
4. **Environmental research** — three current passes with 26 researched soil/climate/geology/topography profiles across at least 12 countries.
5. **Historical vintage research** — three current passes with 17 detailed growing-season observations plus official categorical Rioja vintage ratings from 2001–2025.

The simulation matrix follows the original design philosophy:

`grape baseline × place modifier × vintage modifier × winemaking modifier`

The original 1–5 grape structure remains the baseline. Place and vintage effects are bounded, explicitly simulation-derived transformations based on sourced environmental or growing-season evidence. They are not presented as laboratory measurements or official numeric vintage scores.

See `REFERENCE_DATA.md` and `src/data/research/MATRIX_MODEL.md` for the full provenance and matrix rules.

## Research status

Current detailed environmental coverage includes, among others: Champagne; Côte de Nuits/Côte de Beaune and Gevrey-Chambertin/Meursault; Pauillac, Pomerol, Saint-Émilion and Sauternes; Barolo; Brunello/Montalcino; Chianti Classico; Valpolicella/Amarone; Rioja Alta/Alavesa/Oriental; Santorini; Napa Valley; Marlborough; Stellenbosch; Mosel; Kamptal; Wachau; Tokaj; Uco Valley; Barossa Valley; and Margaret River.

Detailed historical observations currently include Champagne 2021/2022; Bourgogne 2021/2022; Bordeaux 2020/2021/2022; Napa Valley 2021/2022/2023; Chianti Classico 2021/2025; Brunello/Montalcino 2021; Stellenbosch 2021; Mosel 2023/2025; and Uco Valley 2022.

If a year-specific record has not been researched, the engine does not invent historical weather. The original Python `VINTAGE_QUALITY` table is retained only as legacy design history and is not treated as authoritative data.

## Architecture

- `src/game/engine.ts`: pure game rules and state transitions.
- `src/game/reference.ts`: canonical adapter for the original detailed grape/region model.
- `src/game/research.ts`: hand-researched legal/appellation overlay and provenance validation.
- `src/game/environment.ts`: soil, climate, vintage and matrix lookup/application.
- `src/game/world.ts`: deterministic fictional commercial generation constrained by validated wine reference data.
- `src/game/pairing.ts`: menu/preparation/sauce/aromatic pairing system.
- `src/game/systems.ts`: beverage-program operations.
- `src/data/official/`: normalized authoritative bulk indices.
- `src/data/research/`: source registries, rich appellation profiles, environmental profiles and historical vintage observations.

The rule engine does not depend on React. Simulation and reference logic can grow without coupling it to presentation code.

## Run locally

```bash
cd sommelier-web
npm install
npm run dev
```

Quality checks:

```bash
npm test
npm run build
```

## Product roadmap

1. Continue old-school source-by-source research, prioritizing deeper site, soil, climate, vintage and production-method coverage over shallow name counts.
2. Normalize cultivar synonymy/parentage against VIVC and preserve local names without duplicate grape identities.
3. Expand environmental resolution from region/appellation toward subzone, commune, MGA/climat and vineyard/site where authoritative data supports it.
4. Expand sourced historical vintages without fabricating weather; retain measured observations in original units and keep derived effects separate.
5. Complete the winemaking matrix: extraction, whole cluster, oak, lees, malolactic, oxidative handling, drying/appassimento, botrytis, fortification, flor/solera, sparkling production, amphora/qvevri and other techniques.
6. Deepen service decisions: faults, glassware, decanting, temperature, pacing, pairing by course, upselling and recovery.
7. Expand blind tasting into sight, nose, palate, structure, climate, grape, region, vintage and quality-tier deduction.
8. Restore and expand weekly events, career progression, allocations, restaurant moves and producer/guest arcs from the original prototype.
9. Split this folder into its own repository before public launch.

## Data rule

Game balance and factual accuracy are separate concerns. Factual wine identity, law, geography, soil, climate and historical vintage claims need provenance. Simulation-derived commercial values and matrices must remain clearly distinguishable from those facts.
