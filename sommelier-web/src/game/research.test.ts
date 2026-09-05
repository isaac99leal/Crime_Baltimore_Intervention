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
    expect(researchPassCount).toBe(8);
    expect(researchSourcePassCount).toBe(24);
    expect(researchProfiles.length).toBeGreaterThanOrEqual(79);
    expect(researchSources.length).toBeGreaterThanOrEqual(248);
    expect(researchCountries.length).toBeGreaterThanOrEqual(15);
    expect(report.generationCandidates).toBeGreaterThanOrEqual(32);
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
    const madeira = findResearchProfile('pt-madeira-dop');

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
    expect(madeira?.productionRules?.estufagemMinimumHeatingMonths).toBe(3);
    expect(madeira?.generationStatus).toBe('reference-only');
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

  it('preserves exact Georgian PDO production rules when a full specification is available', () => {
    const magraani = findResearchProfile('ge-kisi-magraani-pdo');
    const khvanchkara = findResearchProfile('ge-khvanchkara-pdo');
    const zegaani = findResearchProfile('ge-zegaani-pdo');

    expect(magraani?.authorizedGrapes).toEqual(['Kisi']);
    expect(magraani?.productionRules?.maxYieldTonnesPerHa).toBe(8);
    expect((magraani?.productionRules?.amber as Record<string, unknown>)?.qvevriRequired).toBe(true);
    expect((magraani?.productionRules?.amber as Record<string, unknown>)?.capMixingTimesPerDay).toEqual([4, 5]);
    expect(khvanchkara?.authorizedGrapes).toEqual(['Aleksandrouli', 'Mujuretuli']);
    expect(khvanchkara?.productionRules?.residualSugarGPerL).toEqual([30, 45]);
    expect(khvanchkara?.productionRules?.maxYieldTonnesPerHa).toBe(7);
    expect(zegaani?.generationStatus).toBe('reference-only');
  });

  it('versions current Chilean origin and label rules instead of flattening the 75% thresholds', () => {
    const current = findResearchProfile('cl-wine-do-framework-2026');
    const secano = findResearchProfile('cl-secano-interior-special-do-2026');
    const multiOrigin = current?.productionRules?.multiOriginSameVariety as Record<string, unknown>;
    const supplementary = current?.productionRules?.supplementaryGeographicTerms as Record<string, unknown>;

    expect(current?.productionRules?.effectiveVersionDate).toBe('2026-07-14');
    expect(current?.productionRules?.minimumGeographicOriginPct).toBe(75);
    expect(current?.productionRules?.singleNamedVarietyMinPct).toBe(75);
    expect(current?.productionRules?.vintageClaimMinPct).toBe(75);
    expect(multiOrigin.maximumNamedRegionsOrSubregions).toBe(3);
    expect(multiOrigin.minorComponentMinPct).toBe(15);
    expect(supplementary.minimumQualifyingVolumePct).toBe(85);
    expect(secano?.authorizedGrapes).toEqual(['País', 'Cinsault']);
    expect(secano?.eligibleNamedAreas).toContain('Coelemu');
    expect(secano?.eligibleAdditionalCommunes).toContain('Tomé');
    expect(secano?.generationStatus).toBe('reference-only');
  });

  it('adds a field-level Jerez product matrix rather than a generic sherry style flag', () => {
    const jerez = findResearchProfile('es-jerez-product-matrix-2024');
    const analytical = jerez?.productionRules?.analytical as Record<string, Record<string, unknown>>;
    const ageing = jerez?.productionRules?.ageingMechanisms as Record<string, string>;
    const qualified = jerez?.productionRules?.qualifiedAgeYears as Record<string, number>;

    expect(analytical.Fino.alcoholPct).toEqual([15, 17]);
    expect(analytical.Fino.sugarGPerLMax).toBe(4);
    expect(analytical['Pedro Ximénez'].sugarGPerLMin).toBe(212);
    expect(ageing.Fino).toContain('biological');
    expect(ageing.Amontillado).toContain('oxidative');
    expect(qualified.VOS).toBe(20);
    expect(qualified.VORS).toBe(30);
    expect(jerez?.geography && (jerez.geography as Record<string, unknown>).municipalities).toHaveLength(10);
  });

  it('versions the 2025 Jerez amendment instead of preserving universal fortification assumptions', () => {
    const current = findResearchProfile('es-jerez-current-amendment-2025');
    const fino = current?.productionRules?.fino as Record<string, unknown>;
    const reserva = current?.productionRules?.reserva as Record<string, unknown>;

    expect(current?.productionRules?.effectiveFrom).toBe('2025-08-24');
    expect(current?.productionRules?.wineCategory1Allowed).toBe(true);
    expect(current?.productionRules?.liqueurWineCategory3Allowed).toBe(true);
    expect(current?.productionRules?.fortificationUniversallyRequired).toBe(false);
    expect(fino.sanlucarDeBarramedaAgeingAllowedCurrent).toBe(false);
    expect(fino.transitionExistingBiologicalAgeingStockThrough).toBe('2030-12-31');
    expect(reserva.normallyRestrictedToCategory3LiqueurWine).toBe(true);
    expect(current?.generationStatus).toBe('reference-only');
  });

  it('keeps Port category ageing and bottle behavior separate by product', () => {
    const port = findResearchProfile('pt-port-product-matrix-2026');
    const rules = port?.productionRules as Record<string, Record<string, unknown>>;
    const service = port?.serviceResearch as Record<string, Record<string, unknown>>;

    expect(rules.LBV.preBottlingAgeYears).toEqual([4, 6]);
    expect(rules.Vintage.bottledYearsAfterHarvest).toEqual([2, 3]);
    expect(rules.Crusted.minimumBottleAgeBeforeSaleYears).toBe(3);
    expect(rules.Colheita.minimumWoodAgeYears).toBe(7);
    expect((rules.AgeIndication.permittedAgeIndicationsYears as number[])).toEqual([10, 20, 30, 40, 50]);
    expect(service.officialAfterOpeningGuidance.VintageDays).toEqual([1, 2]);
    expect(port?.generationStatus).toBe('reference-only');
  });

  it('adds current Port certification and bottling windows without promoting procedural generation', () => {
    const port = findResearchProfile('pt-port-current-category-certification-2026');
    const rules = port?.productionRules as Record<string, Record<string, unknown>>;

    expect(rules.Vintage.bottlingDeadline).toBe('30 July of the third year after harvest');
    expect(rules.LBV.preBottlingAgeYears).toEqual([4, 6]);
    expect(rules.LBV.bottlingDeadline).toBe('31 December of the sixth year after harvest');
    expect(rules.Colheita.minimumWoodAgeYears).toBe(7);
    expect(rules.AgeIndication.permittedAgeIndicationsYears).toEqual([10, 20, 30, 40, 50]);
    expect(rules.AgeIndication.veryVeryOldMinimumAgeYears).toBe(80);
    expect(port?.generationStatus).toBe('reference-only');
  });

  it('expands current Tokaj specialty categories into distinct production rules', () => {
    const tokaj = findResearchProfile('hu-tokaj-product-matrix-2026');
    const rules = tokaj?.productionRules as Record<string, Record<string, unknown> | number | string>;
    const aszu = rules.Aszu as Record<string, unknown>;
    const drySzamorodni = rules.drySzamorodni as Record<string, unknown>;
    const sweetSzamorodni = rules.sweetSzamorodni as Record<string, unknown>;
    const eszencia = rules.Eszencia as Record<string, unknown>;

    expect(aszu.minimumResidualSugarGPerL).toBe(120);
    expect(aszu.sixPuttonyosMinimumResidualSugarGPerL).toBe(150);
    expect(aszu.minimumWoodAgeMonths).toBe(18);
    expect(drySzamorodni.maximumResidualSugarGPerL).toBe(9);
    expect(sweetSzamorodni.minimumResidualSugarGPerL).toBe(45);
    expect(eszencia.maximumLitresPer100KgAszuBerries).toBe(6);
    expect(rules.AszuPlusForditasPlusEszenciaMaximumLitresPer100KgAszuBerries).toBe(220);
  });

  it('keeps South African WO identity, product legality and vine statistics as separate layers', () => {
    const current = findResearchProfile('za-wine-origin-framework-feb2026');
    expect(current?.classificationTerms).toEqual(['geographical unit', 'overarching geographical unit', 'overarching region', 'region', 'subregion', 'district', 'ward']);
    expect(current?.productionRules?.productionAreaSnapshot).toBe('2026-02');
    expect(current?.productionRules?.indexedProductionAreaIdentities).toBe(152);
    expect(current?.productionRules?.certificationScope).toEqual(['origin', 'vintage year', 'variety']);
    expect(current?.productionRules?.identityDoesNotImplyProductRules).toBe(true);
    expect(current?.generationStatus).toBe('framework-only');
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
