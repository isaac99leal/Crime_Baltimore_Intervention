# Autonomous research continuation — global trade and indigenous cultivar expansion

Date: 2026-09-05

This entry continues the autonomous research log. The governing rule remains unchanged: trade/producer evidence may enrich commercial bottle, vineyard and cellar observations, but cannot independently establish protected-origin law, cultivar genetics/synonymy, historical weather, or universal grape behavior.

## Trade-source architecture corrected and scaled

- Fixed a latent integration gap: `trade_source_registry_pass3.json` and the newest discovery files existed on the branch but were not loaded by the canonical `tradeSheetIngestion.ts` runtime.
- Canonical trade ingestion now loads **3 verified/curated source passes**, **3 discovery passes**, and **5 normalized technical-observation passes**.
- The verified/curated registry remains at **33+ inspected importer/distributor/merchant sources**.
- The staged discovery funnel now exceeds **190 unique candidates**, with **140+ still deliberately left as directory leads** until their own websites and resource depth are inspected.
- Added a UK Top-50 wholesaler/importer discovery tranche from Harpers; ranking/directory membership remains discovery-only evidence.
- Added a separate global trade-directory planning universe with **34 market categories and 886 listing slots**. Listing slots are not treated as unique companies because firms can appear in multiple market categories.
- Directory snapshot drift is retained explicitly: e.g. the aggregate Australia index showed 58 while a live category snapshot showed 56; the USA index/live snapshot similarly differed. Directory counts are therefore versioned observations rather than immutable facts.

## Technical trajectories instead of static producer style

- Added `tradeTechnicalTrajectory(producer, wine)`.
- The engine now identifies fields that actually change across vintage-specific technical records instead of flattening them into one producer-style constant.
- Cara Sur Criolla Chica is a regression example: 2018 and 2022 retain distinct ABV, yield and maturation-vessel observations while vineyard identity remains stable.
- This trajectory model is intended for later linkage into vintage-conditioned cellar/sensory simulation.

## Third, fourth and fifth technical-observation passes

New observations materially expand commercial evidence for under-modeled cultivars and processes.

### Spain
- La Zorra Teso Blanco: Rufete Blanco / Palomino Fino / Viura / Moscatel de Grano Menudo, old vines, named parcels, mixed slate/granite/clay, skin maceration and native fermentation.
- José Antonio García Doña Blanca 2019: 100% Doña Blanca, Valtuille old-vine parcel, extended skin/stem contact, used 500 L French barrel fermentation/ageing, spontaneous MLF and source-stated SO2.
- José Antonio García Valtuille 2020: Mencía plus old mixed white varieties, multiple named sites, 65% whole cluster, open-top foudre, 40-day maceration and mixed 300/500 L barrel élevage.
- La Zorra Teso Rufete 2019: 100% Rufete, 800–850 m, old vines, 72-hour cold soak, native fermentation and limited used-oak maturation.

### Georgia
- Gvantsa's Ojaleshi: roughly 800 bottles from a few estate rows; hand selection, qvevri fermentation, wild yeast, low sulfur and unfiltered bottling.
- Orgo Kisi: family vineyard planted in the 1930s, six months qvevri skin contact and source-stated total SO2.
- Rosha Gravitas: 50% Kisi / 50% Khikhvi, 20-year vineyard, partial stems, four months qvevri contact and roughly 3,000 bottles.

### Argentina
- Cara Sur Criolla Chica 2018 and 2022: same old Finca Maggio source with separate vintage yield, ABV, production and concrete-vessel observations.
- Luna Duna Tinto 2023: Criolla Chica / Criolla Blanca, 1930 pergola planting, native fermentation and 8,000 L concrete maturation.

### Roussillon / oxidative categories
- Domaine de Saü Rancio Sec: old Grenache Gris, native ferment, used casks, never topped, broad cellar-temperature exposure and naturally achieved 18.5% alcohol without fortification.
- Domaine de Rombeau Rancio Sec 2009 and Rivesaltes Rancio 2009: separate oxidative regimes with old barrels, demijohn/outdoor or warm-rafter ageing and long bottling timelines.

### Cyprus
- Makarounas Xynisteri Aerides: ungrafted Xynisteri, 400–600 m, 18–24 h cold soak, spontaneous stainless fermentation and lees/bâtonnage detail.
- Makarounas Maratheftiko: extended maceration, spontaneous stainless fermentation and used 300 L French barrel maturation.
- Makarounas Spourtiko: ungrafted fruit, whole-cluster pressing, spontaneous stainless fermentation, lees ageing and bâtonnage.
- Makarounas Promara Amphora: cold soak, spontaneous fermentation in 500/800/1200 L amphoras and sur-lie maturation.
- Makarounas Yiannoudi/Giannoudi: importer page spelling discrepancy is **not** normalized away; it is stored as an explicit identity-reconciliation item.

### Greece / Crete / Attika
- Douloufakis Liatiko Amphora versus standard Liatiko now provides within-cultivar process contrast: amphora/native/no-sulfur extraction and used-barrel finishing versus cold soak, stainless fermentation, MLF and split large-oak/barrique/stainless maturation.
- Douloufakis Vidiano versus Vidiano Aspros Lagos provides another controlled contrast: stainless/cold fermentation and short lees ageing versus 225 L French oak + acacia fermentation, three months bâtonnage and five months wood ageing.
- Douloufakis Femina Malvasia provides current commercial process evidence for Malvasia di Candia Aromatica.
- Mylonas Assyrtiko provides non-Santorini Attika evidence with 2.5 ha of 25+ year vines, 8-hour maceration and fine-lees stainless ageing.
- Mylonas Savatiano Retsina remains separately represented with grape cooling, pre-fermentation maceration, resin addition during fermentation and fine-lees ageing.

### Italy
- Broglia Timorasso retains current product evidence plus the importer-documented 2018 first-vintage project, planned 7,000-bottle scale and stainless fermentation/maturation.

## Commercial cultivar parsing and evidence quality

- Hardened `explicitTradeCultivars` so semicolon-delimited and percentage-labelled mixed compositions produce clean cultivar tokens.
- Regression case: `85% Mencía; 15% Godello, Palomino, Doña Blanca` now yields four cultivar identities rather than a malformed pseudo-variety.
- Commercial-use evidence generated from these observations remains separate from Adelaide bearing area, GI legality and cultivar genetics.
- Regional vintage observations continue to attach only as grape × place context and never become a universal grape vintage score.

## Schema and identity audit

- Added `tradeSchemaAudit.ts`.
- Every technical field not yet classified by the trade evidence policy is now surfaced as schema-normalization debt instead of silently being treated as mature ontology.
- Added a dedicated identity-reconciliation queue; the Makarounas Giannoudi/Yiannoudi discrepancy is a locked regression case.
- Authority-restricted fields such as protected-origin legal status, prime cultivar identity/genetics and historical weather remain prohibited in ordinary trade observations.

## Failure found and repaired

- CI initially failed because the legacy `tradeSourceRegistryScale.ts` wrapper still appended registry pass 3 manually after the canonical ingestion engine began loading it directly.
- This duplicated 13 verified source IDs.
- The wrapper was corrected to consume the canonical combined `tradeSources` registry rather than maintaining a shadow merge.
- The failure was structural; the research observations themselves were not invalidated.

## Validation

- CI run **`33959952313`** passed the complete test suite and production build on code-bearing commit **`90aae3e620a3294e88e5c406a65de5907b423d9b`**.
- The immediately preceding corrected registry run `33959720532` was also green before the fifth observation/schema-audit tranche.
- Dependency installation still reports **5 known vulnerabilities (3 moderate, 1 high, 1 critical)**; this pass does not claim security remediation.

## Next pressure

- Promote hundreds-scale directory leads one by one through website verification → portfolio mapping → technical-resource scoring → field-level ingestion.
- Add additional market discovery pools beyond the current specialist US and UK tranches, especially France, Italy, Spain, South Africa, Australia, New Zealand, Portugal, Chile, Argentina and smaller emerging markets.
- Continue using the commercial-cultivar gap queue to prioritize current-bearing grapes with missing bottle-use, GI/non-GI context, regional vintage evidence or cellar-process observations.
- Build a normalized technical-field ontology from the schema-audit queue so granular aliases converge without deleting source wording.
- Expand cultivar identity reconciliation through VIVC/national authorities before promoting importer spelling/synonym claims to lookup aliases.
