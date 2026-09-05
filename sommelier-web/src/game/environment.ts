import environmentalData from '../data/research/environmental_profiles.json';
import vintageData from '../data/research/vintage_observations.json';
import { researchProfileById, researchSourceById } from './research';

export type PlaceMatrixModifiers = {
  scale: string;
  derived: boolean;
  confidence: number;
  acidity: number;
  tannin: number;
  body: number;
  alcohol: number;
  fruitIntensity: number;
  earthIntensity: number;
  aromaticFreshness: number;
  droughtStress: number;
  diseasePressure: number;
  frostRisk: number;
  botrytisSuitability: number;
};

export type VintageMatrixModifiers = {
  derived: boolean;
  confidence: number;
  acidity: number;
  ripeness: number;
  concentration: number;
  tanninRipeness: number;
  aromaticFreshness: number;
  diseasePressure: number;
  yield: number;
  ageability: number;
  botrytisSuitability: number;
};

export type EnvironmentalProfile = {
  id: string;
  researchProfileId?: string;
  country: string;
  name: string;
  scope: string;
  climate: Record<string, unknown>;
  soils: Array<Record<string, unknown>>;
  topography?: Record<string, unknown>;
  matrixModifiers: PlaceMatrixModifiers;
  sourceRefs: string[];
};

export type VintageObservation = {
  id: string;
  environmentProfileId?: string;
  country: string;
  region: string;
  year: number;
  growingSeason: Record<string, unknown>;
  styleEffects?: string[];
  publishedDrinkWindowYears?: number[];
  matrixModifiers: VintageMatrixModifiers;
  sourceRefs: string[];
};

export type AuthorityVintageRating = {
  region: string;
  year: number;
  rating: string;
  sourceRefs: string[];
};

type EnvironmentalFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  profiles: EnvironmentalProfile[];
};

type VintageFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  observations: VintageObservation[];
  authorityRatings: AuthorityVintageRating[];
};

const environmentalFile = environmentalData as unknown as EnvironmentalFile;
const vintageFile = vintageData as unknown as VintageFile;

export const environmentalResearchMethod = environmentalFile.method;
export const vintageResearchMethod = vintageFile.method;
export const environmentalProfiles = environmentalFile.profiles;
export const vintageObservations = vintageFile.observations;
export const authorityVintageRatings = vintageFile.authorityRatings;
export const environmentalProfileById = new Map(environmentalProfiles.map((profile) => [profile.id, profile]));
export const vintageObservationById = new Map(vintageObservations.map((vintage) => [vintage.id, vintage]));

export function findEnvironmentalProfile(id: string): EnvironmentalProfile | undefined {
  return environmentalProfileById.get(id);
}

export function findVintageObservation(id: string): VintageObservation | undefined {
  return vintageObservationById.get(id);
}

export function vintageObservationsForRegion(region: string): VintageObservation[] {
  return vintageObservations.filter((vintage) => vintage.region === region).sort((a, b) => b.year - a.year);
}

const placeMatrixNumericKeys: Array<keyof Omit<PlaceMatrixModifiers, 'scale' | 'derived' | 'confidence'>> = [
  'acidity', 'tannin', 'body', 'alcohol', 'fruitIntensity', 'earthIntensity', 'aromaticFreshness',
  'droughtStress', 'diseasePressure', 'frostRisk', 'botrytisSuitability',
];

const vintageMatrixNumericKeys: Array<keyof Omit<VintageMatrixModifiers, 'derived' | 'confidence'>> = [
  'acidity', 'ripeness', 'concentration', 'tanninRipeness', 'aromaticFreshness', 'diseasePressure',
  'yield', 'ageability', 'botrytisSuitability',
];

function validateSourceRefs(owner: string, refs: string[], issues: string[]) {
  if (!Array.isArray(refs) || refs.length === 0) issues.push(`${owner} has no source references`);
  for (const sourceId of refs ?? []) {
    if (!researchSourceById.has(sourceId)) issues.push(`${owner} references unknown source: ${sourceId}`);
  }
}

function validateBoundedMatrix(owner: string, values: Record<string, unknown>, keys: string[], issues: string[]) {
  for (const key of keys) {
    const value = values[key];
    if (typeof value !== 'number' || !Number.isFinite(value) || value < -1 || value > 1) {
      issues.push(`${owner} has invalid matrix value ${key}: ${String(value)}`);
    }
  }
}

export function validateEnvironmentalResearch() {
  const issues: string[] = [];
  const environmentIds = new Set<string>();
  const vintageIds = new Set<string>();
  const ratingKeys = new Set<string>();

  for (const profile of environmentalProfiles) {
    if (environmentIds.has(profile.id)) issues.push(`Duplicate environmental profile id: ${profile.id}`);
    environmentIds.add(profile.id);
    if (!profile.country || !profile.name || !profile.scope) issues.push(`Incomplete environmental profile: ${profile.id}`);
    if (!profile.soils?.length) issues.push(`Environmental profile has no soil records: ${profile.id}`);
    if (!profile.climate || Object.keys(profile.climate).length === 0) issues.push(`Environmental profile has no climate record: ${profile.id}`);
    if (profile.researchProfileId && !researchProfileById.has(profile.researchProfileId)) {
      issues.push(`Environmental profile ${profile.id} references unknown research profile ${profile.researchProfileId}`);
    }
    validateSourceRefs(`Environmental profile ${profile.id}`, profile.sourceRefs, issues);
    if (profile.matrixModifiers.derived !== true) issues.push(`Environmental matrix must be marked derived: ${profile.id}`);
    if (profile.matrixModifiers.confidence < 1 || profile.matrixModifiers.confidence > 5) issues.push(`Invalid environmental confidence: ${profile.id}`);
    validateBoundedMatrix(profile.id, profile.matrixModifiers as unknown as Record<string, unknown>, placeMatrixNumericKeys as string[], issues);
  }

  for (const vintage of vintageObservations) {
    if (vintageIds.has(vintage.id)) issues.push(`Duplicate vintage observation id: ${vintage.id}`);
    vintageIds.add(vintage.id);
    if (!Number.isInteger(vintage.year) || vintage.year < 1900 || vintage.year > 2100) issues.push(`Invalid vintage year: ${vintage.id}`);
    if (vintage.environmentProfileId && !environmentalProfileById.has(vintage.environmentProfileId)) {
      issues.push(`Vintage ${vintage.id} references unknown environment profile ${vintage.environmentProfileId}`);
    }
    validateSourceRefs(`Vintage ${vintage.id}`, vintage.sourceRefs, issues);
    if (vintage.matrixModifiers.derived !== true) issues.push(`Vintage matrix must be marked derived: ${vintage.id}`);
    if (vintage.matrixModifiers.confidence < 1 || vintage.matrixModifiers.confidence > 5) issues.push(`Invalid vintage confidence: ${vintage.id}`);
    validateBoundedMatrix(vintage.id, vintage.matrixModifiers as unknown as Record<string, unknown>, vintageMatrixNumericKeys as string[], issues);
    const unsafe = vintage as unknown as Record<string, unknown>;
    if ('qualityScore' in unsafe || 'legacyQualityScore' in unsafe) issues.push(`Legacy unsourced vintage score leaked into sourced layer: ${vintage.id}`);
  }

  const allowedRatings = new Set(['Excellent', 'Very good', 'Good', 'Normal', 'Medium']);
  for (const rating of authorityVintageRatings) {
    const key = `${rating.region}:${rating.year}`;
    if (ratingKeys.has(key)) issues.push(`Duplicate authority vintage rating: ${key}`);
    ratingKeys.add(key);
    if (!allowedRatings.has(rating.rating)) issues.push(`Unknown authority vintage rating ${rating.rating}: ${key}`);
    validateSourceRefs(`Authority vintage rating ${key}`, rating.sourceRefs, issues);
  }

  return {
    environmentalProfiles: environmentalProfiles.length,
    vintageObservations: vintageObservations.length,
    authorityVintageRatings: authorityVintageRatings.length,
    countries: new Set(environmentalProfiles.map((profile) => profile.country)).size,
    issues,
  };
}
