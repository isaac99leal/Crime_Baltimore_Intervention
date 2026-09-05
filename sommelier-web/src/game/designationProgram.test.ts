import { describe, expect, it } from 'vitest';
import {
  coverageForCountry,
  designationCoverage,
  globalDesignationGoal,
  liveDesignationIndexCounts,
  pendingDesignationCountries,
  requiredDesignationRecordDepth,
  validateDesignationProgram,
} from './designationProgram';

describe('global wine designation coverage program', () => {
  it('accounts for every verified planting country, including unresolved jurisdictions', () => {
    const report = validateDesignationProgram();
    expect(designationCoverage).toHaveLength(60);
    expect(report.verifiedPlantingCountries).toBe(60);
    expect(report.sourceIdentifiedCountries).toBeGreaterThanOrEqual(25);
    expect(report.pendingCountries).toBeGreaterThan(0);
    expect(report.issues).toEqual([]);
  });

  it('does not pretend authority discovery is the same thing as a live complete index', () => {
    expect(coverageForCountry('United States')?.ingestionStatus).toBe('live-index');
    expect(coverageForCountry('France')?.ingestionStatus).toBe('live-index');
    expect(coverageForCountry('Argentina')?.ingestionStatus).toBe('authority-identified');
    expect(coverageForCountry('Australia')?.ingestionStatus).toBe('authority-identified');
    expect(pendingDesignationCountries.length).toBeGreaterThan(0);
  });

  it('keeps the already-normalized EU and US registry counts intact', () => {
    expect(liveDesignationIndexCounts.eambrosiaWineGis).toBe(1665);
    expect(liveDesignationIndexCounts.ttbAvas).toBe(280);
  });

  it('makes exhaustive depth part of the data contract, not an informal roadmap', () => {
    expect(globalDesignationGoal.toLowerCase()).toContain('every legally recognized');
    expect(requiredDesignationRecordDepth).toContain('historical legal version applicable to each vintage');
    expect(requiredDesignationRecordDepth).toContain('old-vine/vine-age rules if any');
    expect(requiredDesignationRecordDepth).toContain('winemaking practices required/permitted/prohibited');
    expect(requiredDesignationRecordDepth.length).toBeGreaterThanOrEqual(20);
  });
});
