import guestData from '../data/guest_archetypes.json';
import { ageInventoryConditionOneWeek } from './bottleCondition';
import { wineById, wineCatalog } from './catalog';
import { menuDishes, scorePairing } from './pairing';
import type {
  GameState,
  Guest,
  ServiceResult,
  ServiceScenario,
  TastingChallenge,
} from './types';

type GuestArchetype = {
  id: string;
  name: string;
  description: string;
  price_ceiling: number[];
  adventure_level: number[];
  wine_knowledge?: number[];
  patience?: number[];
  preferred_regions: string[];
  conversation_hints: string[];
  celebrations?: string[];
  frequency: number;
};

const archetypes = (guestData as { archetypes: GuestArchetype[] }).archetypes;
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
      lotId: `opening-${index + 1}`,
      bin: `A-${String(index + 1).padStart(2, '0')}`,
      storageZone: index < 6 ? 'service-cellar' : 'reserve-cellar',
      receivedWeek: 1,
      condition: 100,
      par: index < 4 ? 6 : 3,
      offMenu: false,
      btg: index === 3 || index === 7,
      btgPrice: Math.max(10, Math.round(wine.suggestedPrice / 4.2)),
      btgPourMl: 150,
      openBottleMl: 0,
    })),
    serviceCount: 0,
    lifetimeRevenue: 0,
    tastingCorrect: 0,
    tastingTotal: 0,
    btgSales: 0,
    cogs: 0,
    shrinkage: 0,
    restaurant: {
      name: 'Northline',
      concept: 'Seasonal contemporary dining',
      seats: 74,
      managementTrust: 55,
      beverageTarget: 0.31,
      rentShare: 0.08,
      storageCapacity: 850,
      offsiteCapacity: 600,
    },
    wineList: {
      revision: 1,
      dirty: false,
      lastPrintedWeek: 1,
      pages: 18,
      reprintSpend: 0,
      philosophy: 'Balanced classic and discovery list with disciplined pricing and useful depth.',
    },
    suppliers: [
      { id: 'north-coast-portfolio', name: 'North Coast Portfolio', specialty: 'France, Germany, grower Champagne', relationship: 38, reliability: 84, exclusivity: 42, paymentTermsDays: 30, allocationAccess: 22, lastContactWeek: 1, notes: ['Responds to clean depletion reports and steady placements.'] },
      { id: 'meridian-selections', name: 'Meridian Selections', specialty: 'Italy, Spain, Portugal', relationship: 46, reliability: 78, exclusivity: 35, paymentTermsDays: 30, allocationAccess: 28, lastContactWeek: 1, notes: ['Values staff education and producer dinner support.'] },
      { id: 'field-and-cellar', name: 'Field & Cellar', specialty: 'Domestic, emerging regions, small growers', relationship: 51, reliability: 73, exclusivity: 24, paymentTermsDays: 14, allocationAccess: 18, lastContactWeek: 1, notes: ['Flexible on mixed cases; limited quantities on cult wines.'] },
    ],
    allocations: [],
    staff: [
      { id: 'maya', name: 'Maya Chen', role: 'captain', wage: 23, wineKnowledge: 42, service: 78, sales: 64, morale: 74, trainingHours: 0 },
      { id: 'jonah', name: 'Jonah Reed', role: 'server', wage: 18, wineKnowledge: 31, service: 67, sales: 57, morale: 70, trainingHours: 0 },
      { id: 'ines', name: 'Inés Duarte', role: 'bartender', wage: 21, wineKnowledge: 48, service: 72, sales: 69, morale: 76, trainingHours: 0 },
    ],
    equipment: [
      { id: 'cellar-cooling', name: 'Cellar cooling and monitoring', category: 'storage', level: 1, maxLevel: 5, baseCost: 900, maintenance: 28, benefit: 'Reduces storage risk and unlocks deeper long-term inventory.' },
      { id: 'preservation', name: 'BTG preservation system', category: 'preservation', level: 1, maxLevel: 5, baseCost: 650, maintenance: 18, benefit: 'Reduces open-bottle waste and supports more ambitious BTG selections.' },
      { id: 'service-kit', name: 'Service and decanting kit', category: 'service', level: 1, maxLevel: 4, baseCost: 320, maintenance: 8, benefit: 'Improves service consistency for fragile, mature, and sparkling bottles.' },
      { id: 'inventory-software', name: 'Inventory and list publishing system', category: 'software', level: 1, maxLevel: 4, baseCost: 480, maintenance: 14, benefit: 'Reduces admin time, bin errors, and menu/list mismatch.' },
    ],
    certifications: [
      { id: 'court-service', school: 'Court of Cellar & Service', title: 'Professional Service Diploma', level: 0, maxLevel: 4, progress: 0, examFee: 350, studyHoursRequired: 40, reputationBonus: 4, earningMultiplier: 1.04 },
      { id: 'wine-studies', school: 'Institute of Wine Studies', title: 'Wine Theory & Trade Diploma', level: 0, maxLevel: 4, progress: 0, examFee: 425, studyHoursRequired: 52, reputationBonus: 5, earningMultiplier: 1.05 },
    ],
    time: { available: 62, committed: 42, service: 38, admin: 4, study: 0, relationships: 0, training: 0 },
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
    : [...state.inventory, {
      wineId,
      bottles: quantity,
      listed: false,
      listPrice: wine.suggestedPrice,
      lotId: `week-${state.week}-${wineId}`,
      bin: `NEW-${state.week}`,
      storageZone: 'service-cellar' as const,
      receivedWeek: state.week,
      condition: 100,
      par: quantity,
      offMenu: true,
      btg: false,
      openBottleMl: 0,
    }];
  return { ...state, cash: state.cash - totalCost, cogs: state.cogs + totalCost, inventory };
}

export function toggleListing(state: GameState, wineId: string): GameState {
  return {
    ...state,
    wineList: { ...state.wineList, dirty: true },
    inventory: state.inventory.map((item) => item.wineId === wineId ? { ...item, listed: !item.listed, offMenu: item.listed } : item),
  };
}

export function changePrice(state: GameState, wineId: string, delta: number): GameState {
  return {
    ...state,
    wineList: { ...state.wineList, dirty: true },
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
  const [knowledgeMin, knowledgeMax] = numericRange(archetype.wine_knowledge, [0.2, 0.6]);
  const [patienceMin, patienceMax] = numericRange(archetype.patience, [0.4, 0.8]);
  const ceiling = randomBetween(budgetMin, budgetMax);
  const guest: Guest = {
    id: `${archetype.id}-${Date.now()}-${Math.random()}`,
    name: archetype.name,
    description: archetype.description,
    budget: Math.max(35, Math.round(ceiling)),
    preferredRegions: archetype.preferred_regions,
    hint: randomFrom(archetype.conversation_hints),
    adventure: randomBetween(adventureMin, adventureMax),
    wineKnowledge: randomBetween(knowledgeMin, knowledgeMax),
    patience: randomBetween(patienceMin, patienceMax),
    occasion: archetype.celebrations?.length ? randomFrom(archetype.celebrations) : undefined,
  };
  return { guest, dish: randomFrom(menuDishes) };
}

export function recommendWine(state: GameState, scenario: ServiceScenario, wineId: string): { state: GameState; result: ServiceResult } {
  const item = state.inventory.find((candidate) => candidate.wineId === wineId);
  const wine = wineById.get(wineId);
  if (!item || !wine || item.bottles <= 0 || !item.listed) {
    return {
      state,
      result: { score: 0, pairingScore: 0, revenue: 0, tip: 0, reputationDelta: -1, summary: 'That bottle is not available on the active list.', breakdown: ['Check physical stock, listing status, and the current published list.'] },
    };
  }

  const pairing = scorePairing(wine, scenario.dish);
  let score = pairing.score;
  if (scenario.guest.preferredRegions.some((region) => [wine.region, wine.country, wine.appellation].includes(region))) score += 8;
  if (item.listPrice <= scenario.guest.budget) score += 12;
  else score -= Math.min(35, ((item.listPrice - scenario.guest.budget) / scenario.guest.budget) * 45);
  if (scenario.guest.adventure > 0.7 && wine.prestige < 70) score += 5;
  if ((scenario.guest.wineKnowledge ?? 0) > 0.75 && wine.prestige > 78) score += 4;
  score = Math.round(clamp(score, 0, 100));

  const tipRate = 0.06 + (score / 100) * 0.12;
  const tip = Math.round(item.listPrice * tipRate);
  const revenue = item.listPrice + tip;
  const reputationDelta = score >= 85 ? 2 : score >= 68 ? 1 : score < 45 ? -2 : 0;
  const summary = score >= 85
    ? 'Exceptional match. The table trusts you and remembers the recommendation.'
    : score >= 68
      ? 'Strong service. The wine fits the dish, preparation, and guest brief.'
      : score >= 45
        ? 'Acceptable, but one or more structural, preparation, or guest factors are off.'
        : 'Poor fit. Revisit the dish, sauce, cooking method, budget, and guest cues.';

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
  return {
    state: nextState,
    result: {
      score,
      pairingScore: pairing.score,
      revenue,
      tip,
      reputationDelta,
      summary,
      breakdown: pairing.breakdown,
    },
  };
}

export function advanceWeek(state: GameState): { state: GameState; overhead: number } {
  const payroll = Math.round(state.staff.reduce((sum, member) => sum + member.wage * 28, 0));
  const maintenance = state.equipment.reduce((sum, item) => sum + item.maintenance * item.level, 0);
  const overhead = 900 + payroll + maintenance + Math.round((state.week - 1) * 55);
  const cash = state.cash - overhead;
  const bottleAgeing = ageInventoryConditionOneWeek(state);
  return {
    overhead,
    state: {
      ...state,
      week: state.week + 1,
      cash,
      reputation: clamp(state.reputation + (cash < 0 ? -4 : 0), 0, 100),
      inventory: bottleAgeing.inventory,
      wineList: bottleAgeing.quarantined > 0 ? { ...state.wineList, dirty: true } : state.wineList,
      restaurant: { ...state.restaurant, managementTrust: clamp(state.restaurant.managementTrust + (cash < 0 ? -3 : 0.4), 0, 100) },
      time: { available: 62, committed: 42, service: 38, admin: 4, study: 0, relationships: 0, training: 0 },
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
