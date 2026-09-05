import { describe, expect, it } from 'vitest';
import {
  applyWinemakingDecisions,
  decisionOption,
  validateWinemakingResearch,
  winemakingDecisions,
  winemakingResearchPassCount,
} from './winemaking';
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
  it('contains broad multi-pass cellar-process coverage with bounded matrices', () => {
    const report = validateWinemakingResearch();
    expect(winemakingResearchPassCount).toBe(2);
    expect(report.decisions).toBeGreaterThanOrEqual(43);
    expect(report.stages).toBeGreaterThanOrEqual(8);
    expect(report.options).toBeGreaterThanOrEqual(120);
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

  it('adds special-wine process primitives instead of hiding them in tasting notes', () => {
    const required = [
      'tokaj-special-extraction', 'jerez-cabeceo-sweetening', 'white-juice-turbidity',
      'fermentation-nutrient-timing', 'fermentation-temperature-trajectory',
      'post-fermentation-so2-timing', 'smoke-impact-remediation', 'molecular-so2-target',
    ];
    for (const id of required) expect(winemakingDecisions.some((decision) => decision.id === id)).toBe(true);
    expect(decisionOption('tokaj-special-extraction', 'eszencia-free-run')?.matrix.sweetness).toBeGreaterThan(0.7);
    expect(decisionOption('post-fermentation-so2-timing', 'extended-unsulfured')?.matrix.microbialRisk).toBeGreaterThan(0.2);
    expect(decisionOption('smoke-impact-remediation', 'activated-carbon')?.matrix.fruitIntensity).toBeLessThan(0);
  });

  it('models white-juice turbidity and nutrient timing as tradeoffs, not generic quality bonuses', () => {
    const moderate = decisionOption('white-juice-turbidity', 'moderate-around-100ntu');
    const high = decisionOption('white-juice-turbidity', 'high-solids');
    const early = decisionOption('fermentation-nutrient-timing', 'dap-early');
    const late = decisionOption('fermentation-nutrient-timing', 'dap-late');
    expect(moderate?.matrix.fruitIntensity).toBeGreaterThan(0);
    expect(high?.matrix.reductiveRisk).toBeGreaterThan(0);
    expect(early?.matrix.reductiveRisk).toBeLessThan(0);
    expect(late?.matrix.microbialRisk).toBeGreaterThan(0);
  });

  it('models carbonic maceration as a specific technique rather than a generic light-red switch', () => {
    const carbonic = decisionOption('carbonic-mode', 'full');
    expect(carbonic?.matrix.tannin).toBeLessThan(0);
    expect(carbonic?.matrix.fruitIntensity).toBeGreaterThan(0);
    expect(carbonic?.matrix.aromaticFreshness).toBeGreaterThan(0);
  });
});
