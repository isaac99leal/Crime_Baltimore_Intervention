import profileData from '../data/research/appellation_profiles.json';
import profileDataPass2 from '../data/research/appellation_profiles_pass2.json';
import profileDataPass3 from '../data/research/appellation_profiles_pass3.json';
import profileDataPass4 from '../data/research/appellation_profiles_pass4.json';
import profileDataPass5 from '../data/research/appellation_profiles_pass5.json';
import profileDataPass6 from '../data/research/appellation_profiles_pass6.json';
import profileDataPass7 from '../data/research/appellation_profiles_pass7.json';
import sourceData from '../data/research/sources.json';
import sourceDataPass2 from '../data/research/sources_pass2.json';
import sourceDataPass3 from '../data/research/sources_pass3.json';
import sourceDataPass4 from '../data/research/sources_pass4.json';
import sourceDataPass5 from '../data/research/sources_pass5.json';
import sourceDataPass6 from '../data/research/sources_pass6.json';
import sourceDataPass7 from '../data/research/sources_pass7.json';
import sourceDataPass8 from '../data/research/sources_pass8.json';
import sourceDataPass9 from '../data/research/sources_pass9.json';
import sourceDataPass10 from '../data/research/sources_pass10.json';
import sourceDataPass11 from '../data/research/sources_pass11.json';
import sourceDataPass12 from '../data/research/sources_pass12.json';
import sourceDataPass13 from '../data/research/sources_pass13.json';
import sourceDataPass14 from '../data/research/sources_pass14.json';
import sourceDataPass15 from '../data/research/sources_pass15.json';
import sourceDataPass16 from '../data/research/sources_pass16.json';
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
  [key: string]: unknown;
};

type ResearchProfileFile = {
  schemaVersion: number;
  updatedAt: string;
  method?: string;
  profiles: ResearchProfile[];
};

type ResearchSourceFile = {
  updatedAt: string;
  policy?: string;
  sources: ResearchSource[];
};

const profileFiles: ResearchProfileFile[] = [
  profileData as unknown as ResearchProfileFile,
  profileDataPass2 as unknown as ResearchProfileFile,
  profileDataPass3 as unknown as ResearchProfileFile,
  profileDataPass4 as unknown as ResearchProfileFile,
  profileDataPass5 as unknown as ResearchProfileFile,
  profileDataPass6 as unknown as ResearchProfileFile,
  profileDataPass7 as unknown as ResearchProfileFile,
];

const sourceFiles: ResearchSourceFile[] = [
  sourceData as unknown as ResearchSourceFile,
  sourceDataPass2 as unknown as ResearchSourceFile,
  sourceDataPass3 as unknown as ResearchSourceFile,
  sourceDataPass4 as unknown as ResearchSourceFile,
  sourceDataPass5 as unknown as ResearchSourceFile,
  sourceDataPass6 as unknown as ResearchSourceFile,
  sourceDataPass7 as unknown as ResearchSourceFile,
  sourceDataPass8 as unknown as ResearchSourceFile,
  sourceDataPass9 as unknown as ResearchSourceFile,
  sourceDataPass10 as unknown as ResearchSourceFile,
  sourceDataPass11 as unknown as ResearchSourceFile,
  sourceDataPass12 as unknown as ResearchSourceFile,
  sourceDataPass13 as unknown as ResearchSourceFile,
  sourceDataPass14 as unknown as ResearchSourceFile,
  sourceDataPass15 as unknown as ResearchSourceFile,
  sourceDataPass16 as unknown as ResearchSourceFile,
];

export const researchMethod = profileFiles.find((file) => file.method)?.method ?? 'Hand-researched wine reference overlay.';
export const researchPolicy = sourceFiles.find((file) => file.policy)?.policy ?? 'Prefer primary legal and official sources.';
export const researchPassCount = profileFiles.length;
export const researchSourcePassCount = sourceFiles.length;
export const researchSources = sourceFiles.flatMap((file) => file.sources);
export const researchProfiles = profileFiles.flatMap((file) => file.profiles);
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
