import { describe, expect, it } from 'vitest';
import {
  authorityVintageRatings,
  environmentalProfiles,
  findEnvironmentalProfile,
  findVintageObservation,
  validateEnvironmentalResearch,
  vintageObservations,
} from './environment';

const rec = (value: unknown) => value as Record<string, unknown>;

describe('soil climate vintage and matrix research', () => {
  it('keeps a sourced environmental layer with bounded derived matrices', () => {
    const report = validateEnvironmentalResearch();
    expect(environmentalProfiles.length).toBeGreaterThanOrEqual(9);
    expect(vintageObservations.length).toBeGreaterThanOrEqual(10);
    expect(authorityVintageRatings.length).toBeGreaterThanOrEqual(25);
    expect(report.countries).toBeGreaterThanOrEqual(5);
    expect(report.issues).toEqual([]);
  });

  it('preserves meaningful soil and climate distinctions by place', () => {
    const champagne = findEnvironmentalProfile('env-fr-champagne');
    const barolo = findEnvironmentalProfile('env-it-barolo');
    const alta = findEnvironmentalProfile('env-es-rioja-alta');
    const alavesa = findEnvironmentalProfile('env-es-rioja-alavesa');
    const oriental = findEnvironmentalProfile('env-es-rioja-oriental');
    const meursault = findEnvironmentalProfile('env-fr-meursault');

    expect(champagne && rec(champagne.climate).annualMeanTempC).toBe(11);
    expect(champagne && rec(champagne.soils[0]).shareOfOutcroppingSedimentaryRockPct).toBe(75);
    expect(barolo?.soils.map((soil) => rec(soil).name)).toContain("Sant'Agata Fossili Marls");
    expect(meursault && rec(meursault.topography).keyElevationM).toBe(260);
    expect(alavesa && rec(alavesa.soils[0]).estimatedSharePct).toBe(95);
    expect(alta?.matrixModifiers.acidity).toBeGreaterThan(oriental?.matrixModifiers.acidity ?? 0);
    expect(oriental?.matrixModifiers.alcohol).toBeGreaterThan(alta?.matrixModifiers.alcohol ?? 0);
  });

  it('stores actual growing-season observations instead of legacy generic quality scores', () => {
    const champagne2021 = findVintageObservation('vintage-fr-champagne-2021');
    const champagne2022 = findVintageObservation('vintage-fr-champagne-2022');
    const burgundy2022 = findVintageObservation('vintage-fr-bourgogne-2022');
    const bordeaux2021 = findVintageObservation('vintage-fr-bordeaux-2021');
    const bordeaux2022 = findVintageObservation('vintage-fr-bordeaux-2022');

    expect(rec(champagne2021?.growingSeason).harvestStart).toBe('2021-09-06');
    expect(rec(champagne2022?.growingSeason).commercialYieldKgHa).toBe(12000);
    expect(rec(burgundy2022?.growingSeason).volumeHectolitresApprox).toBe(1750000);
    expect(rec(bordeaux2021?.growingSeason).productionVsTenYearAveragePct).toBe(-20);
    expect(bordeaux2021?.matrixModifiers.botrytisSuitability).toBeGreaterThan(0.5);
    expect(bordeaux2022?.matrixModifiers.ripeness).toBeGreaterThan(0.5);
    for (const vintage of vintageObservations) {
      expect(vintage).not.toHaveProperty('qualityScore');
      expect(vintage).not.toHaveProperty('legacyQualityScore');
    }
  });

  it('keeps measured Napa rainfall separate from derived vintage effects', () => {
    const napa2022 = findVintageObservation('vintage-us-napa-2022');
    const napa2023 = findVintageObservation('vintage-us-napa-2023');
    expect(rec(napa2022?.growingSeason).chartPeriodRainfallInches).toBe(15.49);
    expect(rec(napa2023?.growingSeason).chartPeriodRainfallInches).toBe(40.06);
    expect(napa2022?.matrixModifiers.derived).toBe(true);
    expect(napa2022?.matrixModifiers.confidence).toBeLessThanOrEqual(2);
  });

  it('preserves authority vintage ratings as categories rather than inventing numeric scores', () => {
    const rioja2025 = authorityVintageRatings.find((rating) => rating.region === 'Rioja DOCa' && rating.year === 2025);
    const rioja2019 = authorityVintageRatings.find((rating) => rating.region === 'Rioja DOCa' && rating.year === 2019);
    const rioja2018 = authorityVintageRatings.find((rating) => rating.region === 'Rioja DOCa' && rating.year === 2018);
    expect(rioja2025?.rating).toBe('Excellent');
    expect(rioja2019?.rating).toBe('Excellent');
    expect(rioja2018?.rating).toBe('Good');
  });
});
