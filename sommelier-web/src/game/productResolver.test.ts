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
    expect(productResolutionPassCount).toBe(2);
    expect(productResolutionRules.length).toBeGreaterThanOrEqual(37);
    expect(report.generationSafe).toBeGreaterThanOrEqual(23);
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

  it('keeps Port and Jerez reference-only until exact product regulation extraction is complete', () => {
    const port = resolveWineProduct({ country: 'Portugal', designation: 'Porto / Port', vintage: 1963, requestedTerms: 'Vintage Port' });
    const fino = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'Fino' });

    expect(port.rule?.generationStatus).toBe('reference-only');
    expect(port.rule?.ageingArchetype).toBe('bottle-aged-fortified');
    expect(port.historicalComplianceVerified).toBe(false);
    expect(fino.rule?.generationStatus).toBe('reference-only');
    expect(fino.rule?.ageingArchetype).toBe('biological-flor');
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
