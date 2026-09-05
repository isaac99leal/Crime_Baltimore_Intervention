import { describe, expect, it } from 'vitest';
import {
  applyResearchMatrices,
  authorityVintageRatingForPlace,
  authorityVintageRatings,
  environmentalProfileForPlace,
  environmentalProfiles,
  environmentalResearchPassCount,
  findEnvironmentalProfile,
  findVintageObservation,
  validateEnvironmentalResearch,
  vintageObservationForPlace,
  vintageObservations,
  vintageResearchPassCount,
} from './environment';
import type { ReferencePlace } from './reference';
import type { WineProfile } from './types';

const rec = (value: unknown) => value as Record<string, unknown>;

function place(country: string, name: string, path: string[]): ReferencePlace {
  return {
    id: `${country}:${name}`,
    country,
    name,
    kind: 'appellation',
    path,
    classificationTiers: [],
    primaryGrapes: [],
    authorizedGrapes: [],
    soils: [],
  };
}

describe('soil climate vintage and matrix research', () => {
  it('keeps multi-pass sourced environmental and vintage layers with bounded derived matrices', () => {
    const report = validateEnvironmentalResearch();
    expect(environmentalResearchPassCount).toBe(3);
    expect(vintageResearchPassCount).toBe(3);
    expect(environmentalProfiles.length).toBeGreaterThanOrEqual(26);
    expect(vintageObservations.length).toBeGreaterThanOrEqual(17);
    expect(authorityVintageRatings.length).toBeGreaterThanOrEqual(25);
    expect(report.countries).toBeGreaterThanOrEqual(12);
    expect(report.issues).toEqual([]);
  });

  it('preserves meaningful soil and climate distinctions by place', () => {
    const champagne = findEnvironmentalProfile('env-fr-champagne');
    const barolo = findEnvironmentalProfile('env-it-barolo');
    const alta = findEnvironmentalProfile('env-es-rioja-alta');
    const alavesa = findEnvironmentalProfile('env-es-rioja-alavesa');
    const oriental = findEnvironmentalProfile('env-es-rioja-oriental');
    const meursault = findEnvironmentalProfile('env-fr-meursault');
    const pomerol = findEnvironmentalProfile('env-fr-pomerol');
    const brunello = findEnvironmentalProfile('env-it-brunello-montalcino');
    const chianti = findEnvironmentalProfile('env-it-chianti-classico');
    const santorini = findEnvironmentalProfile('env-gr-santorini');
    const mosel = findEnvironmentalProfile('env-de-mosel');
    const kamptal = findEnvironmentalProfile('env-at-kamptal');
    const tokaj = findEnvironmentalProfile('env-hu-tokaj');
    const uco = findEnvironmentalProfile('env-ar-uco-valley');
    const barossa = findEnvironmentalProfile('env-au-barossa-valley');
    const margaretRiver = findEnvironmentalProfile('env-au-margaret-river');

    expect(champagne && rec(champagne.climate).annualMeanTempC).toBe(11);
    expect(champagne && rec(champagne.soils[0]).shareOfOutcroppingSedimentaryRockPct).toBe(75);
    expect(barolo?.soils.map((soil) => rec(soil).name)).toContain("Sant'Agata Fossili Marls");
    expect(meursault && rec(meursault.topography).keyElevationM).toBe(260);
    expect(alavesa && rec(alavesa.soils[0]).estimatedSharePct).toBe(95);
    expect(alta?.matrixModifiers.acidity).toBeGreaterThan(oriental?.matrixModifiers.acidity ?? 0);
    expect(oriental?.matrixModifiers.alcohol).toBeGreaterThan(alta?.matrixModifiers.alcohol ?? 0);
    expect(pomerol?.soils.map((soil) => rec(soil).name)).toContain('iron-rich subsoil');
    expect(rec(brunello?.topography).elevationM).toEqual([120, 650]);
    expect(rec(chianti?.climate).annualRainfallMm).toEqual([800, 900]);
    expect(santorini?.matrixModifiers.droughtStress).toBeGreaterThan(0.8);
    expect(santorini?.matrixModifiers.diseasePressure).toBeLessThan(0);
    expect(rec(mosel?.topography).extremeSlopePct).toBe(70);
    expect(kamptal?.soils.map((soil) => rec(soil).name)).toContain('Heiligenstein Permian sandstone');
    expect(tokaj?.matrixModifiers.botrytisSuitability).toBeGreaterThan(0.8);
    expect(rec(uco?.topography).majorDepartments).toEqual(['Tupungato', 'Tunuyán', 'San Carlos']);
    expect(rec(barossa?.topography).altitudeM).toEqual([130, 430]);
    expect(rec(margaretRiver?.climate).meanJanuaryTempC).toBe(20.9);
  });

  it('maps detailed game geography to the most specific researched environment', () => {
    const meursault = place('France', 'Meursault', ['Burgundy', 'Côte de Beaune', 'Meursault']);
    const gevrey = place('France', 'Gevrey-Chambertin', ['Burgundy', 'Côte de Nuits', 'Gevrey-Chambertin']);
    const pauillac = place('France', 'Pauillac', ['Bordeaux', 'Médoc', 'Pauillac']);
    const saintEmilion = place('France', 'Saint-Émilion Grand Cru', ['Bordeaux', 'Saint-Émilion', 'Saint-Émilion Grand Cru']);
    const montalcino = place('Italy', 'Brunello di Montalcino', ['Tuscany', 'Brunello di Montalcino']);
    const santorini = place('Greece', 'Santorini', ['Aegean Islands', 'Santorini']);
    const oriental = place('Spain', 'Rioja Oriental', ['Rioja', 'Rioja Oriental']);
    const rutherford = place('United States', 'Rutherford', ['California', 'Napa Valley', 'Rutherford']);
    const marlborough = place('New Zealand', 'Marlborough', ['South Island', 'Marlborough']);
    const stellenbosch = place('South Africa', 'Stellenbosch', ['Coastal Region', 'Stellenbosch']);
    const mosel = place('Germany', 'Mosel', ['Mosel']);
    const kamptal = place('Austria', 'Kamptal', ['Niederösterreich', 'Kamptal']);
    const wachau = place('Austria', 'Wachau', ['Niederösterreich', 'Wachau']);
    const tokaj = place('Hungary', 'Tokaj', ['Tokaj']);
    const uco = place('Argentina', 'Valle de Uco', ['Mendoza', 'Valle de Uco']);
    const barossa = place('Australia', 'Barossa Valley', ['South Australia', 'Barossa Valley']);
    const margaretRiver = place('Australia', 'Margaret River', ['Western Australia', 'Margaret River']);

    expect(environmentalProfileForPlace(meursault)?.id).toBe('env-fr-meursault');
    expect(environmentalProfileForPlace(gevrey)?.id).toBe('env-fr-gevrey-chambertin');
    expect(environmentalProfileForPlace(pauillac)?.id).toBe('env-fr-pauillac');
    expect(environmentalProfileForPlace(saintEmilion)?.id).toBe('env-fr-saint-emilion');
    expect(environmentalProfileForPlace(montalcino)?.id).toBe('env-it-brunello-montalcino');
    expect(environmentalProfileForPlace(santorini)?.id).toBe('env-gr-santorini');
    expect(environmentalProfileForPlace(oriental)?.id).toBe('env-es-rioja-oriental');
    expect(environmentalProfileForPlace(rutherford)?.id).toBe('env-us-napa-valley');
    expect(environmentalProfileForPlace(marlborough)?.id).toBe('env-nz-marlborough');
    expect(environmentalProfileForPlace(stellenbosch)?.id).toBe('env-za-stellenbosch');
    expect(environmentalProfileForPlace(mosel)?.id).toBe('env-de-mosel');
    expect(environmentalProfileForPlace(kamptal)?.id).toBe('env-at-kamptal');
    expect(environmentalProfileForPlace(wachau)?.id).toBe('env-at-wachau');
    expect(environmentalProfileForPlace(tokaj)?.id).toBe('env-hu-tokaj');
    expect(environmentalProfileForPlace(uco)?.id).toBe('env-ar-uco-valley');
    expect(environmentalProfileForPlace(barossa)?.id).toBe('env-au-barossa-valley');
    expect(environmentalProfileForPlace(margaretRiver)?.id).toBe('env-au-margaret-river');
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

  it('includes sourced classic-region vintage observations in the same model', () => {
    const chianti2021 = findVintageObservation('vintage-it-chianti-classico-2021');
    const chianti2025 = findVintageObservation('vintage-it-chianti-classico-2025');
    const brunello2021 = findVintageObservation('vintage-it-brunello-montalcino-2021');
    const stellenbosch2021 = findVintageObservation('vintage-za-stellenbosch-2021');
    const mosel2023 = findVintageObservation('vintage-de-mosel-2023');
    const mosel2025 = findVintageObservation('vintage-de-mosel-2025');
    const uco2022 = findVintageObservation('vintage-ar-uco-valley-2022');

    expect(rec(chianti2021?.growingSeason).sangioveseHarvestStart).toBe('around 2021-09-20');
    expect(rec(chianti2025?.growingSeason).productionHectolitres).toBe(265000);
    expect(brunello2021?.matrixModifiers.yield).toBeLessThan(0);
    expect(stellenbosch2021?.matrixModifiers.ageability).toBeGreaterThan(0.3);
    expect(rec(mosel2023?.growingSeason).estimatedMustHectolitres).toBe(710000);
    expect(rec(mosel2025?.growingSeason).selectionLossesSteepSlopesPct).toEqual([50, 75]);
    expect(uco2022?.matrixModifiers.yield).toBeLessThan(-0.3);
    expect(rec(uco2022?.growingSeason).nationalYieldVs2021Pct).toBe(-12);
  });

  it('resolves researched vintages through game geography and applies place plus vintage matrices', () => {
    const champagne = place('France', 'Champagne', ['Champagne']);
    const environment = environmentalProfileForPlace(champagne);
    const vintage = vintageObservationForPlace(champagne, 2022);
    const base: WineProfile = {
      acidity: 3,
      tannin: 1.5,
      body: 2.5,
      sweetness: 1,
      fruitIntensity: 3,
      earthIntensity: 2,
      alcohol: 12,
    };
    const modeled = applyResearchMatrices(base, environment, vintage);

    expect(environment?.id).toBe('env-fr-champagne');
    expect(vintage?.id).toBe('vintage-fr-champagne-2022');
    expect(modeled.acidity).toBeGreaterThan(base.acidity);
    expect(modeled.body).toBeLessThan(base.body);
    expect(modeled.alcohol ?? 0).toBeLessThan(base.alcohol ?? Number.POSITIVE_INFINITY);

    const chianti = place('Italy', 'Chianti Classico', ['Tuscany', 'Chianti Classico']);
    const brunello = place('Italy', 'Brunello di Montalcino', ['Tuscany', 'Brunello di Montalcino']);
    const stellenbosch = place('South Africa', 'Stellenbosch', ['Coastal Region', 'Stellenbosch']);
    const mosel = place('Germany', 'Mosel', ['Mosel']);
    const uco = place('Argentina', 'Valle de Uco', ['Mendoza', 'Valle de Uco']);
    expect(vintageObservationForPlace(chianti, 2021)?.id).toBe('vintage-it-chianti-classico-2021');
    expect(vintageObservationForPlace(brunello, 2021)?.id).toBe('vintage-it-brunello-montalcino-2021');
    expect(vintageObservationForPlace(stellenbosch, 2021)?.id).toBe('vintage-za-stellenbosch-2021');
    expect(vintageObservationForPlace(mosel, 2025)?.id).toBe('vintage-de-mosel-2025');
    expect(vintageObservationForPlace(uco, 2022)?.id).toBe('vintage-ar-uco-valley-2022');
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
    const riojaPlace = place('Spain', 'Rioja Alta', ['Rioja', 'Rioja Alta']);

    expect(rioja2025?.rating).toBe('Excellent');
    expect(rioja2019?.rating).toBe('Excellent');
    expect(rioja2018?.rating).toBe('Good');
    expect(authorityVintageRatingForPlace(riojaPlace, 2019)?.rating).toBe('Excellent');
  });
});
