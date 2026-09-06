import { describe, expect, it } from 'vitest';
import {
  scaledTradeDiscoveryCandidates,
  scaledTradeDiscoveryCountsByStage,
  tradeDiscoveryResearchQueue,
  validateScaledTradeDiscovery,
} from './tradeSourceDiscoveryScale';

describe('scaled importer and distributor discovery funnel', () => {
  it('expands beyond hand-picked sources into a large deduplicated specialist research queue', () => {
    const report = validateScaledTradeDiscovery();
    expect(report.passes).toBe(2);
    expect(report.uniqueCandidates).toBeGreaterThan(140);
    expect(report.directoryLeads).toBeGreaterThan(100);
    expect(report.observationIngested).toBeGreaterThanOrEqual(5);
    expect(report.issues).toEqual([]);
  });

  it('deduplicates spelling and company-suffix variants without pretending unrelated firms are the same', () => {
    const bowler = scaledTradeDiscoveryCandidates.find((candidate) => candidate.verifiedTradeSourceIds.includes('trade-bowler'));
    const jose = scaledTradeDiscoveryCandidates.find((candidate) => candidate.verifiedTradeSourceIds.includes('trade-jose-pastor'));
    expect(bowler?.stage).toBe('observation-ingested');
    expect(jose?.stage).toBe('observation-ingested');
    expect(new Set(scaledTradeDiscoveryCandidates.map((candidate) => candidate.normalizedKey)).size).toBe(scaledTradeDiscoveryCandidates.length);
  });

  it('keeps the majority of network discoveries as leads until their own sites are inspected', () => {
    expect(tradeDiscoveryResearchQueue.length).toBeGreaterThan(scaledTradeDiscoveryCountsByStage['website-verified']);
    expect(tradeDiscoveryResearchQueue.every((candidate) => candidate.stage === 'directory-lead')).toBe(true);
  });
});
