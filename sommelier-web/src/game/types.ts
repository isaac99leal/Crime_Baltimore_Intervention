export type DataConfidence = 'curated' | 'derived';

export type WineProfile = {
  acidity: number;
  tannin: number;
  body: number;
  sweetness: number;
  fruitIntensity: number;
  earthIntensity: number;
  alcohol?: number;
};

export type WineNotes = {
  identity: string;
  growingSeason: string;
  tasting: string;
  service: string;
  cellar: string;
  pairing: string;
  ageEvolution?: string;
  legalAgeing?: string;
  historicalIdentity?: string;
  winemaking?: string;
};

export type WineDefinition = {
  id: string;
  label: string;
  producer?: string;
  cuvee?: string;
  grape: string;
  blend?: { grape: string; percent: number }[];
  region: string;
  appellation?: string;
  vineyard?: string;
  country: string;
  vintage?: number;
  classification?: string;
  color?: string;
  style?: string;
  farming?: string;
  elevage?: string;
  cost: number;
  suggestedPrice: number;
  prestige: number;
  rarity?: number;
  productionCases?: number;
  profile: WineProfile;
  aromas: string[];
  notes?: WineNotes;
  drinkingWindow?: [number, number];
  story: string;
  fictional?: boolean;
  dataConfidence?: DataConfidence;
  referencePath?: string[];
  agePhase?: string;
  ageYears?: number;
  storageQuality?: number;
  legalAgeingRuleIds?: string[];
};

export type StorageZone = 'service-cellar' | 'reserve-cellar' | 'offsite' | 'bar' | 'quarantine';

export type InventoryItem = {
  wineId: string;
  bottles: number;
  listed: boolean;
  listPrice: number;
  lotId?: string;
  bin?: string;
  storageZone?: StorageZone;
  receivedWeek?: number;
  condition?: number;
  par?: number;
  offMenu?: boolean;
  btg?: boolean;
  btgPrice?: number;
  btgPourMl?: number;
  openBottleMl?: number;
};

export type SupplierRelationship = {
  id: string;
  name: string;
  specialty: string;
  relationship: number;
  reliability: number;
  exclusivity: number;
  paymentTermsDays: number;
  allocationAccess: number;
  lastContactWeek: number;
  notes: string[];
};

export type AllocationOffer = {
  id: string;
  supplierId: string;
  wineId: string;
  bottles: number;
  unitCost: number;
  expiresWeek: number;
  minRelationship: number;
  prestige: number;
  mustTake?: string[];
};

export type StaffRole = 'sommelier' | 'captain' | 'server' | 'bartender' | 'cellar-assistant';

export type StaffMember = {
  id: string;
  name: string;
  role: StaffRole;
  wage: number;
  wineKnowledge: number;
  service: number;
  sales: number;
  morale: number;
  trainingHours: number;
};

export type EquipmentItem = {
  id: string;
  name: string;
  category: 'storage' | 'service' | 'preservation' | 'software' | 'training';
  level: number;
  maxLevel: number;
  baseCost: number;
  maintenance: number;
  benefit: string;
};

export type CertificationTrack = {
  id: string;
  school: string;
  title: string;
  level: number;
  maxLevel: number;
  progress: number;
  examFee: number;
  studyHoursRequired: number;
  reputationBonus: number;
  earningMultiplier: number;
};

export type RestaurantState = {
  name: string;
  concept: string;
  seats: number;
  managementTrust: number;
  beverageTarget: number;
  rentShare: number;
  storageCapacity: number;
  offsiteCapacity: number;
};

export type WineListState = {
  revision: number;
  dirty: boolean;
  lastPrintedWeek: number;
  pages: number;
  reprintSpend: number;
  philosophy: string;
};

export type TimeLedger = {
  available: number;
  committed: number;
  service: number;
  admin: number;
  study: number;
  relationships: number;
  training: number;
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
  btgSales: number;
  cogs: number;
  shrinkage: number;
  restaurant: RestaurantState;
  wineList: WineListState;
  suppliers: SupplierRelationship[];
  allocations: AllocationOffer[];
  staff: StaffMember[];
  equipment: EquipmentItem[];
  certifications: CertificationTrack[];
  time: TimeLedger;
};

export type Guest = {
  id: string;
  name: string;
  description: string;
  budget: number;
  preferredRegions: string[];
  hint: string;
  adventure: number;
  patience?: number;
  wineKnowledge?: number;
  occasion?: string;
  requestedStyle?: string;
};

export type Dish = {
  name: string;
  pairingKey: string;
  detail: string;
  course?: string;
  cookingMethod?: string;
  sauce?: string;
  flavorProfile?: string;
  weight?: 'light' | 'medium' | 'heavy' | string;
  pairingKeywords?: string[];
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
  pairingScore?: number;
  breakdown?: string[];
};

export type TastingChallenge = {
  wine: WineDefinition;
  options: string[];
};
