# Sommelier Web — reboot

This folder is a browser-first reboot of the original Pygame sommelier simulator. The original implementation remains intact on the source branch.

## Current playable systems

- Dining-room recommendation and detailed food-pairing scoring.
- Cellar inventory, lots/bins/storage condition, pricing, BTG, list management and reprints.
- Deterministic wholesale market with 15,000 fictional commercial offers constrained to validated wine reference data.
- Blind tasting.
- Weekly office/economy loop.
- Suppliers, allocations, staff training, equipment and fictional certification progression.
- Browser/local-storage saves.

## Wine data architecture

The game deliberately separates factual identity, legal rules, historical evidence and simulation-derived sensory behavior.

- `src/game/reference.ts` — generation-safe detailed grape/geography layer from the original project.
- `src/data/official/` — authoritative normalized identity/index snapshots.
- `src/game/research.ts` + `src/data/research/appellation_profiles*.json` — sourced legal/appellation research.
- `src/game/environment.ts` — sourced climate/soil/geology and historical growing-season matrices.
- `src/game/vintageArchive.ts` — centuries-deep historical vintage evidence ledger without fabricated weather.
- `src/game/ageing.ts` — legal ageing/vine-age rules plus separate bottle-age evolution.
- `src/game/winemaking.ts` — detailed cellar-decision engine with designation/product legality gates.
- `src/game/noteEvolution.ts` — separate vintage, winemaking and time-derived tasting-note layers.
- `src/game/designationProgram.ts` — global wine-GI/equivalent coverage accounting.
- `REFERENCE_DATA.md` — data-policy and provenance contract.

Current authoritative indices include 1,997 winegrape records, 60 winegrape-growing countries, 613 statistical planting geographies, 280 U.S. AVAs and 1,665 EU wine GIs. Statistical planting areas are never treated as legal GIs.

The global designation target is exhaustive but not yet complete. EU/eAmbrosia and U.S./TTB are live normalized registry indices. Additional national/provincial authority sources have been identified for Australia, New Zealand, Japan, Georgia, Argentina, Chile, South Africa, Ontario, British Columbia, Brazil, Mexico and the United Kingdom, but authority identification is not counted as completed ingestion. Remaining jurisdictions stay in an explicit pending queue. No GI is intentionally excluded because it is small or obscure.

## Vintage and ageing

The old universal 45-year generation cap has been removed. The new model separates harvest/vintage evidence, historical legal regime, mandatory legal ageing before release, bottle age/storage condition, and style-specific sensory evolution.

The historical authority ledger already reaches 1756 for documented Port archive entries. A historical archive entry proves documentary evidence at the stated level; it does not create fake rainfall, vintage scores or modern DOP law for that year.

The current age archetype model is deliberately broad. Exact products such as Vintage Port versus Tawny/Colheita Port, dry Tokaj versus Tokaji Aszú, or a generic Rioja red versus a legally qualified Gran Reserva must resolve through product-specific rules before their final ageing and winemaking path can be considered authoritative.

## Winemaking

The winemaking matrix currently models more than 35 separate decision points and more than 90 options across harvest, extraction, fermentation, MLF, lees, oak, oxygen, fortification, flor, blending, sparkling production, clarification, filtration and bottling. Choices that can be legally restricted are blocked until the exact product/designation resolver says they are permitted.

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

## Repository status

This remains a draft reboot in `revamp/sommelier-web-v2`. It is intentionally staged in `sommelier-web/` so it can later be extracted into a dedicated repository. Do not treat incomplete reference coverage as authoritative merely because the UI can display it.
