import { wineById } from './catalog';
import type { GameState, InventoryItem, StorageZone, WineDefinition } from './types';

export type BottleConditionAssessment = {
  derived: true;
  weeklyConditionLoss: number;
  storageProtection: number;
  ageVulnerability: number;
  historicalStoragePenalty: number;
  evidenceRefs: string[];
  notes: string[];
};

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));

function coolingLevel(state: GameState): number {
  return state.equipment.find((item) => item.id === 'cellar-cooling')?.level ?? 0;
}

function zoneProtection(zone: StorageZone | undefined, cooling: number): number {
  if (zone === 'reserve-cellar') return clamp01(0.955 + cooling * 0.008);
  if (zone === 'service-cellar') return clamp01(0.925 + cooling * 0.011);
  if (zone === 'offsite') return 0.965;
  if (zone === 'quarantine') return 0.90;
  if (zone === 'bar') return 0.80;
  return 0.90;
}

export function assessBottleCondition(
  state: GameState,
  item: InventoryItem,
  wine: WineDefinition,
): BottleConditionAssessment {
  const protection = zoneProtection(item.storageZone, coolingLevel(state));
  const ageYears = Math.max(0, wine.ageYears ?? (wine.vintage ? 2026 - wine.vintage : 0));
  const ageVulnerability = clamp01((ageYears - 8) / 42);
  const historicalStoragePenalty = clamp01(1 - (wine.storageQuality ?? 0.96));
  const zoneExposure = 1 - protection;

  // This is a bounded operational simulation transform, not a prediction of bottle failure.
  // Poor storage matters more as bottles age; prior storage history adds a smaller independent penalty.
  const weeklyConditionLoss = Math.max(0.005,
    0.008
      + zoneExposure * 0.16
      + historicalStoragePenalty * 0.045
      + ageVulnerability * zoneExposure * 0.24,
  );

  const notes: string[] = [];
  if (item.storageZone === 'bar') notes.push('Bar storage carries the highest sealed-bottle exposure in the current restaurant model.');
  if (ageVulnerability > 0.55) notes.push('Mature-bottle vulnerability amplifies poor-storage effects.');
  if (historicalStoragePenalty > 0.15) notes.push('Pre-acquisition storage quality contributes an independent condition penalty.');

  return {
    derived: true,
    weeklyConditionLoss,
    storageProtection: protection,
    ageVulnerability,
    historicalStoragePenalty,
    evidenceRefs: ['premox-review-2021', 'wine-aging-capacity-review-2021', 'awri-closure-trial-2026'],
    notes,
  };
}

export function ageInventoryConditionOneWeek(state: GameState): { inventory: InventoryItem[]; totalConditionLoss: number; quarantined: number } {
  let totalConditionLoss = 0;
  let quarantined = 0;

  const inventory = state.inventory.map((item) => {
    const wine = wineById.get(item.wineId);
    if (!wine || item.bottles <= 0) return item;
    const assessment = assessBottleCondition(state, item, wine);
    const current = item.condition ?? 100;
    const nextCondition = Math.max(0, current - assessment.weeklyConditionLoss);
    totalConditionLoss += current - nextCondition;

    if (nextCondition <= 35 && item.storageZone !== 'quarantine') {
      quarantined += 1;
      return {
        ...item,
        condition: nextCondition,
        storageZone: 'quarantine' as const,
        listed: false,
        offMenu: true,
        btg: false,
      };
    }

    return { ...item, condition: nextCondition };
  });

  return { inventory, totalConditionLoss, quarantined };
}
