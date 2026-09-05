import { describe, expect, it } from 'vitest';
import {
  commercialCultivarResearchQueue,
  countryCultivarGapCounts,
  countryCultivarResearchQueue,
  currentBearingCultivarsWithoutTradeTech,
  currentBearingCultivarsWithoutVintageContext,
  currentBearingCultivarsWithoutWineUse,
  currentCommercialCultivarResearchQueue,
  validateCommercialCultivarResearchQueue,
} from './commercialCultivarResearchQueue';

describe('long-tail commercial cultivar research prioritization', () => {
  it('turns the authority bearing-area universe into explicit research work rather than leaving the long tail invisible', () => {
    const report = validateCommercialCultivarResearchQueue();
    expect(report.globalQueue).toBeGreaterThan(1200);
    expect(report.currentBearingQueue).toBeGreaterThan(1000);
    expect(report.currentWithoutWineUse).toBeGreaterThan(500);
    expect(report.currentWithoutTradeTech).toBeGreaterThan(800);
    expect(report.currentWithoutVintageContext).toBeGreaterThan(800);
    expect(report.countryCultivarQueue).toBeGreaterThan(1000);
    expect(report.countries).toBeGreaterThan(30);
    expect(report.issues).toEqual([]);
  });

  it('does not call a statistically planted grape commercially corroborated until legal or trade wine evidence exists', () => {
    const shesh = currentCommercialCultivarResearchQueue.find((item) => item.cultivar === 'Shesh i Zi');
    expect(shesh).toBeDefined();
    if (shesh?.gaps.includes('no-commercial-wine-use-corroboration')) {
      expect(currentBearingCultivarsWithoutWineUse.some((item) => item.cultivar === 'Shesh i Zi')).toBe(true);
    }
  });

  it('removes the commercial-use gap when researched wine-use evidence exists while retaining other missing-depth gaps', () => {
    const nebbiolo = commercialCultivarResearchQueue.find((item) => item.cultivar === 'Nebbiolo');
    expect(nebbiolo?.gaps).not.toContain('no-commercial-wine-use-corroboration');
    expect(nebbiolo?.priorityScore).toBeGreaterThan(0);
  });

  it('preserves the massive technical and vintage research backlog even after the first importer passes', () => {
    expect(currentBearingCultivarsWithoutTradeTech.length).toBeGreaterThan(currentBearingCultivarsWithoutWineUse.length);
    expect(currentBearingCultivarsWithoutVintageContext.length).toBeGreaterThan(800);
  });

  it('prioritizes cultivation evidence separately by country rather than assuming evidence in one country transfers globally', () => {
    const argentina = countryCultivarGapCounts.Argentina;
    expect(argentina?.statisticallyObservedCultivars).toBeGreaterThan(20);
    expect(argentina?.withoutCountryTradeTech).toBeGreaterThan(0);
    expect(countryCultivarResearchQueue.some((item) => item.country === 'Albania' && item.cultivar === 'Shesh i Zi')).toBe(true);
  });
});
