import grapesData from '../data/grapes.json';
import regionsData from '../data/regions.json';

export type RawGrape = {
  name: string;
  color?: string;
  origin_country?: string;
  origin_region?: string;
  aliases?: string[];
  key_regions?: string[];
  typical_profile?: {
    acidity?: number;
    tannin?: number;
    body?: number;
    sweetness?: number;
    alcohol_range?: number[] | { min?: number; max?: number };
    fruit_intensity?: number;
    earth_intensity?: number;
    oak_affinity?: number;
  };
  primary_aromas?: string[];
  secondary_aromas?: string[];
  tertiary_aromas?: string[];
  aging_potential?: string;
  food_affinities?: string[];
  fun_fact?: string;
};

export type PlaceKind = 'region' | 'subregion' | 'appellation' | 'commune' | 'vineyard' | 'district' | 'zone';

export type ReferencePlace = {
  id: string;
  name: string;
  country: string;
  kind: PlaceKind;
  path: string[];
  classification?: string;
  classificationTiers: string[];
  primaryGrapes: string[];
  authorizedGrapes: string[];
  soils: string[];
  climate?: string;
  styleNotes?: string;
  priceTier?: string;
  elevation?: number[];
};

type RawNode = Record<string, unknown>;

function record(value: unknown): RawNode | undefined {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RawNode : undefined;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function numbers(value: unknown): number[] {
  return Array.isArray(value) ? value.filter((item): item is number => typeof item === 'number') : [];
}

function slug(value: string): string {
  return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

export const grapeReference = (grapesData as { grapes: RawGrape[] }).grapes;
export const grapeByName = new Map<string, RawGrape>();
for (const grape of grapeReference) {
  grapeByName.set(grape.name.toLowerCase(), grape);
  for (const alias of grape.aliases ?? []) grapeByName.set(alias.toLowerCase(), grape);
}

const root = regionsData as { regions?: unknown[] };
const placeResults: ReferencePlace[] = [];

const childKinds: [string, PlaceKind][] = [
  ['wine_regions', 'region'],
  ['sub_regions', 'subregion'],
  ['appellations', 'appellation'],
  ['communes', 'commune'],
  ['villages', 'commune'],
  ['vineyards', 'vineyard'],
  ['crus', 'vineyard'],
  ['districts', 'district'],
  ['sub_zones', 'zone'],
  ['zones', 'zone'],
];

function walkNode(
  nodeValue: unknown,
  country: string,
  kind: PlaceKind,
  parentPath: string[],
  inherited: { primary: string[]; authorized: string[]; climate?: string },
) {
  const node = record(nodeValue);
  if (!node || typeof node.name !== 'string') return;

  const primary = unique([...inherited.primary, ...strings(node.primary_grapes)]);
  const authorizedLocal = strings(node.authorized_grapes);
  const authorized = unique(authorizedLocal.length ? authorizedLocal : [...inherited.authorized, ...primary]);
  const path = [...parentPath, node.name];
  const classification = typeof node.classification === 'string'
    ? node.classification
    : typeof node.classification_system === 'string' ? node.classification_system : undefined;

  placeResults.push({
    id: `${slug(country)}:${path.map(slug).join(':')}`,
    name: node.name,
    country,
    kind,
    path,
    classification,
    classificationTiers: strings(node.classification_tiers),
    primaryGrapes: primary,
    authorizedGrapes: authorized,
    soils: unique([...strings(node.soil_types), ...strings(node.soils)]),
    climate: typeof node.climate === 'string' ? node.climate : inherited.climate,
    styleNotes: typeof node.style_notes === 'string' ? node.style_notes : undefined,
    priceTier: typeof node.price_tier === 'string' ? node.price_tier : undefined,
    elevation: numbers(node.elevation_m),
  });

  for (const [key, childKind] of childKinds) {
    const children = node[key];
    if (!Array.isArray(children)) continue;
    for (const child of children) {
      walkNode(child, country, childKind, path, {
        primary,
        authorized,
        climate: typeof node.climate === 'string' ? node.climate : inherited.climate,
      });
    }
  }
}

for (const countryValue of root.regions ?? []) {
  const countryNode = record(countryValue);
  if (!countryNode || typeof countryNode.country !== 'string') continue;
  const country = countryNode.country;
  const wineRegions = countryNode.wine_regions;
  if (!Array.isArray(wineRegions)) continue;
  for (const region of wineRegions) walkNode(region, country, 'region', [], { primary: [], authorized: [] });
}

const placeMap = new Map<string, ReferencePlace>();
for (const place of placeResults) placeMap.set(place.id, place);
export const referencePlaces = [...placeMap.values()];
export const referenceCountries = [...new Set(referencePlaces.map((place) => place.country))].sort();
export const referenceAppellations = referencePlaces.filter((place) => ['region', 'subregion', 'appellation', 'commune'].includes(place.kind));
export const referenceVineyards = referencePlaces.filter((place) => place.kind === 'vineyard');

export function findGrape(name: string): RawGrape | undefined {
  return grapeByName.get(name.toLowerCase());
}

export function placeAllowsGrape(place: ReferencePlace, grapeName: string): boolean {
  const canonical = findGrape(grapeName)?.name ?? grapeName;
  const allowed = place.authorizedGrapes.length ? place.authorizedGrapes : place.primaryGrapes;
  if (!allowed.length) return true;
  return allowed.some((name) => (findGrape(name)?.name ?? name).toLowerCase() === canonical.toLowerCase());
}

export function validateReferenceIntegrity() {
  const issues: string[] = [];
  for (const place of referencePlaces) {
    for (const grape of [...place.primaryGrapes, ...place.authorizedGrapes]) {
      if (!findGrape(grape)) issues.push(`${place.country} / ${place.path.join(' / ')} references unknown grape: ${grape}`);
    }
  }
  return {
    countries: referenceCountries.length,
    grapes: grapeReference.length,
    places: referencePlaces.length,
    vineyards: referenceVineyards.length,
    issues,
  };
}
