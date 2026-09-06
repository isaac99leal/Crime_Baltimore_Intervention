import { describe, expect, it } from 'vitest';
import {
  auditTradeObservationSchema,
  topTradeSchemaFieldsNeedingClassification,
  tradeIdentityReconciliationQueue,
  unclassifiedTradeFieldUsage,
} from './tradeSchemaAudit';

describe('trade observation schema and identity audit', () => {
  it('makes schema drift visible instead of silently treating every granular field as standardized', () => {
    const report = auditTradeObservationSchema();
    expect(report.observations).toBeGreaterThanOrEqual(43);
    expect(report.uniqueFieldNames).toBeGreaterThanOrEqual(60);
    expect(report.unclassifiedFields).toBeGreaterThan(0);
    expect(report.unclassifiedObservationUses).toBeGreaterThan(0);
    expect(unclassifiedTradeFieldUsage.length).toBe(report.unclassifiedFields);
    expect(report.issues).toEqual([]);
  });

  it('preserves the Giannoudi/Yiannoudi importer spelling discrepancy as reconciliation work', () => {
    expect(tradeIdentityReconciliationQueue.some((item) =>
      item.observationId === 'tradeobs-diamond-makarounas-yiannoudi'
      && item.field === 'tradeDisplayedWineName'
      && item.value === 'Giannoudi',
    )).toBe(true);
  });

  it('returns a ranked schema-classification queue for future normalization passes', () => {
    const queue = topTradeSchemaFieldsNeedingClassification(10);
    expect(queue.length).toBeGreaterThan(0);
    expect(queue.length).toBeLessThanOrEqual(10);
    for (let index = 1; index < queue.length; index += 1) {
      expect(queue[index - 1].observations).toBeGreaterThanOrEqual(queue[index].observations);
    }
  });
});
