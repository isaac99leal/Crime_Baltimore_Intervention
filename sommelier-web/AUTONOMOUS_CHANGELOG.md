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
