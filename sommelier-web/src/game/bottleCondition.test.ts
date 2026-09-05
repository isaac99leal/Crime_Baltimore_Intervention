import { describe, expect, it } from 'vitest';
import { ageInventoryConditionOneWeek, assessBottleCondition } from './bottleCondition';
import { wineById } from './catalog';
import { createInitialGame } from './engine';

describe('sealed bottle condition ageing', () => {
  it('penalizes poor bar storage more than a well-cooled reserve cellar', () => {
    const base = createInitialGame();
    const item = base.inventory[0];
    const wine = wineById.get(item.wineId)!;
    const boosted = {
      ...base,
      equipment: base.equipment.map((entry) => entry.id === 'cellar-cooling' ? { ...entry, level: 5 } : entry),
    };
    const reserve = assessBottleCondition(boosted, { ...item, storageZone: 'reserve-cellar' }, { ...wine, ageYears: 28 });
    const bar = assessBottleCondition(boosted, { ...item, storageZone: 'bar' }, { ...wine, ageYears: 28 });
    expect(reserve.storageProtection).toBeGreaterThan(bar.storageProtection);
    expect(reserve.weeklyConditionLoss).toBeLessThan(bar.weeklyConditionLoss);
  });

  it('makes mature bottles more sensitive to the same weak storage environment', () => {
    const state = createInitialGame();
    const item = { ...state.inventory[0], storageZone: 'bar' as const };
    const wine = wineById.get(item.wineId)!;
    const young = assessBottleCondition(state, item, { ...wine, ageYears: 3 });
    const mature = assessBottleCondition(state, item, { ...wine, ageYears: 45 });
    expect(mature.ageVulnerability).toBeGreaterThan(young.ageVulnerability);
    expect(mature.weeklyConditionLoss).toBeGreaterThan(young.weeklyConditionLoss);
  });

  it('quarantines badly compromised stock instead of silently leaving it on the list', () => {
    const base = createInitialGame();
    const target = base.inventory[0];
    const state = {
      ...base,
      inventory: base.inventory.map((item) => item.wineId === target.wineId ? { ...item, condition: 35.01, listed: true, btg: true, storageZone: 'bar' as const } : item),
    };
    const result = ageInventoryConditionOneWeek(state);
    const after = result.inventory.find((item) => item.wineId === target.wineId)!;
    expect(after.condition ?? 100).toBeLessThanOrEqual(35);
    expect(after.storageZone).toBe('quarantine');
    expect(after.listed).toBe(false);
    expect(after.btg).toBe(false);
    expect(result.quarantined).toBe(1);
  });
});
