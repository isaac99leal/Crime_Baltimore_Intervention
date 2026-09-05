import guestData from '../data/guest_archetypes.json';
import pairingData from '../data/food_pairings.json';
import { wineById, wineCatalog } from './catalog';
import type {
  Dish,
  GameState,
  Guest,
  ServiceResult,
  ServiceScenario,
  TastingChallenge,
  WineDefinition,
} from './types';

type GuestArchetype = {
  id: string;
  name: string;
  description: string;
  price_ceiling: number[];
  adventure_level: number[];
  preferred_regions: string[];
  conversation_hints: string[];
  frequency: number;
};

type PairRule = {
  ideal_wine_attributes?: Record<string, number[]>;
  ideal_grapes?: string[];
  avoid_grapes?: string[];
  notes?: string;
};

const archetypes = (guestData as { archetypes: GuestArchetype[] }).archetypes;
const rules = (pairingData as { protein_pairings: Record<string, PairRule> }).protein_pairings;

const dishes: Dish[] = [
  { name: 'Dry-aged ribeye', pairingKey: 'beef', detail: 'Charred crust, bordelaise, pommes fondant' },
  { name: 'Roast lamb saddle', pairingKey: 'lamb', detail: 'Rosemary, garlic, olive jus' },
  { name: 'Duck breast', pairingKey: 'duck', detail: 'Sour cherry, black pepper, turnip' },
  { name: 'Butter-poached halibut', pairingKey: 'fish_white', detail: 'Leek, beurre blanc, chive' },
  { name: 'King salmon', pairingKey: 'fish_rich', detail: 'Miso glaze, sesame, charred scallion' },
  { name: 'Oysters on the half shell', pairingKey: 'shellfish', detail: 'Mignonette, cucumber, sea herbs' },
  { name: 'Wild mushroom risotto', pairingKey: 'mushroom', detail: 'Porcini, parmesan, thyme' },
  { name: 'Herb-roasted chicken', pairingKey: 'poultry', detail: 'Morels, jus, spring peas' },
];

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const randomFrom = <T,>(items: T[]): T => items[Math.floor(Math.random() * items.length)];
const randomBetween = (min: number, max: number) => min + Math.random() * (max - min);

function numericRange(values: number[] | undefined, fallback: [number, number]): [number, number] {
  if (!values || values.length < 2) return fallback;
  return [values[0], values[1]];
}

export function createInitialGame(): GameState {
  return {
    week: 1,
    cash: 12000,
    reputation: 50,
    knowledge: 1,
    xp: 0,
    inventory: wineCatalog.slice(0, 8).map((wine, index) => ({
      wineId: wine.id,
      bottles: index < 4 ? 6 : 3,
      listed: true,
      listPrice: wine.suggestedPrice,
    })),
    serviceCount: 0,
    lifetimeRevenue: 0,
    tastingCorrect: 0,
    tastingTotal: 0,
  };
}

export function buyWine(state: GameState, wineId: string, quantity = 3): GameState {
  const wine = wineById.get(wineId);
  if (!wine || quantity <= 0) return state;
  const totalCost = wine.cost * quantity;
  if (state.cash < totalCost) return state;
  const current = state.inventory.find((item) => item.wineId === wineId);
  const inventory = current
    ? state.inventory.map((item) => item.wineId === wineId ? { ...item, bottles: item.bottles + quantity } : item)
    : [...state.inventory, { wineId, bottles: quantity, listed: false, listPrice: wine.suggestedPrice }];
  return { ...state, cash: state.cash - totalCost, inventory };
}

export function toggleListing(state: GameState, wineId: string): GameState {
  return {
    ...state,
    inventory: state.inventory.map((item) => item.wineId === wineId ? { ...item, listed: !item.listed } : item),
  };
}

export function changePrice(state: GameState, wineId: string, delta: number): GameState {
  return {
    ...state,
    inventory: state.inventory.map((item) => item.wineId === wineId
      ? { ...item, listPrice: Math.max(10, Math.round(item.listPrice + delta)) }
      : item),
  };
}

function pickArchetype(): GuestArchetype {
  const total = archetypes.reduce((sum, item) => sum + item.frequency, 0);
  let roll = Math.random() * total;
  for (const item of archetypes) {
    roll -= item.frequency;
    if (roll <= 0) return item;
  }
  return archetypes[archetypes.length - 1];
}

export function generateServiceScenario(): ServiceScenario {
  const archetype = pickArchetype();
  const [budgetMin, budgetMax] = numericRange(archetype.price_ceiling, [60, 250]);
  const [adventureMin, adventureMax] = numericRange(archetype.adventure_level, [0.3, 0.6]);
  const ceiling = randomBetween(budgetMin, budgetMax);
  const guest: Guest = {
    id: `${archetype.id}-${Date.now()}-${Math.random()}`,
    name: archetype.name,
    description: archetype.description,
    budget: Math.max(35, Math.round(ceiling)),
    preferredRegions: archetype.preferred_regions,
    hint: randomFrom(archetype.conversation_hints),
    adventure: randomBetween(adventureMin, adventureMax),
  };
  return { guest, dish: randomFrom(dishes) };
}

function profileValueForRule(wine: WineDefinition, ruleKey: string): number | undefined {
  const map: Record<string, keyof WineDefinition['profile']> = {
    acidity: 'acidity',
    tannin: 'tannin',
    body: 'body',
    sweetness: 'sweetness',
    fruit_intensity: 'fruitIntensity',
    earth_intensity: 'earthIntensity',
  };
  const profileKey = map[ruleKey];
  return profileKey ? wine.profile[profileKey] : undefined;
}

function attributeFit(wine: WineDefinition, rule: PairRule): number {
  const entries = Object.entries(rule.ideal_wine_attributes ?? {});
  if (!entries.length) return 0;
  const matches = entries.filter(([name, range]) => {
    if (range.length < 2) return false;
    const value = profileValueForRule(wine, name);
    return typeof value === 'number' && value >= range[0] && value <= range[1];
  }).length;
  return (matches / entries.length) * 22;
}

export function recommendWine(state: GameState, scenario: ServiceScenario, wineId: string): { state: GameState; result: ServiceResult } {
  const item = state.inventory.find((candidate) => candidate.wineId === wineId);
  const wine = wineById.get(wineId);
  if (!item || !wine || item.bottles <= 0 || !item.listed) {
    return {
      state,
      result: { score: 0, revenue: 0, tip: 0, reputationDelta: -1, summary: 'That bottle is not available on the active list.' },
    };
  }

  const rule = rules[scenario.dish.pairingKey] ?? {};
  let score = 34 + attributeFit(wine, rule);
  if (rule.ideal_grapes?.includes(wine.grape)) score += 27;
  if (rule.avoid_grapes?.includes(wine.grape)) score -= 32;
  if (scenario.guest.preferredRegions.some((region) => [wine.region, wine.country].includes(region))) score += 10;
  if (item.listPrice <= scenario.guest.budget) score += 12;
  else score -= Math.min(35, ((item.listPrice - scenario.guest.budget) / scenario.guest.budget) * 45);
  if (scenario.guest.adventure > 0.7 && wine.prestige < 70) score += 6;
  score = Math.round(clamp(score, 0, 100));

  const tipRate = 0.06 + (score / 100) * 0.12;
  const tip = Math.round(item.listPrice * tipRate);
  const revenue = item.listPrice + tip;
  const reputationDelta = score >= 85 ? 2 : score >= 68 ? 1 : score < 45 ? -2 : 0;
  const summary = score >= 85
    ? 'Exceptional match. The table trusts you and remembers the recommendation.'
    : score >= 68
      ? 'Strong service. The pairing works and the guest is satisfied.'
      : score >= 45
        ? 'Acceptable, but the recommendation missed part of the brief.'
        : 'Poor fit. Revisit the dish, budget, and guest cues before choosing.';

  const nextState: GameState = {
    ...state,
    cash: state.cash + revenue,
    reputation: clamp(state.reputation + reputationDelta, 0, 100),
    xp: state.xp + Math.max(1, Math.round(score / 12)),
    serviceCount: state.serviceCount + 1,
    lifetimeRevenue: state.lifetimeRevenue + revenue,
    inventory: state.inventory.map((candidate) => candidate.wineId === wineId
      ? { ...candidate, bottles: candidate.bottles - 1 }
      : candidate),
  };
  return { state: nextState, result: { score, revenue, tip, reputationDelta, summary } };
}

export function advanceWeek(state: GameState): { state: GameState; overhead: number } {
  const overhead = 1300 + (state.week - 1) * 80;
  const cash = state.cash - overhead;
  return {
    overhead,
    state: {
      ...state,
      week: state.week + 1,
      cash,
      reputation: clamp(state.reputation + (cash < 0 ? -4 : 0), 0, 100),
    },
  };
}

export function makeTastingChallenge(): TastingChallenge {
  const wine = randomFrom(wineCatalog);
  const otherGrapes = wineCatalog.map((item) => item.grape).filter((grape) => grape !== wine.grape);
  const options = [wine.grape];
  while (options.length < 4) {
    const candidate = randomFrom(otherGrapes);
    if (!options.includes(candidate)) options.push(candidate);
  }
  options.sort(() => Math.random() - 0.5);
  return { wine, options };
}

export function resolveTasting(state: GameState, challenge: TastingChallenge, answer: string): { state: GameState; correct: boolean } {
  const correct = answer === challenge.wine.grape;
  return {
    correct,
    state: {
      ...state,
      tastingTotal: state.tastingTotal + 1,
      tastingCorrect: state.tastingCorrect + (correct ? 1 : 0),
      knowledge: state.knowledge + (correct ? 0.18 : 0.04),
      xp: state.xp + (correct ? 12 : 3),
    },
  };
}
