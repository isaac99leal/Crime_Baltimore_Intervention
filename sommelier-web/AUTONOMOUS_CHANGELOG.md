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
