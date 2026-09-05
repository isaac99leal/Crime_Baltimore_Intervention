import varietyData from '../data/official/adelaide-varieties.json';
import regionData from '../data/official/adelaide-regions.json';
import vintageData from '../data/research/vintage_observations.json';
import vintageDataPass2 from '../data/research/vintage_observations_pass2.json';
import vintageDataPass3 from '../data/research/vintage_observations_pass3.json';
import { researchProfiles } from './research';
import { tradeObservations } from './tradeSheetIngestion';

type AdelaideVarietyRecord = {
  name: string;
  origin: string | null;
  colour: string | null;
  area2000: number | null;
  area2010: number | null;
  area2016: number | null;
  area2023: number | null;
};

type AdelaideVarietyFile = {
  source: Record<string, unknown>;
  count: number;
  records: AdelaideVarietyRecord[];
};

type AdelaidePlanting = {
  name: string;
  area: number;
  origin: string | null;
  colour: string | null;
  sourceCode: string;
};

type AdelaideRegionRecord = {
  country: string;
  path: string[];
  scope: 'national' | 'regional' | string;
  sourceYears: number[];
  topPlantings: AdelaidePlanting[];
};

type AdelaideRegionFile = {
  source: Record<string, unknown>;
  count: number;
  records: AdelaideRegionRecord[];
};

type VintageObservation = {
  id: string;
  country: string;
  region: string;
  year: number;
  growingSeason?: Record<string, unknown>;
  styleEffects?: string[];
  matrixModifiers?: Record<string, unknown>;
  sourceRefs: string[];
};

type VintageObservationFile = {
  observations: VintageObservation[];
};

const varieties = varietyData as unknown as AdelaideVarietyFile;
const regions = regionData as unknown as AdelaideRegionFile;
const vintageFiles = [
  vintageData as unknown as VintageObservationFile,
  vintageDataPass2 as unknown as VintageObservationFile,
  vintageDataPass3 as unknown as VintageObservationFile,
];
const vintageObservations = vintageFiles.flatMap((file) => file.observations);

export type CultivarAreaSeries = {
  name: string;
  origin: string | null;
  colour: string | null;
  areaHa: {
    2000: number | null;
    2010: number | null;
    2016: number | null;
    2023: number | null;
  };
};

export type CultivationObservation = {
  cultivar: string;
  country: string;
  path: string[];
  scope: string;
  areaHa: number;
  sourceYears: number[];
  origin: string | null;
  colour: string | null;
  sourceCode: string;
  geographyStatus: 'statistical-not-gi';
};

export type LegalWineUseEvidence = {
  cultivar: string;
  profileId: string;
  country: string;
  designation: string;
  legalClass: string;
  role: 'principal' | 'authorized';
};

export type TradeWineUseEvidence = {
  cultivar: string;
  observationId: string;
  producer: string;
  wine: string | null;
  vintage: number | null;
  country: string;
  region: string;
  sourceRef: string;
  technicalFields: Record<string, unknown>;
};

export type CultivarVintageContext = {
  cultivar: string;
  observationId: string;
  country: string;
  region: string;
  year: number;
  growingSeason?: Record<string, unknown>;
  styleEffects?: string[];
  matrixModifiers?: Record<string, unknown>;
  sourceRefs: string[];
  matchBasis: Array<'statistical-cultivation-geography' | 'legal-wine-use-geography' | 'trade-wine-use-geography'>;
  scope: 'regional-context-not-universal-cultivar-rating';
};

export type CommercialCultivarStatus =
  | 'statistical-bearing-area-only'
  | 'wine-use-corroborated'
  | 'wine-use-with-regional-area';

export type CommercialCultivarCoverage = {
  name: string;
  areaSeries?: CultivarAreaSeries;
  cultivation: CultivationObservation[];
  legalWineUse: LegalWineUseEvidence[];
  tradeWineUse: TradeWineUseEvidence[];
  vintageContexts: CultivarVintageContext[];
  status: CommercialCultivarStatus;
};

export const commercialCultivarMethod =
  'Commercial-cultivar evidence keeps statistical bearing area, statistical cultivation geography, protected-origin legality, producer/importer wine-use evidence, regional vintage observations, and wine-specific cellar choices in separate evidence channels. Statistical planting evidence never creates a GI, cultivar synonym, or bottle-generation permission by itself. Regional vintage context is never converted into one universal cultivar vintage score.';

export const cultivarAreaSeries: CultivarAreaSeries[] = varieties.records.map((record) => ({
  name: record.name,
  origin: record.origin,
  colour: record.colour,
  areaHa: {
    2000: record.area2000,
    2010: record.area2010,
    2016: record.area2016,
    2023: record.area2023,
  },
}));

export const commercialBearingVarieties = cultivarAreaSeries.filter((record) =>
  Object.values(record.areaHa).some((area) => typeof area === 'number' && area > 0),
);

export const currentBearingVarieties = cultivarAreaSeries.filter((record) =>
  typeof record.areaHa[2023] === 'number' && (record.areaHa[2023] ?? 0) > 0,
);

export const regionalCultivationObservations: CultivationObservation[] = regions.records.flatMap((record) =>
  (record.topPlantings ?? [])
    .filter((planting) => typeof planting.area === 'number' && planting.area > 0)
    .map((planting) => ({
      cultivar: planting.name,
      country: record.country,
      path: record.path ?? [],
      scope: record.scope,
      areaHa: planting.area,
      sourceYears: record.sourceYears ?? [],
      origin: planting.origin,
      colour: planting.colour,
      sourceCode: planting.sourceCode,
      geographyStatus: 'statistical-not-gi' as const,
    })),
);

const legalEvidence: LegalWineUseEvidence[] = [];
for (const profile of researchProfiles) {
  const principal = new Set(profile.principalGrapes ?? []);
  for (const cultivar of principal) {
    legalEvidence.push({
      cultivar,
      profileId: profile.id,
      country: profile.country,
      designation: profile.name,
      legalClass: profile.legalClass,
      role: 'principal',
    });
  }
  for (const cultivar of profile.authorizedGrapes ?? []) {
    if (principal.has(cultivar)) continue;
    legalEvidence.push({
      cultivar,
      profileId: profile.id,
      country: profile.country,
      designation: profile.name,
      legalClass: profile.legalClass,
      role: 'authorized',
    });
  }
}
export const legalWineUseEvidence = legalEvidence;

function explicitTradeCultivars(fields: Record<string, unknown>): string[] {
  const names = new Set<string>();
  for (const key of ['varieties', 'grapes', 'authorizedVarieties']) {
    const value = fields[key];
    if (Array.isArray(value)) {
      for (const item of value) if (typeof item === 'string' && item.trim()) names.add(item.trim());
    }
  }

  const composition = fields.varietyComposition;
  if (typeof composition === 'string') {
    for (const piece of composition.split(/[,+/&]/)) {
      const cleaned = piece
        .replace(/\b\d+(?:\.\d+)?\s*%\b/g, '')
        .replace(/^\s*\d+(?:\.\d+)?\s*%\s*/g, '')
        .trim();
      if (cleaned && !/\bblend\b/i.test(cleaned)) names.add(cleaned);
    }
  }
  return [...names];
}

export const tradeWineUseEvidence: TradeWineUseEvidence[] = tradeObservations.flatMap((observation) =>
  explicitTradeCultivars(observation.fields).map((cultivar) => ({
    cultivar,
    observationId: observation.id,
    producer: observation.producer,
    wine: observation.wine,
    vintage: observation.vintage,
    country: observation.country,
    region: observation.region,
    sourceRef: observation.sourceRef,
    technicalFields: observation.fields,
  })),
);

const exact = (value: string) => value.toLocaleLowerCase();
const geoKey = (value: string) => value
  .normalize('NFKD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/[^a-zA-Z0-9]+/g, ' ')
  .trim()
  .toLocaleLowerCase();
const areaByName = new Map(cultivarAreaSeries.map((record) => [exact(record.name), record]));
const cultivationByName = new Map<string, CultivationObservation[]>();
for (const record of regionalCultivationObservations) {
  const key = exact(record.cultivar);
  const bucket = cultivationByName.get(key) ?? [];
  bucket.push(record);
  cultivationByName.set(key, bucket);
}
const legalByName = new Map<string, LegalWineUseEvidence[]>();
for (const record of legalWineUseEvidence) {
  const key = exact(record.cultivar);
  const bucket = legalByName.get(key) ?? [];
  bucket.push(record);
  legalByName.set(key, bucket);
}
const tradeByName = new Map<string, TradeWineUseEvidence[]>();
for (const record of tradeWineUseEvidence) {
  const key = exact(record.cultivar);
  const bucket = tradeByName.get(key) ?? [];
  bucket.push(record);
  tradeByName.set(key, bucket);
}

function vintageContexts(name: string): CultivarVintageContext[] {
  const key = exact(name);
  const locations: Array<{ country: string; label: string; basis: CultivarVintageContext['matchBasis'][number] }> = [];
  for (const record of cultivationByName.get(key) ?? []) {
    for (const label of record.path) locations.push({ country: record.country, label, basis: 'statistical-cultivation-geography' });
  }
  for (const record of legalByName.get(key) ?? []) {
    locations.push({ country: record.country, label: record.designation, basis: 'legal-wine-use-geography' });
  }
  for (const record of tradeByName.get(key) ?? []) {
    locations.push({ country: record.country, label: record.region, basis: 'trade-wine-use-geography' });
  }

  const contexts: CultivarVintageContext[] = [];
  for (const observation of vintageObservations) {
    const observationRegion = geoKey(observation.region);
    const bases = new Set<CultivarVintageContext['matchBasis'][number]>();
    for (const location of locations) {
      if (location.country !== observation.country) continue;
      const label = geoKey(location.label);
      if (!label || !observationRegion) continue;
      if (label === observationRegion || (label.length >= 6 && observationRegion.includes(label)) || (observationRegion.length >= 6 && label.includes(observationRegion))) {
        bases.add(location.basis);
      }
    }
    if (!bases.size) continue;
    contexts.push({
      cultivar: name,
      observationId: observation.id,
      country: observation.country,
      region: observation.region,
      year: observation.year,
      growingSeason: observation.growingSeason,
      styleEffects: observation.styleEffects,
      matrixModifiers: observation.matrixModifiers,
      sourceRefs: observation.sourceRefs,
      matchBasis: [...bases],
      scope: 'regional-context-not-universal-cultivar-rating',
    });
  }
  return contexts.sort((a, b) => a.year - b.year || a.region.localeCompare(b.region));
}

export function commercialCultivarCoverage(name: string): CommercialCultivarCoverage | undefined {
  const key = exact(name);
  const areaSeries = areaByName.get(key);
  const cultivation = cultivationByName.get(key) ?? [];
  const legalWineUse = legalByName.get(key) ?? [];
  const tradeWineUse = tradeByName.get(key) ?? [];
  if (!areaSeries && !cultivation.length && !legalWineUse.length && !tradeWineUse.length) return undefined;

  const wineUse = legalWineUse.length > 0 || tradeWineUse.length > 0;
  const regionalArea = cultivation.length > 0;
  const status: CommercialCultivarStatus = wineUse && regionalArea
    ? 'wine-use-with-regional-area'
    : wineUse
      ? 'wine-use-corroborated'
      : 'statistical-bearing-area-only';

  return { name: areaSeries?.name ?? name, areaSeries, cultivation, legalWineUse, tradeWineUse, vintageContexts: vintageContexts(name), status };
}

export function cultivationForCultivar(name: string, country?: string): CultivationObservation[] {
  const records = cultivationByName.get(exact(name)) ?? [];
  return country ? records.filter((record) => record.country === country) : records;
}

export function vintageContextsForCultivar(name: string): CultivarVintageContext[] {
  return vintageContexts(name);
}

export function validateCommercialCultivarEvidence() {
  const issues: string[] = [];
  if (varieties.count !== varieties.records.length) issues.push(`Adelaide variety count mismatch: ${varieties.count} vs ${varieties.records.length}`);
  if (regions.count !== regions.records.length) issues.push(`Adelaide geography count mismatch: ${regions.count} vs ${regions.records.length}`);
  if (regionalCultivationObservations.some((record) => record.geographyStatus !== 'statistical-not-gi')) {
    issues.push('A statistical cultivation geography escaped the non-GI guardrail.');
  }
  if (!commercialCultivarMethod.toLocaleLowerCase().includes('statistical planting evidence never creates a gi')) {
    issues.push('Commercial cultivar method lost the statistical-geography guardrail.');
  }
  if (!commercialCultivarMethod.toLocaleLowerCase().includes('never converted into one universal cultivar vintage score')) {
    issues.push('Commercial cultivar method lost the regional-vintage guardrail.');
  }
  return {
    authorityVarieties: varieties.records.length,
    everBearingVarieties: commercialBearingVarieties.length,
    currentBearingVarieties: currentBearingVarieties.length,
    cultivationObservations: regionalCultivationObservations.length,
    legalWineUseObservations: legalWineUseEvidence.length,
    tradeWineUseObservations: tradeWineUseEvidence.length,
    regionalVintageObservationsAvailable: vintageObservations.length,
    issues,
  };
}
