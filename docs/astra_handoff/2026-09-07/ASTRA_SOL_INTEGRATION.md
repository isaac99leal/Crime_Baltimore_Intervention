# Astra + Sol integration — 2026-09-07

This continuation combines PR #77 at `253519bba84c515e0b171735c91685bec5cfc8f4` and PR #78 at `2d5372c2db501d00580061fa4cb71fb5349b3155`, retaining their common Astra foundation. The original branches remain unchanged.

Sol's Burgundy closeout includes Rully, Blagny, the Mâconnais Premier Crus and Corton reconciliation. His identity registry contains 60 reviewed, source-scoped Adelaide links across seven evidence documents. See the Sol addendum for source details and remaining legal limitations.

## Integration repairs

The latest #78 CI failed one assertion: `Xarel·lo` correctly produces an R2 punctuation-folded search candidate for Xarello, whereas the test expected UNKNOWN. The regression now checks the actual candidate status, absent canonical identity and prohibition on confirmed identity. Other synonyms remain UNKNOWN. Resolver behavior and evidence were not weakened.

The historical reconciliation script now requires every required site source ID, matching runtime behavior. Its input manifest also includes all additive identity evidence shards. The original reconciliation JSON is a historical snapshot and has not been silently regenerated as a new legal approval.

## Measured continuation

Run `python scripts/variety_identity_coverage.py --output <path>` to reproduce the attached report. Input hashes include the global census and every identity shard. Coverage uses global source rows only, without adding country totals or summing across years. Source duplicates and missing measurements remain intact.

| Census year | Reviewed share of reported positive hectares |
| --- | ---: |
| 2000 | 54.1920% |
| 2010 | 62.6918% |
| 2016 | 61.2647% |
| 2023 | 62.1336% |

Of 1,998 source rows, 60 resolve at R5 and 1,938 remain R1. The report has 33 unresolved rows above 10,000 hectares and 207 above 1,000 hectares in 2023, with the top 50 retained for review. These are source-row counts, not distinct grape counts: categories such as “other”, “other red” and “other white” are deliberately retained and must not be promoted to botanical identities.

No resolver-generated R0 conflicts currently exist. This does not clear the unresolved or quarantined names described by Sol. The report emits a structured blocking conflict queue when competing registered evidence exists; it does not invent conflicts from missing evidence.

Next research targets by area include Trebbiano Toscano, Alicante Henri Bouschet, Côt, Mazuelo and Prosecco. Each requires exact source-scoped primary evidence before promotion. Historical appellation-law applicability and transitional harvest requirements remain separate legal work, not resolved by botanical links.
