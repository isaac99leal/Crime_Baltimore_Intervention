import { describe, expect, it } from 'vitest';
import {
  archiveHasYear,
  findHistoricalVintageArchive,
  historicalVintageArchivePassCount,
  historicalVintageEvidence,
  validateHistoricalVintageArchives,
} from './vintageArchive';

describe('historical vintage evidence ledger', () => {
  it('supports centuries-deep multi-pass authority archives without fabricating missing years', () => {
    const report = validateHistoricalVintageArchives();
    const port = findHistoricalVintageArchive('archive-pt-vintage-port-1756-2017');
    expect(historicalVintageArchivePassCount).toBe(2);
    expect(report.archives).toBeGreaterThanOrEqual(4);
    expect(report.documentedYears).toBeGreaterThanOrEqual(140);
    expect(report.earliestDocumentedYear).toBe(1756);
    expect(port?.earliestYear).toBe(1756);
    expect(port?.latestYear).toBe(2017);
    expect(report.issues).toEqual([]);
  });

  it('distinguishes documented authority years from unknown years', () => {
    const port = findHistoricalVintageArchive('archive-pt-vintage-port-1756-2017');
    expect(port && archiveHasYear(port, 1756)).toBe(true);
    expect(port && archiveHasYear(port, 1815)).toBe(true);
    expect(port && archiveHasYear(port, 1963)).toBe(true);
    expect(historicalVintageEvidence('archive-pt-vintage-port-1756-2017', 1878)).toBe('authority-archive-detail-available');
    expect(historicalVintageEvidence('archive-pt-vintage-port-1756-2017', 1879)).toBe('unknown');
  });

  it('keeps a monitoring-system claim weaker than an ingested annual record', () => {
    expect(historicalVintageEvidence('archive-fr-champagne-matu-monitoring-1956-present', 1988)).toBe('monitoring-system-confirmed-detail-not-yet-ingested');
    expect(historicalVintageEvidence('archive-fr-champagne-matu-monitoring-1956-present', 1955)).toBe('unknown');
  });

  it('includes the complete Ontario authority vintage-report sequence currently published', () => {
    const ontario = findHistoricalVintageArchive('archive-ca-ontario-vintage-reports-2001-2025');
    expect(ontario?.years).toHaveLength(25);
    expect(ontario?.years[0]).toBe(2001);
    expect(ontario?.years[ontario.years.length - 1]).toBe(2025);
  });

  it('adds the SAWIS South African harvest-report sequence without treating national reports as ward weather', () => {
    const southAfrica = findHistoricalVintageArchive('archive-za-harvest-reports-2002-2026');
    expect(southAfrica?.years).toHaveLength(25);
    expect(southAfrica?.years[0]).toBe(2002);
    expect(southAfrica?.years[southAfrica.years.length - 1]).toBe(2026);
    expect(historicalVintageEvidence('archive-za-harvest-reports-2002-2026', 2012)).toBe('authority-report-available');
    expect(southAfrica?.historicalIdentityNote).toContain('must not be applied uniformly');
  });
});
