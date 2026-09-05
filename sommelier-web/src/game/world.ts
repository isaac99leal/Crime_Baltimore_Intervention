import { findGrape, placeAllowsGrape, referenceAppellations, type RawGrape, type ReferencePlace } from './reference';
import type { WineDefinition, WineProfile } from './types';

function xmur3(value: string) {
  let h = 1779033703 ^ value.length;
  for (let i = 0; i < value.length; i += 1) {
    h = Math.imul(h ^ value.charCodeAt(i), 3432918353);
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

function vintageFor(grape: RawGrape, random: () => number): number {
  const current = 2025;
  const potential = grape.aging_potential?.toLowerCase() ?? '';
  const maxAge = potential.includes('exception') ? 45 : potential.includes('excellent') ? 30 : potential.includes('good') ? 20 : 12;
  return current - Math.floor(random() * maxAge);
}

function generatedNotes(place: ReferencePlace, grape: RawGrape, vintage: number, aromas: string[]): WineDefinition['notes'] {
  return {
    identity: `${vintage} ${grape.name} from ${place.country} / ${place.path.join(' / ')}. Geography and grape identity come from the curated reference layer; producer and cuvée are fictional.`,
    growingSeason: 'Vintage-specific weather detail is not asserted unless a curated historical vintage record exists. The game currently models bottle age without inventing historical weather.',
    tasting: `${aromas.slice(0, 4).join(', ')}; structure follows the reference profile for ${grape.name}.`,
    service: 'Serve according to structural weight, temperature, age, and sediment risk; detailed service rules are resolved by the simulation engine.',
    cellar: grape.aging_potential ? `Reference aging potential: ${grape.aging_potential}.` : 'Cellaring potential is evaluated from structure and bottle condition.',
    pairing: grape.food_affinities?.length ? `Reference affinities include ${grape.food_affinities.slice(0, 4).join(', ')}.` : 'Pairing is scored from acidity, tannin, body, sweetness, aromatic bridges, preparation, sauce, and guest preference.',
  };
}

export function generateWine(seed: string): WineDefinition {
  const random = rng(seed);
  if (!usablePlaces.length) throw new Error('Reference geography contains no appellations with normalized grape identities.');
  const place = pick(usablePlaces, random);
  const grape = grapeForPlace(place, random);
  if (!grape) throw new Error(`Could not generate a normalized grape for ${place.name}.`);
  const vintage = vintageFor(grape, random);
  const producer = producerName(place.country, random);
  const cuvees = ['Tradition', 'Vieilles Vignes', 'Reserve', 'Selection', 'Estate', 'Parcelle', 'Classico', 'Single Vineyard'];
  const cuvee = pick(cuvees, random);
  const profile = profileFor(grape, random);
  const aromas = [...new Set([...(grape.primary_aromas ?? []), ...(grape.secondary_aromas ?? []), ...(vintage < 2012 ? grape.tertiary_aromas ?? [] : [])])].slice(0, 7);
  const prestigeBase = place.priceTier === 'ultra_luxury' ? 88 : place.priceTier === 'luxury' ? 80 : place.priceTier === 'premium' ? 70 : place.priceTier === 'budget' ? 42 : 58;
  const prestige = Math.round(clamp(prestigeBase + (random() - 0.5) * 18, 25, 98));
  const cost = Math.max(7, Math.round(9 + prestige * prestige * 0.009 * (0.75 + random() * 0.65)));
  const suggestedPrice = Math.max(cost + 12, Math.round(cost * (2.1 + random() * 1.1)));
  const vineyard = place.kind === 'vineyard' ? place.name : undefined;
  const appellation = place.kind !== 'region' ? place.name : undefined;

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
    style: `${grape.color ?? 'wine'} / still`,
    cost,
    suggestedPrice,
    prestige,
    rarity: Math.round(clamp(25 + prestige * 0.65 + random() * 20, 1, 100)),
    productionCases: Math.max(80, Math.round(15000 * Math.pow(1 - prestige / 110, 2) + random() * 600)),
    profile,
    aromas,
    notes: generatedNotes(place, grape, vintage, aromas),
    story: `${producer} is a fictional producer generated inside the real reference framework of ${place.country} / ${place.path.join(' / ')}.`,
    fictional: true,
    dataConfidence: 'derived',
    referencePath: [place.country, ...place.path],
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
