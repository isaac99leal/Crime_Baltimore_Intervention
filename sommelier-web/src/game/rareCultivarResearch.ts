import rareData from '../data/research/rare_cultivar_profiles_pass1.json';
import { researchSourceById } from './research';

export type RareCultivarProfile = {
  id: string;
  name: string;
  country: string;
  region: string;
  color: string;
  researchStatus: string;
  generationStatus: 'reference-only';
  historicalStatus: Record<string, unknown>;
  phenology?: Record<string, unknown>;
  diseaseAndClimate?: Record<string, unknown>;
  viticulture?: Record<string, unknown>;
  researchNotes?: string[];
  sourceRefs: string[];
};

export type HistoricalVarietyQueue = {
  region: string;
  names: string[];
};

type RareFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  profiles: RareCultivarProfile[];
  historicalVarietyResearchQueue: HistoricalVarietyQueue[];
  queuePolicy: string;
};

const file = rareData as unknown as RareFile;
export const rareCultivarResearchMethod = file.method;
export const rareCultivarProfiles = file.profiles;
export const historicalVarietyResearchQueue = file.historicalVarietyResearchQueue;
export const rareCultivarQueuePolicy = file.queuePolicy;
export const rareCultivarByName = new Map(rareCultivarProfiles.map((profile) => [profile.name.toLocaleLowerCase(), profile]));

export function findRareCultivar(name: string): RareCultivarProfile | undefined {
  return rareCultivarByName.get(name.toLocaleLowerCase());
}

export function validateRareCultivarResearch() {
  const issues: string[] = [];
  const profileIds = new Set<string>();
  const queued = new Set<string>();

  for (const profile of rareCultivarProfiles) {
    if (profileIds.has(profile.id)) issues.push(`Duplicate rare-cultivar profile: ${profile.id}`);
    profileIds.add(profile.id);
    if (!profile.name || !profile.country || !profile.region || !profile.historicalStatus) issues.push(`Incomplete rare-cultivar profile: ${profile.id}`);
    if (profile.generationStatus !== 'reference-only') issues.push(`Rare-cultivar profile escaped generation safety: ${profile.id}`);
    for (const sourceId of profile.sourceRefs) if (!researchSourceById.has(sourceId)) issues.push(`Unknown rare-cultivar source ${sourceId} in ${profile.id}`);
  }

  for (const group of historicalVarietyResearchQueue) {
    if (!group.region || !group.names.length) issues.push('Incomplete historical variety research queue group.');
    for (const name of group.names) queued.add(`${group.region}:${name}`);
  }

  if (!rareCultivarQueuePolicy.toLowerCase().includes('does not establish')) issues.push('Rare-cultivar queue lost its evidence-safety policy.');

  return {
    detailedProfiles: rareCultivarProfiles.length,
    queueRegions: historicalVarietyResearchQueue.length,
    queuedNames: queued.size,
    issues,
  };
}
