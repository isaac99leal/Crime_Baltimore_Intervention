import { describe, expect, it } from 'vitest';
import {
  ageingArchetype,
  ageingRulesForDesignation,
  legalAgeingRules,
  modelBottleAge,
  oldVineDefinitions,
  oldVineRulesForScope,
  qualifiesForOldVineRule,
  validateAgeingResearch,
} from './ageing';
import type { WineProfile } from './types';

const base: WineProfile = {
  acidity: 3.5,
  tannin: 4.2,
  body: 4,
  sweetness: 1,
  fruitIntensity: 4.4,
  earthIntensity: 1.8,
  alcohol: 13.5,
};

describe('legal ageing, old-vine terminology and bottle evolution', () => {
  it('keeps legal rules source-backed and separate from sensory ageing', () => {
    const report = validateAgeingResearch();
    expect(legalAgeingRules.length).toBeGreaterThanOrEqual(13);
    expect(oldVineDefinitions.length).toBeGreaterThanOrEqual(7);
    expect(report.issues).toEqual([]);
  });

  it('preserves major designation ageing requirements without flattening levels', () => {
    const champagne = ageingRulesForDesignation('Champagne');
    const rioja = ageingRulesForDesignation('Rioja DOCa');
    const brunello = ageingRulesForDesignation('Brunello di Montalcino DOCG');
    const port = ageingRulesForDesignation('Porto / Port');
    const madeira = ageingRulesForDesignation('Madeira DOP');

    expect(champagne.find((rule) => rule.productLevel === 'Vintage Champagne')?.requirements.minimumTotalMonths).toBe(36);
    expect(rioja.find((rule) => rule.productLevel === 'Gran Reserva red')?.requirements.minimumTotalMonths).toBe(60);
    expect(rioja.find((rule) => rule.productLevel === 'Reserva red')?.requirements.minimumBottleMonths).toBe(6);
    expect(brunello.find((rule) => rule.productLevel === 'Riserva')?.requirements.minimumBottleMonths).toBe(6);
    expect(port.find((rule) => rule.productLevel === 'Colheita')?.requirements.minimumCaskYears).toBe(7);
    expect(madeira.find((rule) => rule.productLevel === 'Canteiro')?.requirements.minimumCaskYears).toBe(2);
  });

  it('treats old-vine labels as jurisdictional definitions rather than a generic marketing toggle', () => {
    const global = oldVineRulesForScope('France').find((rule) => rule.id === 'oldvine-oiv-global-2024');
    const barossa = oldVineRulesForScope('Barossa');
    const ancestor = barossa.find((rule) => rule.id === 'oldvine-au-barossa-ancestor');
    const southAfrica = oldVineRulesForScope('South Africa').find((rule) => rule.id === 'oldvine-za-certified-heritage');

    expect(global && qualifiesForOldVineRule(global, 35)).toBe(true);
    expect(global && qualifiesForOldVineRule(global, 34)).toBe(false);
    expect(ancestor && qualifiesForOldVineRule(ancestor, 125)).toBe(true);
    expect(ancestor && qualifiesForOldVineRule(ancestor, 124)).toBe(false);
    expect(southAfrica?.requirements.plantingDateShownOnSeal).toBe(true);
  });

  it('changes notes and structure as bottle age advances', () => {
    const young = modelBottleAge(base, 2022, 2026, 'structured-red', 0.95);
    const mature = modelBottleAge(base, 1996, 2026, 'structured-red', 0.95);

    expect(young.phase).toBe('youth');
    expect(mature.phase === 'mature' || mature.phase === 'late-mature').toBe(true);
    expect(mature.profile.tannin).toBeLessThan(young.profile.tannin);
    expect(mature.profile.fruitIntensity).toBeLessThan(young.profile.fruitIntensity);
    expect(mature.profile.earthIntensity).toBeGreaterThan(young.profile.earthIntensity);
    expect(mature.emergingAromas).toContain('tobacco');
    expect(mature.serviceFlags).toContain('sediment risk');
  });

  it('uses slower evolution for oxidative fortified and sweet botrytized archetypes', () => {
    const madeira = modelBottleAge(base, 1900, 2026, 'oxidative-fortified', 0.95);
    const red = modelBottleAge(base, 1900, 2026, 'structured-red', 0.95);
    const sauternes = modelBottleAge({ ...base, tannin: 0.7, sweetness: 5 }, 1976, 2026, 'sweet-botrytis', 0.95);

    expect(madeira.phase).not.toBe('fragile');
    expect(red.phase).toBe('fragile');
    expect(madeira.emergingAromas).toContain('walnut');
    expect(sauternes.emergingAromas).toContain('honey');
  });

  it('selects broad ageing archetypes only when geography makes the style sufficiently clear', () => {
    expect(ageingArchetype('Portugal', 'Madeira DOP', 'white')).toBe('oxidative-fortified');
    expect(ageingArchetype('France', 'Sauternes', 'white')).toBe('sweet-botrytis');
    expect(ageingArchetype('France', 'Champagne', 'white')).toBe('traditional-sparkling');
    expect(ageingArchetype('Italy', 'Barolo', 'red')).toBe('structured-red');
  });
});
