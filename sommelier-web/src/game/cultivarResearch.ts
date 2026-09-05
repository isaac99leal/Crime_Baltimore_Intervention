import cultivarData from '../data/research/cultivar_profiles_pass1.json';
import { researchSourceById } from './research';

export type CultivarResistance = {
  powderyMildew?: string;
  downyMildew?: string;
  botrytis?: string;
  blackRot?: string;
  loci?: Record<string, string[]>;
};

export type CultivarResearchProfile = {
  id: string;
  name: string;
  color: string;
  generationStatus: 'reference-only';
  pedigree: string;
  crossingYear: number;
  nationalRegistrationYear: number;
  resistance: CultivarResistance;
  viticulture: Record<string, unknown>;
  enology: Record<string, unknown>;
  sourceRefs: string[];
};

type CultivarFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  piwiRegistry: {
    jurisdiction: string;
    asOf: string;
    totalProductionCultivars: number;
    declaredPiwiCount: number;
    declarationBasis: string;
    sourceRefs: string[];
    cultivars: string[];
  };
  profiles: CultivarResearchProfile[];
};

const file = cultivarData as unknown as CultivarFile;
export const cultivarResearchMethod = file.method;
export const germanPiwiRegistry = file.piwiRegistry;
export const cultivarResearchProfiles = file.profiles;
export const cultivarResearchByName = new Map(cultivarResearchProfiles.map((profile) => [profile.name.toLocaleLowerCase(), profile]));

export function findCultivarResearch(name: string): CultivarResearchProfile | undefined {
  return cultivarResearchByName.get(name.toLocaleLowerCase());
}

export function validateCultivarResearch() {
  const issues: string[] = [];
  const names = new Set<string>();
  const ids = new Set<string>();
  if (germanPiwiRegistry.cultivars.length !== germanPiwiRegistry.declaredPiwiCount) {
    issues.push(`PIWI registry count mismatch: declared ${germanPiwiRegistry.declaredPiwiCount}, listed ${germanPiwiRegistry.cultivars.length}`);
  }
  if (germanPiwiRegistry.declaredPiwiCount !== 36) issues.push('Expected the 2024 Bundessortenamt 36-cultivar PIWI list.');
  for (const sourceId of germanPiwiRegistry.sourceRefs) if (!researchSourceById.has(sourceId)) issues.push(`Unknown PIWI registry source: ${sourceId}`);
  for (const name of germanPiwiRegistry.cultivars) {
    const key = name.toLocaleLowerCase();
    if (names.has(key)) issues.push(`Duplicate PIWI cultivar: ${name}`);
    names.add(key);
  }
  for (const profile of cultivarResearchProfiles) {
    if (ids.has(profile.id)) issues.push(`Duplicate cultivar profile id: ${profile.id}`);
    ids.add(profile.id);
    if (!profile.name || !profile.pedigree || !profile.crossingYear || !profile.nationalRegistrationYear) issues.push(`Incomplete cultivar profile: ${profile.id}`);
    if (profile.generationStatus !== 'reference-only') issues.push(`Cultivar research profile escaped generation safety: ${profile.id}`);
    if (!germanPiwiRegistry.cultivars.includes(profile.name)) issues.push(`Deep cultivar profile absent from PIWI registry: ${profile.name}`);
    for (const sourceId of profile.sourceRefs) if (!researchSourceById.has(sourceId)) issues.push(`Unknown cultivar source ${sourceId} in ${profile.id}`);
  }
  return {
    registryCultivars: germanPiwiRegistry.cultivars.length,
    detailedProfiles: cultivarResearchProfiles.length,
    issues,
  };
}
