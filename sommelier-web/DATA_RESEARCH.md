# Wine data research method

The simulator uses three distinct data layers. They must not be conflated.

## 1. Legacy deep model

The original `grapes.json` and `regions.json` contain the hand-built material from the Pygame project: grape profiles, appellations, subregions, communes, vineyards, classification systems, soils, climates and related domain notes. This material remains valuable and is not discarded.

## 2. Authoritative bulk reference indices

`src/data/official/` contains normalized source snapshots from authoritative or academic datasets. These files establish real identities and geography at scale. They do not automatically make a place or grape safe for procedural bottle generation.

Current normalized sources include University of Adelaide winegrape variety/planting data, the TTB American Viticultural Area register, and the European Commission eAmbrosia wine GI register.

## 3. Hand-researched overlay

`src/data/research/` is the old-school research layer. Each important region, appellation, GI, or legal framework is researched individually and stored with explicit source references.

A rich profile can contain:

- legal class and geographic hierarchy;
- authorized and principal grapes;
- wine/product types;
- subregions, communes, climats, vineyards, MGAs or other official named units;
- classification and label terminology;
- minimum ageing, lees ageing, oak ageing, bottle ageing and release rules;
- blend percentages, yields, alcohol minima and origin/vintage percentages;
- production method constraints such as bottle fermentation, appassimento, fortification or hand harvest;
- climate, elevation, soils and viticultural context when supported;
- conservative style and ageing notes;
- version-sensitive legal notes and unresolved research questions;
- source IDs pointing to regulators, certification bodies, official consortia or other primary sources.

## Research rules

1. Primary legal and regulatory sources override secondary descriptions.
2. A statistical planting region is never relabelled as an appellation.
3. A registered GI is not assumed to define permitted grapes or styles unless its product specification has been researched.
4. Similar grape names are not merged automatically. Synonyms and transliterations require explicit normalization evidence.
5. `reference-only` records establish a factual identity but cannot drive bottle generation by themselves.
6. `framework-only` records define country or regional legal logic but are not bottle appellations.
7. `candidate` means the record is detailed enough to be considered for generation. It does not bypass normal reference-integrity checks.
8. Vintage-dependent laws must retain effective dates or transitional rules. Current rules must not be projected backward onto historical vintages.
9. Descriptive tasting profiles must remain separate from legal requirements.
10. Fictional producers and cuvées may exist in the game, but their geography, grape composition, style and labelling must fit the researched factual framework.

## Validation

`src/game/research.ts` validates profile/source identity, source links, completeness scores and generation status. It also reports grape names that do not yet resolve to the legacy grape master. Those unresolved names are a research queue, not an invitation to invent aliases.

`src/game/research.test.ts` locks representative legal constraints into CI so future expansion cannot accidentally flatten important distinctions such as Barolo's Nebbiolo requirement, Brunello ageing, Franciacorta lees ageing, Rioja ageing categories, Priorat's place hierarchy, or Chilean origin-percentage rules.

## Research backlog

The intended direction is continuous jurisdiction-by-jurisdiction enrichment. Priority areas include complete Champagne cru/village structure; Burgundy climats and appellation specifications; Bordeaux commune and classification rules; complete Barolo/Barbaresco MGA normalization; Toscana UGA and Montalcino terroir mapping; complete Jerez style tables; Port regulations and grape rules; all Austrian DACs; German Anbaugebiete/Bereiche/Lagen and Prädikat/VdP separation; Greek PDO/PGI systems; Hungary/Tokaj; every Georgian PDO; full South African WO hierarchy; Australian GIs; New Zealand registered GIs; Chilean DO areas; Argentine GIs/DOCs; Canadian VQAs; U.S. AVAs; and emerging regions only when reliable primary information is available.
