import { describe, expect, it } from 'vitest';
import { createInitialGame } from './engine';
import { reprintWineList, sellBtgPour, studyCertification, toggleBtg, trainStaff, workSupplierRelationship } from './systems';

describe('beverage program systems', () => {
  it('tracks BTG bottle depletion and revenue by pour', () => {
    const state = createInitialGame();
    const item = state.inventory.find((candidate) => candidate.btg)!;
    const before = item.bottles;
    const result = sellBtgPour(state, item.wineId);
    const after = result.state.inventory.find((candidate) => candidate.wineId === item.wineId)!;
    expect(result.revenue).toBeGreaterThan(0);
    expect(after.bottles).toBe(before - 1);
    expect(after.openBottleMl).toBe(600);
  });

  it('marks the wine list dirty and charges for a physical reprint', () => {
    const state = createInitialGame();
    const wineId = state.inventory[0].wineId;
    const changed = toggleBtg(state, wineId);
    expect(changed.wineList.dirty).toBe(true);
    const result = reprintWineList(changed);
    expect(result.cost).toBeGreaterThan(0);
    expect(result.state.wineList.dirty).toBe(false);
    expect(result.state.wineList.revision).toBe(2);
    expect(result.state.cash).toBeLessThan(changed.cash);
  });

  it('makes relationship, staff training, and study compete for finite time', () => {
    const state = createInitialGame();
    const supplier = workSupplierRelationship(state, state.suppliers[0].id);
    const trained = trainStaff(supplier, supplier.staff[0].id, 'wine');
    const studied = studyCertification(trained, trained.certifications[0].id, 4);
    expect(studied.time.relationships).toBe(3);
    expect(studied.time.training).toBe(4);
    expect(studied.time.study).toBe(4);
    expect(studied.time.committed).toBe(state.time.committed + 11);
  });
});
