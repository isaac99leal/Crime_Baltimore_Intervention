import { describe, expect, it } from 'vitest';
import {
  findResearchProfile,
  researchCountries,
  researchProfiles,
  researchSources,
  validateResearchLibrary,
} from './research';

describe('hand-researched wine reference overlay', () => {
  it('has meaningful research depth with resolvable provenance', () => {
    const report = validateResearchLibrary();
    expect(researchProfiles.length).toBeGreaterThanOrEqual(25);
    expect(researchSources.length).toBeGreaterThanOrEqual(30);
    expect(researchCountries.length).toBeGreaterThanOrEqual(10);
    expect(report.generationCandidates).toBeGreaterThanOrEqual(15);
    expect(report.issues).toEqual([]);
  });

  it('preserves legal and stylistic rules instead of flattening appellations', () => {
    const barolo = findResearchProfile('it-barolo-docg');
    const brunello = findResearchProfile('it-brunello-di-montalcino-docg');
    const franciacorta = findResearchProfile('it-franciacorta-docg');
    const rioja = findResearchProfile('es-rioja-doca');
    const priorat = findResearchProfile('es-priorat-doq');
    const chile = findResearchProfile('cl-wine-do-framework');

    expect(barolo?.authorizedGrapes).toEqual(['Nebbiolo']);
    expect(brunello?.productionRules?.grapeComposition).toBe('100% Sangiovese (locally called Brunello)');
    expect(brunello?.productionRules?.minimumOakYears).toBe(2);
    expect(franciacorta?.productionRules?.minimumLeesMonths).toBe(18);
    expect(franciacorta?.productionRules?.minimumLeesMonthsRiserva).toBe(60);
    expect(rioja?.productionRules?.granReservaRedTotalMonths).toBe(60);
    expect(priorat?.classificationTerms).toContain('Gran Vinya Classificada');
    expect(chile?.productionRules?.minimumGeographicOriginPct).toBe(75);
  });

  it('reports unresolved grape spellings as research work, not as fabricated aliases', () => {
    const report = validateResearchLibrary();
    expect(Array.isArray(report.unresolvedGrapes)).toBe(true);
    expect(new Set(report.unresolvedGrapes).size).toBe(report.unresolvedGrapes.length);
  });
});
