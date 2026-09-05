import { describe, expect, it } from 'vitest';
import { createInitialGame } from './engine';
import { createStaffBtgBlindChallenge, simulateStaffBtgBlindTasting } from './staffBlindTasting';

describe('staff BTG blind-tasting training', () => {
  it('builds a blind challenge only from an actual BTG bottle in inventory', () => {
    const state = createInitialGame();
    const btg = state.inventory.find((item) => item.btg);
    const nonBtg = state.inventory.find((item) => !item.btg);
    expect(btg).toBeTruthy();
    const challenge = btg && createStaffBtgBlindChallenge(state, 'maya', btg.wineId);
    expect(challenge).toBeTruthy();
    expect(challenge?.options).toHaveLength(4);
    expect(challenge?.options).toContain(challenge?.correctOption);
    expect(challenge?.clues.length).toBeGreaterThanOrEqual(2);
    expect(nonBtg && createStaffBtgBlindChallenge(state, 'maya', nonBtg.wineId)).toBeUndefined();
  });

  it('uses staff knowledge and training to change blind-tasting success probability', () => {
    const base = createInitialGame();
    const btg = base.inventory.find((item) => item.btg)!;
    const novice = {
      ...base,
      staff: base.staff.map((person) => person.id === 'maya' ? { ...person, wineKnowledge: 20, service: 50, trainingHours: 0 } : person),
    };
    const expert = {
      ...base,
      staff: base.staff.map((person) => person.id === 'maya' ? { ...person, wineKnowledge: 90, service: 85, trainingHours: 80 } : person),
    };
    const noviceResult = simulateStaffBtgBlindTasting(novice, 'maya', btg.wineId);
    const expertResult = simulateStaffBtgBlindTasting(expert, 'maya', btg.wineId);
    expect(expertResult?.chancePct ?? 0).toBeGreaterThan(noviceResult?.chancePct ?? 100);
  });

  it('consumes training time and creates learning from the actual BTG drill', () => {
    const state = createInitialGame();
    const btg = state.inventory.find((item) => item.btg)!;
    const before = state.staff.find((person) => person.id === 'jonah')!;
    const result = simulateStaffBtgBlindTasting(state, 'jonah', btg.wineId)!;
    const after = result.state.staff.find((person) => person.id === 'jonah')!;
    expect(result.state.time.training).toBe(state.time.training + 1.5);
    expect(result.state.time.committed).toBe(state.time.committed + 1.5);
    expect(after.trainingHours).toBe(before.trainingHours + 1.5);
    expect(after.wineKnowledge).toBeGreaterThan(before.wineKnowledge);
    expect(result.learningGain).toBeGreaterThan(0);
  });

  it('refuses to award staff training when the weekly time budget is exhausted', () => {
    const base = createInitialGame();
    const btg = base.inventory.find((item) => item.btg)!;
    const state = { ...base, time: { ...base.time, committed: base.time.available } };
    expect(simulateStaffBtgBlindTasting(state, 'maya', btg.wineId)).toBeUndefined();
  });

  it('is deterministic for the same week, staff state and BTG bottle', () => {
    const state = createInitialGame();
    const btg = state.inventory.find((item) => item.btg)!;
    const a = simulateStaffBtgBlindTasting(state, 'ines', btg.wineId)!;
    const b = simulateStaffBtgBlindTasting(state, 'ines', btg.wineId)!;
    expect(a.rollPct).toBe(b.rollPct);
    expect(a.correct).toBe(b.correct);
    expect(a.selectedOption).toBe(b.selectedOption);
  });
});
