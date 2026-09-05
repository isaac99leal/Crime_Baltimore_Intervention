import { describe, expect, it } from 'vitest';
import {
  findRareCultivar,
  historicalVarietyResearchQueue,
  rareCultivarQueuePolicy,
  validateRareCultivarResearch,
} from './rareCultivarResearch';

describe('rare and historically eroded cultivar research', () => {
  it('preserves deep rare-cultivar profiles and a larger identity research queue', () => {
    const report = validateRareCultivarResearch();
    expect(report.detailedProfiles).toBeGreaterThanOrEqual(3);
    expect(report.queueRegions).toBeGreaterThanOrEqual(5);
    expect(report.queuedNames).toBeGreaterThanOrEqual(30);
    expect(report.issues).toEqual([]);
  });

  it('records historical scarcity without converting it into a current planting claim', () => {
    const kisi = findRareCultivar('Kisi');
    const ojaleshi = findRareCultivar('Ojaleshi');
    expect(String(kisi?.historicalStatus.summary)).toContain('nearly extinct');
    expect((ojaleshi?.historicalStatus.publishedSnapshot as Record<string, unknown>)?.year).toBe(2004);
    expect((ojaleshi?.historicalStatus.publishedSnapshot as Record<string, unknown>)?.areaHa).toBe(141);
  });

  it('retains extreme low-yield observations without generalizing them', () => {
    const jani = findRareCultivar('Jani');
    expect((jani?.viticulture as Record<string, unknown>)?.yieldTonnesPerHaOfficialRange).toEqual([2.2, 3.5]);
    expect(jani?.generationStatus).toBe('reference-only');
  });

  it('keeps official historical variety names as a normalization queue rather than fabricated aliases', () => {
    const abkhazia = historicalVarietyResearchQueue.find((group) => group.region === 'Abkhazia');
    expect(abkhazia?.names).toContain('Avasikhva');
    expect(abkhazia?.names).toContain('Khunaliji');
    expect(rareCultivarQueuePolicy.toLowerCase()).toContain('does not establish');
  });
});
