import microSiteData from '../data/research/willamette_micro_sites.json';
import microSiteDataPass2 from '../data/research/willamette_micro_sites_pass2.json';
import { researchSourceById } from './research';

export type WillametteBlock = {
  block: string;
  name?: string;
  zone?: string;
  variety: string;
  clone: string;
  rootstock?: string;
  rows?: number;
  acres?: number;
  plantedYear?: number;
  [key: string]: unknown;
};

export type WillametteZone = {
  name: string;
  [key: string]: unknown;
};

export type WillametteParcel = {
  variety: string;
  clone: string;
  rootstock?: string;
  acres?: number;
  [key: string]: unknown;
};

export type WillametteBlockObservation = {
  block: string;
  variety: string;
  clone: string;
  evidenceContext: string;
  [key: string]: unknown;
};

export type WillametteCloneSiteObservation = {
  clone: string;
  [key: string]: unknown;
};

export type WillametteDataQualityFlag = {
  id: string;
  severity: string;
  detail: string;
  fieldSet?: string[];
};

export type WillametteMicroSite = {
  id: string;
  name: string;
  parentRegion: string;
  ava?: string;
  sourceRefs: string[];
  blocks?: WillametteBlock[];
  zones?: WillametteZone[];
  contractedParcels?: WillametteParcel[];
  blockObservations?: WillametteBlockObservation[];
  cloneBySiteObservations?: WillametteCloneSiteObservation[];
  dataQualityFlags?: WillametteDataQualityFlag[];
  [key: string]: unknown;
};

type WillametteMicroSiteFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  sites: WillametteMicroSite[];
};

const files = [
  microSiteData as unknown as WillametteMicroSiteFile,
  microSiteDataPass2 as unknown as WillametteMicroSiteFile,
];

export const willametteMicroSiteMethod = files.map((file) => file.method).join(' ');
export const willametteMicroSitePassCount = files.length;
export const willametteMicroSites = files.flatMap((file) => file.sites);
export const willametteMicroSiteCount = willametteMicroSites.length;
export const willametteNamedBlockCount = willametteMicroSites.reduce((sum, site) => sum + (site.blocks?.length ?? 0), 0);
export const willametteZoneCount = willametteMicroSites.reduce((sum, site) => sum + (site.zones?.length ?? 0), 0);
export const willametteContractedParcelCount = willametteMicroSites.reduce((sum, site) => sum + (site.contractedParcels?.length ?? 0), 0);
export const willametteBlockObservationCount = willametteMicroSites.reduce((sum, site) => sum + (site.blockObservations?.length ?? 0), 0);
export const willametteCloneSiteObservationCount = willametteMicroSites.reduce((sum, site) => sum + (site.cloneBySiteObservations?.length ?? 0), 0);
export const willametteDataQualityFlagCount = willametteMicroSites.reduce((sum, site) => sum + (site.dataQualityFlags?.length ?? 0), 0);
export const willametteSubSiteObservationCount = willametteNamedBlockCount
  + willametteZoneCount
  + willametteContractedParcelCount
  + willametteBlockObservationCount
  + willametteCloneSiteObservationCount;

export const willametteMicroSiteById = new Map(willametteMicroSites.map((site) => [site.id, site]));

export function findWillametteSite(id: string): WillametteMicroSite | undefined {
  return willametteMicroSiteById.get(id);
}

export function findWillametteBlocks(siteId: string, block: string): WillametteBlock[] {
  return findWillametteSite(siteId)?.blocks?.filter((candidate) => candidate.block === block) ?? [];
}

export function validateWillametteMicroSites() {
  const issues: string[] = [];
  const ids = new Set<string>();

  for (const site of willametteMicroSites) {
    if (ids.has(site.id)) issues.push(`Duplicate Willamette micro-site id: ${site.id}`);
    ids.add(site.id);
    if (!site.name || !site.parentRegion || !site.sourceRefs?.length) issues.push(`Incomplete Willamette micro-site: ${site.id}`);
    for (const sourceRef of site.sourceRefs ?? []) {
      if (!researchSourceById.has(sourceRef)) issues.push(`Unknown Willamette source ${sourceRef} in ${site.id}`);
    }

    const blockKeys = new Set<string>();
    for (const block of site.blocks ?? []) {
      if (!block.block || !block.variety || !block.clone) issues.push(`Incomplete exact block in ${site.id}: ${block.block || 'unnamed'}`);
      const key = `${block.zone ?? ''}|${block.block}`;
      if (blockKeys.has(key)) issues.push(`Duplicate exact block identity in ${site.id}: ${key}`);
      blockKeys.add(key);
      if (block.acres !== undefined && block.acres <= 0) issues.push(`Non-positive block acreage in ${site.id}: ${block.block}`);
      if (block.rows !== undefined && block.rows <= 0) issues.push(`Non-positive row count in ${site.id}: ${block.block}`);
    }

    for (const flag of site.dataQualityFlags ?? []) {
      if (!flag.id || !flag.severity || !flag.detail) issues.push(`Incomplete Willamette data-quality flag in ${site.id}`);
    }
  }

  const openClaim = findWillametteSite('us-or-open-claim-vineyard');
  const openClaimAcres = (openClaim?.blocks ?? []).reduce((sum, block) => sum + (block.acres ?? 0), 0);
  if (Math.abs(openClaimAcres - 20.78) > 0.01) issues.push(`Open Claim block acreage does not reconcile: ${openClaimAcres.toFixed(2)} vs 20.78`);

  const terry = findWillametteSite('us-or-terry-family-vineyard');
  if (terry?.blocks?.length !== 13) issues.push(`Terry Family block count mismatch: ${terry?.blocks?.length ?? 0}`);

  const shea = findWillametteSite('us-or-shea-vineyard');
  const sheaBlockTwo = shea?.blocks?.filter((block) => block.block === '2') ?? [];
  if (sheaBlockTwo.length !== 1) issues.push('Shea East Hill Block 2 identity is missing or duplicated.');
  if (!(shea?.blocks ?? []).some((block) => block.block === 'Third Hill Block 2')) issues.push('Shea Third Hill Block 2 identity is missing.');

  const lingua = findWillametteSite('us-or-lingua-franca-estate');
  const linguaBlockThreeClones = new Set((lingua?.blockObservations ?? []).filter((item) => item.block === '3').map((item) => item.clone));
  if (!linguaBlockThreeClones.has('PN777') || !linguaBlockThreeClones.has('PN115')) {
    issues.push('Lingua Franca Block 3 source-context clone observations were incorrectly collapsed.');
  }

  const knudsen = findWillametteSite('us-or-knudsen-vineyards');
  const knudsenBlock12 = (knudsen?.blockObservations ?? []).filter((item) => item.block === '12');
  const knudsenBlock12Clones = new Set(knudsenBlock12.map((item) => item.clone));
  const knudsenBlock12PlantingYears = new Set(knudsenBlock12.map((item) => item.plantedYear));
  if (!knudsenBlock12Clones.has('4407') || !knudsenBlock12Clones.has('828') || knudsenBlock12PlantingYears.size < 2) {
    issues.push('Knudsen Block 12 contradictory producer observations were incorrectly collapsed.');
  }
  if (!(knudsen?.dataQualityFlags ?? []).some((flag) => flag.id === 'knudsen-block12-clone-planting-conflict')) {
    issues.push('Knudsen Block 12 material conflict lost its explicit data-quality flag.');
  }

  const blakeslee = findWillametteSite('us-or-blakeslee-vineyard');
  if (blakeslee?.blocks?.length !== 6) issues.push(`Blakeslee exact block count mismatch: ${blakeslee?.blocks?.length ?? 0}`);

  return {
    passes: willametteMicroSitePassCount,
    sites: willametteMicroSiteCount,
    exactBlocks: willametteNamedBlockCount,
    zones: willametteZoneCount,
    contractedParcels: willametteContractedParcelCount,
    blockObservations: willametteBlockObservationCount,
    cloneSiteObservations: willametteCloneSiteObservationCount,
    totalSubSiteObservations: willametteSubSiteObservationCount,
    dataQualityFlags: willametteDataQualityFlagCount,
    issues,
  };
}
