import { describe, expect, it } from 'vitest';
import {
  productResolutionPassCount,
  productResolutionRules,
  productWinemakingLegality,
  resolveWineProduct,
  validateProductResolver,
} from './productResolver';
import { winemakingDecisionById } from './winemaking';

describe('exact wine product resolver', () => {
  it('validates a non-trivial multi-pass product library with no broken rule links', () => {
    const report = validateProductResolver();
    expect(productResolutionPassCount).toBe(3);
    expect(productResolutionRules.length).toBeGreaterThanOrEqual(54);
    expect(report.generationSafe).toBeGreaterThanOrEqual(27);
    expect(report.designations).toBeGreaterThanOrEqual(11);
    expect(report.issues).toEqual([]);
  });

  it('resolves Brunello Riserva separately from normale and preserves composition/ageing', () => {
    const riserva = resolveWineProduct({
      country: 'Italy',
      designation: 'Brunello di Montalcino',
      vintage: 2021,
      color: 'red',
      grape: 'Sangiovese',
      requestedTerms: 'Riserva',
    });
    expect(riserva.status).toBe('resolved');
    expect(riserva.rule?.productName).toBe('Brunello di Montalcino Riserva');
    expect(riserva.rule?.composition?.[0]).toMatchObject({ grape: 'Sangiovese', minPct: 100, maxPct: 100 });
    expect(riserva.rule?.ageingRuleIds).toContain('age-it-brunello-riserva-current');
    expect(riserva.exactProductGenerationSafe).toBe(true);
    expect(riserva.historicalComplianceVerified).toBe(false);
  });

  it('does not flatten Rioja color and ageing levels', () => {
    const red = resolveWineProduct({ country: 'Spain', designation: 'Rioja', color: 'red', requestedTerms: 'Crianza' });
    const white = resolveWineProduct({ country: 'Spain', designation: 'Rioja', color: 'white', requestedTerms: 'Crianza' });
    const granReserva = resolveWineProduct({ country: 'Spain', designation: 'Rioja', color: 'red', requestedTerms: 'Gran Reserva' });

    expect(red.rule?.ageingRuleIds).toContain('age-es-rioja-crianza-red-current');
    expect(white.rule?.ageingRuleIds).toContain('age-es-rioja-crianza-white-rose-current');
    expect(granReserva.rule?.ageingRuleIds).toContain('age-es-rioja-gran-reserva-red-current');
  });

  it('prefers the most specific Tokaj product term and keeps incomplete products conditional', () => {
    const six = resolveWineProduct({ country: 'Hungary', designation: 'Tokaj', requestedTerms: 'Tokaji Aszú 6 puttonyos' });
    const eszencia = resolveWineProduct({ country: 'Hungary', designation: 'Tokaj', requestedTerms: 'Eszencia' });

    expect(six.rule?.productName).toBe('Tokaji Aszú 6 puttonyos');
    expect(six.rule?.minimumResidualSugarGPerL).toBe(150);
    expect(six.exactProductGenerationSafe).toBe(true);
    expect(eszencia.rule?.generationStatus).toBe('conditional');
    expect(eszencia.exactProductGenerationSafe).toBe(false);
  });

  it('resolves current Tokaj late harvest and Szamorodni as distinct exact products', () => {
    const late = resolveWineProduct({ country: 'Hungary', designation: 'Tokaj', requestedTerms: 'late harvest current' });
    const dry = resolveWineProduct({ country: 'Hungary', designation: 'Tokaj', requestedTerms: 'dry Szamorodni' });
    const sweet = resolveWineProduct({ country: 'Hungary', designation: 'Tokaj', requestedTerms: 'sweet Szamorodni' });
    const aszu = resolveWineProduct({ country: 'Hungary', designation: 'Tokaj', requestedTerms: 'Aszú current' });

    expect(late.rule?.minimumResidualSugarGPerL).toBe(45);
    expect(late.exactProductGenerationSafe).toBe(true);
    expect(dry.rule?.maximumResidualSugarGPerL).toBe(9);
    expect(dry.rule?.minimumWoodAgeMonths).toBe(6);
    expect(sweet.rule?.minimumResidualSugarGPerL).toBe(45);
    expect(sweet.rule?.minimumWoodAgeMonths).toBe(6);
    expect(aszu.rule?.minimumResidualSugarGPerL).toBe(120);
    expect(aszu.rule?.minimumActualAlcoholPct).toBe(9);
    expect(aszu.rule?.minimumWoodAgeMonths).toBe(18);
  });

  it('adds detailed Jerez process and analytical product rules without prematurely making them generation-safe', () => {
    const fino = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'Fino current' });
    const oloroso = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'Oloroso current' });
    const px = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'PX detailed', grape: 'Pedro Ximénez' });
    const vors = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'VORS' });

    expect(fino.rule?.alcoholPctRange).toEqual([15, 17]);
    expect(fino.rule?.maximumResidualSugarGPerL).toBe(4);
    expect(fino.rule?.minimumAverageAgeYears).toBe(2);
    expect(fino.exactProductGenerationSafe).toBe(false);
    expect(oloroso.rule?.ageingArchetype).toBe('oxidative-fortified');
    expect(px.rule?.minimumResidualSugarGPerL).toBe(212);
    expect(px.rule?.minimumOxidativeAgeingMonths).toBe(24);
    expect(vors.rule?.minimumAverageAgeYears).toBe(30);
  });

  it('keeps Port reference-only while resolving newly modeled Crusted and Very Very Old identities', () => {
    const port = resolveWineProduct({ country: 'Portugal', designation: 'Porto / Port', vintage: 1963, requestedTerms: 'Vintage Port' });
    const crusted = resolveWineProduct({ country: 'Portugal', designation: 'Porto / Port', requestedTerms: 'Crusted' });
    const vvo = resolveWineProduct({ country: 'Portugal', designation: 'Porto / Port', requestedTerms: 'Very Very Old' });

    expect(port.rule?.generationStatus).toBe('reference-only');
    expect(port.rule?.ageingArchetype).toBe('bottle-aged-fortified');
    expect(port.historicalComplianceVerified).toBe(false);
    expect(crusted.rule?.minimumBottleAgeYears).toBe(3);
    expect(crusted.rule?.generationStatus).toBe('reference-only');
    expect(vvo.rule?.minimumWoodAgeYears).toBe(80);
  });

  it('keeps legacy Jerez rules reference-only for generic terms while detailed current terms resolve to the new matrix', () => {
    const generic = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'Fino' });
    const detailed = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'Fino current' });
    expect(generic.rule?.generationStatus).toBe('reference-only');
    expect(generic.rule?.ageingArchetype).toBe('biological-flor');
    expect(detailed.rule?.profileId).toBe('es-jerez-product-matrix-2024');
    expect(detailed.rule?.generationStatus).toBe('conditional');
  });

  it('resolves Georgian white and amber Kisi Magraani as different legal/process products', () => {
    const white = resolveWineProduct({ country: 'Georgia', designation: 'Kisi Magraani', color: 'white', grape: 'Kisi', requestedTerms: 'white dry' });
    const amber = resolveWineProduct({ country: 'Georgia', designation: 'Magraani’s Kisi', color: 'white', grape: 'Kisi', requestedTerms: 'amber qvevri' });

    expect(white.status).toBe('resolved');
    expect(white.rule?.productName).toBe('Kisi Magraani white dry');
    expect(white.rule?.exclusiveComposition).toBe(true);
    expect(amber.rule?.productName).toBe('Kisi Magraani amber dry');
    expect(amber.rule?.ageingArchetype).toBe('amber-skin-contact');
    expect(amber.exactProductGenerationSafe).toBe(true);
  });

  it('requires an actual Aleksandrouli-Mujuretuli blend for exact Khvanchkara resolution', () => {
    const single = resolveWineProduct({ country: 'Georgia', designation: 'Khvanchkara', color: 'red', grape: 'Aleksandrouli', requestedTerms: 'Khvanchkara' });
    const blend = resolveWineProduct({
      country: 'Georgia', designation: 'Khvanchkara', color: 'red', requestedTerms: 'Khvanchkara',
      blend: [{ grape: 'Aleksandrouli', percent: 55 }, { grape: 'Mujuretuli', percent: 45 }],
    });
    const contaminated = resolveWineProduct({
      country: 'Georgia', designation: 'Khvanchkara', color: 'red', requestedTerms: 'Khvanchkara',
      blend: [{ grape: 'Aleksandrouli', percent: 45 }, { grape: 'Mujuretuli', percent: 45 }, { grape: 'Saperavi', percent: 10 }],
    });

    expect(single.status).toBe('unresolved');
    expect(blend.status).toBe('resolved');
    expect(blend.rule?.requiresBlend).toBe(true);
    expect(blend.rule?.maximumResidualSugarGPerL).toBe(45);
    expect(contaminated.status).toBe('unresolved');
  });

  it('uses product rules as a conservative legality gate for constrained winemaking choices', () => {
    const finoResolution = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'Fino' });
    const flor = winemakingDecisionById.get('flor-ageing');
    expect(finoResolution.rule).toBeTruthy();
    expect(flor).toBeTruthy();
    const biological = flor?.options.find((option) => option.id === 'biological');
    const oxidative = flor?.options.find((option) => option.id === 'biological-then-oxidative');
    expect(finoResolution.rule && flor && biological && productWinemakingLegality(finoResolution.rule, flor, biological)).toBe(true);
    expect(finoResolution.rule && flor && oxidative && productWinemakingLegality(finoResolution.rule, flor, oxidative)).toBe(false);

    const amberResolution = resolveWineProduct({ country: 'Georgia', designation: 'Kisi Magraani', color: 'white', grape: 'Kisi', requestedTerms: 'amber' });
    const vessel = winemakingDecisionById.get('fermentation-vessel');
    const qvevri = vessel?.options.find((option) => option.id === 'amphora');
    const steel = vessel?.options.find((option) => option.id === 'stainless');
    expect(amberResolution.rule && vessel && qvevri && productWinemakingLegality(amberResolution.rule, vessel, qvevri)).toBe(true);
    expect(amberResolution.rule && vessel && steel && productWinemakingLegality(amberResolution.rule, vessel, steel)).toBe(false);
  });

  it('rejects a composition that cannot satisfy an exact product', () => {
    const wrong = resolveWineProduct({
      country: 'Italy',
      designation: 'Brunello di Montalcino',
      color: 'red',
      grape: 'Merlot',
      requestedTerms: 'Riserva',
    });
    expect(wrong.status).toBe('unresolved');
  });
});
