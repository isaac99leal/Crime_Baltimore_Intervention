import directoryData from '../data/research/trade_directory_universe.json';
import { researchSourceById } from './research';

type DirectoryMarket = {
  market: string;
  listed: number;
};

type LiveSnapshot = {
  market: string;
  observedListed: number;
  sourceUrl: string;
  observationDate: string;
  note: string;
};

type DirectoryUniverseFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  sourceRef: string;
  indexSnapshot: DirectoryMarket[];
  liveCategorySnapshots: LiveSnapshot[];
  guardrails: string[];
};

const data = directoryData as unknown as DirectoryUniverseFile;

export const tradeDirectoryMethod = data.method;
export const tradeDirectoryMarkets = data.indexSnapshot;
export const tradeDirectoryLiveSnapshots = data.liveCategorySnapshots;
export const tradeDirectoryListingSlots = tradeDirectoryMarkets.reduce((sum, record) => sum + record.listed, 0);
export const tradeDirectoryMarketCount = tradeDirectoryMarkets.length;

export type TradeDirectoryDrift = {
  market: string;
  indexListed: number;
  liveListed: number;
  delta: number;
  observationDate: string;
};

export const tradeDirectoryDrift: TradeDirectoryDrift[] = tradeDirectoryLiveSnapshots
  .map((live) => {
    const index = tradeDirectoryMarkets.find((record) => record.market === live.market);
    if (!index) return undefined;
    return {
      market: live.market,
      indexListed: index.listed,
      liveListed: live.observedListed,
      delta: live.observedListed - index.listed,
      observationDate: live.observationDate,
    };
  })
  .filter((record): record is TradeDirectoryDrift => Boolean(record));

export function tradeDirectoryPriorityMarkets(limit = 10): DirectoryMarket[] {
  return [...tradeDirectoryMarkets]
    .sort((a, b) => b.listed - a.listed || a.market.localeCompare(b.market))
    .slice(0, Math.max(0, limit));
}

export function validateTradeDirectoryUniverse() {
  const issues: string[] = [];
  const names = new Set<string>();
  if (!researchSourceById.has(data.sourceRef)) issues.push(`Unknown directory sourceRef: ${data.sourceRef}`);
  for (const market of tradeDirectoryMarkets) {
    if (names.has(market.market)) issues.push(`Duplicate directory market: ${market.market}`);
    names.add(market.market);
    if (!market.market || !Number.isInteger(market.listed) || market.listed < 0) issues.push(`Invalid directory market record: ${market.market}`);
  }
  for (const live of tradeDirectoryLiveSnapshots) {
    if (!names.has(live.market)) issues.push(`Live directory snapshot has no index market: ${live.market}`);
    if (!live.sourceUrl || !live.observationDate) issues.push(`Incomplete live directory snapshot: ${live.market}`);
  }
  if (!data.guardrails.some((guardrail) => guardrail.includes('discovery lead only'))) {
    issues.push('Directory universe lost the discovery-only authority guardrail.');
  }
  return {
    markets: tradeDirectoryMarketCount,
    listingSlots: tradeDirectoryListingSlots,
    driftRecords: tradeDirectoryDrift.length,
    issues,
  };
}
