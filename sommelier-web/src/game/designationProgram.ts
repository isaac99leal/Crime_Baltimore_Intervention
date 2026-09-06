import countryData from '../data/official/adelaide-countries.json';
import eambrosiaData from '../data/official/eambrosia-wine-gis.json';
import ttbData from '../data/official/ttb-avas.json';
import expandedRegistryData from '../data/research/designation_registry_records_pass1.json';
import expandedRegistryDataPass2 from '../data/research/designation_registry_records_pass2.json';
import programData from '../data/research/designation_registry_program.json';
import { researchSourceById } from './research';

export type DesignationIngestionStatus = 'live-index' | 'authority-identified' | 'pending-authority-discovery';

export type DesignationRegistry = {
  id: string;
  system: string;
  countries: string[];
  coverage: string;
  ingestionStatus: Exclude<DesignationIngestionStatus, 'pending-authority-discovery'>;
  localIndex?: string;
  sourceRefs?: string[];
  notes?: string;
};

type CountryFile = {
  count: number;
  records: Array<{ name: string; area2023?: number | null }>;
};

type OfficialIndex = { count: number; records: Array<Record<string, unknown>> };
type ExpandedIndex = { count: number };

type ProgramFile = {
  schemaVersion: number;
  updatedAt: string;
  goal: string;
  policy: string[];
  registries: DesignationRegistry[];
  requiredRecordDepth: string[];
};

const countriesFile = countryData as unknown as CountryFile;
const eambrosiaFile = eambrosiaData as unknown as OfficialIndex;
const ttbFile = ttbData as unknown as OfficialIndex;
const expandedFiles = [expandedRegistryData, expandedRegistryDataPass2] as unknown as ExpandedIndex[];
const programFile = programData as unknown as ProgramFile;

export const globalDesignationGoal = programFile.goal;
export const globalDesignationPolicy = programFile.policy;
export const requiredDesignationRecordDepth = programFile.requiredRecordDepth;
export const designationRegistries = programFile.registries;
export const verifiedPlantingCountries = countriesFile.records.map((record) => record.name);

export type CountryDesignationCoverage = {
  country: string;
  plantedArea2023: number | null;
  ingestionStatus: DesignationIngestionStatus;
  registries: DesignationRegistry[];
};

export const designationCoverage: CountryDesignationCoverage[] = countriesFile.records.map((country) => {
  const registries = designationRegistries.filter((registry) => registry.countries.includes(country.name));
  const status: DesignationIngestionStatus = registries.some((registry) => registry.ingestionStatus === 'live-index')
    ? 'live-index'
    : registries.length
      ? 'authority-identified'
      : 'pending-authority-discovery';
  return {
    country: country.name,
    plantedArea2023: country.area2023 ?? null,
    ingestionStatus: status,
    registries,
  };
});

export const pendingDesignationCountries = designationCoverage
  .filter((record) => record.ingestionStatus === 'pending-authority-discovery')
  .map((record) => record.country);

export const sourceIdentifiedDesignationCountries = designationCoverage
  .filter((record) => record.ingestionStatus !== 'pending-authority-discovery')
  .map((record) => record.country);

export const liveDesignationIndexCounts = {
  eambrosiaWineGis: eambrosiaFile.count,
  ttbAvas: ttbFile.count,
  expandedAuthorityDesignations: expandedFiles.reduce((sum, file) => sum + file.count, 0),
};

export function coverageForCountry(country: string): CountryDesignationCoverage | undefined {
  return designationCoverage.find((record) => record.country === country);
}

export function validateDesignationProgram() {
  const issues: string[] = [];
  const ids = new Set<string>();
  const coverageCountries = new Set<string>();

  if (countriesFile.count !== countriesFile.records.length) issues.push('Authoritative country count does not match country records.');
  if (!globalDesignationGoal.toLowerCase().includes('every legally recognized')) issues.push('Global designation goal lost exhaustive-coverage requirement.');
  if (requiredDesignationRecordDepth.length < 15) issues.push('Designation record-depth contract is too shallow.');

  for (const registry of designationRegistries) {
    if (ids.has(registry.id)) issues.push(`Duplicate designation registry id: ${registry.id}`);
    ids.add(registry.id);
    if (!registry.system || !registry.countries.length || !registry.coverage) issues.push(`Incomplete designation registry: ${registry.id}`);
    if (!['live-index', 'authority-identified'].includes(registry.ingestionStatus)) issues.push(`Invalid ingestion status: ${registry.id}`);
    if (registry.ingestionStatus === 'live-index' && !registry.localIndex) issues.push(`Live registry lacks local index: ${registry.id}`);
    for (const sourceId of registry.sourceRefs ?? []) {
      if (!researchSourceById.has(sourceId)) issues.push(`Unknown designation source ${sourceId} in ${registry.id}`);
    }
  }

  for (const record of designationCoverage) {
    if (coverageCountries.has(record.country)) issues.push(`Duplicate designation country coverage: ${record.country}`);
    coverageCountries.add(record.country);
    if (!record.ingestionStatus) issues.push(`Missing designation status: ${record.country}`);
  }

  for (const country of verifiedPlantingCountries) {
    if (!coverageCountries.has(country)) issues.push(`Verified planting country omitted from designation program: ${country}`);
  }

  if (eambrosiaFile.count < 1600) issues.push('eAmbrosia wine GI index unexpectedly small.');
  if (ttbFile.count < 280) issues.push('TTB AVA index unexpectedly small.');
  if (liveDesignationIndexCounts.expandedAuthorityDesignations < 407) issues.push('Expanded authority designation index unexpectedly small.');

  return {
    verifiedPlantingCountries: designationCoverage.length,
    sourceIdentifiedCountries: sourceIdentifiedDesignationCountries.length,
    pendingCountries: pendingDesignationCountries.length,
    registries: designationRegistries.length,
    liveIndexCounts: liveDesignationIndexCounts,
    issues,
  };
}
