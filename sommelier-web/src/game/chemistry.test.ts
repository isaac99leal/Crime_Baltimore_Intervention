import { describe, expect, it } from 'vitest';
import {
  assessSmokeTaintMarkers,
  assessWineChemistry,
  validateWineChemistryResearch,
  wineChemistryPassCount,
  wineChemistryRecords,
} from './chemistry';

describe('wine chemistry and process-risk layer', () => {
  it('keeps factual chemistry records source-backed and simulation outputs separate', () => {
    const report = validateWineChemistryResearch();
    expect(wineChemistryPassCount).toBe(2);
    expect(wineChemistryRecords.length).toBeGreaterThanOrEqual(28);
    expect(report.domains).toBeGreaterThanOrEqual(9);
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

  it('models white-juice solids as a tradeoff rather than a monotonic quality slider', () => {
    const veryClear = assessWineChemistry({ color: 'white', juiceTurbidityNtu: 20 });
    const compromise = assessWineChemistry({ color: 'white', juiceTurbidityNtu: 100 });
    const highSolids = assessWineChemistry({ color: 'white', juiceTurbidityNtu: 320 });
    expect(veryClear.risks.fermentationStress).toBeGreaterThan(compromise.risks.fermentationStress);
    expect(highSolids.processEffects.reductiveAromaPressure).toBeGreaterThan(compromise.processEffects.reductiveAromaPressure);
    expect(highSolids.processEffects.juiceOxidationPressure).toBeGreaterThan(compromise.processEffects.juiceOxidationPressure);
    expect(compromise.processEffects.fruitRetention).toBeGreaterThan(veryClear.processEffects.fruitRetention);
  });

  it('models the post-fermentation Brett window and molecular SO2 guide separately from generic microbial risk', () => {
    const exposed = assessWineChemistry({
      color: 'red',
      ph: 3.75,
      malolacticStatus: 'active',
      daysUnsulfuredPostFermentation: 25,
      molecularSo2MgL: 0.2,
      residualYanMgL: 70,
    });
    const protectedWine = assessWineChemistry({
      color: 'red',
      ph: 3.45,
      malolacticStatus: 'complete',
      daysUnsulfuredPostFermentation: 1,
      molecularSo2MgL: 0.7,
      residualYanMgL: 10,
    });
    expect(exposed.risks.brettanomyces).toBeGreaterThan(protectedWine.risks.brettanomyces);
    expect(exposed.flags.some((flag) => flag.includes('Brett risk window'))).toBe(true);
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

  it('interprets smoke markers with cultivar-specific AWRI risk tables and latent glycoside release', () => {
    const low = assessSmokeTaintMarkers({ cultivar: 'Chardonnay', markersUgKg: { guaiacol: 0.4, guaiacolRutinoside: 0.8, syringolGentiobioside: 8 } });
    const high = assessSmokeTaintMarkers({ cultivar: 'Chardonnay', markersUgKg: { guaiacol: 10, guaiacolRutinoside: 10, syringolGentiobioside: 120 } });
    expect(high.riskIndex).toBeGreaterThan(low.riskIndex);
    expect(high.latentGlycosidePressure).toBeGreaterThan(low.latentGlycosidePressure);
    expect(high.ageingReleasePotential).toBeGreaterThan(0.5);
    expect(high.sensoryFamilies).toContain('ashy');
    expect(high.flags.some((flag) => flag.includes('high-risk'))).toBe(true);
  });

  it('does not reuse Chardonnay smoke thresholds for Pinot Noir or Shiraz', () => {
    const marker = { guaiacol: 3 };
    const chardonnay = assessSmokeTaintMarkers({ cultivar: 'Chardonnay', markersUgKg: marker });
    const pinot = assessSmokeTaintMarkers({ cultivar: 'Pinot Noir', markersUgKg: marker });
    const shiraz = assessSmokeTaintMarkers({ cultivar: 'Shiraz', markersUgKg: marker });
    expect(pinot.riskIndex).toBeGreaterThan(chardonnay.riskIndex);
    expect(chardonnay.riskIndex).toBeGreaterThan(shiraz.riskIndex);
  });
});
