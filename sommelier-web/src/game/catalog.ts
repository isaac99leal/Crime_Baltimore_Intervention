import grapesData from '../data/grapes.json';
import { generateWineBook } from './world';
import type { WineDefinition } from './types';

type RawGrape = {
  name: string;
  origin_country?: string;
  origin_region?: string;
  typical_profile?: {
    acidity?: number;
    tannin?: number;
    body?: number;
    sweetness?: number;
    fruit_intensity?: number;
    earth_intensity?: number;
  };
  primary_aromas?: string[];
  secondary_aromas?: string[];
  fun_fact?: string;
};

const rawGrapes = (grapesData as { grapes: RawGrape[] }).grapes;
const byName = new Map(rawGrapes.map((grape) => [grape.name, grape]));

const bottleSpecs = [
  ['left-bank-cab', 'Château Beaumont Reserve', 'Cabernet Sauvignon', 'Bordeaux', 'France', 38, 105, 78],
  ['willamette-pinot', 'Eola Hills Selection', 'Pinot Noir', 'Willamette Valley', 'United States', 31, 88, 70],
  ['chablis-chard', 'Mont de Milieu', 'Chardonnay', 'Chablis', 'France', 29, 82, 73],
  ['mosel-riesling', 'Slate & River Kabinett', 'Riesling', 'Mosel', 'Germany', 18, 58, 61],
  ['barolo-nebbiolo', 'Serralunga Classico', 'Nebbiolo', 'Barolo', 'Italy', 44, 125, 86],
  ['chianti-sangiovese', 'Radda Riserva', 'Sangiovese', 'Chianti Classico', 'Italy', 24, 72, 69],
  ['rioja-tempranillo', 'Haro Reserva', 'Tempranillo', 'Rioja', 'Spain', 22, 68, 68],
  ['rias-albarino', 'Salnés Albariño', 'Albariño', 'Rías Baixas', 'Spain', 16, 52, 57],
  ['santorini-assyrtiko', 'Volcanic Vines', 'Assyrtiko', 'Santorini', 'Greece', 21, 64, 65],
  ['beaujolais-gamay', 'Morgon Côte du Py', 'Gamay', 'Beaujolais', 'France', 19, 60, 63],
  ['loire-chenin', 'Savennieres Sec', 'Chenin Blanc', 'Loire', 'France', 23, 69, 67],
  ['rhone-syrah', 'Crozes-Hermitage', 'Syrah', 'Rhône', 'France', 25, 74, 71],
  ['marlborough-sb', 'Awatere Sauvignon', 'Sauvignon Blanc', 'Marlborough', 'New Zealand', 14, 46, 48],
  ['wachau-gruner', 'Federspiel Grüner', 'Grüner Veltliner', 'Wachau', 'Austria', 17, 54, 56],
] as const;

function profileValue(value: number | undefined, fallback: number) {
  return typeof value === 'number' ? value : fallback;
}

export const launchCatalog: WineDefinition[] = bottleSpecs.map(
  ([id, label, grapeName, region, country, cost, suggestedPrice, prestige]) => {
    const grape = byName.get(grapeName);
    const profile = grape?.typical_profile;
    return {
      id,
      label,
      grape: grapeName,
      region,
      country,
      cost,
      suggestedPrice,
      prestige,
      profile: {
        acidity: profileValue(profile?.acidity, 3),
        tannin: profileValue(profile?.tannin, 2.5),
        body: profileValue(profile?.body, 3),
        sweetness: profileValue(profile?.sweetness, 1),
        fruitIntensity: profileValue(profile?.fruit_intensity, 3),
        earthIntensity: profileValue(profile?.earth_intensity, 2),
      },
      aromas: [...(grape?.primary_aromas ?? []), ...(grape?.secondary_aromas ?? [])].slice(0, 5),
      story: grape?.fun_fact ?? `${grapeName} from ${region}.`,
      dataConfidence: 'curated',
    };
  },
);

// The commercial universe is generated deterministically from real reference geography and
// real grape identities. Producers/cuvées are fictional and explicitly marked as such.
export const worldWineBook = generateWineBook('sommelier-canonical-world-v1', 15000);
export const wineCatalog: WineDefinition[] = [...launchCatalog, ...worldWineBook];
export const wineById = new Map(wineCatalog.map((wine) => [wine.id, wine]));
