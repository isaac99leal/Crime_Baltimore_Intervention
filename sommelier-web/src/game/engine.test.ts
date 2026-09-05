import { describe, expect, it } from 'vitest';
import { buyWine, changePrice, createInitialGame, recommendWine, resolveTasting, toggleListing } from './engine';
import { wineCatalog } from './catalog';

const scenario = {
  guest: {
    id: 'test',
    name: 'Test Guest',
    description: 'A guest',
    budget: 500,
    preferredRegions: ['Bordeaux'],
    hint: 'wants a classic pairing',
    adventure: 0.2,
  },
  dish: { name: 'Ribeye', pairingKey: 'beef', detail: 'grilled' },
};

describe('sommelier game engine', () => {
  it('buys wine and deducts wholesale cost', () => {
    const state = createInitialGame();
    const target = wineCatalog[10];
    const next = buyWine(state, target.id, 3);
    expect(next.cash).toBe(state.cash - target.cost * 3);
    expect(next.inventory.find((item) => item.wineId === target.id)?.bottles).toBeGreaterThanOrEqual(3);
  });

  it('can change price and listing state without mutating the original', () => {
    const state = createInitialGame();
    const id = state.inventory[0].wineId;
    const repriced = changePrice(state, id, 15);
    const toggled = toggleListing(repriced, id);
    expect(repriced).not.toBe(state);
    expect(repriced.inventory[0].listPrice).toBe(state.inventory[0].listPrice + 15);
    expect(toggled.inventory[0].listed).toBe(false);
  });

  it('consumes inventory and produces revenue during service', () => {
    const state = createInitialGame();
    const id = 'left-bank-cab';
    const before = state.inventory.find((item) => item.wineId === id)!;
    const outcome = recommendWine(state, scenario, id);
    const after = outcome.state.inventory.find((item) => item.wineId === id)!;
    expect(after.bottles).toBe(before.bottles - 1);
    expect(outcome.result.score).toBeGreaterThan(60);
    expect(outcome.state.cash).toBeGreaterThan(state.cash);
  });

  it('scores a correct blind tasting answer', () => {
    const state = createInitialGame();
    const wine = wineCatalog[0];
    const challenge = { wine, options: [wine.grape, 'Riesling', 'Gamay', 'Chardonnay'] };
    const result = resolveTasting(state, challenge, wine.grape);
    expect(result.correct).toBe(true);
    expect(result.state.tastingCorrect).toBe(1);
    expect(result.state.knowledge).toBeGreaterThan(state.knowledge);
  });
});
