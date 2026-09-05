import { describe, expect, it } from 'vitest';
import { applyWinemakingDecisions, decisionOption, validateWinemakingResearch, winemakingDecisions } from './winemaking';
import type { WineProfile } from './types';

const base: WineProfile = {
  acidity: 3,
  tannin: 3,
  body: 3,
  sweetness: 1,
  fruitIntensity: 3,
  earthIntensity: 2,
  alcohol: 13,
};

describe('deep winemaking decision matrix', () => {
  it('contains broad cellar-process coverage with bounded matrices', () => {
    const report = validateWinemakingResearch();
    expect(report.decisions).toBeGreaterThanOrEqual(35);
    expect(report.stages).toBeGreaterThanOrEqual(8);
    expect(report.options).toBeGreaterThanOrEqual(90);
    expect(report.issues).toEqual([]);
  });

  it('requires designation/product legality before applying regulated choices', () => {
    const blocked = applyWinemakingDecisions(base, [
      { decisionId: 'fortification', optionId: 'during-fermentation' },
      { decisionId: 'maturation-vessel', optionId: 'small-oak' },
    ]);
    expect(blocked.selected).toHaveLength(0);
    expect(blocked.blocked).toHaveLength(2);

    const allowed = applyWinemakingDecisions(
      base,
      [{ decisionId: 'fortification', optionId: 'during-fermentation' }],
      () => true,
    );
    expect(allowed.selected).toHaveLength(1);
    expect(allowed.profile.sweetness).toBeGreaterThan(base.sweetness);
    expect(allowed.profile.body).toBeGreaterThan(base.body);
  });

  it('applies non-regulated process choices without bypassing the legal gate for regulated ones', () => {
    const result = applyWinemakingDecisions(base, [
      { decisionId: 'harvest-sorting', optionId: 'strict' },
      { decisionId: 'fermentation-temperature', optionId: 'cool' },
      { decisionId: 'oak-toast', optionId: 'heavy' },
    ]);
    expect(result.selected.map((entry) => entry.decisionId)).toEqual(['harvest-sorting', 'fermentation-temperature', 'oak-toast']);
    expect(result.extraAxes.microbialRisk).toBeLessThan(0);
    expect(result.extraAxes.oakInfluence).toBeGreaterThan(0);
    expect(result.profile.fruitIntensity).toBeGreaterThan(base.fruitIntensity - 0.01);
  });

  it('keeps extraction, MLF, oxygen, lees, oak and bottling as separate decisions', () => {
    const required = [
      'maceration-duration', 'mlf', 'oxygen-fermentation', 'lees-contact', 'batonnage',
      'oak-species', 'oak-new-percentage', 'oak-toast', 'micro-oxygenation',
      'sulfur-management', 'bottling-oxygen', 'closure', 'bottle-format',
    ];
    for (const id of required) expect(winemakingDecisions.some((decision) => decision.id === id)).toBe(true);
  });

  it('models carbonic maceration as a specific technique rather than a generic light-red switch', () => {
    const carbonic = decisionOption('carbonic-mode', 'full');
    expect(carbonic?.matrix.tannin).toBeLessThan(0);
    expect(carbonic?.matrix.fruitIntensity).toBeGreaterThan(0);
    expect(carbonic?.matrix.aromaticFreshness).toBeGreaterThan(0);
  });
});
