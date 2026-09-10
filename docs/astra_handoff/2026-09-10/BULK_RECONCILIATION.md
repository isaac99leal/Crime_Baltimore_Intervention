# Bulk continuation — 2026-09-10

Built on PR #86 at de1d203766f4a83db724275f343d487b212149a5, including the merged bulk operationalization and evidence-semantics cleanup. The older unfinished Astra batch is retained on its checkpoint branch; its overlapping shard numbers are not imported into this lineage.

## Changes

National classification and PIWI country evidence now matches case-insensitive literal names (with surrounding whitespace ignored) and explicitly declared aliases. Accent and punctuation folding remains useful for search but does not establish these evidence associations. Both Adelaide and VIVC-only operational records use the same rule. Classification does not imply GI entitlement.

The identity audit preserves existing census totals and unresolved lists. Additional named-row metrics exclude exactly the three Adelaide categories Other, Other red and Other white. Substring matches do not exclude grape names. The named-row queue is a research queue, not a simulator eligibility gate or a count of distinct botanical identities.

The classification regression now checks Calardis Blanc and Pougnet explicitly. Only two names in the current operational universe overlap the loaded national-classification table, so the previous requirement for more than five matches was unsupported.

## Current data checkpoint

- 1,998 census rows; 1,996 operational Adelaide names.
- 2,038 total operational records, all simulation-enabled.
- 105 strong census identity links; 80.6386% of reported 2023 hectares.
- Four unresolved named rows exceed 10,000 hectares: Catarratto Bianco (R0), Cereza (R3), Criolla Grande (R3), Bordô (R1).
- Côt remains confirmed. Scientific candidates remain candidates; operational availability does not require identity promotion.

## Next work

Expand source-backed national/PIWI evidence records with provenance and status exposed alongside country summaries. Review the four large-area identity cases with source-specific evidence, retaining Catarratto conflict and scientific-candidate distinctions until resolved. Do not reuse old Astra shard filenames over Sol's newer shards.

## Source detail continuation

The initial PR #87 commit passed GitHub's complete Wine catalog audit workflow (run 34472910244).

Operational records now expose `classification_evidence` and `piwi_evidence` as immutable tuples. Each assertion retains its registry filename, source name, matched literal name or declared alias, country, recorded status, effective date when supplied, source IDs, and source URLs. Country summaries use the same loader. Unknown dates, countries, and statuses remain absent; an unresolved source ID is preserved without an invented URL.

These are stored source assertions. This change does not revalidate the source documents or turn a historical status into a current eligibility decision. It adds no identities, acreage, resistance traits, or legal GI entitlement. Both Adelaide and VIVC-only records expose the same evidence structure.

Regression checks cover the recorded French classification, a declared PIWI alias, missing source metadata, and agreement between evidence and country summaries across all operational records.
