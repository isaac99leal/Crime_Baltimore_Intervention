import ageingData from '../data/research/ageing_old_vine_rules.json';
import { researchSourceById } from './research';
import type { WineProfile } from './types';

export type AgeingRule = {
  id: string;
  country: string;
  designation: string;
  productLevel: string;
  ruleType: string;
  legal: boolean;
  effective: string;
  requirements: Record<string, unknown>;
  mechanisms?: string[];
  sourceRefs: string[];
};

export type OldVineDefinition = {
  id: string;
  scope: string;
  term: string;
  effectiveFrom?: string;
  legalOrCertification: string;
  requirements: Record<string, unknown>;
  sourceRefs: string[];
};

type AgeingFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  ageingRules: AgeingRule[];
  oldVineDefinitions: OldVineDefinition[];
};

const file = ageingData as unknown as AgeingFile;
export const ageingResearchMethod = file.method;
export const legalAgeingRules = file.ageingRules;
export const oldVineDefinitions = file.oldVineDefinitions;

export type AgeingArchetype =
  | 'fresh-aromatic-white'
  | 'structured-white'
  | 'structured-red'
  | 'light-red'
  | 'traditional-sparkling'
  | 'sweet-botrytis'
  | 'oxidative-fortified'
  | 'bottle-aged-fortified'
  | 'biological-flor'
  | 'oxidative-flor-derived'
  | 'amber-skin-contact'
  | 'neutral';

export type BottleAgePhase = 'youth' | 'development' | 'mature' | 'late-mature' | 'fragile';

export type BottleAgeResult = {
  yearsSinceVintage: number;
  phase: BottleAgePhase;
  derived: true;
  confidence: number;
  profile: WineProfile;
  emergingAromas: string[];
  fadingAromas: string[];
  serviceFlags: string[];
  explanation: string;
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const norm = (value: string) => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

export function ageingRulesForDesignation(designation: string): AgeingRule[] {
  const target = norm(designation);
  return legalAgeingRules.filter((rule) => target.includes(norm(rule.designation)) || norm(rule.designation).includes(target));
}

export function oldVineRulesForScope(scope: string): OldVineDefinition[] {
  const target = norm(scope);
  return oldVineDefinitions.filter((rule) => norm(rule.scope) === 'international-reference' || target.includes(norm(rule.scope)) || norm(rule.scope).includes(target));
}

export function qualifiesForOldVineRule(rule: OldVineDefinition, vineAgeYears: number, oldVineSharePct = 100): boolean {
  const minimumAge = typeof rule.requirements.minimumPlantAgeYears === 'number' ? rule.requirements.minimumPlantAgeYears : 0;
  const minimumShare = typeof rule.requirements.minimumShareOldVinesPct === 'number' ? rule.requirements.minimumShareOldVinesPct : 0;
  return vineAgeYears >= minimumAge && oldVineSharePct >= minimumShare;
}

export function ageingArchetype(country: string, placeText: string, color?: string): AgeingArchetype {
  const place = norm(`${country} ${placeText}`);
  if (place.includes('madeira')) return 'oxidative-fortified';
  if (place.includes('port') || place.includes('porto')) return 'bottle-aged-fortified';
  if (place.includes('sauternes') || place.includes('barsac') || place.includes('tokaj')) return 'sweet-botrytis';
  if (place.includes('champagne')) return 'traditional-sparkling';
  if (place.includes('jerez') || place.includes('sherry')) return 'oxidative-flor-derived';
  if (color?.toLowerCase() === 'red') return 'structured-red';
  if (color?.toLowerCase() === 'white') return 'structured-white';
  return 'neutral';
}

function maturitySpeed(archetype: AgeingArchetype): number {
  switch (archetype) {
    case 'fresh-aromatic-white': return 1.6;
    case 'light-red': return 1.35;
    case 'structured-white': return 0.9;
    case 'structured-red': return 0.75;
    case 'traditional-sparkling': return 0.7;
    case 'sweet-botrytis': return 0.42;
    case 'oxidative-fortified': return 0.20;
    case 'bottle-aged-fortified': return 0.35;
    case 'biological-flor': return 0.75;
    case 'oxidative-flor-derived': return 0.30;
    case 'amber-skin-contact': return 0.65;
    default: return 1;
  }
}

function phaseFor(effectiveAge: number): BottleAgePhase {
  if (effectiveAge < 4) return 'youth';
  if (effectiveAge < 10) return 'development';
  if (effectiveAge < 24) return 'mature';
  if (effectiveAge < 45) return 'late-mature';
  return 'fragile';
}

const aromaSets: Record<AgeingArchetype, { emerging: string[]; fading: string[] }> = {
  'fresh-aromatic-white': { emerging: ['dried citrus', 'hay', 'wax', 'nutty tones'], fading: ['fresh flowers', 'fresh tropical fruit', 'green herbs'] },
  'structured-white': { emerging: ['wax', 'toast', 'hazelnut', 'dried citrus', 'honey', 'mushroom'], fading: ['fresh orchard fruit', 'fresh flowers'] },
  'structured-red': { emerging: ['dried cherry', 'dried plum', 'tobacco', 'leather', 'forest floor', 'mushroom', 'cedar'], fading: ['fresh berry fruit', 'violet', 'primary fermentation fruit'] },
  'light-red': { emerging: ['dried red fruit', 'tea', 'forest floor', 'mushroom'], fading: ['fresh strawberry', 'fresh cherry', 'violet'] },
  'traditional-sparkling': { emerging: ['brioche', 'toast', 'biscuit', 'dried fruit', 'coffee', 'cocoa', 'mushroom'], fading: ['fresh citrus', 'fresh apple', 'white flowers'] },
  'sweet-botrytis': { emerging: ['honey', 'saffron', 'dried apricot', 'orange marmalade', 'beeswax', 'caramelized citrus'], fading: ['fresh stone fruit', 'fresh floral notes'] },
  'oxidative-fortified': { emerging: ['walnut', 'toffee', 'caramel', 'coffee', 'dried citrus peel', 'spice', 'iodine'], fading: ['fresh fruit'] },
  'bottle-aged-fortified': { emerging: ['fig', 'date', 'cocoa', 'walnut', 'spice', 'tobacco'], fading: ['fresh black fruit', 'fresh red fruit'] },
  'biological-flor': { emerging: ['almond', 'bread dough', 'saline notes'], fading: ['primary fruit'] },
  'oxidative-flor-derived': { emerging: ['walnut', 'hazelnut', 'dried orange peel', 'spice', 'toffee'], fading: ['primary fruit'] },
  'amber-skin-contact': { emerging: ['dried apricot', 'tea', 'nut skin', 'dried herbs', 'resin'], fading: ['fresh floral notes'] },
  neutral: { emerging: ['dried fruit', 'savory notes'], fading: ['fresh fruit'] },
};

/**
 * Derived bottle-age model. This is intentionally not a factual vintage score.
 * Storage quality is 0..1 and represents a game abstraction of temperature stability,
 * light exposure, closure condition and handling history.
 */
export function modelBottleAge(
  base: WineProfile,
  vintage: number,
  currentYear: number,
  archetype: AgeingArchetype,
  storageQuality = 0.92,
): BottleAgeResult {
  const yearsSinceVintage = Math.max(0, currentYear - vintage);
  const storagePenalty = 1 + (1 - clamp(storageQuality, 0, 1)) * 1.8;
  const effectiveAge = yearsSinceVintage * maturitySpeed(archetype) * storagePenalty;
  const phase = phaseFor(effectiveAge);
  const progress = clamp(effectiveAge / 28, 0, 1.6);
  const fragile = phase === 'fragile' ? clamp((effectiveAge - 45) / 35, 0, 1) : 0;

  const profile: WineProfile = {
    ...base,
    acidity: clamp(base.acidity - progress * 0.18 - fragile * 0.20, 1, 5),
    tannin: clamp(base.tannin - progress * 0.55 - fragile * 0.25, 0.5, 5),
    body: clamp(base.body - fragile * 0.35, 1, 5),
    sweetness: base.sweetness,
    fruitIntensity: clamp(base.fruitIntensity - progress * 0.65 - fragile * 0.45, 0.5, 5),
    earthIntensity: clamp(base.earthIntensity + progress * 0.45 - fragile * 0.15, 0.5, 5),
    alcohol: base.alcohol,
  };

  if (archetype === 'oxidative-fortified') {
    profile.fruitIntensity = clamp(base.fruitIntensity - progress * 0.25, 0.5, 5);
    profile.earthIntensity = clamp(base.earthIntensity + progress * 0.30, 0.5, 5);
  }
  if (archetype === 'sweet-botrytis') {
    profile.acidity = clamp(base.acidity - progress * 0.08, 1, 5);
    profile.fruitIntensity = clamp(base.fruitIntensity - progress * 0.30, 0.5, 5);
  }

  const aromas = aromaSets[archetype];
  const emergingCount = phase === 'youth' ? 1 : phase === 'development' ? 3 : phase === 'mature' ? 5 : aromas.emerging.length;
  const serviceFlags: string[] = [];
  if (yearsSinceVintage >= 12 && ['structured-red', 'bottle-aged-fortified'].includes(archetype)) serviceFlags.push('sediment risk');
  if (phase === 'late-mature' || phase === 'fragile') serviceFlags.push('gentle handling');
  if (phase === 'fragile') serviceFlags.push('decant only for sediment and minimize air exposure');
  if (storageQuality < 0.65) serviceFlags.push('accelerated ageing from compromised storage');

  return {
    yearsSinceVintage,
    phase,
    derived: true,
    confidence: archetype === 'neutral' ? 1 : 3,
    profile,
    emergingAromas: aromas.emerging.slice(0, emergingCount),
    fadingAromas: phase === 'youth' ? [] : aromas.fading,
    serviceFlags,
    explanation: `Derived bottle-age model: ${yearsSinceVintage} years from vintage, ${archetype}, storage quality ${clamp(storageQuality, 0, 1).toFixed(2)}. Legal ageing requirements and vintage weather are separate inputs.`,
  };
}

export function validateAgeingResearch() {
  const issues: string[] = [];
  const ids = new Set<string>();
  for (const rule of legalAgeingRules) {
    if (ids.has(rule.id)) issues.push(`Duplicate ageing rule: ${rule.id}`);
    ids.add(rule.id);
    if (!rule.legal || !rule.country || !rule.designation || !rule.productLevel) issues.push(`Incomplete legal ageing rule: ${rule.id}`);
    if (!rule.sourceRefs.length) issues.push(`Ageing rule has no source: ${rule.id}`);
    for (const source of rule.sourceRefs) if (!researchSourceById.has(source)) issues.push(`Unknown source ${source} in ${rule.id}`);
  }
  for (const rule of oldVineDefinitions) {
    if (ids.has(rule.id)) issues.push(`Duplicate old-vine rule: ${rule.id}`);
    ids.add(rule.id);
    if (!rule.term || !rule.scope) issues.push(`Incomplete old-vine rule: ${rule.id}`);
    for (const source of rule.sourceRefs) if (!researchSourceById.has(source)) issues.push(`Unknown source ${source} in ${rule.id}`);
  }
  return { ageingRules: legalAgeingRules.length, oldVineDefinitions: oldVineDefinitions.length, issues };
}
