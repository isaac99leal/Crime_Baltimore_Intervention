import type { AgeingArchetype, BottleAgeResult } from './ageing';
import type { VintageObservation } from './environment';
import type { WinemakingResult } from './winemaking';

export type NoteLayer = {
  layer: 'vintage' | 'winemaking' | 'time';
  derived: true;
  descriptors: string[];
  fading: string[];
  explanation: string;
};

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

export function vintageNoteLayer(vintage?: VintageObservation, archetype?: AgeingArchetype): NoteLayer {
  if (!vintage) {
    return {
      layer: 'vintage',
      derived: true,
      descriptors: [],
      fading: [],
      explanation: 'No year-specific sourced vintage observation is loaded, so the engine does not invent vintage-conditioned aroma descriptors.',
    };
  }

  const m = vintage.matrixModifiers;
  const descriptors: string[] = [];
  const fading: string[] = [];

  if (m.ripeness >= 0.45) descriptors.push('riper fruit spectrum');
  else if (m.ripeness <= -0.35) descriptors.push('less-ripe fruit spectrum');
  if (m.concentration >= 0.45) descriptors.push('concentrated fruit expression');
  else if (m.concentration <= -0.35) descriptors.push('more delicate fruit expression');
  if (m.aromaticFreshness >= 0.35) descriptors.push('heightened aromatic freshness');
  else if (m.aromaticFreshness <= -0.35) fading.push('fresh high-toned aromatic expression');
  if (m.acidity >= 0.35) descriptors.push('brisk acid-driven impression');
  if (m.tanninRipeness >= 0.40) descriptors.push('riper phenolic impression');
  else if (m.tanninRipeness <= -0.35) descriptors.push('firmer greener phenolic impression');
  if (m.botrytisSuitability >= 0.45 && archetype === 'sweet-botrytis') {
    descriptors.push('honeyed botrytis-linked character', 'saffron-like botrytis complexity', 'dried-stone-fruit concentration');
  }
  if (m.diseasePressure >= 0.45) {
    descriptors.push('selection-sensitive vintage character');
  }

  return {
    layer: 'vintage',
    derived: true,
    descriptors: unique(descriptors),
    fading: unique(fading),
    explanation: `Derived from the sourced ${vintage.year} growing-season record for ${vintage.region}; these are simulation descriptors, not quoted tasting notes or an official score.`,
  };
}

const winemakingDescriptorMap: Record<string, Record<string, string[]>> = {
  'carbonic-mode': {
    semi: ['high-toned fermentation fruit', 'confectionary fruit character'],
    full: ['pronounced fermentation fruit', 'confectionary fruit character', 'banana-like ester potential'],
  },
  mlf: {
    complete: ['rounder lactic impression', 'buttery/creamy note potential'],
    partial: ['subtle lactic creaminess'],
  },
  'lees-contact': {
    short: ['subtle lees-derived dough character'],
    extended: ['bread-dough character', 'lees-derived creaminess', 'autolytic complexity'],
  },
  batonnage: {
    occasional: ['lees-derived creaminess'],
    frequent: ['pronounced lees-derived creaminess', 'bread-dough character'],
  },
  'oak-species': {
    european: ['oak spice', 'cedar-like oak character'],
    american: ['vanilla-like oak character', 'coconut-like oak character'],
    mixed: ['mixed oak spice'],
  },
  'oak-toast': {
    light: ['subtle toasted wood'],
    medium: ['toast', 'baking-spice oak character'],
    heavy: ['charred toast', 'smoke-like oak character', 'coffee-like roast character'],
  },
  'oak-new-percentage': {
    medium: ['clear new-oak signature'],
    high: ['pronounced new-oak signature'],
  },
  'flor-ageing': {
    biological: ['almond-like character', 'bread-dough character', 'saline/savory impression'],
    'biological-then-oxidative': ['almond', 'walnut', 'saline/savory impression', 'oxidative nutty complexity'],
  },
  fortification: {
    'during-fermentation': ['fortified ripe-fruit character'],
    'after-fermentation': ['spirit-integrated fortified character'],
  },
  'harvest-raisining': {
    natural: ['dried-fruit concentration', 'raisin/date-like character'],
    controlled: ['dried-fruit concentration'],
  },
  'topping-ullage': {
    'managed-ullage': ['incipient oxidative nuttiness'],
    oxidative: ['walnut-like oxidation', 'dried-fruit oxidation', 'toffee-like oxidative character'],
  },
  'sparkling-lees-age': {
    medium: ['biscuit-like autolysis', 'bread-dough character'],
    long: ['brioche-like autolysis', 'toast', 'biscuit', 'yeast-derived complexity'],
  },
};

export function winemakingNoteLayer(result?: WinemakingResult): NoteLayer {
  if (!result?.selected.length) {
    return {
      layer: 'winemaking',
      derived: true,
      descriptors: [],
      fading: [],
      explanation: 'No legally resolved winemaking selections have been applied, so the engine does not invent secondary winemaking aromas.',
    };
  }

  const descriptors: string[] = [];
  for (const selection of result.selected) {
    descriptors.push(...(winemakingDescriptorMap[selection.decisionId]?.[selection.optionId] ?? []));
  }
  if (result.extraAxes.oxidativeDevelopment >= 0.35) descriptors.push('oxidative nutty development');
  if (result.extraAxes.autolysis >= 0.35) descriptors.push('autolytic bread/biscuit complexity');
  if (result.extraAxes.oakInfluence >= 0.35) descriptors.push('pronounced oak-derived secondary character');

  return {
    layer: 'winemaking',
    derived: true,
    descriptors: unique(descriptors),
    fading: [],
    explanation: 'Derived only from winemaking options that passed the exact designation/product legality gate; descriptors are potential sensory consequences rather than guaranteed analytical outcomes.',
  };
}

export function timeNoteLayer(age: BottleAgeResult): NoteLayer {
  return {
    layer: 'time',
    derived: true,
    descriptors: unique(age.emergingAromas),
    fading: unique(age.fadingAromas),
    explanation: age.explanation,
  };
}

export function composeNoteLayers(
  primary: string[],
  vintage: NoteLayer,
  winemaking: NoteLayer,
  time: NoteLayer,
): { active: string[]; faded: string[] } {
  const faded = unique([...vintage.fading, ...winemaking.fading, ...time.fading]);
  const fadedTokens = faded.map((value) => value.toLowerCase());
  const activePrimary = primary.filter((descriptor) => !fadedTokens.some((token) => token.includes(descriptor.toLowerCase()) || descriptor.toLowerCase().includes(token)));
  return {
    active: unique([...activePrimary, ...vintage.descriptors, ...winemaking.descriptors, ...time.descriptors]),
    faded,
  };
}