export type WineProfile = {
  acidity: number;
  tannin: number;
  body: number;
  sweetness: number;
  fruitIntensity: number;
  earthIntensity: number;
};

export type WineDefinition = {
  id: string;
  label: string;
  grape: string;
  region: string;
  country: string;
  cost: number;
  suggestedPrice: number;
  prestige: number;
  profile: WineProfile;
  aromas: string[];
  story: string;
};

export type InventoryItem = {
  wineId: string;
  bottles: number;
  listed: boolean;
  listPrice: number;
};

export type GameState = {
  week: number;
  cash: number;
  reputation: number;
  knowledge: number;
  xp: number;
  inventory: InventoryItem[];
  serviceCount: number;
  lifetimeRevenue: number;
  tastingCorrect: number;
  tastingTotal: number;
};

export type Guest = {
  id: string;
  name: string;
  description: string;
  budget: number;
  preferredRegions: string[];
  hint: string;
  adventure: number;
};

export type Dish = {
  name: string;
  pairingKey: string;
  detail: string;
};

export type ServiceScenario = {
  guest: Guest;
  dish: Dish;
};

export type ServiceResult = {
  score: number;
  revenue: number;
  tip: number;
  reputationDelta: number;
  summary: string;
};

export type TastingChallenge = {
  wine: WineDefinition;
  options: string[];
};
