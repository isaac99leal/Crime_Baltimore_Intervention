import { describe, expect, it } from 'vitest';
import {
  scaledVerifiedTradeSourceById,
  scaledVerifiedTradeSources,
  specialistCultivarTradeSources,
  techResourceQualifiedSources,
  validateScaledVerifiedTradeSources,
  verifiedTradeSourcePassCount,
} from './tradeSourceRegistryScale';

describe('verified specialist importer and distributor registry scale', () => {
  it('locks three verified-source passes and thirty-three curated/verified trade sources', () => {
    const report = validateScaledVerifiedTradeSources();
    expect(verifiedTradeSourcePassCount).toBe(3);
    expect(scaledVerifiedTradeSources.length).toBeGreaterThanOrEqual(33);
    expect(report.techResourceQualified).toBeGreaterThanOrEqual(8);
    expect(report.specialistCultivarSources).toBeGreaterThanOrEqual(8);
    expect(report.issues).toEqual([]);
  });

  it('includes high-value technical hubs and indigenous-grape specialist portfolios', () => {
    for (const id of [
      'trade-demaison',
      'trade-diamond',
      'trade-georgian-wine-house',
      'trade-vias',
      'trade-kysela',
      'trade-portovino',
    ]) {
      expect(scaledVerifiedTradeSourceById.has(id)).toBe(true);
    }
    expect(techResourceQualifiedSources.some((source) => source.id === 'trade-demaison')).toBe(true);
    expect(specialistCultivarTradeSources.some((source) => source.id === 'trade-diamond')).toBe(true);
  });

  it('keeps verified website status distinct from field-level observation ingestion', () => {
    const georgia = scaledVerifiedTradeSourceById.get('trade-georgian-wine-house');
    expect(georgia?.trustTier).toBe('trade-verified');
    expect(georgia?.strengths.some((strength) => strength.toLowerCase().includes('indigenous'))).toBe(true);
  });
});
