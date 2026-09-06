import discoveryPass2 from '../data/research/trade_source_discovery_queue_pass2.json';
import discoveryPass3 from '../data/research/trade_source_discovery_queue_pass3.json';
import { tradeObservations, tradeSources, type TradeDiscoveryStage } from './tradeSheetIngestion';
import { researchSourceById } from './research';

type DiscoveryGroup = { sourceRef: string; candidates: string[] };
type DiscoveryFile = { schemaVersion: number; updatedAt: string; method: string; groups: DiscoveryGroup[] };

const files = [discoveryPass2 as DiscoveryFile, discoveryPass3 as DiscoveryFile];

const normalize = (value: string) => value
  .normalize('NFKD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/&/g, ' and ')
  .replace(/\b(?:wines?|wine co(?:mpany)?|imports?|importers?|selections?|wine merchants?|wine and spirits)\b/gi, ' ')
  .replace(/[^a-zA-Z0-9]+/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()
  .toLocaleLowerCase();

export type ScaledTradeDiscoveryCandidate = {
  canonicalDisplayName: string;
  normalizedKey: string;
  aliases: string[];
  stage: TradeDiscoveryStage;
  discoverySourceRefs: string[];
  verifiedTradeSourceIds: string[];
  observationCount: number;
};

const candidates = new Map<string, ScaledTradeDiscoveryCandidate>();
for (const file of files) {
  for (const group of file.groups) {
    for (const name of group.candidates) {
      const key = normalize(name);
      if (!key) continue;
      const existing = candidates.get(key);
      if (existing) {
        if (!existing.aliases.includes(name)) existing.aliases.push(name);
        if (!existing.discoverySourceRefs.includes(group.sourceRef)) existing.discoverySourceRefs.push(group.sourceRef);
      } else {
        candidates.set(key, {
          canonicalDisplayName: name,
          normalizedKey: key,
          aliases: [name],
          stage: 'directory-lead',
          discoverySourceRefs: [group.sourceRef],
          verifiedTradeSourceIds: [],
          observationCount: 0,
        });
      }
    }
  }
}

for (const source of tradeSources) {
  const key = normalize(source.name);
  const existing = candidates.get(key) ?? {
    canonicalDisplayName: source.name,
    normalizedKey: key,
    aliases: [source.name],
    stage: 'directory-lead' as TradeDiscoveryStage,
    discoverySourceRefs: [],
    verifiedTradeSourceIds: [],
    observationCount: 0,
  };
  if (!existing.verifiedTradeSourceIds.includes(source.id)) existing.verifiedTradeSourceIds.push(source.id);
  if (!existing.discoverySourceRefs.includes(source.sourceRef)) existing.discoverySourceRefs.push(source.sourceRef);
  existing.stage = 'website-verified';
  candidates.set(key, existing);
}

for (const observation of tradeObservations) {
  const source = tradeSources.find((candidate) => candidate.id === observation.tradeSourceId);
  if (!source) continue;
  const key = normalize(source.name);
  const existing = candidates.get(key);
  if (!existing) continue;
  existing.observationCount += 1;
  existing.stage = 'observation-ingested';
}

export const scaledTradeDiscoveryCandidates = [...candidates.values()].sort((a, b) =>
  b.observationCount - a.observationCount || b.discoverySourceRefs.length - a.discoverySourceRefs.length || a.canonicalDisplayName.localeCompare(b.canonicalDisplayName),
);

export const scaledTradeDiscoveryCount = scaledTradeDiscoveryCandidates.length;
export const scaledTradeDiscoveryCountsByStage = Object.fromEntries(
  (['directory-lead', 'website-verified', 'portfolio-structured', 'tech-sheet-capable', 'observation-ingested'] as TradeDiscoveryStage[])
    .map((stage) => [stage, scaledTradeDiscoveryCandidates.filter((candidate) => candidate.stage === stage).length]),
) as Record<TradeDiscoveryStage, number>;

export const tradeDiscoveryResearchQueue = scaledTradeDiscoveryCandidates.filter((candidate) => candidate.stage === 'directory-lead');

export function validateScaledTradeDiscovery() {
  const issues: string[] = [];
  const keys = new Set<string>();
  for (const candidate of scaledTradeDiscoveryCandidates) {
    if (!candidate.normalizedKey || !candidate.canonicalDisplayName) issues.push('Incomplete scaled trade discovery candidate.');
    if (keys.has(candidate.normalizedKey)) issues.push(`Duplicate scaled trade candidate key: ${candidate.normalizedKey}`);
    keys.add(candidate.normalizedKey);
    for (const sourceRef of candidate.discoverySourceRefs) {
      if (!researchSourceById.has(sourceRef)) issues.push(`Unknown discovery sourceRef ${sourceRef} for ${candidate.canonicalDisplayName}`);
    }
  }
  return {
    passes: files.length,
    uniqueCandidates: scaledTradeDiscoveryCount,
    directoryLeads: tradeDiscoveryResearchQueue.length,
    websiteVerified: scaledTradeDiscoveryCountsByStage['website-verified'],
    observationIngested: scaledTradeDiscoveryCountsByStage['observation-ingested'],
    issues,
  };
}
