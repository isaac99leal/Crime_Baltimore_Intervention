import rareData from '../data/research/rare_cultivar_profiles_pass1.json';
import rareDataPass2 from '../data/research/rare_cultivar_profiles_pass2.json';
import { researchSourceById } from './research';

export type RareCultivarProfile = {
  id: string;
  name: string;
  aliases?: string[];
  country: string;
  region: string;
  color: string;
  researchStatus: string;
  generationStatus: 'reference-only';
  historicalStatus: Record<string, unknown>;
  identity?: Record<string, unknown>;
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

const files = [rareData as unknown as RareFile, rareDataPass2 as unknown as RareFile];
export const rareCultivarResearchMethod = files.map((file) => file.method).join(' ');
export const rareCultivarProfiles = files.flatMap((file) => file.profiles);
export const historicalVarietyResearchQueue = files.flatMap((file) => file.historicalVarietyResearchQueue);
export const rareCultivarQueuePolicy = files.map((file) => file.queuePolicy).join(' ');
export const rareCultivarPassCount = files.length;

const norm = (value: string) => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
const lookupPairs = rareCultivarProfiles.flatMap((profile) => [profile.name, ...(profile.aliases ?? [])].map((name) => [norm(name), profile] as const));
export const rareCultivarByName = new Map(lookupPairs);

export function findRareCultivar(name: string): RareCultivarProfile | undefined {
  return rareCultivarByName.get(norm(name));
}

export function validateRareCultivarResearch() {
  const issues: string[] = [];
  const profileIds = new Set<string>();
  const lookupNames = new Map<string, string>();
  const queued = new Set<string>();

  for (const profile of rareCultivarProfiles) {
    if (profileIds.has(profile.id)) issues.push(`Duplicate rare-cultivar profile: ${profile.id}`);
    profileIds.add(profile.id);
    if (!profile.name || !profile.country || !profile.region || !profile.historicalStatus) issues.push(`Incomplete rare-cultivar profile: ${profile.id}`);
    if (profile.generationStatus !== 'reference-only') issues.push(`Rare-cultivar profile escaped generation safety: ${profile.id}`);
    for (const sourceId of profile.sourceRefs) if (!researchSourceById.has(sourceId)) issues.push(`Unknown rare-cultivar source ${sourceId} in ${profile.id}`);
    for (const name of [profile.name, ...(profile.aliases ?? [])]) {
      const key = norm(name);
      const existing = lookupNames.get(key);
      if (existing && existing !== profile.id) issues.push(`Rare-cultivar lookup collision for ${name}: ${existing} vs ${profile.id}`);
      lookupNames.set(key, profile.id);
    }
  }

  for (const group of historicalVarietyResearchQueue) {
    if (!group.region || !group.names.length) issues.push('Incomplete historical variety research queue group.');
    for (const name of group.names) queued.add(`${group.region}:${name}`);
  }

  if (!rareCultivarQueuePolicy.toLowerCase().includes('does not establish')) issues.push('Rare-cultivar queue lost its evidence-safety policy.');

  return {
    passes: rareCultivarPassCount,
    detailedProfiles: rareCultivarProfiles.length,
    queueRegions: historicalVarietyResearchQueue.length,
    queuedNames: queued.size,
    issues,
  };
}
