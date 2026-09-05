import registryData from '../data/research/designation_registry_records_pass1.json';
import registryDataPass2 from '../data/research/designation_registry_records_pass2.json';
import registryDataPass3 from '../data/research/designation_registry_records_pass3.json';
import { researchSourceById } from './research';

export type ExpandedDesignation = {
  id: string;
  country: string;
  name: string;
  legalClass: string;
  level: string;
  parent?: string;
  location?: string;
  aliases: string[];
  registrationNumber?: string;
  registrationDate?: string;
  sourceRef: string;
  generationStatus: 'reference-only';
};

type RegistryGroup = {
  country: string;
  sourceRef: string;
  defaultLegalClass: string | null;
  fields: string[];
  records: unknown[][];
};

type RegistryFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  count: number;
  groups: RegistryGroup[];
};

const files = [
  registryData as unknown as RegistryFile,
  registryDataPass2 as unknown as RegistryFile,
  registryDataPass3 as unknown as RegistryFile,
];

function slug(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function valueFor(group: RegistryGroup, row: unknown[], field: string): unknown {
  const index = group.fields.indexOf(field);
  return index >= 0 ? row[index] : undefined;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.length ? value : undefined;
}

function aliasesValue(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.length > 0) : [];
}

function expandGroup(group: RegistryGroup): ExpandedDesignation[] {
  return group.records.map((row) => {
    const name = stringValue(valueFor(group, row, 'name')) ?? '';
    const legalClass = stringValue(valueFor(group, row, 'legalClass')) ?? group.defaultLegalClass ?? 'protected-origin';
    const location = stringValue(valueFor(group, row, 'location'));
    const level = stringValue(valueFor(group, row, 'level')) ?? 'protected-origin';
    const disambiguator = [legalClass, location].filter(Boolean).join('-');
    return {
      id: `${slug(group.country)}:${slug(name)}${disambiguator ? `:${slug(disambiguator)}` : ''}`,
      country: group.country,
      name,
      legalClass,
      level,
      parent: stringValue(valueFor(group, row, 'parent')),
      location,
      aliases: aliasesValue(valueFor(group, row, 'aliases')),
      registrationNumber: stringValue(valueFor(group, row, 'registrationNumber')),
      registrationDate: stringValue(valueFor(group, row, 'registrationDate')),
      sourceRef: group.sourceRef,
      generationStatus: 'reference-only' as const,
    };
  });
}

export const expandedDesignationMethod = files.map((file) => file.method).join(' ');
export const expandedDesignationPassCount = files.length;
export const expandedDesignationRecords = files.flatMap((file) => file.groups.flatMap(expandGroup));
export const expandedDesignationById = new Map(expandedDesignationRecords.map((record) => [record.id, record]));
export const expandedDesignationCountries = [...new Set(expandedDesignationRecords.map((record) => record.country))].sort();
export const expandedDesignationCountsByCountry = Object.fromEntries(
  expandedDesignationCountries.map((country) => [country, expandedDesignationRecords.filter((record) => record.country === country).length]),
) as Record<string, number>;

export function designationsForCountry(country: string): ExpandedDesignation[] {
  return expandedDesignationRecords.filter((record) => record.country === country);
}

export function findExpandedDesignation(country: string, name: string, location?: string): ExpandedDesignation[] {
  const target = name.toLocaleLowerCase();
  return expandedDesignationRecords.filter((record) => {
    const nameMatch = record.country === country && (
      record.name.toLocaleLowerCase() === target || record.aliases.some((alias) => alias.toLocaleLowerCase() === target)
    );
    return nameMatch && (!location || record.location === location);
  });
}

export function validateExpandedDesignationRegistry() {
  const issues: string[] = [];
  const ids = new Set<string>();
  const expected = files.reduce((sum, file) => sum + file.count, 0);

  if (expandedDesignationRecords.length !== expected) {
    issues.push(`Expanded designation count mismatch: expected ${expected}, got ${expandedDesignationRecords.length}`);
  }

  for (const record of expandedDesignationRecords) {
    if (!record.name || !record.country || !record.legalClass || !record.level) issues.push(`Incomplete designation identity: ${record.id}`);
    if (ids.has(record.id)) issues.push(`Duplicate expanded designation id: ${record.id}`);
    ids.add(record.id);
    if (!researchSourceById.has(record.sourceRef)) issues.push(`Unknown source ${record.sourceRef} in ${record.id}`);
    if (record.generationStatus !== 'reference-only') issues.push(`Registry identity escaped generation safety: ${record.id}`);
  }

  for (const country of ['Australia', 'Chile', 'South Africa']) {
    const countryRecords = designationsForCountry(country);
    for (const record of countryRecords) {
      if (record.parent && !countryRecords.some((candidate) => candidate.name === record.parent)) {
        issues.push(`${country} designation parent not found for ${record.name}: ${record.parent}`);
      }
    }
  }

  return {
    records: expandedDesignationRecords.length,
    passes: expandedDesignationPassCount,
    countries: expandedDesignationCountries.length,
    countsByCountry: expandedDesignationCountsByCountry,
    issues,
  };
}
