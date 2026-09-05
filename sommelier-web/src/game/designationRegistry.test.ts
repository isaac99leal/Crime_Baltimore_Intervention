import { describe, expect, it } from 'vitest';
import {
  designationsForCountry,
  expandedDesignationPassCount,
  expandedDesignationRecords,
  findExpandedDesignation,
  validateExpandedDesignationRegistry,
} from './designationRegistry';

describe('expanded authority designation registry', () => {
  it('locks the authority registry tranches to their researched sizes', () => {
    const report = validateExpandedDesignationRegistry();
    expect(expandedDesignationPassCount).toBe(2);
    expect(expandedDesignationRecords).toHaveLength(407);
    expect(report.countsByCountry.Australia).toBe(114);
    expect(report.countsByCountry.Argentina).toBe(121);
    expect(report.countsByCountry.Georgia).toBe(32);
    expect(report.countsByCountry['New Zealand']).toBe(22);
    expect(report.countsByCountry.Chile).toBe(118);
    expect(report.issues).toEqual([]);
  });

  it('preserves Australian legal hierarchy instead of flattening regions and subregions', () => {
    expect(findExpandedDesignation('Australia', 'High Eden')[0]?.parent).toBe('Eden Valley');
    expect(findExpandedDesignation('Australia', 'Great Western')[0]?.parent).toBe('Grampians');
    expect(findExpandedDesignation('Australia', 'Swan Valley')[0]?.parent).toBe('Swan District');
  });

  it('preserves current Chilean region-subregion-zone-area hierarchy', () => {
    expect(findExpandedDesignation('Chile', 'Valle del Cachapoal')[0]?.parent).toBe('Valle del Rapel');
    expect(findExpandedDesignation('Chile', 'Apalta')[0]?.parent).toBe('Valle de Colchagua');
    expect(findExpandedDesignation('Chile', 'Colbún')[0]?.parent).toBe('Valle del Loncomilla');
    expect(findExpandedDesignation('Chile', 'Traiguén')[0]?.parent).toBe('Valle del Malleco');
    expect(findExpandedDesignation('Chile', 'Chiloé')[0]?.parent).toBe('Región Vitícola Austral');
  });

  it('preserves same-name Argentine origins when jurisdiction or legal class differs', () => {
    expect(findExpandedDesignation('Argentina', 'Luján de Cuyo')).toHaveLength(2);
    expect(new Set(findExpandedDesignation('Argentina', 'Luján de Cuyo').map((record) => record.legalClass))).toEqual(new Set(['IG', 'DOC']));
    expect(findExpandedDesignation('Argentina', 'Rivadavia')).toHaveLength(2);
  });

  it('keeps every registry identity reference-only until product rules are separately researched', () => {
    for (const country of ['Georgia', 'New Zealand', 'Chile']) {
      expect(designationsForCountry(country).every((record) => record.generationStatus === 'reference-only')).toBe(true);
    }
  });
});
