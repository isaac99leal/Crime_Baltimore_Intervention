import { describe, expect, it } from 'vitest';
import { auditWineProvenance, createAuditChallenge } from './audit';
import { generateWine } from './world';
import type { WineDefinition } from './types';

function generated(seed = 'audit-base'): WineDefinition {
  return generateWine(seed);
}

describe('provenance audit and training challenge engine', () => {
  it('does not invent hard identity defects across a generated stress book', () => {
    for (let i = 0; i < 500; i += 1) {
      const wine = generated(`audit-stress-${i}`);
      const audit = auditWineProvenance(wine);
      expect(audit.passedHardIdentityChecks).toBe(true);
      expect(audit.findings.some((finding) => finding.id === 'unknown-grape')).toBe(false);
      expect(audit.findings.some((finding) => finding.id === 'gi-grape-mismatch')).toBe(false);
      expect(audit.findings.some((finding) => finding.id === 'future-vintage')).toBe(false);
    }
  });

  it('escalates an unknown cultivar instead of guessing a synonym', () => {
    const wine = { ...generated(), grape: 'Definitely Not A Real Grape' };
    const audit = auditWineProvenance(wine);
    expect(audit.passedHardIdentityChecks).toBe(false);
    expect(audit.band).toBe('critical');
    expect(audit.findings[0]?.id).toBe('unknown-grape');
  });

  it('catches impossible chronology independently of product provenance', () => {
    const wine = { ...generated(), vintage: 2034 };
    const audit = auditWineProvenance(wine, 2026);
    expect(audit.findings.some((finding) => finding.id === 'future-vintage')).toBe(true);
    expect(audit.passedHardIdentityChecks).toBe(false);
  });

  it('catches broken product provenance references', () => {
    const base = generated();
    const wine: WineDefinition = {
      ...base,
      productRuleId: base.productRuleId ?? 'product-it-brunello',
      productName: base.productName ?? 'Resolved product',
      productResolutionStatus: 'resolved',
      productSourceIds: ['source-that-does-not-exist'],
    };
    const audit = auditWineProvenance(wine);
    expect(audit.findings.some((finding) => finding.id === 'broken-source-refs')).toBe(true);
    expect(audit.band).toBe('critical');
  });

  it('treats historical-law uncertainty as a distinct audit issue rather than invalidating geography', () => {
    const wine: WineDefinition = {
      ...generated(),
      vintage: 1963,
      legalEraStatus: 'product-resolved-historical-law-unverified',
      productResolutionStatus: 'resolved',
    };
    const audit = auditWineProvenance(wine);
    expect(audit.findings.some((finding) => finding.id === 'historical-law-unverified')).toBe(true);
    expect(audit.findings.find((finding) => finding.id === 'historical-law-unverified')?.category).toBe('historical-law');
  });

  it('turns the highest material finding into a staff-training audit question', () => {
    const wine = { ...generated(), vintage: 2032 };
    const challenge = createAuditChallenge(wine, 2026);
    expect(challenge.correctOption).toBe('Chronology/vintage problem');
    expect(challenge.options).toContain(challenge.correctOption);
    expect(challenge.explanation).toContain('Impossible future vintage');
  });
});
