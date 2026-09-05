import { findGrape, placeAllowsGrape, referenceAppellations, type RawGrape, type ReferencePlace } from './reference';
import {
  applyResearchMatrices,
  authorityVintageRatingForPlace,
  environmentalProfileForPlace,
  vintageObservationForPlace,
  type AuthorityVintageRating,
  type EnvironmentalProfile,
  type VintageObservation,
} from './environment';
import {
  ageingArchetype,
  ageingRulesForDesignation,
  modelBottleAge,
  type AgeingArchetype,
  type BottleAgeResult,
} from './ageing';
import type { WineDefinition, WineProfile } from './types';

const MODEL_CURRENT_YEAR = 2026;

function xmur3(value: string) {
  let h = 1779033703 ^ value.length;
  for (let i = 0; i < value.length; i += 1) {
    h = Math.imul(h ^ value.charCodeAt(i), 3432918353;
    h = h << 13 | h >>> 19;
  }
  return () => {
    h = Math.imul(h ^ h >>> 16, 2246822507);
    h = Math.imul(h ^ h >>> 13, 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}

function mulberry32(seed: number) {
  return () => {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function rng(seed: string) {
  return mulberry32(xmur3(seed)());
}

function pick<T>(items: T[], random: () => number): T {
  return items[Math.floor(random() * items.length)];
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

const producerLexicon: Record<string, { prefixes: string[]; families: string[]; places: string[] }> = {
  France: { prefixes: ['Domaine', 'Château', 'Maison', 'Clos'], families: ['Martin', 'Morel', 'Garnier', 'Lenoir', 'Vidal', 'Mercier', 'Perron', 'Faure'], places: ['des Aulnes', 'du Coteau', 'de la Pierre', 'des Ormes'] },
  Italy: { prefixes: ['Tenuta', 'Podere', 'Azienda', 'Cascina'], families: ['Benedetti', 'Rinaldi', 'Fontana', 'Serafini', 'Gatti', 'Martelli', 'Bellandi', 'Ferrante'], places: ['del Colle', 'della Quercia', 'di Pietra', 'Valverde'] },
  Spain: { prefixes: ['Bodega', 'Viñedos', 'Finca', 'Dominio'], families: ['Serrano', 'Montalvo', 'Rueda', 'Carrasco', 'Ibarra', 'Salcedo', 'Varela', 'Ortega'], places: ['del Alto', 'de la Peña', 'del Camino', 'del Roble'] },
  Portugal: { prefixes: ['Quinta', 'Herdade', 'Casa', 'Adega'], families: ['Ferreira', 'Moura', 'Pacheco', 'Barros', 'Tavares', 'Macedo', 'Neves', 'Coelho'], places: ['da Fonte', 'do Vale', 'da Pedra', 'do Pinhal'] },
  Germany: { prefixes: ['Weingut', 'Schloss', 'Gut'], families: ['Keller', 'Vogel', 'Bergmann', 'Kramer', 'Dietrich', 'Reuter', 'Seifert', 'Baumann'], places: ['Sonnenberg', 'Steinweg', 'Falkenhof', 'Alte Reben'] },
  Austria: { prefixes: ['Weingut', 'Gut', 'Hof'], families: ['Gruber', 'Hofer', 'Leitner', 'Pichler', 'Wimmer', 'Eder', 'Mayr', 'Koller'], places: ['Stein', 'Höhe', 'Terrassen', 'Alte Reben'] },
  'United States': { prefixes: ['', 'Estate', 'Cellars'], families: ['Alder', 'Canyon', 'Redwood', 'Madrone', 'Juniper', 'Stonebridge', 'North Fork', 'High Meadow'], places: ['Ridge', 'Creek', 'Bench', 'Hill'] },
  Australia: { prefixes: ['', 'Estate', 'Wines'], families: ['Ironbark', 'Mallee', 'Stringybark', 'Red Gum', 'Sandstone', 'Long Paddock', 'Wattle', 'Dry Creek'], places: ['Hill', 'Range', 'Vale', 'Ridge'] },
  'New Zealand': { prefixes: ['', 'Estate', 'Vineyards'], families: ['Kauri', 'Tussock', 'Rimu', 'Southern Cross', 'Greywacke', 'Harbour', 'Kōwhai', 'Long Cloud'], places: ['Hill', 'Terrace', 'Valley', 'Ridge'] },
};

const genericLexicon = { prefixes: ['', 'Estate', 'Cellars', 'Vineyards'], families: ['North Star', 'Stone Field', 'High Ridge', 'Old Road', 'River Bend', 'Blue Hill', 'Long Valley', 'Three Pines'], places: ['Estate', 'Cellars', 'Vineyard', 'Wines'] };

function producerName(country: string, random: () => number): string {
  const lexicon = producerLexicon[country] ?? genericLexicon;
  const prefix = pick(lexicon.prefixes, random);
  const family = pick(lexicon.families, random);
  const place = pick(lexicon.places, random);
  const mode = Math.floor(random() * 3);
  return mode === 0 ? [prefix, family].filter(Boolean).join(' ') : mode === 1 ? [prefix, place].filter(Boolean).join(' ') : [family, place].filter(Boolean).join(' ');
}

function validatedGrapesForPlace(place: ReferencePlace): RawGrape[] {
  const resolved = [...place.primaryGrapes, ...place.authorizedGrapes]
    .map(findGrape)
    .filter((grape): grape is RawGrape => Boolean(grape))
    .filter((grape) => placeAllowsGrape(place, grape.name));
  return [...new Map(resolved.map((grape) => [grape.name, grape])).values()];
}

const usablePlaces = referenceAppellations.filter((place) => validatedGrapesForPlace(place).length > 0);

function grapeForPlace(place: ReferencePlace, random: () => number): RawGrape | undefined {
  const candidates = validatedGrapesForPlace(place);
  return candidates.length ? pick(candidates, random) : undefined;
}

function alcohol(profile: RawGrape['typical_profile']): number | undefined {
  const range = profile?.alcohol_range;
  if (Array.isArray(range) && range.length >= 2) return (range[0] + range[1]) / 2;
  if (range && !Array.isArray(range)) {
    const min = typeof range.min === 'number' ? range.min : undefined;
    const max = typeof range.max === 'number' ? range.max : undefined;
    if (min !== undefined && max !== undefined) return (min + max) / 2;
  }
  return undefined;
}

function profileFor(grape: RawGrape, random: () => number): WineProfile {
  const source = grape.typical_profile ?? {};
  const jitter = () => (random() - 0.5) * 0.35;
  return {
    acidity: clamp((source.acidity ?? 3) + jitter(), 1, 5),
    tannin: clamp((source.tannin ?? 1.5) + jitter(), 0.5, 5),
    body: clamp((source.body ?? 3) + jitter(), 1, 5),
    sweetness: clamp((source.sweetness ?? 1) + jitter() * 0.35, 0.5, 5),
    fruitIntensity: clamp((source.fruit_intensity ?? 3) + jitter(), 1, 5),
    earthIntensity: clamp((source.earth_intensity ?? 2) + jitter(), 0.5, 5),
    alcohol: alcohol(source),
  };
}

function vintageHorizon(archetype: AgeingArchetype, grape: RawGrape): number {
  const byStyle: Record<AgeingArchetype, number> = {
    'fresh-aromatic-white': 30,
    'structured-white': 70,
    'structured-red': 90,
    'light-red': 55,
    'traditional-sparkling': 100,
    'sweet-botrytis': 150,
    'oxidative-fortified': 220,
    'bottle-aged-fortified': 170,
    'biological-flor': 60,
    'oxidative-flor-derived': 130,
    'amber-skin-contact': 80,
    neutral: 55,
  };
  const potential = grape.aging_potential?.toLowerCase() ?? '';
  const grapeFloor = potential.includes('exception') ? 90 : potential.includes('excellent') ? 65 : potential.includes('good') ? 40 : 25;
  return Math.max(byStyle[archetype], grapeFloor);
}

function vintageFor(place: ReferencePlace, grape: RawGrape, random: () => number): number {
  const latestCommercialVintage = 2025;
  const archetype = ageingArchetype(place.country, [place.name, ...place.path].join(' / '), grape.color);
  const horizon = vintageHorizon(archetype, grape);
  const archivalTail = random() < 0.035 && horizon >= 80;
  const age = archivalTail
    ? Math.floor(horizon * (0.55 + random() * 0.45))
    : Math.floor(Math.pow(random(), 2.8) * horizon);
  return latestCommercialVintage - age;
}

function soilNames(environment?: EnvironmentalProfile): string[] {
  if (!environment) return [];
  return environment.soils
    .map((soil) => typeof soil.name === 'string' ? soil.name : '')
    .filter(Boolean);
}

function growingSeasonNote(
  vintage: number,
  environment?: EnvironmentalProfile,
  observation?: VintageObservation,
  authorityRating?: AuthorityVintageRating,
): string {
  if (observation) {
    const effects = observation.styleEffects?.slice(0, 3).join('; ');
    return `Source-backed ${vintage} growing-season record loaded for ${observation.region}.${effects ? ` Expected style implications: ${effects}.` : ''} Numeric vintage effects are simulation-derived from the sourced observations, not an official quality score.`;
  }
  if (authorityRating) {
    return `Official ${authorityRating.region} vintage classification for ${vintage}: ${authorityRating.rating}. The category is preserved as published and is not converted into a fabricated numeric quality score.`;
  }
  if (environment) {
    return `No source-backed year-specific growing-season record is loaded for ${vintage}. The profile uses sourced ${environment.name} climate, geology and soil context at the place layer only; historical weather is not invented.`;
  }
  return 'No source-backed year-specific growing-season record is loaded for this bottle. Bottle age is modeled without inventing historical weather.';
}

function generatedNotes(
  place: ReferencePlace,
  grape: RawGrape,
  vintage: number,
  aromas: string[],
  age: BottleAgeResult,
  environment?: EnvironmentalProfile,
  observation?: VintageObservation,
  authorityRating?: AuthorityVintageRating,
): WineDefinition['notes'] {
  const soils = soilNames(environment);
  const matrixContext = environment
    ? ` Research model includes the sourced ${environment.name} place layer${soils.length ? ` (${soils.slice(0, 3).join(', ')})` : ''}${observation ? ` plus the sourced ${vintage} vintage layer` : ''}.`
    : observation ? ` Research model includes a sourced ${vintage} regional vintage layer.` : '';
  const ageingRules = ageingRulesForDesignation(place.name);
  const ageingSummary = ageingRules.length
    ? `Sourced current ageing rules exist for: ${ageingRules.map((rule) => rule.productLevel).join(', ')}. This fictional bottle is not asserted to qualify for a specific level unless the product-generation layer explicitly selects and validates it.`
    : 'No designation-specific legal ageing rule is currently attached to this generated product.';
  const historicalIdentity = vintage < 1936
    ? `The ${vintage} harvest predates many modern GI/AOC systems. The displayed place is a modern geographic reference/equivalent; the engine does not assert that today's designation law or label wording applied in ${vintage}.`
    : `The engine keeps modern designation identity separate from historical legal-version research. Current rules are not silently projected backward into ${vintage}.`;

  return {
    identity: `${vintage} ${grape.name} from ${place.country} / ${place.path.join(' / ')}. Geography and grape identity come from the curated reference layer; producer and cuvée are fictional.`,
    growingSeason: growingSeasonNote(vintage, environment, observation, authorityRating),
    tasting: `${aromas.slice(0, 6).join(', ')}; structure starts from the curated reference profile for ${grape.name}.${matrixContext} Bottle-age evolution is then applied as a separate simulation layer.`,
    service: age.serviceFlags.length ? `Age-aware service: ${age.serviceFlags.join('; ')}.` : 'Serve according to structural weight, temperature, age, and sediment risk.',
    cellar: grape.aging_potential ? `Reference aging potential: ${grape.aging_potential}. Bottle phase: ${age.phase} at ${age.yearsSinceVintage} years.${observation ? ` Vintage ageability modifier: ${observation.matrixModifiers.ageability >= 0 ? '+' : ''}${observation.matrixModifiers.ageability.toFixed(2)} (simulation-derived).` : ''}` : `Bottle phase: ${age.phase} at ${age.yearsSinceVintage} years.`,
    pairing: grape.food_affinities?.length ? `Reference affinities include ${grape.food_affinities.slice(0, 4).join(', ')}.` : 'Pairing is scored from acidity, tannin, body, sweetness, aromatic bridges, preparation, sauce, and guest preference.',
    ageEvolution: `${age.explanation} Emerging age-linked notes: ${age.emergingAromas.join(', ')}.${age.fadingAromas.length ? ` Receding primary families: ${age.fadingAromas.join(', ')}.` : ''}`,
    legalAgeing: ageingSummary,
    historicalIdentity,
  };
}

export function generateWine(seed: string): WineDefinition {
  const random = rng(seed);
  if (!usablePlaces.length) throw new Error('Reference geography contains no appellations with normalized grape identities.');
  const place = pick(usablePlaces, random);
  const grape = grapeForPlace(place, random);
  if (!grape) throw new Error(`Could not generate a normalized grape for ${place.name}.`);
  const vintage = vintageFor(place, grape, random);
  const producer = producerName(place.country, random);
  // Old-vine terminology is no longer assigned randomly. It requires a documented/simulated vine-age record and jurisdictional rule.
  const cuvees = ['Tradition', 'Reserve', 'Selection', 'Estate', 'Parcelle', 'Classico', 'Single Vineyard'];
  const cuvee = pick(cuvees, random);
  const environment = environmentalProfileForPlace(place);
  const vintageObservation = vintageObservationForPlace(place, vintage);
  const authorityRating = authorityVintageRatingForPlace(place, vintage);
  const archetype = ageingArchetype(place.country, [place.name, ...place.path].join(' / '), grape.color);
  const storageQuality = clamp(0.82 + random() * 0.17 - Math.max(0, MODEL_CURRENT_YEAR - vintage - 60) * 0.0005, 0.55, 0.99);
  const placeVintageProfile = applyResearchMatrices(profileFor(grape, random), environment, vintageObservation);
  const age = modelBottleAge(placeVintageProfile, vintage, MODEL_CURRENT_YEAR, archetype, storageQuality);
  const aromas = [...new Set([
    ...(age.phase === 'youth' ? grape.primary_aromas ?? [] : []),
    ...(grape.secondary_aromas ?? []),
    ...(age.phase !== 'youth' ? grape.tertiary_aromas ?? [] : []),
    ...age.emergingAromas,
  ])].slice(0, 10);
  const prestigeBase = place.priceTier === 'ultra_luxury' ? 88 : place.priceTier === 'luxury' ? 80 : place.priceTier === 'premium' ? 70 : place.priceTier === 'budget' ? 42 : 58;
  const archiveBonus = clamp(age.yearsSinceVintage / 8, 0, 18);
  const prestige = Math.round(clamp(prestigeBase + archiveBonus + (random() - 0.5) * 18, 25, 99));
  const scarcityMultiplier = 1 + clamp(age.yearsSinceVintage / 50, 0, 4.5);
  const cost = Math.max(7, Math.round((9 + prestige * prestige * 0.009 * (0.75 + random() * 0.65)) * scarcityMultiplier));
  const suggestedPrice = Math.max(cost + 12, Math.round(cost * (2.1 + random() * 1.1)));
  const vineyard = place.kind === 'vineyard' ? place.name : undefined;
  const appellation = place.kind !== 'region' ? place.name : undefined;
  const vintageYieldFactor = vintageObservation ? clamp(1 + vintageObservation.matrixModifiers.yield * 0.25, 0.75, 1.25) : 1;
  const survivalFactor = clamp(1 - age.yearsSinceVintage / 260, 0.08, 1);
  const productionCases = Math.max(1, Math.round((15000 * Math.pow(1 - prestige / 110, 2) + random() * 600) * vintageYieldFactor * survivalFactor));
  const ageingRuleIds = ageingRulesForDesignation(place.name).map((rule) => rule.id);

  return {
    id: `world-${seed}`,
    label: `${producer} ${cuvee}`,
    producer,
    cuvee,
    grape: grape.name,
    region: place.path[0] ?? place.name,
    appellation,
    vineyard,
    country: place.country,
    vintage,
    classification: place.classification ?? place.classificationTiers[0],
    color: grape.color,
    style: `${grape.color ?? 'wine'} / style pending product-rule resolution`,
    cost,
    suggestedPrice,
    prestige,
    rarity: Math.round(clamp(25 + prestige * 0.65 + random() * 20 + age.yearsSinceVintage * 0.08, 1, 100)),
    productionCases,
    profile: age.profile,
    aromas,
    notes: generatedNotes(place, grape, vintage, aromas, age, environment, vintageObservation, authorityRating),
    story: `${producer} is a fictional producer generated inside the real reference framework of ${place.country} / ${place.path.join(' / ')}.`,
    fictional: true,
    dataConfidence: 'derived',
    referencePath: [place.country, ...place.path],
    agePhase: age.phase,
    ageYears: age.yearsSinceVintage,
    storageQuality,
    legalAgeingRuleIds: ageingRuleIds,
  };
}

export function generateWineBook(seed: string, count = 10000): WineDefinition[] {
  const wines: WineDefinition[] = [];
  const signatures = new Set<string>();
  for (let i = 0; wines.length < count && i < count * 4; i += 1) {
    const wine = generateWine(`${seed}-${i}`);
    const signature = `${wine.country}|${wine.referencePath?.join('|')}|${wine.grape}|${wine.producer}|${wine.vintage}|${wine.cuvee}`;
    if (!signatures.has(signature)) {
      signatures.add(signature);
      wines.push(wine);
    }
  }
  return wines;
}

export function validateGeneratedWine(wine: WineDefinition): boolean {
  if (!wine.referencePath?.length) return false;
  const path = wine.referencePath.slice(1);
  const place = referenceAppellations.find((candidate) => candidate.country === wine.country && candidate.path.join('|') === path.join('|'));
  return Boolean(place && findGrape(wine.grape) && placeAllowsGrape(place, wine.grape));
}
