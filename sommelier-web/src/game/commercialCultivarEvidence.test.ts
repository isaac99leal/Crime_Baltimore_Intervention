import { describe, expect, it } from 'vitest';
import {
  commercialBearingVarieties,
  commercialCultivarCoverage,
  cultivationForCultivar,
  currentBearingVarieties,
  regionalCultivationObservations,
  validateCommercialCultivarEvidence,
  vintageContextsForCultivar,
} from './commercialCultivarEvidence';

describe('commercial cultivar cultivation and wine-use evidence', () => {
  it('promotes the Adelaide statistical archive into a broad commercial-viticulture evidence layer', () => {
    const report = validateCommercialCultivarEvidence();
    expect(report.authorityVarieties).toBe(1997);
    expect(commercialBearingVarieties.length).toBeGreaterThan(1200);
    expect(currentBearingVarieties.length).toBeGreaterThan(1000);
    expect(regionalCultivationObservations.length).toBeGreaterThan(2500);
    expect(report.regionalVintageObservationsAvailable).toBeGreaterThanOrEqual(15);
    expect(report.issues).toEqual([]);
  });

  it('keeps exact historical/global bearing-area series rather than one timeless acreage number', () => {
    const aglianico = commercialCultivarCoverage('Aglianico');
    expect(aglianico?.areaSeries?.areaHa[2000]).toBeCloseTo(9346.0044);
    expect(aglianico?.areaSeries?.areaHa[2023]).toBeCloseTo(9603.8876);
  });

  it('exposes documented local cultivation without relabelling statistical geography as a GI', () => {
    const shesh = cultivationForCultivar('Shesh i Zi', 'Albania');
    expect(shesh.some((record) => record.areaHa === 2720)).toBe(true);
    expect(shesh.every((record) => record.geographyStatus === 'statistical-not-gi')).toBe(true);
  });

  it('separates statistical cultivation from protected-origin wine-use corroboration', () => {
    const nebbiolo = commercialCultivarCoverage('Nebbiolo');
    expect(nebbiolo?.legalWineUse.some((record) => record.designation === 'Barolo')).toBe(true);
    expect(nebbiolo?.status).not.toBe('statistical-bearing-area-only');
  });

  it('corroborates commercial wine use from importer technical evidence and retains actual cellar choices', () => {
    const romorantin = commercialCultivarCoverage('Romorantin');
    const cazin = romorantin?.tradeWineUse.find((record) => record.producer === 'Cazin');
    expect(cazin?.vintage).toBe(2023);
    expect(cazin?.technicalFields.vineAgeYearsRange).toEqual([40, 90]);
    expect(cazin?.technicalFields.malolactic).toContain('does not undergo');
    expect(cazin?.technicalFields.maturationVessel).toBe('used 300 L barrels');
  });

  it('keeps regional vintage evidence attached to grape-place context rather than inventing a global grape vintage score', () => {
    const contexts = vintageContextsForCultivar('Sangiovese');
    const chianti2021 = contexts.find((context) => context.region === 'Chianti Classico' && context.year === 2021);
    expect(chianti2021?.scope).toBe('regional-context-not-universal-cultivar-rating');
    expect(chianti2021?.styleEffects).toContain('fine ripe tannins');
    expect(chianti2021?.matchBasis).toContain('legal-wine-use-geography');
  });

  it('still preserves existing vintage-specific importer evidence for established cultivars', () => {
    const zinfandel = commercialCultivarCoverage('Zinfandel');
    expect(zinfandel?.tradeWineUse.some((record) => record.producer === 'Bedrock Wine Co.')).toBe(true);
    expect(zinfandel?.tradeWineUse.some((record) => record.vintage === 2024)).toBe(true);
  });
});
