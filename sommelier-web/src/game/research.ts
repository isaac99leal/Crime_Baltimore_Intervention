import profileData from '../data/research/appellation_profiles.json';
import sourceData from '../data/research/sources.json';
import { findGrape } from './reference';

export type ResearchGenerationStatus = 'candidate' | 'reference-only' | 'framework-only';

export type ResearchSource = {
  id: string;
  publisher: string;
  title: string;
  url: string;
  jurisdiction: string;
  kind: string;
  accessed: string;
};

export type ResearchProfile = {
  id: string;
  country: string;
  name: string;
  recordType: string;
  legalClass: string;
  hierarchy: string[];
  researchCompleteness: number;
  generationStatus: ResearchGenerationStatus;
  products?: string[];
  authorizedGrapes?: string[];
  principalGrapes?: string[];
  subregions?: string[];
  premierCruClimats?: string[];
  classificationTerms?: string[];
  productionRules?: Record<string, unknown>;
  terroir?: Record<string, unknown>;
  styleNotes?: string[];
  researchNotes?: string[];
  sourceRefs: string[];
  registration?: Record<string, unknown>;
};

type ResearchProfileFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  profiles: ResearchProfile[];
};

type ResearchSourceFile = {
  updatedAt: string;
  policy: string;
  sources: ResearchSource[];
};

const profilesFile = profileData as ResearchProfileFile;
const sourcesFile = sourceData as ResearchSourceFile;

export const researchMethod = profilesFile.method;
export const researchPolicy = sourcesFile.policy;
export const researchSources = sourcesFile.sources;
export const researchProfiles = profilesFile.profiles;
export const researchSourceById = new Map(researchSources.map((source) => [source.id, source]));
export const researchProfileById = new Map(researchProfiles.map((profile) => [profile.id, profile]));
export const researchCountries = [...new Set(researchProfiles.map((profile) => profile.country))].sort();

export function findResearchProfile(id: string): ResearchProfile | undefined {
  return researchProfileById.get(id);
}

export function researchProfilesForCountry(country: string): ResearchProfile[] {
  return researchProfiles.filter((profile) => profile.country === country);
}

export function sourceRecordsForProfile(profile: ResearchProfile): ResearchSource[] {
  return profile.sourceRefs
    .map((sourceId) => researchSourceById.get(sourceId))
    .filter((source): source is ResearchSource => Boolean(source));
}

export function researchGenerationCandidates(): ResearchProfile[] {
  return researchProfiles.filter((profile) => profile.generationStatus === 'candidate');
}

export type ResearchValidationReport = {
  profiles: number;
  sources: number;
  countries: number;
  generationCandidates: number;
  issues: string[];
  unresolvedGrapes: string[];
};

export function validateResearchLibrary(): ResearchValidationReport {
  const issues: string[] = [];
  const unresolvedGrapes = new Set<string>();
  const sourceIds = new Set<string>();
  const profileIds = new Set<string>();

  for (const source of researchSources) {
    if (sourceIds.has(source.id)) issues.push(`Duplicate research source id: ${source.id}`);
    sourceIds.add(source.id);
    if (!source.publisher || !source.title || !source.url) issues.push(`Incomplete research source: ${source.id}`);
  }

  for (const profile of researchProfiles) {
    if (profileIds.has(profile.id)) issues.push(`Duplicate research profile id: ${profile.id}`);
    profileIds.add(profile.id);

    if (!profile.name || !profile.country || !profile.legalClass) issues.push(`Incomplete research profile identity: ${profile.id}`);
    if (!Array.isArray(profile.hierarchy) || !profile.hierarchy.length) issues.push(`Missing hierarchy: ${profile.id}`);
    if (!Number.isInteger(profile.researchCompleteness) || profile.researchCompleteness < 1 || profile.researchCompleteness > 5) {
      issues.push(`Invalid research completeness: ${profile.id}`);
    }
    if (!['candidate', 'reference-only', 'framework-only'].includes(profile.generationStatus)) {
      issues.push(`Invalid generation status: ${profile.id}`);
    }
    if (!Array.isArray(profile.sourceRefs) || !profile.sourceRefs.length) issues.push(`Profile has no sources: ${profile.id}`);
    for (const sourceId of profile.sourceRefs ?? []) {
      if (!researchSourceById.has(sourceId)) issues.push(`Unknown source ${sourceId} in profile ${profile.id}`);
    }

    if (profile.generationStatus === 'candidate' && !(profile.products?.length)) {
      issues.push(`Generation candidate has no product definition: ${profile.id}`);
    }

    for (const grape of [...(profile.principalGrapes ?? []), ...(profile.authorizedGrapes ?? [])]) {
      if (!findGrape(grape)) unresolvedGrapes.add(grape);
    }
  }

  return {
    profiles: researchProfiles.length,
    sources: researchSources.length,
    countries: researchCountries.length,
    generationCandidates: researchGenerationCandidates().length,
    issues,
    unresolvedGrapes: [...unresolvedGrapes].sort(),
  };
}
