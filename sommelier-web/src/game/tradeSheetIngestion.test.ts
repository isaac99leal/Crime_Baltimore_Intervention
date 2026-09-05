import { describe, expect, it } from 'vitest';
import {
  createTradeObservationCandidate,
  detectTradeConflicts,
  tradeFieldAuthority,
  tradeObservations,
  tradeObservationsForProducer,
  tradeSources,
  validateTradeSheetIngestion,
} from './tradeSheetIngestion';

describe('trade tech-sheet research ingestion', () => {
  it('loads a curated importer/distributor registry and normalized seed observations', () => {
    const report = validateTradeSheetIngestion();
    expect(tradeSources).toHaveLength(5);
    expect(tradeObservations.length).toBeGreaterThanOrEqual(5);
    expect(report.fieldsExtracted).toBeGreaterThanOrEqual(40);
    expect(report.conflicts).toBe(0);
    expect(report.issues).toEqual([]);
  });

  it('allows vineyard and cellar facts but refuses trade material as legal or genetic authority', () => {
    expect(tradeFieldAuthority('rootstock')).toBe('trade-allowed');
    expect(tradeFieldAuthority('ageingMonths')).toBe('trade-allowed');
    expect(tradeFieldAuthority('protectedOriginLegalStatus')).toBe('corroboration-required');
    expect(tradeFieldAuthority('primeCultivarIdentity')).toBe('corroboration-required');
    expect(tradeFieldAuthority('historicalWeather')).toBe('corroboration-required');
  });

  it('keeps importer producer-level ranges contextual rather than converting them into vintage facts', () => {
    const jose = tradeObservationsForProducer('Jose Gil')[0];
    expect(jose.vintage).toBeNull();
    expect(jose.fields.vineAgeYearsRange).toEqual([5, 130]);
    expect(jose.fields.elevationMRange).toEqual([540, 600]);
  });

  it('preserves wine-vintage specific technical data separately', () => {
    const bedrock = tradeObservations.find((observation) => observation.id === 'tradeobs-skurnik-bedrock-katushas-2024');
    expect(bedrock?.vintage).toBe(2024);
    expect(bedrock?.fields.vineyardPlantedYear).toBe(1915);
    expect(bedrock?.fields.newOakPct).toBe(25);
    expect(bedrock?.fields.alcoholPct).toBe(14.5);
  });

  it('detects same-entity same-vintage conflicts without overwriting either observation', () => {
    const original = tradeObservations[0];
    const conflicting = {
      ...original,
      id: `${original.id}-conflict-test`,
      fields: { ...original.fields, alcoholPct: 13.9 },
    };
    const conflicts = detectTradeConflicts([original, conflicting]);
    expect(conflicts.some((conflict) => conflict.field === 'alcoholPct')).toBe(true);
  });

  it('quarantines a proposed trade observation that attempts to establish GI law', () => {
    const result = createTradeObservationCandidate({
      id: 'test-illegal-promotion',
      tradeSourceId: 'trade-skurnik',
      sourceUrl: 'https://www.skurnik.com/example',
      producer: 'Example',
      wine: 'Example Wine',
      vintage: 2025,
      country: 'United States',
      region: 'Oregon',
      fields: { protectedOriginLegalStatus: 'invented-law' },
      evidenceChannel: 'test',
      sourceRef: 'trade-skurnik-techsheets-pass20',
    });
    expect(result.accepted).toBe(false);
    expect(result.issues.join(' ')).toContain('corroboration');
  });
});
