import { describe, expect, it } from 'vitest';
import { grapeReference, referenceCountries, referencePlaces, validateReferenceIntegrity } from './reference';
import { generateWine, generateWineBook, validateGeneratedWine } from './world';

describe('canonical wine reference layer', () => {
  it('preserves the deep real-world dataset rather than replacing it with a toy catalog', () => {
    const report = validateReferenceIntegrity();
    expect(grapeReference.length).toBeGreaterThan(300);
    expect(referenceCountries.length).toBeGreaterThan(25);
    expect(referencePlaces.length).toBeGreaterThan(500);
    expect(report.grapes).toBe(grapeReference.length);
  });

  it('generates only wines whose geography and grape resolve to reference data', () => {
    for (let i = 0; i < 250; i += 1) {
      expect(validateGeneratedWine(generateWine(`validation-${i}`))).toBe(true);
    }
  });

  it('can build a large deterministic wine book without inventing geography', () => {
    const book = generateWineBook('career-seed', 1000);
    expect(book).toHaveLength(1000);
    expect(book.every(validateGeneratedWine)).toBe(true);
    expect(new Set(book.map((wine) => wine.country)).size).toBeGreaterThan(10);
  });

  it('attaches exact researched products only when the resolver can validate the chosen single-grape case', () => {
    const book = generateWineBook('resolver-integration', 2500);
    const resolved = book.filter((wine) => wine.productRuleId);
    expect(resolved.length).toBeGreaterThan(10);
    expect(resolved.every((wine) => wine.productResolutionStatus === 'resolved')).toBe(true);
    expect(resolved.every((wine) => Boolean(wine.productName))).toBe(true);
    expect(resolved.every((wine) => typeof wine.provenanceRisk === 'number' && wine.provenanceRisk >= 0 && wine.provenanceRisk <= 1)).toBe(true);
  });
});
