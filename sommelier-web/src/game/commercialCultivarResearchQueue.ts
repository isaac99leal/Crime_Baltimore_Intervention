import {
  commercialBearingVarieties,
  commercialCultivarCoverage,
  currentBearingVarieties,
  regionalCultivationObservations,
} from './commercialCultivarEvidence';

export type CultivarResearchGap =
  | 'no-commercial-wine-use-corroboration'
  | 'no-regional-cultivation-detail'
  | 'no-legal-wine-use-profile'
  | 'no-trade-technical-observation'
  | 'no-regional-vintage-context';

export type CultivarResearchQueueItem = {
  cultivar: string;
  origin: string | null;
  colour: string | null;
  currentAreaHa: number | null;
  latestDocumentedAreaHa: number;
  regionalObservationCount: number;
  countryCount: number;
  gaps: CultivarResearchGap[];
  priorityScore: number;
};

export type CountryCultivarResearchQueueItem = {
  country: string;
  cultivar: string;
  observedAreaHa: number;
  statisticalPaths: string[][];
  sourceYears: number[];
  legalWineUseInCountry: boolean;
  tradeWineUseInCountry: boolean;
  regionalVintageContextInCountry: boolean;
  gaps: Array<'no-country-wine-use-corroboration' | 'no-country-legal-profile' | 'no-country-trade-tech' | 'no-country-vintage-context'>;
  priorityScore: number;
};

const latestArea = (areas: Record<number, number | null>): number => {
  for (const year of [2023, 2016, 2010, 2000]) {
    const area = areas[year];
    if (typeof area === 'number' && area > 0) return area;
  }
  return 0;
};

const scoreGlobal = (currentAreaHa: number | null, latestDocumentedAreaHa: number, regionalCount: number, countryCount: number, gaps: CultivarResearchGap[]) => {
  const area = currentAreaHa ?? latestDocumentedAreaHa;
  const areaWeight = area > 0 ? Math.log10(area + 1) * 18 : 0;
  const regionalWeight = Math.min(20, regionalCount * 2.5);
  const countryWeight = Math.min(15, countryCount * 3);
  const missingUseWeight = gaps.includes('no-commercial-wine-use-corroboration') ? 25 : 0;
  const missingTechWeight = gaps.includes('no-trade-technical-observation') ? 8 : 0;
  const missingVintageWeight = gaps.includes('no-regional-vintage-context') ? 6 : 0;
  return Math.round((areaWeight + regionalWeight + countryWeight + missingUseWeight + missingTechWeight + missingVintageWeight) * 10) / 10;
};

export const commercialCultivarResearchQueue: CultivarResearchQueueItem[] = commercialBearingVarieties.map((record) => {
  const coverage = commercialCultivarCoverage(record.name);
  const cultivation = coverage?.cultivation ?? [];
  const legal = coverage?.legalWineUse ?? [];
  const trade = coverage?.tradeWineUse ?? [];
  const vintages = coverage?.vintageContexts ?? [];
  const countries = new Set(cultivation.map((item) => item.country));
  const currentAreaHa = record.areaHa[2023];
  const documentedArea = latestArea(record.areaHa as Record<number, number | null>);
  const gaps: CultivarResearchGap[] = [];
  if (!legal.length && !trade.length) gaps.push('no-commercial-wine-use-corroboration');
  if (!cultivation.length) gaps.push('no-regional-cultivation-detail');
  if (!legal.length) gaps.push('no-legal-wine-use-profile');
  if (!trade.length) gaps.push('no-trade-technical-observation');
  if (!vintages.length) gaps.push('no-regional-vintage-context');

  return {
    cultivar: record.name,
    origin: record.origin,
    colour: record.colour,
    currentAreaHa,
    latestDocumentedAreaHa: documentedArea,
    regionalObservationCount: cultivation.length,
    countryCount: countries.size,
    gaps,
    priorityScore: scoreGlobal(currentAreaHa, documentedArea, cultivation.length, countries.size, gaps),
  };
}).sort((a, b) => b.priorityScore - a.priorityScore || b.latestDocumentedAreaHa - a.latestDocumentedAreaHa || a.cultivar.localeCompare(b.cultivar));

export const currentCommercialCultivarResearchQueue = commercialCultivarResearchQueue.filter((item) => (item.currentAreaHa ?? 0) > 0);
export const currentBearingCultivarsWithoutWineUse = currentCommercialCultivarResearchQueue.filter((item) => item.gaps.includes('no-commercial-wine-use-corroboration'));
export const currentBearingCultivarsWithoutTradeTech = currentCommercialCultivarResearchQueue.filter((item) => item.gaps.includes('no-trade-technical-observation'));
export const currentBearingCultivarsWithoutVintageContext = currentCommercialCultivarResearchQueue.filter((item) => item.gaps.includes('no-regional-vintage-context'));

const countryCultivarBuckets = new Map<string, typeof regionalCultivationObservations>();
for (const observation of regionalCultivationObservations) {
  const key = `${observation.country}|${observation.cultivar.toLocaleLowerCase()}`;
  const bucket = countryCultivarBuckets.get(key) ?? [];
  bucket.push(observation);
  countryCultivarBuckets.set(key, bucket);
}

export const countryCultivarResearchQueue: CountryCultivarResearchQueueItem[] = [...countryCultivarBuckets.values()].map((observations) => {
  const first = observations[0];
  const coverage = commercialCultivarCoverage(first.cultivar);
  const legalWineUseInCountry = (coverage?.legalWineUse ?? []).some((record) => record.country === first.country);
  const tradeWineUseInCountry = (coverage?.tradeWineUse ?? []).some((record) => record.country === first.country);
  const regionalVintageContextInCountry = (coverage?.vintageContexts ?? []).some((record) => record.country === first.country);
  const gaps: CountryCultivarResearchQueueItem['gaps'] = [];
  if (!legalWineUseInCountry && !tradeWineUseInCountry) gaps.push('no-country-wine-use-corroboration');
  if (!legalWineUseInCountry) gaps.push('no-country-legal-profile');
  if (!tradeWineUseInCountry) gaps.push('no-country-trade-tech');
  if (!regionalVintageContextInCountry) gaps.push('no-country-vintage-context');
  const observedAreaHa = observations.reduce((sum, observation) => sum + observation.areaHa, 0);
  const sourceYears = [...new Set(observations.flatMap((observation) => observation.sourceYears))].sort((a, b) => a - b);
  const statisticalPaths = observations.map((observation) => observation.path);
  const priorityScore = Math.round((Math.log10(observedAreaHa + 1) * 20 + Math.min(20, observations.length * 3) + gaps.length * 7) * 10) / 10;

  return {
    country: first.country,
    cultivar: first.cultivar,
    observedAreaHa,
    statisticalPaths,
    sourceYears,
    legalWineUseInCountry,
    tradeWineUseInCountry,
    regionalVintageContextInCountry,
    gaps,
    priorityScore,
  };
}).sort((a, b) => b.priorityScore - a.priorityScore || b.observedAreaHa - a.observedAreaHa || a.country.localeCompare(b.country) || a.cultivar.localeCompare(b.cultivar));

export const countryCultivarGapCounts = Object.fromEntries(
  [...new Set(countryCultivarResearchQueue.map((item) => item.country))].sort().map((country) => {
    const records = countryCultivarResearchQueue.filter((item) => item.country === country);
    return [country, {
      statisticallyObservedCultivars: records.length,
      withoutCountryWineUse: records.filter((item) => item.gaps.includes('no-country-wine-use-corroboration')).length,
      withoutCountryTradeTech: records.filter((item) => item.gaps.includes('no-country-trade-tech')).length,
      withoutCountryVintageContext: records.filter((item) => item.gaps.includes('no-country-vintage-context')).length,
    }];
  }),
) as Record<string, {
  statisticallyObservedCultivars: number;
  withoutCountryWineUse: number;
  withoutCountryTradeTech: number;
  withoutCountryVintageContext: number;
}>;

export function validateCommercialCultivarResearchQueue() {
  const issues: string[] = [];
  if (commercialCultivarResearchQueue.length !== commercialBearingVarieties.length) {
    issues.push(`Commercial cultivar queue mismatch: ${commercialCultivarResearchQueue.length} vs ${commercialBearingVarieties.length}`);
  }
  if (currentCommercialCultivarResearchQueue.length !== currentBearingVarieties.length) {
    issues.push(`Current-bearing queue mismatch: ${currentCommercialCultivarResearchQueue.length} vs ${currentBearingVarieties.length}`);
  }
  if (commercialCultivarResearchQueue.some((item) => item.priorityScore < 0 || !Number.isFinite(item.priorityScore))) {
    issues.push('Invalid cultivar research priority score.');
  }
  if (countryCultivarResearchQueue.some((item) => !item.country || !item.cultivar || item.observedAreaHa <= 0)) {
    issues.push('Invalid country-cultivar research queue item.');
  }
  return {
    globalQueue: commercialCultivarResearchQueue.length,
    currentBearingQueue: currentCommercialCultivarResearchQueue.length,
    currentWithoutWineUse: currentBearingCultivarsWithoutWineUse.length,
    currentWithoutTradeTech: currentBearingCultivarsWithoutTradeTech.length,
    currentWithoutVintageContext: currentBearingCultivarsWithoutVintageContext.length,
    countryCultivarQueue: countryCultivarResearchQueue.length,
    countries: Object.keys(countryCultivarGapCounts).length,
    issues,
  };
}
