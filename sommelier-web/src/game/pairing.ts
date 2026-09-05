import pairingData from '../data/food_pairings.json';
import type { Dish, WineDefinition } from './types';

type PairRule = {
  ideal_wine_attributes?: Record<string, number[]>;
  ideal_grapes?: string[];
  avoid_grapes?: string[];
  notes?: string;
};

type Modifier = {
  body_bonus?: number;
  tannin_bonus?: number;
  tannin_penalty?: number;
  acidity_bonus?: number;
  acidity_need?: number;
  fruit_bonus?: number;
  earth_bonus?: number;
  sweetness_bonus?: number;
  notes?: string;
};

type RawMenuItem = {
  name: string;
  course: string;
  primary_protein: string;
  cooking_method: string;
  sauce: string;
  flavor_profile: string;
  weight: string;
  pairing_keywords: string[];
};

type Bridge = {
  found_in_wines: string[];
  found_in_foods: string[];
  effect: string;
};

type PairingData = {
  protein_pairings: Record<string, PairRule>;
  cooking_method_modifiers: Record<string, Modifier>;
  sauce_modifiers: Record<string, Modifier>;
  flavor_bridges?: { bridges?: Record<string, Bridge> };
  menu_items: RawMenuItem[];
};

const data = pairingData as PairingData;

export const menuDishes: Dish[] = data.menu_items.map((item) => ({
  name: item.name,
  pairingKey: item.primary_protein,
  course: item.course,
  cookingMethod: item.cooking_method,
  sauce: item.sauce,
  flavorProfile: item.flavor_profile,
  weight: item.weight,
  pairingKeywords: item.pairing_keywords,
  detail: [item.cooking_method, item.sauce && item.sauce.replaceAll('_', ' '), item.flavor_profile, `${item.weight} weight`]
    .filter(Boolean)
    .join(' · '),
}));

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

function profileValue(wine: WineDefinition, key: string): number | undefined {
  const map: Record<string, keyof WineDefinition['profile']> = {
    acidity: 'acidity',
    tannin: 'tannin',
    body: 'body',
    sweetness: 'sweetness',
    fruit_intensity: 'fruitIntensity',
    earth_intensity: 'earthIntensity',
  };
  const mapped = map[key];
  return mapped ? wine.profile[mapped] : undefined;
}

function structuralFit(wine: WineDefinition, rule: PairRule): number {
  const entries = Object.entries(rule.ideal_wine_attributes ?? {});
  if (!entries.length) return 11;
  let total = 0;
  let count = 0;
  for (const [key, range] of entries) {
    if (range.length < 2) continue;
    const value = profileValue(wine, key);
    if (typeof value !== 'number') continue;
    const [min, max] = range;
    const distance = value < min ? min - value : value > max ? value - max : 0;
    total += clamp(1 - distance / 2.2, 0, 1);
    count += 1;
  }
  return count ? (total / count) * 22 : 11;
}

function modifierContribution(wine: WineDefinition, modifier: Modifier | undefined): number {
  if (!modifier) return 0;
  const centered = (value: number) => (value - 3) / 2;
  return (
    (modifier.body_bonus ?? 0) * centered(wine.profile.body) * 5 +
    (modifier.tannin_bonus ?? 0) * centered(wine.profile.tannin) * 5 +
    (modifier.tannin_penalty ?? 0) * centered(wine.profile.tannin) * 6 +
    (modifier.acidity_bonus ?? 0) * centered(wine.profile.acidity) * 5 +
    (modifier.acidity_need ?? 0) * centered(wine.profile.acidity) * 6 +
    (modifier.fruit_bonus ?? 0) * centered(wine.profile.fruitIntensity) * 5 +
    (modifier.earth_bonus ?? 0) * centered(wine.profile.earthIntensity) * 5 +
    (modifier.sweetness_bonus ?? 0) * centered(wine.profile.sweetness) * 6
  );
}

function termMatchesWine(wine: WineDefinition, term: string): boolean {
  const needle = term.toLowerCase();
  const fields = [wine.grape, wine.region, wine.appellation, wine.vineyard, wine.classification, wine.style, wine.label]
    .filter((value): value is string => Boolean(value))
    .map((value) => value.toLowerCase());
  return fields.some((field) => field === needle || field.includes(needle) || needle.includes(field));
}

function weightFit(wine: WineDefinition, weight: string | undefined): number {
  const target = weight === 'light' ? 2 : weight === 'heavy' ? 4.25 : 3.15;
  return clamp(8 - Math.abs(wine.profile.body - target) * 3, 0, 8);
}

function aromaticBridgeScore(wine: WineDefinition, dish: Dish): { score: number; notes: string[] } {
  const bridges = data.flavor_bridges?.bridges ?? {};
  const foodText = [dish.name, dish.detail, dish.flavorProfile, ...(dish.pairingKeywords ?? [])].filter(Boolean).join(' ').toLowerCase();
  let score = 0;
  const notes: string[] = [];
  for (const bridge of Object.values(bridges)) {
    const wineMatch = bridge.found_in_wines.some((term) => termMatchesWine(wine, term));
    const foodMatch = bridge.found_in_foods.some((term) => foodText.includes(term.toLowerCase()));
    if (wineMatch && foodMatch) {
      score += 4;
      if (notes.length < 2) notes.push(bridge.effect);
    }
  }
  return { score: Math.min(score, 8), notes };
}

export function scorePairing(wine: WineDefinition, dish: Dish): { score: number; breakdown: string[] } {
  const rule = data.protein_pairings[dish.pairingKey] ?? {};
  const method = dish.cookingMethod ? data.cooking_method_modifiers[dish.cookingMethod] : undefined;
  const sauce = dish.sauce ? data.sauce_modifiers[dish.sauce] : undefined;
  const bridge = aromaticBridgeScore(wine, dish);

  let score = 28 + structuralFit(wine, rule) + weightFit(wine, dish.weight);
  const idealMatch = rule.ideal_grapes?.some((term) => termMatchesWine(wine, term)) ?? false;
  const avoidMatch = rule.avoid_grapes?.some((term) => termMatchesWine(wine, term)) ?? false;
  if (idealMatch) score += 15;
  if (avoidMatch) score -= 22;
  score += modifierContribution(wine, method);
  score += modifierContribution(wine, sauce);
  score += bridge.score;

  const breakdown: string[] = [];
  if (rule.notes) breakdown.push(rule.notes);
  if (method?.notes) breakdown.push(`${dish.cookingMethod}: ${method.notes}`);
  if (sauce?.notes) breakdown.push(`${dish.sauce?.replaceAll('_', ' ')}: ${sauce.notes}`);
  breakdown.push(...bridge.notes);
  if (idealMatch) breakdown.push(`${wine.grape} or its wine style is specifically favored for this food category.`);
  if (avoidMatch) breakdown.push(`${wine.grape} or its wine style is a known risk for this food category.`);

  return { score: Math.round(clamp(score, 0, 76)), breakdown: breakdown.slice(0, 5) };
}
