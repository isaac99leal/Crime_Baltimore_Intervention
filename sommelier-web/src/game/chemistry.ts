import chemistryData from '../data/research/wine_chemistry_processes.json';
import { researchSourceById } from './research';

export type ChemistryRecord = {
  id: string;
  domain: string;
  factType: 'source-backed';
  facts: string[];
  measurements?: Record<string, unknown>;
  conditions?: Record<string, unknown>;
  sourceRefs: string[];
};

type ChemistryFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  records: ChemistryRecord[];
};

const file = chemistryData as unknown as ChemistryFile;
export const wineChemistryMethod = file.method;
export const wineChemistryRecords = file.records;
export const wineChemistryById = new Map(wineChemistryRecords.map((record) => [record.id, record]));

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const ramp = (value: number, low: number, high: number) => high === low ? Number(value >= high) : clamp01((value - low) / (high - low));

export type FermentationChemistryInput = {
  color: 'white' | 'red' | 'rose' | 'other';
  yanMgL?: number;
  fermentationTemperatureC?: number;
  ph?: number;
  volatileAcidityGPerL?: number;
  ethylAcetateMgL?: number;
  dissolvedOxygenPreBottlingMgL?: number;
  freeSo2MgL?: number;
  closureOtrRelative?: number;
  storageQuality?: number;
  nutrientAddition?: 'none' | 'organic' | 'dap' | 'mixed';
  fermentationStage?: 'pre-fermentation' | 'growth' | 'mid' | 'late' | 'complete';
};

export type ChemistryAssessment = {
  derived: true;
  confidence: number;
  risks: {
    fermentationStress: number;
    growthPhaseH2s: number;
    latePhaseH2s: number;
    volatileAcidity: number;
    ethylAcetate: number;
    microbialInstability: number;
    oxidationLoad: number;
    prematureOxidation: number;
    reductiveDevelopment: number;
  };
  processEffects: {
    phenolicExtraction: number;
    fruitRetention: number;
    shelfLifePressure: number;
  };
  flags: string[];
  evidenceRefs: string[];
  explanation: string;
};

/**
 * Conservative simulation transform from measured/process inputs to bounded game risks.
 * Values are relative risk indices, not laboratory probabilities or diagnoses.
 */
export function assessWineChemistry(input: FermentationChemistryInput): ChemistryAssessment {
  const flags: string[] = [];
  const evidenceRefs = new Set<string>();
  let evidenceInputs = 0;
  let fermentationStress = 0.15;
  let growthPhaseH2s = 0.12;
  let latePhaseH2s = 0.08;
  let volatileAcidity = 0.10;
  let ethylAcetate = 0.10;
  let microbialInstability = 0.15;
  let oxidationLoad = 0.10;
  let prematureOxidation = 0.08;
  let reductiveDevelopment = 0.10;
  let phenolicExtraction = 0;
  let fruitRetention = 0;
  let shelfLifePressure = 0;

  if (typeof input.yanMgL === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-yan-2026');
    evidenceRefs.add('awri-h2s-2026');
    const guide = input.color === 'red' ? 100 : 150;
    const deficit = clamp01((guide - input.yanMgL) / Math.max(guide, 1));
    fermentationStress += deficit * 0.52;
    growthPhaseH2s += deficit * 0.55;
    if (input.yanMgL < guide) flags.push(`YAN below the AWRI low-risk guide used for this simulation context (${guide} mg/L); outcome remains strain- and must-dependent`);
    if (input.color !== 'red' && input.yanMgL >= 250 && input.yanMgL <= 350) flags.push('YAN lies within AWRI clean/fruity white-wine guide range; this is not a universal optimum');
    if (input.nutrientAddition === 'dap' && input.fermentationStage === 'late') {
      latePhaseH2s += 0.08;
      flags.push('Late-phase H2S is not assumed to resolve from DAP because yeast growth may already have ceased');
    } else if (input.nutrientAddition && input.nutrientAddition !== 'none' && deficit > 0) {
      fermentationStress -= 0.10;
      growthPhaseH2s -= 0.08;
    }
  }

  if (typeof input.fermentationTemperatureC === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-fermentation-temperature-2026');
    const hot = ramp(input.fermentationTemperatureC, 28, 35);
    phenolicExtraction += input.color === 'red' ? hot * 0.65 : hot * 0.15;
    fruitRetention -= ramp(input.fermentationTemperatureC, 20, 35) * 0.25;
    if (input.fermentationTemperatureC > 35) {
      fermentationStress += 0.60;
      flags.push('Fermentation temperature above 35°C: elevated yeast-viability/sluggish-fermentation concern');
    } else if (input.fermentationTemperatureC >= 30) {
      fermentationStress += 0.12;
    }
  }

  if (typeof input.ph === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-acidity-ph-2026');
    microbialInstability += ramp(input.ph, 3.2, 4.0) * 0.50;
    shelfLifePressure += ramp(input.ph, 3.3, 4.0) * 0.32;
    if (input.ph >= 3.7) flags.push('Higher pH increases microbial/SO₂-management pressure; pH is kept separate from titratable acidity');
  }

  if (typeof input.volatileAcidityGPerL === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-faults-2026');
    volatileAcidity = ramp(input.volatileAcidityGPerL, 0.1, 0.9);
    if (input.volatileAcidityGPerL > 0.7) flags.push('Volatile acidity exceeds a commonly detrimental sensory guide cited by AWRI; legal/style context remains separate');
  }

  if (typeof input.ethylAcetateMgL === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-faults-2026');
    ethylAcetate = ramp(input.ethylAcetateMgL, 30, 180);
    if (input.ethylAcetateMgL >= 150) flags.push('Ethyl acetate is in the AWRI defective-wine reference range');
  }

  if (typeof input.dissolvedOxygenPreBottlingMgL === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-gas-adjustment-2026');
    const oxygenExcess = ramp(input.dissolvedOxygenPreBottlingMgL, 0.5, 4);
    oxidationLoad += oxygenExcess * 0.62;
    shelfLifePressure += oxygenExcess * 0.30;
    if (input.dissolvedOxygenPreBottlingMgL > 0.5) flags.push('Pre-bottling dissolved oxygen is above the AWRI general <0.5 mg/L target used as a packaging-risk guide');
  }

  if (typeof input.freeSo2MgL === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-gas-adjustment-2026');
    const lowReserve = ramp(25 - input.freeSo2MgL, 0, 25);
    oxidationLoad += lowReserve * 0.20;
    microbialInstability += lowReserve * 0.18;
  }

  if (typeof input.closureOtrRelative === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-closure-trial-2026');
    const otr = clamp01(input.closureOtrRelative);
    oxidationLoad += otr * 0.28;
    reductiveDevelopment += (1 - otr) * 0.22;
    shelfLifePressure += otr * 0.14;
  }

  if (typeof input.storageQuality === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('premox-review-2021');
    const storagePenalty = 1 - clamp01(input.storageQuality);
    prematureOxidation += storagePenalty * 0.55;
    shelfLifePressure += storagePenalty * 0.45;
  }

  evidenceRefs.add('premox-review-2021');
  evidenceRefs.add('wine-aging-capacity-review-2021');
  prematureOxidation += clamp01(oxidationLoad) * 0.42 + clamp01(shelfLifePressure) * 0.28;
  if (prematureOxidation > 0.62) flags.push('Multifactor premature-oxidation risk is elevated; this is a simulation risk index, not a diagnosis');

  if (input.fermentationStage === 'late') {
    latePhaseH2s += 0.12;
    evidenceRefs.add('awri-h2s-2026');
  }

  const confidence = Math.max(1, Math.min(5, 1 + Math.floor(evidenceInputs / 2)));
  return {
    derived: true,
    confidence,
    risks: {
      fermentationStress: clamp01(fermentationStress),
      growthPhaseH2s: clamp01(growthPhaseH2s),
      latePhaseH2s: clamp01(latePhaseH2s),
      volatileAcidity: clamp01(volatileAcidity),
      ethylAcetate: clamp01(ethylAcetate),
      microbialInstability: clamp01(microbialInstability),
      oxidationLoad: clamp01(oxidationLoad),
      prematureOxidation: clamp01(prematureOxidation),
      reductiveDevelopment: clamp01(reductiveDevelopment),
    },
    processEffects: {
      phenolicExtraction: Math.max(-1, Math.min(1, phenolicExtraction)),
      fruitRetention: Math.max(-1, Math.min(1, fruitRetention)),
      shelfLifePressure: clamp01(shelfLifePressure),
    },
    flags,
    evidenceRefs: [...evidenceRefs],
    explanation: 'Derived chemistry risk model. Source-backed measurements guide the transform, but output values are bounded simulation indices rather than probabilities, laboratory results or fault diagnoses.',
  };
}

export function validateWineChemistryResearch() {
  const issues: string[] = [];
  const ids = new Set<string>();
  for (const record of wineChemistryRecords) {
    if (ids.has(record.id)) issues.push(`Duplicate chemistry record: ${record.id}`);
    ids.add(record.id);
    if (!record.domain || record.factType !== 'source-backed' || !record.facts.length) issues.push(`Incomplete chemistry record: ${record.id}`);
    if (!record.sourceRefs.length) issues.push(`Chemistry record has no provenance: ${record.id}`);
    for (const sourceId of record.sourceRefs) if (!researchSourceById.has(sourceId)) issues.push(`Unknown chemistry source ${sourceId} in ${record.id}`);
  }
  return { records: wineChemistryRecords.length, domains: new Set(wineChemistryRecords.map((record) => record.domain)).size, issues };
}
