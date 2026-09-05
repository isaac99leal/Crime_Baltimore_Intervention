import { describe, expect, it } from 'vitest';
import {
  findResearchProfile,
  researchCountries,
  researchPassCount,
  researchProfiles,
  researchSourcePassCount,
  researchSources,
  validateResearchLibrary,
} from './research';

describe('hand-researched wine reference overlay', () => {
  it('has meaningful research depth with resolvable provenance', () => {
    const report = validateResearchLibrary();
    expect(researchPassCount).toBe(3);
    expect(researchSourcePassCount).toBe(12);
    expect(researchProfiles.length).toBeGreaterThanOrEqual(65);
    expect(researchSources.length).toBeGreaterThanOrEqual(150);
    expect(researchCountries.length).toBeGreaterThanOrEqual(15);
    expect(report.generationCandidates).toBeGreaterThanOrEqual(28);
    expect(report.issues).toEqual([]);
  });

  it('preserves European legal and stylistic rules instead of flattening appellations', () => {
    const barolo = findResearchProfile('it-barolo-docg');
    const brunello = findResearchProfile('it-brunello-di-montalcino-docg');
    const franciacorta = findResearchProfile('it-franciacorta-docg');
    const rioja = findResearchProfile('es-rioja-doca');
    const priorat = findResearchProfile('es-priorat-doq');
    const santorini = findResearchProfile('gr-santorini-pdo');
    const nemea = findResearchProfile('gr-nemea-pdo');
    const tokaj = findResearchProfile('hu-tokaj-pdo');
    const germany = findResearchProfile('de-quality-origin-framework');

    expect(barolo?.authorizedGrapes).toEqual(['Nebbiolo']);
    expect(brunello?.productionRules?.grapeComposition).toBe('100% Sangiovese (locally called Brunello)');
    expect(brunello?.productionRules?.minimumOakYears).toBe(2);
    expect(franciacorta?.productionRules?.minimumLeesMonths).toBe(18);
    expect(franciacorta?.productionRules?.minimumLeesMonthsRiserva).toBe(60);
    expect(rioja?.productionRules?.granReservaRedTotalMonths).toBe(60);
    expect(priorat?.classificationTerms).toContain('Gran Vinya Classificada');
    expect(santorini?.productionRules?.dryAssyrtikoMinPct).toBe(85);
    expect(santorini?.productionRules?.vinsantoMinimumOxidativeAgeingMonths).toBe(24);
    expect(nemea?.productionRules?.agiorgitikoPct).toBe(100);
    expect(tokaj?.authorizedGrapes).toHaveLength(6);
    expect(tokaj?.productionRules?.sixPuttonyosResidualSugarMinGPerL).toBe(150);
    expect(germany?.productionRules?.praedikatEnrichmentAllowed).toBe(false);
  });

  it('keeps Burgundy and Bordeaux hierarchy distinctions explicit', () => {
    const chablisGrandCru = findResearchProfile('fr-chablis-grand-cru-aop');
    const gevrey = findResearchProfile('fr-gevrey-chambertin-aop');
    const meursault = findResearchProfile('fr-meursault-aop');
    const aloxe = findResearchProfile('fr-aloxe-corton-aop');
    const margaux = findResearchProfile('fr-margaux-aop');
    const pomerol = findResearchProfile('fr-pomerol-aop');
    const sauternes = findResearchProfile('fr-sauternes-aop');
    const saintEmilionGrandCru = findResearchProfile('fr-saint-emilion-grand-cru-aop');

    expect(chablisGrandCru?.grandCruClimats).toHaveLength(7);
    expect(chablisGrandCru?.productionRules?.officialGrandCruClimatCount).toBe(7);
    expect(gevrey?.premierCruClimatCount).toBe(26);
    expect(gevrey?.relatedGrandCrus).toHaveLength(9);
    expect(meursault?.premierCruClimatCount).toBe(19);
    expect(aloxe?.premierCruClimatCount).toBe(14);
    expect(aloxe?.relatedGrandCrus).toContain('Corton-Charlemagne');
    expect(margaux?.productionRules?.classifiedGrowthCount1855).toBe(21);
    expect(pomerol?.classificationTerms).toEqual([]);
    expect(sauternes?.communes).toEqual(['Barsac', 'Bommes', 'Fargues', 'Preignac', 'Sauternes']);
    expect(saintEmilionGrandCru?.classificationTerms).toContain('Premier Grand Cru Classé');
  });

  it('preserves New World origin, variety and vintage percentage rules', () => {
    const chile = findResearchProfile('cl-wine-do-framework');
    const usa = findResearchProfile('us-federal-wine-label-framework');
    const ontario = findResearchProfile('ca-ontario-vqa-framework');
    const bc = findResearchProfile('ca-bc-vqa-framework');
    const australia = findResearchProfile('au-wine-gi-framework');

    expect(chile?.productionRules?.minimumGeographicOriginPct).toBe(75);
    expect(usa?.productionRules?.avaOriginMinPct).toBe(85);
    expect(usa?.productionRules?.singleVarietyMinPct).toBe(75);
    expect(usa?.productionRules?.avaVintageMinPct).toBe(95);
    expect(ontario?.productionRules?.ontarioOriginPct).toBe(100);
    expect(ontario?.productionRules?.singleVarietyMinPct).toBe(85);
    expect(bc?.productionRules?.currentNamedGiOriginMinPct).toBe(85);
    expect(bc?.productionRules?.vintageMinPct).toBe(85);
    expect(australia?.productionRules?.singleGiMinPct).toBe(85);
    expect(australia?.productionRules?.multipleGiClaimsTotalMinPct).toBe(95);
    expect(australia?.productionRules?.multipleGiMaxCount).toBe(3);
  });

  it('reports unresolved grape spellings as research work, not as fabricated aliases', () => {
    const report = validateResearchLibrary();
    expect(Array.isArray(report.unresolvedGrapes)).toBe(true);
    expect(new Set(report.unresolvedGrapes).size).toBe(report.unresolvedGrapes.length);
  });
});
