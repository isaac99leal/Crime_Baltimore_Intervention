import { describe, expect, it } from 'vitest';
import {
  productResolutionRules,
  productWinemakingLegality,
  resolveWineProduct,
  validateProductResolver,
} from './productResolver';
import { winemakingDecisionById } from './winemaking';

describe('exact wine product resolver', () => {
  it('validates a non-trivial product library with no broken provenance links', () => {
    const report = validateProductResolver();
    expect(productResolutionRules.length).toBeGreaterThanOrEqual(30);
    expect(report.generationSafe).toBeGreaterThanOrEqual(20);
    expect(report.designations).toBeGreaterThanOrEqual(8);
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

  it('uses product rules as a conservative legality gate for constrained winemaking choices', () => {
    const resolution = resolveWineProduct({ country: 'Spain', designation: 'Jerez-Xérès-Sherry', requestedTerms: 'Fino' });
    const flor = winemakingDecisionById.get('flor-ageing');
    expect(resolution.rule).toBeTruthy();
    expect(flor).toBeTruthy();
    const biological = flor?.options.find((option) => option.id === 'biological');
    const oxidative = flor?.options.find((option) => option.id === 'biological-then-oxidative');
    expect(resolution.rule && flor && biological && productWinemakingLegality(resolution.rule, flor, biological)).toBe(true);
    expect(resolution.rule && flor && oxidative && productWinemakingLegality(resolution.rule, flor, oxidative)).toBe(false);
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
