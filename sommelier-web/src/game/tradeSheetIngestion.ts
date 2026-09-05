import registryData from '../data/research/trade_source_registry.json';
import observationData from '../data/research/trade_tech_sheet_observations_pass1.json';
import { researchSourceById } from './research';

export type TradeTrustTier = 'trade-curated';

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
  vineyard?: string;
  fields: Record<string, unknown>;
  evidenceChannel: string;
  sourceRef: string;
};

type TradeRegistryFile = {
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

type TradeObservationFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  observations: TradeObservation[];
};

const registry = registryData as unknown as TradeRegistryFile;
const observationsFile = observationData as unknown as TradeObservationFile;

export const tradeSourceMethod = registry.method;
export const tradeFieldPolicy = registry.fieldPolicy;
export const tradeConflictPolicy = registry.conflictPolicy;
export const tradeSources = registry.sources;
export const tradeSourceById = new Map(tradeSources.map((source) => [source.id, source]));
export const tradeObservations = observationsFile.observations;
export const tradeObservationById = new Map(tradeObservations.map((observation) => [observation.id, observation]));

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
    sources: tradeSources.length,
    observations: tradeObservations.length,
    fieldsExtracted: tradeObservations.reduce((sum, observation) => sum + Object.keys(observation.fields).length, 0),
    conflicts: detectTradeConflicts().length,
    issues,
  };
}
