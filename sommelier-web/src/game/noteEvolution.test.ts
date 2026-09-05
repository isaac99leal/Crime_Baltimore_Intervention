import { describe, expect, it } from 'vitest';
import { modelBottleAge } from './ageing';
import { composeNoteLayers, timeNoteLayer, vintageNoteLayer, winemakingNoteLayer } from './noteEvolution';
import type { VintageObservation } from './environment';
import type { WinemakingResult } from './winemaking';
import type { WineProfile } from './types';

const base: WineProfile = {
  acidity: 3.5,
  tannin: 3.8,
  body: 3.5,
  sweetness: 1,
  fruitIntensity: 4,
  earthIntensity: 2,
  alcohol: 13.5,
};

function vintage(overrides: Partial<VintageObservation['matrixModifiers']>): VintageObservation {
  return {
    id: 'test-vintage',
    country: 'Test',
    region: 'Test Region',
    year: 1990,
    growingSeason: {},
    matrixModifiers: {
      derived: true,
      confidence: 4,
      acidity: 0,
      ripeness: 0,
      concentration: 0,
      tanninRipeness: 0,
      aromaticFreshness: 0,
      diseasePressure: 0,
      yield: 0,
      ageability: 0,
      botrytisSuitability: 0,
      ...overrides,
    },
    sourceRefs: ['test'],
  };
}

describe('layered tasting-note evolution', () => {
  it('lets vintage alter expression without pretending to quote a tasting note', () => {
    const layer = vintageNoteLayer(vintage({ ripeness: 0.6, concentration: 0.5, aromaticFreshness: -0.4 }), 'structured-red');
    expect(layer.descriptors).toContain('riper fruit spectrum');
    expect(layer.descriptors).toContain('concentrated fruit expression');
    expect(layer.fading).toContain('fresh high-toned aromatic expression');
    expect(layer.explanation).toContain('simulation descriptors');
  });

  it('only adds botrytis-linked descriptors for a compatible sweet-botrytis archetype', () => {
    const observation = vintage({ botrytisSuitability: 0.8 });
    expect(vintageNoteLayer(observation, 'sweet-botrytis').descriptors).toContain('saffron-like botrytis complexity');
    expect(vintageNoteLayer(observation, 'structured-red').descriptors).not.toContain('saffron-like botrytis complexity');
  });

  it('derives secondary notes only from winemaking selections that already passed legality', () => {
    const result: WinemakingResult = {
      profile: base,
      derived: true,
      selected: [
        { decisionId: 'oak-toast', optionId: 'heavy', label: 'heavy toast' },
        { decisionId: 'lees-contact', optionId: 'extended', label: 'extended lees contact' },
      ],
      blocked: [{ decisionId: 'fortification', optionId: 'during-fermentation', reason: 'not permitted' }],
      extraAxes: {
        aromaticFreshness: 0,
        oakInfluence: 0.5,
        oxidativeDevelopment: 0,
        reductiveRisk: 0,
        autolysis: 0.4,
        colorExtraction: 0,
        phenolicExtraction: 0,
        volatileAcidityRisk: 0,
        microbialRisk: 0,
        ageability: 0,
      },
    };
    const layer = winemakingNoteLayer(result);
    expect(layer.descriptors).toContain('charred toast');
    expect(layer.descriptors).toContain('bread-dough character');
    expect(layer.descriptors.join(' ')).not.toContain('fortified ripe-fruit');
  });

  it('keeps time-derived tertiary notes distinct from vintage and winemaking layers', () => {
    const age = modelBottleAge(base, 1990, 2026, 'structured-red', 0.95);
    const time = timeNoteLayer(age);
    expect(time.layer).toBe('time');
    expect(time.descriptors).toContain('tobacco');
    expect(time.fading).toContain('fresh berry fruit');
  });

  it('composes primary, vintage, winemaking and tertiary descriptors without duplicates', () => {
    const age = modelBottleAge(base, 1990, 2026, 'structured-red', 0.95);
    const notes = composeNoteLayers(
      ['black cherry', 'violet'],
      vintageNoteLayer(vintage({ ripeness: 0.6 }), 'structured-red'),
      winemakingNoteLayer(),
      timeNoteLayer(age),
    );
    expect(notes.active).toContain('black cherry');
    expect(notes.active).toContain('riper fruit spectrum');
    expect(notes.active).toContain('tobacco');
    expect(new Set(notes.active).size).toBe(notes.active.length);
  });
});
