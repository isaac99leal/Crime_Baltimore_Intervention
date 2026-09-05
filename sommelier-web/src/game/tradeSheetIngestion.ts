import registryData from '../data/research/trade_source_registry.json';
import registryDataPass2 from '../data/research/trade_source_registry_pass2.json';
import registryDataPass3 from '../data/research/trade_source_registry_pass3.json';
import discoveryDataPass2 from '../data/research/trade_source_discovery_queue_pass2.json';
import discoveryDataPass3 from '../data/research/trade_source_discovery_queue_pass3.json';
import discoveryDataPass4 from '../data/research/trade_source_discovery_queue_pass4.json';
import observationData from '../data/research/trade_tech_sheet_observations_pass1.json';
import observationDataPass2 from '../data/research/trade_tech_sheet_observations_pass2.json';
import observationDataPass3 from '../data/research/trade_tech_sheet_observations_pass3.json';
import { researchSourceById } from './research';

export type TradeTrustTier = 'trade-curated' | 'trade-verified';
export type TradeDiscoveryStage = 'directory-lead' | 'website-verified' | 'portfolio-structured' | 'tech-sheet-capable' | 'observation-ingested';

export type TradeSource = {
  id: string;
  name: string;
  baseUrl: string;
  sourceRef: string;
  role: string[];
  trustTier: TradeTrustTier;
  discovery: string[];
  versionKeyFields: string[];
  strengths: string[];
  caveats: string[];
};

export type TradeObservation = {
  id: string;
  tradeSourceId: string;
  sourceUrl: string;
  producer: string;
  wine: string | null;
  vintage: number | null;
  country: string;
  region: string;
  vineyard?: string | null;
  fields: Record<string, unknown>;
  evidenceChannel: string;
  sourceRef: string;
};

type TradePolicyRegistryFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  fieldPolicy: {
    tradeSheetMayEstablish: string[];
    requiresPrimaryOrSpecialistCorroboration: string[];
    sensoryPolicy: string;
  };
  sources: TradeSource[];
  conflictPolicy: Record<string, string>;
};

type TradeRegistryFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  sources: TradeSource[];
};

type TradeObservationFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  observations: TradeObservation[];
};

type TradeDiscoveryGroup = {
  sourceRef: string;
  candidates: string[];
};

type TradeDiscoveryFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  groups: TradeDiscoveryGroup[];
  promotionPolicy?: Record<TradeDiscoveryStage, string> | string;
};

export type TradeDiscoveryCandidate = {
  name: string;
  stage: TradeDiscoveryStage;
  discoverySourceRefs: string[];
};

const registry = registryData as unknown as TradePolicyRegistryFile;
const registry2 = registryDataPass2 as unknown as TradeRegistryFile;
const registry3 = registryDataPass3 as unknown as TradeRegistryFile;
const discovery2 = discoveryDataPass2 as unknown as TradeDiscoveryFile;
const discovery3 = discoveryDataPass3 as unknown as TradeDiscoveryFile;
const discovery4 = discoveryDataPass4 as unknown as TradeDiscoveryFile;
const discoveryFiles = [discovery2, discovery3, discovery4];
const observationsFile = observationData as unknown as TradeObservationFile;
const observationsFile2 = observationDataPass2 as unknown as TradeObservationFile;
const observationsFile3 = observationDataPass3 as unknown as TradeObservationFile;

export const tradeSourceMethod = [registry.method, registry2.method, registry3.method, ...discoveryFiles.map((file) => file.method)].join(' ');
export const tradeSourcePassCount = 3;
export const tradeDiscoveryPassCount = discoveryFiles.length;
export const tradeObservationPassCount = 3;
export const tradeFieldPolicy = registry.fieldPolicy;
export const tradeConflictPolicy = registry.conflictPolicy;
export const tradePromotionPolicy = typeof discovery2.promotionPolicy === 'object' && discovery2.promotionPolicy
  ? discovery2.promotionPolicy
  : {} as Record<TradeDiscoveryStage, string>;
export const tradeSources = [...registry.sources, ...registry2.sources, ...registry3.sources];
export const tradeSourceById = new Map(tradeSources.map((source) => [source.id, source]));
export const tradeObservations = [...observationsFile.observations, ...observationsFile2.observations, ...observationsFile3.observations];
export const tradeObservationById = new Map(tradeObservations.map((observation) => [observation.id, observation]));

const normalizedTradeName = (value: string) => value
  .normalize('NFKD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/&/g, 'and')
  .replace(/\b(?:wine|wines|imports?|importers?|selections?|distribution|distributors?|merchant|merchants|company|co|ltd|llc|inc)\b/g, ' ')
  .replace(/[^a-zA-Z0-9]+/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()
  .toLocaleLowerCase();

const discoveryMap = new Map<string, TradeDiscoveryCandidate>();
for (const discovery of discoveryFiles) {
  for (const group of discovery.groups) {
    for (const name of group.candidates) {
      const key = normalizedTradeName(name);
      const existing = discoveryMap.get(key);
      if (existing) {
        if (!existing.discoverySourceRefs.includes(group.sourceRef)) existing.discoverySourceRefs.push(group.sourceRef);
        continue;
      }
      discoveryMap.set(key, { name, stage: 'directory-lead', discoverySourceRefs: [group.sourceRef] });
    }
  }
}

for (const source of tradeSources) {
  const key = normalizedTradeName(source.name);
  const current = discoveryMap.get(key);
  const stage: TradeDiscoveryStage = source.trustTier === 'trade-curated' ? 'observation-ingested' : 'website-verified';
  if (current) {
    current.stage = stage;
  } else {
    discoveryMap.set(key, { name: source.name, stage, discoverySourceRefs: [source.sourceRef] });
  }
}
for (const observation of tradeObservations) {
  const source = tradeSourceById.get(observation.tradeSourceId);
  if (!source) continue;
  const record = discoveryMap.get(normalizedTradeName(source.name));
  if (record) record.stage = 'observation-ingested';
}

export const tradeDiscoveryCandidates = [...discoveryMap.values()].sort((a, b) => a.name.localeCompare(b.name));
export const tradeDiscoveryCandidateCount = tradeDiscoveryCandidates.length;
export const tradeDiscoveryCountsByStage = Object.fromEntries(
  (['directory-lead', 'website-verified', 'portfolio-structured', 'tech-sheet-capable', 'observation-ingested'] as TradeDiscoveryStage[])
    .map((stage) => [stage, tradeDiscoveryCandidates.filter((candidate) => candidate.stage === stage).length]),
) as Record<TradeDiscoveryStage, number>;

const stable = (value: unknown): string => {
  if (Array.isArray(value)) return JSON.stringify([...value].sort((a, b) => String(a).localeCompare(String(b))));
  if (value && typeof value === 'object') {
    return JSON.stringify(Object.fromEntries(Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b))));
  }
  return JSON.stringify(value);
};

export function tradeSource(id: string): TradeSource | undefined {
  return tradeSourceById.get(id);
}

export function tradeObservationsForProducer(producer: string): TradeObservation[] {
  const target = producer.toLocaleLowerCase();
  return tradeObservations.filter((observation) => observation.producer.toLocaleLowerCase() === target);
}

export function tradeFieldAuthority(field: string): 'trade-allowed' | 'corroboration-required' | 'unclassified' {
  if (tradeFieldPolicy.tradeSheetMayEstablish.includes(field)) return 'trade-allowed';
  if (tradeFieldPolicy.requiresPrimaryOrSpecialistCorroboration.includes(field)) return 'corroboration-required';
  return 'unclassified';
}

export type TradeFactCandidate = {
  entityKey: string;
  field: string;
  value: unknown;
  observationId: string;
  sourceRef: string;
  vintage: number | null;
  authority: ReturnType<typeof tradeFieldAuthority>;
};

export function flattenTradeFacts(observation: TradeObservation): TradeFactCandidate[] {
  const entityKey = [observation.producer, observation.wine ?? 'producer', observation.vintage ?? 'undated'].join('|');
  return Object.entries(observation.fields).map(([field, value]) => ({
    entityKey,
    field,
    value,
    observationId: observation.id,
    sourceRef: observation.sourceRef,
    vintage: observation.vintage,
    authority: tradeFieldAuthority(field),
  }));
}

export type TradeConflict = {
  entityKey: string;
  field: string;
  vintage: number | null;
  observations: Array<{ observationId: string; value: unknown }>;
};

export function detectTradeConflicts(records: TradeObservation[] = tradeObservations): TradeConflict[] {
  const buckets = new Map<string, TradeFactCandidate[]>();
  for (const record of records) {
    for (const fact of flattenTradeFacts(record)) {
      const key = `${fact.entityKey}|${fact.field}`;
      const current = buckets.get(key) ?? [];
      current.push(fact);
      buckets.set(key, current);
    }
  }

  const conflicts: TradeConflict[] = [];
  for (const facts of buckets.values()) {
    const uniqueValues = new Set(facts.map((fact) => stable(fact.value)));
    if (facts.length < 2 || uniqueValues.size < 2) continue;
    conflicts.push({
      entityKey: facts[0].entityKey,
      field: facts[0].field,
      vintage: facts[0].vintage,
      observations: facts.map((fact) => ({ observationId: fact.observationId, value: fact.value })),
    });
  }
  return conflicts;
}

export type TradeTechnicalTrajectory = {
  producer: string;
  wine: string;
  records: Array<{ observationId: string; vintage: number; fields: Record<string, unknown> }>;
  changingFields: string[];
};

export function tradeTechnicalTrajectory(producer: string, wine: string): TradeTechnicalTrajectory {
  const producerKey = producer.toLocaleLowerCase();
  const wineKey = wine.toLocaleLowerCase();
  const records = tradeObservations
    .filter((observation) => observation.vintage !== null
      && observation.producer.toLocaleLowerCase() === producerKey
      && (observation.wine ?? '').toLocaleLowerCase() === wineKey)
    .map((observation) => ({ observationId: observation.id, vintage: observation.vintage as number, fields: observation.fields }))
    .sort((a, b) => a.vintage - b.vintage);

  const fields = new Set(records.flatMap((record) => Object.keys(record.fields)));
  const changingFields = [...fields].filter((field) => {
    const observed = records.filter((record) => field in record.fields).map((record) => stable(record.fields[field]));
    return new Set(observed).size > 1;
  }).sort();

  return { producer, wine, records, changingFields };
}

export function createTradeObservationCandidate(input: TradeObservation): { accepted: boolean; issues: string[]; record: TradeObservation } {
  const issues: string[] = [];
  if (!tradeSourceById.has(input.tradeSourceId)) issues.push(`Unknown trade source: ${input.tradeSourceId}`);
  if (!researchSourceById.has(input.sourceRef)) issues.push(`Unknown provenance source: ${input.sourceRef}`);
  if (!input.producer || !input.sourceUrl || !input.country || !input.region) issues.push('Trade observation is missing required identity fields.');
  if (!Object.keys(input.fields).length) issues.push('Trade observation has no extracted fields.');

  for (const field of Object.keys(input.fields)) {
    if (tradeFieldAuthority(field) === 'corroboration-required') {
      issues.push(`${field} requires primary/specialist corroboration and cannot be promoted from trade material alone.`);
    }
  }

  return { accepted: issues.length === 0, issues, record: input };
}

export function validateTradeSheetIngestion() {
  const issues: string[] = [];
  const sourceIds = new Set<string>();
  const observationIds = new Set<string>();

  for (const source of tradeSources) {
    if (sourceIds.has(source.id)) issues.push(`Duplicate trade source id: ${source.id}`);
    sourceIds.add(source.id);
    if (!source.name || !source.baseUrl || !source.sourceRef || !source.discovery.length) issues.push(`Incomplete trade source: ${source.id}`);
    if (!researchSourceById.has(source.sourceRef)) issues.push(`Unknown trade registry sourceRef ${source.sourceRef} in ${source.id}`);
  }

  for (const discovery of discoveryFiles) {
    for (const group of discovery.groups) {
      if (!researchSourceById.has(group.sourceRef)) issues.push(`Unknown trade discovery sourceRef: ${group.sourceRef}`);
      if (!group.candidates.length) issues.push(`Empty trade discovery group: ${group.sourceRef}`);
    }
  }

  for (const observation of tradeObservations) {
    if (observationIds.has(observation.id)) issues.push(`Duplicate trade observation id: ${observation.id}`);
    observationIds.add(observation.id);
    const result = createTradeObservationCandidate(observation);
    if (!result.accepted) issues.push(...result.issues.map((issue) => `${observation.id}: ${issue}`));
  }

  if (!tradeFieldPolicy.requiresPrimaryOrSpecialistCorroboration.includes('primeCultivarIdentity')) {
    issues.push('Trade-sheet policy lost the cultivar-identity corroboration guardrail.');
  }
  if (!tradeFieldPolicy.requiresPrimaryOrSpecialistCorroboration.includes('protectedOriginLegalStatus')) {
    issues.push('Trade-sheet policy lost the protected-origin legal guardrail.');
  }

  return {
    sourcePasses: tradeSourcePassCount,
    discoveryPasses: tradeDiscoveryPassCount,
    observationPasses: tradeObservationPassCount,
    sources: tradeSources.length,
    discoveryCandidates: tradeDiscoveryCandidateCount,
    discoveryCountsByStage: tradeDiscoveryCountsByStage,
    observations: tradeObservations.length,
    fieldsExtracted: tradeObservations.reduce((sum, observation) => sum + Object.keys(observation.fields).length, 0),
    conflicts: detectTradeConflicts().length,
    issues,
  };
}
