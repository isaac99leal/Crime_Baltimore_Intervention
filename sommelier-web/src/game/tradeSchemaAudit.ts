import {
  tradeFieldAuthority,
  tradeObservations,
  type TradeObservation,
} from './tradeSheetIngestion';

export type TradeFieldUsage = {
  field: string;
  observations: number;
  examples: string[];
};

export type TradeIdentityReconciliationItem = {
  observationId: string;
  producer: string;
  wine: string | null;
  field: string;
  value: unknown;
};

export const unclassifiedTradeFieldUsage: TradeFieldUsage[] = (() => {
  const usage = new Map<string, { observations: Set<string>; examples: Set<string> }>();
  for (const observation of tradeObservations) {
    for (const field of Object.keys(observation.fields)) {
      if (tradeFieldAuthority(field) !== 'unclassified') continue;
      const current = usage.get(field) ?? { observations: new Set<string>(), examples: new Set<string>() };
      current.observations.add(observation.id);
      if (current.examples.size < 4) current.examples.add(`${observation.producer} — ${observation.wine ?? 'producer record'}`);
      usage.set(field, current);
    }
  }
  return [...usage.entries()]
    .map(([field, record]) => ({ field, observations: record.observations.size, examples: [...record.examples] }))
    .sort((a, b) => b.observations - a.observations || a.field.localeCompare(b.field));
})();

export const tradeIdentityReconciliationQueue: TradeIdentityReconciliationItem[] = tradeObservations.flatMap((observation) => {
  const entries: TradeIdentityReconciliationItem[] = [];
  if (observation.fields.identityReconciliationRequired === true) {
    for (const field of ['tradeDisplayedWineName', 'varietyComposition', 'varieties']) {
      if (!(field in observation.fields)) continue;
      entries.push({
        observationId: observation.id,
        producer: observation.producer,
        wine: observation.wine,
        field,
        value: observation.fields[field],
      });
    }
  }
  return entries;
});

export type TradeSchemaAuditReport = {
  observations: number;
  uniqueFieldNames: number;
  unclassifiedFields: number;
  unclassifiedObservationUses: number;
  identityReconciliationItems: number;
  issues: string[];
};

export function auditTradeObservationSchema(records: TradeObservation[] = tradeObservations): TradeSchemaAuditReport {
  const issues: string[] = [];
  const fields = new Set<string>();
  let unclassifiedObservationUses = 0;

  for (const observation of records) {
    for (const field of Object.keys(observation.fields)) {
      fields.add(field);
      if (tradeFieldAuthority(field) === 'unclassified') unclassifiedObservationUses += 1;
    }
  }

  const forbiddenPatterns = [/^protectedOriginLegalStatus$/i, /^primeCultivarIdentity$/i, /^geneticParentage$/i, /^historicalWeather$/i];
  for (const observation of records) {
    for (const field of Object.keys(observation.fields)) {
      if (forbiddenPatterns.some((pattern) => pattern.test(field))) {
        issues.push(`Observation ${observation.id} contains authority-restricted field ${field}.`);
      }
    }
  }

  return {
    observations: records.length,
    uniqueFieldNames: fields.size,
    unclassifiedFields: unclassifiedTradeFieldUsage.length,
    unclassifiedObservationUses,
    identityReconciliationItems: tradeIdentityReconciliationQueue.length,
    issues,
  };
}

export function topTradeSchemaFieldsNeedingClassification(limit = 25): TradeFieldUsage[] {
  return unclassifiedTradeFieldUsage.slice(0, Math.max(0, limit));
}
