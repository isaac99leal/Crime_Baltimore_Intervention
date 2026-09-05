import { describe, expect, it } from 'vitest';
import { assessWineChemistry, validateWineChemistryResearch, wineChemistryRecords } from './chemistry';

describe('wine chemistry and process-risk layer', () => {
  it('keeps factual chemistry records source-backed and simulation outputs separate', () => {
    const report = validateWineChemistryResearch();
    expect(wineChemistryRecords.length).toBeGreaterThanOrEqual(18);
    expect(report.domains).toBeGreaterThanOrEqual(7);
    expect(report.issues).toEqual([]);
  });

  it('raises fermentation stress and growth-phase H2S risk for a low-YAN must without making it deterministic', () => {
    const low = assessWineChemistry({ color: 'white', yanMgL: 70, fermentationStage: 'growth', fermentationTemperatureC: 18 });
    const adequate = assessWineChemistry({ color: 'white', yanMgL: 180, fermentationStage: 'growth', fermentationTemperatureC: 18 });
    expect(low.risks.fermentationStress).toBeGreaterThan(adequate.risks.fermentationStress);
    expect(low.risks.growthPhaseH2s).toBeGreaterThan(adequate.risks.growthPhaseH2s);
    expect(low.derived).toBe(true);
    expect(low.flags.some((flag) => flag.includes('YAN below'))).toBe(true);
  });

  it('does not pretend late-phase H2S is automatically fixed by DAP', () => {
    const result = assessWineChemistry({ color: 'white', yanMgL: 80, nutrientAddition: 'dap', fermentationStage: 'late' });
    expect(result.flags.some((flag) => flag.includes('not assumed to resolve from DAP'))).toBe(true);
    expect(result.risks.latePhaseH2s).toBeGreaterThan(0);
  });

  it('models very hot red fermentation as both an extraction and yeast-health problem', () => {
    const hot = assessWineChemistry({ color: 'red', fermentationTemperatureC: 37 });
    const moderate = assessWineChemistry({ color: 'red', fermentationTemperatureC: 25 });
    expect(hot.processEffects.phenolicExtraction).toBeGreaterThan(moderate.processEffects.phenolicExtraction);
    expect(hot.risks.fermentationStress).toBeGreaterThan(moderate.risks.fermentationStress);
  });

  it('combines packaging oxygen, closure and storage rather than treating premox as a single-cause switch', () => {
    const protectedBottle = assessWineChemistry({ color: 'white', dissolvedOxygenPreBottlingMgL: 0.2, closureOtrRelative: 0.15, storageQuality: 0.98 });
    const exposedBottle = assessWineChemistry({ color: 'white', dissolvedOxygenPreBottlingMgL: 3.2, closureOtrRelative: 0.85, storageQuality: 0.55 });
    expect(exposedBottle.risks.oxidationLoad).toBeGreaterThan(protectedBottle.risks.oxidationLoad);
    expect(exposedBottle.risks.prematureOxidation).toBeGreaterThan(protectedBottle.risks.prematureOxidation);
  });

  it('keeps measured VA and ethyl acetate as contextual sensory risks rather than one generic fault score', () => {
    const clean = assessWineChemistry({ color: 'red', volatileAcidityGPerL: 0.25, ethylAcetateMgL: 45 });
    const elevated = assessWineChemistry({ color: 'red', volatileAcidityGPerL: 0.9, ethylAcetateMgL: 170 });
    expect(elevated.risks.volatileAcidity).toBeGreaterThan(clean.risks.volatileAcidity);
    expect(elevated.risks.ethylAcetate).toBeGreaterThan(clean.risks.ethylAcetate);
    expect(elevated.flags.some((flag) => flag.includes('Ethyl acetate'))).toBe(true);
  });
});
