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
    expect(expandedDesignationPassCount).toBe(4);
    expect(expandedDesignationRecords).toHaveLength(589);
    expect(report.countsByCountry.Australia).toBe(114);
    expect(report.countsByCountry.Argentina).toBe(121);
    expect(report.countsByCountry.Georgia).toBe(32);
    expect(report.countsByCountry['New Zealand']).toBe(22);
    expect(report.countsByCountry.Chile).toBe(118);
    expect(report.countsByCountry['South Africa']).toBe(152);
    expect(report.countsByCountry.Japan).toBe(5);
    expect(report.countsByCountry.Moldova).toBe(5);
    expect(report.countsByCountry.Brazil).toBe(13);
    expect(report.countsByCountry['United Kingdom']).toBe(6);
    expect(report.countsByCountry.India).toBe(1);
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

  it('preserves the February 2026 South African WO hierarchy without carrying obsolete names forward', () => {
    expect(findExpandedDesignation('South Africa', 'Goukou River Valley')[0]?.parent).toBe('Still Bay');
    expect(findExpandedDesignation('South Africa', 'Still Bay')[0]?.parent).toBe('Cape South Coast');
    expect(findExpandedDesignation('South Africa', 'Cape South Coast')[0]?.parent).toBe('Cape Coast');
    expect(findExpandedDesignation('South Africa', 'Cape Coast')[0]?.parent).toBe('Western Cape');
    expect(findExpandedDesignation('South Africa', 'Shaw’s Mountain')[0]?.parent).toBe('Overberg');
    expect(findExpandedDesignation('South Africa', 'Keeromsberg')[0]?.parent).toBe('Worcester');
    expect(findExpandedDesignation('South Africa', 'Moordkuil')[0]?.parent).toBe('Worcester');
    expect(findExpandedDesignation('South Africa', 'Rooikrans')[0]?.parent).toBe('Worcester');
    expect(findExpandedDesignation('South Africa', 'Agter-Pakhuis')[0]?.parent).toBe('Olifants River');
    expect(findExpandedDesignation('South Africa', 'Rocklands Valley')[0]?.parent).toBe('Olifants River');
    expect(findExpandedDesignation('South Africa', 'Sutherland-Karoo')[0]?.parent).toBe('Karoo-Hoogland');
    expect(findExpandedDesignation('South Africa', 'Lanseria')[0]?.level).toBe('ward');
    expect(findExpandedDesignation('South Africa', 'Still Bay East')).toHaveLength(0);
  });

  it('preserves bilingual South African aliases as aliases rather than duplicate legal identities', () => {
    expect(findExpandedDesignation('South Africa', 'Kaapstad')[0]?.name).toBe('Cape Town');
    expect(findExpandedDesignation('South Africa', 'Breërivier Vallei')[0]?.name).toBe('Breede River Valley');
    expect(findExpandedDesignation('South Africa', 'Sentraal-Oranjerivier')[0]?.name).toBe('Central Orange River');
    expect(findExpandedDesignation('South Africa', 'Rietrivier VS')[0]?.name).toBe('Rietrivier FS');
  });

  it('preserves same-name Argentine and Brazilian origins by legal class', () => {
    expect(findExpandedDesignation('Argentina', 'Luján de Cuyo')).toHaveLength(2);
    expect(new Set(findExpandedDesignation('Argentina', 'Luján de Cuyo').map((record) => record.legalClass))).toEqual(new Set(['IG', 'DOC']));
    expect(findExpandedDesignation('Argentina', 'Rivadavia')).toHaveLength(2);
    expect(findExpandedDesignation('Brazil', 'Vale dos Vinhedos')).toHaveLength(2);
    expect(new Set(findExpandedDesignation('Brazil', 'Vale dos Vinhedos').map((record) => record.legalClass))).toEqual(new Set(['IP', 'DO']));
  });

  it('adds current Japanese and Moldovan wine GIs without importing non-wine names', () => {
    expect(findExpandedDesignation('Japan', 'Nagano')[0]?.registrationDate).toBe('2021-06-30');
    expect(findExpandedDesignation('Japan', '北海道')[0]?.name).toBe('Hokkaido');
    expect(findExpandedDesignation('Moldova', 'Codru')[0]?.legalClass).toBe('PGI');
    expect(findExpandedDesignation('Moldova', 'Ciumai')[0]?.legalClass).toBe('PDO');
    expect(findExpandedDesignation('Moldova', 'Divin')).toHaveLength(0);
  });

  it('separates registered UK wine names from pending applications and preserves India registration identity', () => {
    expect(findExpandedDesignation('United Kingdom', 'Sussex')[0]?.legalClass).toBe('PDO');
    expect(findExpandedDesignation('United Kingdom', 'The Crouch Valley')).toHaveLength(0);
    expect(findExpandedDesignation('India', 'Nashik Valley Wine')[0]?.registrationNumber).toBe('123');
  });

  it('keeps every registry identity reference-only until product rules are separately researched', () => {
    for (const country of ['Georgia', 'New Zealand', 'Chile', 'South Africa', 'Japan', 'Moldova', 'Brazil', 'United Kingdom', 'India']) {
      expect(designationsForCountry(country).every((record) => record.generationStatus === 'reference-only')).toBe(true);
    }
  });
});
