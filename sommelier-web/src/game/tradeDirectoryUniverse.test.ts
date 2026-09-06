import { describe, expect, it } from 'vitest';
import {
  tradeDirectoryDrift,
  tradeDirectoryListingSlots,
  tradeDirectoryMarketCount,
  tradeDirectoryPriorityMarkets,
  validateTradeDirectoryUniverse,
} from './tradeDirectoryUniverse';

describe('global trade directory research universe', () => {
  it('keeps a hundreds-scale discovery universe without treating directory listings as verified sources', () => {
    const report = validateTradeDirectoryUniverse();
    expect(tradeDirectoryMarketCount).toBe(34);
    expect(tradeDirectoryListingSlots).toBe(886);
    expect(report.driftRecords).toBeGreaterThanOrEqual(2);
    expect(report.issues).toEqual([]);
  });

  it('prioritizes the largest unexplored trade ecosystems without implying quality', () => {
    const top = tradeDirectoryPriorityMarkets(5);
    expect(top[0]).toEqual({ market: 'France', listed: 196 });
    expect(top.some((record) => record.market === 'Italy' && record.listed === 133)).toBe(true);
    expect(top.some((record) => record.market === 'Spain' && record.listed === 88)).toBe(true);
  });

  it('preserves directory drift instead of silently replacing one snapshot', () => {
    const australia = tradeDirectoryDrift.find((record) => record.market === 'Australia');
    const usa = tradeDirectoryDrift.find((record) => record.market === 'USA');
    expect(australia).toMatchObject({ indexListed: 58, liveListed: 56, delta: -2 });
    expect(usa).toMatchObject({ indexListed: 32, liveListed: 30, delta: -2 });
  });
});
