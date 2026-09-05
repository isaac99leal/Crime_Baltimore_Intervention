import registryPass3 from '../data/research/trade_source_registry_pass3.json';
import { researchSourceById } from './research';
import { tradeSources, type TradeSource } from './tradeSheetIngestion';

type TradeRegistryFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  sources: TradeSource[];
};

const file = registryPass3 as unknown as TradeRegistryFile;

export const verifiedTradeSourcePassCount = 3;
export const scaledVerifiedTradeSources = [...tradeSources, ...file.sources];
export const scaledVerifiedTradeSourceById = new Map(scaledVerifiedTradeSources.map((source) => [source.id, source]));
export const techResourceQualifiedSources = scaledVerifiedTradeSources.filter((source) =>
  source.discovery.some((channel) => /tech|resource|sheet|vintage|catalog/i.test(channel)),
);
export const specialistCultivarTradeSources = scaledVerifiedTradeSources.filter((source) =>
  source.strengths.some((strength) => /indigenous|rare|small|special|georgia|greek|cypriot|german|oxidative|fortified/i.test(strength)),
);

export function validateScaledVerifiedTradeSources() {
  const issues: string[] = [];
  const ids = new Set<string>();
  for (const source of scaledVerifiedTradeSources) {
    if (ids.has(source.id)) issues.push(`Duplicate scaled verified trade source: ${source.id}`);
    ids.add(source.id);
    if (!source.name || !source.baseUrl || !source.sourceRef || !source.discovery.length) issues.push(`Incomplete scaled trade source: ${source.id}`);
    if (!researchSourceById.has(source.sourceRef)) issues.push(`Unknown scaled trade source provenance ${source.sourceRef} in ${source.id}`);
  }
  return {
    passes: verifiedTradeSourcePassCount,
    sources: scaledVerifiedTradeSources.length,
    techResourceQualified: techResourceQualifiedSources.length,
    specialistCultivarSources: specialistCultivarTradeSources.length,
    issues,
  };
}
