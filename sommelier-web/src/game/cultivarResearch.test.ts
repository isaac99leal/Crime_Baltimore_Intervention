import { describe, expect, it } from 'vitest';
import { findCultivarResearch, germanPiwiRegistry, validateCultivarResearch } from './cultivarResearch';

describe('PIWI and obscure-cultivar research layer', () => {
  it('preserves the complete 2024 German declared PIWI production-cultivar list', () => {
    const report = validateCultivarResearch();
    expect(germanPiwiRegistry.cultivars).toHaveLength(36);
    expect(germanPiwiRegistry.totalProductionCultivars).toBe(119);
    expect(report.detailedProfiles).toBeGreaterThanOrEqual(7);
    expect(report.issues).toEqual([]);
  });

  it('preserves resistance loci instead of a generic resistant flag', () => {
    const regent = findCultivarResearch('Regent');
    const calardis = findCultivarResearch('Calardis Blanc');
    expect(regent?.resistance.loci?.downyMildew).toContain('Rpv3.1');
    expect(regent?.resistance.loci?.powderyMildew).toEqual(['Ren3', 'Ren9']);
    expect(calardis?.resistance.loci?.downyMildew).toEqual(['Rpv3.1', 'Rpv3.2']);
    expect(calardis?.resistance.loci?.blackRot).toContain('Rgb');
  });

  it('can represent a PIWI with weak resistance to one disease without contradiction', () => {
    const reberger = findCultivarResearch('Reberger');
    expect(reberger?.resistance.downyMildew).toBe('low');
    expect(reberger?.resistance.powderyMildew).toBe('medium-high');
  });

  it('keeps breeder trial observations reference-only rather than procedural legality', () => {
    for (const name of ['Regent', 'Calardis Blanc', 'Felicia', 'Phoenix', 'Villaris', 'Calandro', 'Reberger']) {
      expect(findCultivarResearch(name)?.generationStatus).toBe('reference-only');
    }
  });
});
