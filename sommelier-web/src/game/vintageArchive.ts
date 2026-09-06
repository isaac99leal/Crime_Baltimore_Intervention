import archiveData from '../data/research/historical_vintage_archives.json';
import archiveDataPass2 from '../data/research/historical_vintage_archives_pass2.json';
import { researchSourceById } from './research';

export type VintageArchiveStatus =
  | 'structured-growing-season-ingested'
  | 'authority-archive-detail-available'
  | 'authority-report-available'
  | 'documentary-bottle-or-harvest-evidence'
  | 'monitoring-system-confirmed-detail-not-yet-ingested'
  | 'unknown';

export type HistoricalVintageArchive = {
  id: string;
  country: string;
  modernGeographicReference: string;
  productFamily: string;
  recordStatus: VintageArchiveStatus;
  earliestYear: number;
  latestYear: number;
  years: number[];
  historicalIdentityNote?: string;
  declarationNote?: string;
  sourceRefs: string[];
};

type ArchiveFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  archives: HistoricalVintageArchive[];
  evidenceStatuses: VintageArchiveStatus[];
};

const files = [
  archiveData as unknown as ArchiveFile,
  archiveDataPass2 as unknown as ArchiveFile,
];
export const historicalVintageMethod = files.map((file) => file.method).join(' ');
export const historicalVintageArchivePassCount = files.length;
export const historicalVintageArchives = files.flatMap((file) => file.archives);
export const vintageEvidenceStatuses = [...new Set(files.flatMap((file) => file.evidenceStatuses))];
export const historicalVintageArchiveById = new Map(historicalVintageArchives.map((archive) => [archive.id, archive]));

export function findHistoricalVintageArchive(id: string): HistoricalVintageArchive | undefined {
  return historicalVintageArchiveById.get(id);
}

export function archiveHasYear(archive: HistoricalVintageArchive, year: number): boolean {
  return archive.years.includes(year);
}

export function historicalVintageEvidence(id: string, year: number): VintageArchiveStatus {
  const archive = findHistoricalVintageArchive(id);
  if (!archive) return 'unknown';
  if (archive.years.includes(year)) return archive.recordStatus;
  if (year >= archive.earliestYear && year <= archive.latestYear && archive.recordStatus === 'monitoring-system-confirmed-detail-not-yet-ingested') {
    return 'monitoring-system-confirmed-detail-not-yet-ingested';
  }
  return 'unknown';
}

export function chooseDocumentedArchiveYear(id: string, random: () => number): number | undefined {
  const archive = findHistoricalVintageArchive(id);
  if (!archive?.years.length) return undefined;
  return archive.years[Math.floor(random() * archive.years.length)];
}

export function validateHistoricalVintageArchives() {
  const issues: string[] = [];
  const ids = new Set<string>();
  const allowedStatuses = new Set(vintageEvidenceStatuses);

  for (const archive of historicalVintageArchives) {
    if (ids.has(archive.id)) issues.push(`Duplicate historical vintage archive: ${archive.id}`);
    ids.add(archive.id);
    if (!archive.country || !archive.modernGeographicReference || !archive.productFamily) issues.push(`Incomplete archive identity: ${archive.id}`);
    if (!allowedStatuses.has(archive.recordStatus)) issues.push(`Unknown archive status: ${archive.id}`);
    if (archive.earliestYear > archive.latestYear) issues.push(`Invalid archive range: ${archive.id}`);
    const uniqueYears = new Set(archive.years);
    if (uniqueYears.size !== archive.years.length) issues.push(`Duplicate years in archive: ${archive.id}`);
    for (const year of archive.years) {
      if (!Number.isInteger(year) || year < archive.earliestYear || year > archive.latestYear) issues.push(`Out-of-range year ${year} in ${archive.id}`);
    }
    for (const sourceId of archive.sourceRefs) {
      if (!researchSourceById.has(sourceId)) issues.push(`Unknown source ${sourceId} in ${archive.id}`);
    }
  }

  const documented = historicalVintageArchives.filter((archive) => archive.years.length);
  return {
    passes: historicalVintageArchivePassCount,
    archives: historicalVintageArchives.length,
    documentedYears: historicalVintageArchives.reduce((sum, archive) => sum + archive.years.length, 0),
    earliestDocumentedYear: documented.length ? Math.min(...documented.map((archive) => Math.min(...archive.years))) : undefined,
    issues,
  };
}
