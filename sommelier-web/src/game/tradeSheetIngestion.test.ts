import { describe, expect, it } from 'vitest';
import {
  createTradeObservationCandidate,
  detectTradeConflicts,
  tradeDiscoveryCandidateCount,
  tradeDiscoveryCountsByStage,
  tradeFieldAuthority,
  tradeObservationPassCount,
  tradeObservations,
  tradeObservationsForProducer,
  tradeSourcePassCount,
  tradeSources,
  validateTradeSheetIngestion,
} from './tradeSheetIngestion';

describe('trade tech-sheet research ingestion', () => {
  it('scales from a curated seed registry into verified sources plus a larger discovery queue', () => {
    const report = validateTradeSheetIngestion();
    expect(tradeSourcePassCount).toBe(2);
    expect(tradeObservationPassCount).toBe(2);
    expect(tradeSources.length).toBeGreaterThanOrEqual(20);
    expect(tradeDiscoveryCandidateCount).toBeGreaterThanOrEqual(60);
    expect(tradeDiscoveryCountsByStage['directory-lead']).toBeGreaterThanOrEqual(40);
    expect(tradeObservations.length).toBeGreaterThanOrEqual(16);
    expect(report.fieldsExtracted).toBeGreaterThanOrEqual(120);
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

  it('turns niche commercial grapes into wine-specific technical evidence rather than generic grape prose', () => {
    const romorantin = tradeObservations.find((observation) => observation.id === 'tradeobs-bowler-cazin-romorantin-2023');
    const baco = tradeObservations.find((observation) => observation.id === 'tradeobs-jenny-francois-stavek-baco-noir');
    const inzo = tradeObservations.find((observation) => observation.id === 'tradeobs-massanois-caruso-minini-inzolia');
    expect(romorantin?.fields.varietyComposition).toBe('100% Romorantin');
    expect(romorantin?.fields.vineAgeYearsRange).toEqual([40, 90]);
    expect(baco?.fields.productionQuantityBottles).toBe(450);
    expect(inzo?.fields.varietyComposition).toBe('100% Inzolia');
    expect(inzo?.fields.productionQuantityBottles).toBe(25000);
  });

  it('retains mixed-planting and obscure-variety composition evidence at producer/wine scope', () => {
    const oldArgentina = tradeObservations.find((observation) => observation.id === 'tradeobs-josepastor-elmontanista-viejas-tintas');
    const galicia = tradeObservations.find((observation) => observation.id === 'tradeobs-josepastor-nanclares-tinto');
    expect(oldArgentina?.fields.varieties).toEqual(['Barbera', 'Bonarda', 'Greco Nero', 'Rabosso Veronese', 'Cardin', 'Freisa']);
    expect(galicia?.fields.varieties).toEqual(['Mencía', 'Caiño', 'Espadeiro', 'Sousón', 'Brancellao']);
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
