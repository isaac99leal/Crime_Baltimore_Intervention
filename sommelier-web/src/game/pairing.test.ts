import { describe, expect, it } from 'vitest';
import { wineById } from './catalog';
import { scorePairing } from './pairing';

const cab = wineById.get('left-bank-cab')!;
const albarino = wineById.get('rias-albarino')!;

describe('detailed pairing engine', () => {
  it('rewards structure, cooking method, and sauce for grilled beef', () => {
    const beef = scorePairing(cab, {
      name: 'Côte de Boeuf with Bordelaise',
      pairingKey: 'beef',
      detail: 'grilled · bordelaise · heavy weight',
      cookingMethod: 'grilled',
      sauce: 'bordelaise',
      weight: 'heavy',
      pairingKeywords: ['charred', 'rich'],
    });
    const oyster = scorePairing(cab, {
      name: 'Oysters on the Half Shell',
      pairingKey: 'shellfish',
      detail: 'raw · saline · light weight',
      cookingMethod: 'raw',
      weight: 'light',
      pairingKeywords: ['saline', 'citrus'],
    });
    expect(beef.score).toBeGreaterThan(oyster.score + 20);
  });

  it('prefers a crisp white to Cabernet for raw shellfish', () => {
    const dish = {
      name: 'Oysters on the Half Shell',
      pairingKey: 'shellfish',
      detail: 'raw · saline · citrus',
      cookingMethod: 'raw',
      weight: 'light',
      pairingKeywords: ['mineral', 'saline', 'citrus'],
    };
    expect(scorePairing(albarino, dish).score).toBeGreaterThan(scorePairing(cab, dish).score);
  });
});
