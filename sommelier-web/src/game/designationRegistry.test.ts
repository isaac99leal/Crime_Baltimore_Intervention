import { describe, expect, it } from 'vitest';
import {
  designationsForCountry,
  expandedDesignationRecords,
  findExpandedDesignation,
  validateExpandedDesignationRegistry,
} from './designationRegistry';

describe('expanded authority designation registry', () => {
  it('locks the first four-country registry tranche to its authority-backed size', () => {
    const report = validateExpandedDesignationRegistry();
    expect(expandedDesignationRecords).toHaveLength(289);
    expect(report.countsByCountry.Australia).toBe(114);
    expect(report.countsByCountry.Argentina).toBe(121);
    expect(report.countsByCountry.Georgia).toBe(32);
    expect(report.countsByCountry['New Zealand']).toBe(22);
    expect(report.issues).toEqual([]);
  });

  it('preserves Australian legal hierarchy instead of flattening regions and subregions', () => {
    expect(findExpandedDesignation('Australia', 'High Eden')[0]?.parent).toBe('Eden Valley');
    expect(findExpandedDesignation('Australia', 'Great Western')[0]?.parent).toBe('Grampians');
    expect(findExpandedDesignation('Australia', 'Swan Valley')[0]?.parent).toBe('Swan District');
  });

  it('preserves same-name Argentine origins when jurisdiction or legal class differs', () => {
    expect(findExpandedDesignation('Argentina', 'Luján de Cuyo')).toHaveLength(2);
    expect(new Set(findExpandedDesignation('Argentina', 'Luján de Cuyo').map((record) => record.legalClass))).toEqual(new Set(['IG', 'DOC']));
    expect(findExpandedDesignation('Argentina', 'Rivadavia')).toHaveLength(2);
  });

  it('keeps every registry identity reference-only until product rules are separately researched', () => {
    expect(designationsForCountry('Georgia').every((record) => record.generationStatus === 'reference-only')).toBe(true);
    expect(designationsForCountry('New Zealand').every((record) => record.generationStatus === 'reference-only')).toBe(true);
  });
});
