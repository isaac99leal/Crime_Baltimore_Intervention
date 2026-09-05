# Sommelier Web — reboot

This folder is a browser-first reboot of the original Pygame sommelier simulator.

## Why this exists

The original prototype contains useful domain work: a large grape database, detailed wine regions, guest archetypes, pairing rules, generators, cellar management, service, blind tasting, and event concepts. Its main constraint is product architecture. It is a local Pygame application inside an unrelated repository, with no automated test or deployment path.

This reboot keeps the original game untouched and reuses its data as source material. The new application is designed for a web launch and for incremental expansion.

## Current playable loop

- Dining-room service: read the table, dish, budget, and guest cue; recommend an active bottle; receive a scored result, tip, revenue, reputation, and XP.
- Cellar: view inventory, adjust list prices, and move bottles on or off the active list.
- Wine market: buy inventory at wholesale cost.
- Blind tasting: deduce a grape from structural and aromatic clues.
- Office: review simple KPIs and close the week, which applies operating overhead.
- Automatic local save in the browser.

## Architecture

- `src/game/engine.ts`: pure game rules and state transitions.
- `src/game/catalog.ts`: adapts the existing grape dataset into a small launch catalog.
- `src/game/types.ts`: domain model.
- `src/App.tsx`: application shell and playable screens.
- `src/data/`: existing project data reused directly in this branch.
- `src/game/engine.test.ts`: regression tests for core economy, inventory, service, and tasting rules.

The rule engine does not depend on React. This is intentional: simulation rules can grow without coupling them to presentation code.

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

1. Replace the launch catalog adapter with full region/appellation/producer generation from the existing data.
2. Add restaurant tiers, menu composition, staff, overhead categories, allocations, producer relationships, and critic/regular guest arcs.
3. Add deeper service decisions: discovery questions, glassware, decanting, temperature, cork faults, pacing, pairings by course, upselling, and recovery from mistakes.
4. Expand blind tasting into deductive stages: sight, nose, palate, structure, climate, grape, region, vintage, quality tier.
5. Add weekly events and longer career progression with unlocks and restaurant moves.
6. Add deterministic seeded runs and replayable daily/weekly challenges.
7. Add accessibility settings, sound, onboarding, telemetry hooks, and production deployment.
8. Split this folder into its own repository before public launch. The current GitHub connection can modify repositories but does not expose repository creation, so this branch is a clean staging area for that extraction.

## Data note

The existing data is substantial and should be validated before it is treated as an authoritative wine reference. Game balance and factual accuracy are separate concerns; both need automated checks as the data layer grows.
