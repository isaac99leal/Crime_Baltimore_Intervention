# Autonomous improvement log

This log records self-directed research and engineering passes performed after explicit user authorization. It is deliberately separate from factual wine-reference data.

## Operating rules

- Never invent real countries, GIs/appellations, named vineyards, legal rules, cultivar identities, historical weather, scientific findings, or source citations.
- Keep sourced facts, legal/product rules, and derived simulation parameters in separate layers.
- Prefer primary regulators, statutes, official product specifications, interprofessional authorities, OIV/VIVC/national research institutions, and peer-reviewed technical literature.
- Treat missing evidence as missing evidence. Do not procedurally fill historical facts.
- Stress-test data/model assumptions before expanding them.
- Run tests and the production build after engineering passes and repair regressions before calling a pass green.
- Publish successful work to `revamp/sommelier-web-v2`; do not automatically merge the draft PR.

## 2026-09-04 — resolver / autonomous-research authorization

### Scope
- Began exact wine-product resolver work so a geographic designation no longer implies one generic product.
- Established recurring autonomous improvement policy and this audit log.

### Why
The legal and sensory model needs an intermediate product identity between place and bottle. `Tokaj`, `Porto`, `Rioja`, `Champagne`, `Franciacorta`, `Santorini`, etc. each contain materially different legal products whose grapes, sweetness, winemaking, ageing, release rules, and bottle-age trajectories cannot be inferred from geography alone.

### Model target
`grape/blend + exact historical place/product law + vintage + site/vine status + winemaking decisions + mandatory maturation + bottle/storage history -> resolved bottle identity + tasting/service state`

### Guardrails
- Current law must not be projected backward onto older vintages without an explicit legal-era record.
- Product-level generation is allowed only when the resolver has enough evidence to identify the product and validate its constrained decisions.
- Research-incomplete categories resolve as reference-only/ambiguous rather than guessing.

### Validation
Resolver implementation and CI status are recorded in subsequent entries once committed and tested.

## 2026-09-04 — exact product resolver v1

### Implemented
- Added `product_resolution_rules.json` and `productResolver.ts` as the layer between GI/place identity and bottle simulation.
- Added exact/conditional/reference-only product states rather than one generic wine per designation.
- Initial product records cover multiple legal products within Champagne, Brunello di Montalcino, Franciacorta, Rioja, Santorini, Tokaj, Port, Jerez, Amarone and Madeira process identities.
- Added exact composition checks where the researched profile supports them, including 100% Sangiovese Brunello, Franciacorta product constraints, Santorini Assyrtiko minima and Tokaj Aszú 6 puttonyos residual-sugar minimum.
- Added product-specific ageing-rule links, ageing archetypes and winemaking practice gates.
- Port and Jerez product identities deliberately remain `reference-only` where their current research profiles explicitly state that exact grape/fortification/analytical tables still need extraction.
- Added a fourth hand-research profile pass with a conservative Madeira DOP process/ageing anchor. It remains `reference-only` pending full product-specification extraction.
- Wired generation to select an exact product only when the chosen single-grape case satisfies the researched product rule. Otherwise the bottle remains designation-resolved/product-unresolved.
- Generated wines now expose product rule ID/name, resolver status, legal-era status, product-source IDs and a bounded provenance/research-risk score with explicit flags.
- Product-specific ageing rules now replace the previous designation-wide implication when an exact product is selected.

### Historical-law behavior
A product can resolve while its historical law version remains unverified. For example, identifying a historic bottle as a researched product does not assert that the current consolidated specification applied to that harvest year. This is recorded as `product-resolved-historical-law-unverified` until an effective-dated rule record exists.

### Cultivar normalization finding
The resolver validator surfaced `Aidani` in the researched Santorini specification as unresolved by the legacy grape master. It remains visible in the legal profile and resolver composition model, but is now tracked as an unresolved cultivar-normalization item rather than deleted or silently aliased. Generation can still use a 100% Assyrtiko case that satisfies the researched minimum.

### Stress testing
- Resolver unit tests distinguish Brunello normale/Riserva, Rioja red vs white/rosé ageing, Gran Reserva specificity, Tokaj Aszú 6 puttonyos, reference-only Port/Jerez products, composition rejection and product-specific winemaking legality.
- A 2,500-bottle generation stress test requires exact product IDs to resolve successfully, preserve valid geography/grape identity and carry bounded provenance-risk values.
- CI run `33938791887` passed the complete test suite and production build on commit `77229b70d4370be3688548fb295601c781c059e9` after the unresolved-cultivar validator was corrected in the following branch commit.

### Research lead discovered during stress pass
The user's `Issyk-Tul` example appears likely to refer to **Issyk-Kul, Kyrgyzstan**. Publicly accessible technical literature describes Pinot, Riesling and Chardonnay trials/plantings around Chok-Tal and Kara-Oi and reports vineyard climate requirements/yields; older Soviet/Kyrgyz primary literature still needs to be traced before this becomes factual in-game research data. This stays a research lead, not a populated historical claim.

### Next pressure points
- Add effective-dated historical product-law versions so legal-era verification can become exact rather than conservative.
- Extract complete IVDP Port/Douro rules, Jerez product tables, Madeira product/age/sweetness/vintage categories and Tokaj specialty-wine specifications.
- Resolve outstanding cultivar spellings/synonyms through VIVC/national authorities rather than legacy-name guessing.
- Replace broad ageing archetypes with chemistry/process-conditioned trajectories where evidence supports it.
- Connect product legality directly to generated winemaking decision sets, then expose the system to audit/training gameplay.

## 2026-09-05 — massive authority, chemistry, cultivar and micro-zone expansion

### Authority designation coverage
- Added two structured authority-registry tranches with **407 non-EU/non-TTB protected-origin identities**.
- First tranche: Australia 114 hierarchy records, Argentina 121 IG/DOC register records, Georgia 32 PDOs and New Zealand 22 registered/enduring wine GIs.
- Second tranche: **118 current Chilean region/subregion/zone/area identities** from the current Decree 464 hierarchy.
- Australian parent-child structure, duplicate Argentine names by jurisdiction/legal class, all 32 Georgian PDO identities, New Zealand official spellings and Chilean four-level hierarchy are tested in CI.
- Registry identities remain `reference-only`; a protected place does not inherit grapes, styles, analytical limits or winemaking legality unless a separate product specification is researched.

### Current Chile law
- Added a separately versioned **July 14, 2026 Decree 464** framework instead of overwriting older Chile research.
- Preserved separate 75% tests for geographic origin, named variety and vintage claim.
- Added the 2026 same-variety multi-origin rule: up to three regions or three subregions, descending order, minor component at least 15%, and no mixing region/subregion names in one claim.
- Added the 85% supplementary-label rule for `Andes`, `Entre Cordilleras` and `Costa`, including the current qualifying-area lists.
- Added `Embotellado en Origen` conditions.
- Added a separate `Secano Interior` special-origin record restricted to País/Cinsault and qualifying dryland areas/communes. País synonyms `Mission` and `Criolla` are preserved only as stated by the decree.
- The complete Article 3(b) labelable-grape table remains an extraction task because the SAG normative rendering exposes it as images; the missing table was not reconstructed from secondary lists.

### Georgia deep PDO/product research
- Added complete deep profiles for **Kisi Magraani** and **Khvanchkara**, plus conservative reference-only anchors for Zegaani and Okureshi's Usakhelouri.
- Kisi Magraani now stores village limits, 400–800 m elevation, planting geometry, yield, grape-sugar minima, white-vs-amber analytical limits, fermentation-temperature ceilings, Qvevri requirements, cap mixing, post-fermentation chacha contact, optional wood-ageing minimums and current source-backed climate context.
- Khvanchkara now stores Aleksandrouli/Mujuretuli exclusivity, 30–45 g/L residual sugar, yield/wine-output limits, grape-transport restrictions, 450–750 m viticultural band and a village-linked soil mosaic rather than a single generic soil.
- Historical specification notes are retained without upgrading them into genetic proof: e.g. Kisi Magraani's communist-period low-yield survival story and 1940s institute work are historical-source statements, not proof of a separate prime cultivar.
- Added fourth environmental pass with dedicated Kisi Magraani and Khvanchkara climate/soil/topography profiles; numeric place effects remain derived simulation matrices.

### Exact-product resolver v2
- Added a second product-resolution pass.
- Added `exclusiveComposition` so an exact product can reject any grape outside the researched legal set.
- Added `requiresBlend` so a product can require an actual multi-grape composition rather than accepting a single member of the legal set.
- Kisi Magraani white dry and amber dry now resolve separately; amber requires Qvevri fermentation and extended skin contact in the legality gate.
- Khvanchkara exact resolution now requires an Aleksandrouli–Mujuretuli blend and rejects outside grapes; a single-grape request remains unresolved.
- Zegaani and Okureshi's Usakhelouri product identities remain reference-only until full product specifications are extracted.

### Fermentation chemistry and bottle stability
- Added a source-backed chemistry/stability library covering YAN, H2S timing, fermentation temperature, volatile acidity, ethyl acetate, Brettanomyces volatile phenols, mousiness, pre-bottling dissolved oxygen, oxygen/SO2 interaction, closure oxygen transmission, premature oxidation, pH and tartrate stability.
- Added a derived chemistry engine with separate bounded indices for fermentation stress, growth-phase H2S, late-phase H2S, VA, ethyl acetate, microbial instability, oxidation load, premature oxidation and reductive development.
- Added separate process effects for phenolic extraction, fruit retention and shelf-life pressure.
- The engine explicitly does **not** treat YAN as one universal optimum, DAP as a deterministic late-H2S cure, premox as one-cause behavior, or calculated risks as laboratory probabilities/diagnoses.

### PIWI and cultivar genetics
- Added the complete **36-cultivar** 2024 Bundessortenamt production-cultivar list declared fungus-resistant by applicants, within the 119-production-cultivar official list.
- Added seven deep JKI cultivar profiles: Regent, Calardis Blanc, Felicia, Phoenix, Villaris, Calandro and Reberger.
- Resistance is stored by pathogen and, where supported, by loci such as `Ren3`, `Ren9`, `Rpv3.1`, `Rpv3.2`, `Rpv3.3` and `Rgb` rather than one binary PIWI flag.
- Reberger is deliberately locked as a counterexample: its official breeder profile can show medium-high powdery-mildew resistance while downy-mildew resistance is low. PIWI status therefore never means immunity.
- Pedigree, crossing year, national registration year, breeder trial yield and enological observations remain distinct fields.

### Rare and historically eroded indigenous grapes
- Added deep reference profiles for Georgian **Kisi, Ojaleshi and Jani**.
- Kisi stores official near-extinction/recovery context, survivor-vine evidence and disease/phenology observations without conflating the generic variety with the Magraani local historical form.
- Ojaleshi retains a date-stamped 2004 141-ha historical snapshot and historic maghlari/tree-training context rather than presenting that area as current.
- Jani retains the official 2.2–3.5 t/ha low-yield observation and very-late ripening as source observations, not universal site constants.
- Added a 30+ name historical/local research queue spanning Guria, Samegrelo, Abkhazia, Adjara and Racha-Lechkhumi. Queue membership attests official regional relevance only; it does not establish synonymy, genetics, current commercial planting or generation legality.

### Validation
- Current combined CI run `33951242791` passed `npm test` and `npm run build` on commit `49648eb2dc89759b49b6efcc3ff27012f4affa94`.
- Research tests now require six profile passes and fourteen provenance-source passes.
- Environmental tests require four place/environment research passes.
- Expanded designation tests require 407 authority identities and preserve legal hierarchy.
- Chemistry, PIWI, rare-cultivar, Georgian product-resolution and Chile legal-version tests are all part of the branch CI contract.

### Remaining pressure points
- South African current WO production-area hierarchy is now sourced from SAWIS and is the next registry ingestion target; current data should use the live production-area definition rather than the old 2009 booklet.
- Complete current Chile Article 3(b) cultivar-label table needs image/table extraction from the official normative record.
- Product-level chemistry should next connect actual YAN/pH/DO/SO2/closure measurements and winemaking selections to generated aroma/fault trajectories.
- Full VIVC/national identity normalization is still required for the rare-variety queue and unresolved appellation grape spellings.
- Historical legal versions remain sparse compared with the modern-law layer and need systematic archival backfilling.
