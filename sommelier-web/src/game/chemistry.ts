import chemistryData from '../data/research/wine_chemistry_processes.json';
import chemistryDataPass2 from '../data/research/wine_chemistry_processes_pass2.json';
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

const files = [
  chemistryData as unknown as ChemistryFile,
  chemistryDataPass2 as unknown as ChemistryFile,
];
export const wineChemistryMethod = files.map((candidate) => candidate.method).join(' ');
export const wineChemistryPassCount = files.length;
export const wineChemistryRecords = files.flatMap((candidate) => candidate.records);
export const wineChemistryById = new Map(wineChemistryRecords.map((record) => [record.id, record]));

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const clampSigned = (value: number) => Math.max(-1, Math.min(1, value));
const ramp = (value: number, low: number, high: number) => high === low ? Number(value >= high) : clamp01((value - low) / (high - low));

export type FermentationChemistryInput = {
  color: 'white' | 'red' | 'rose' | 'other';
  yanMgL?: number;
  residualYanMgL?: number;
  fermentationTemperatureC?: number;
  juiceTurbidityNtu?: number;
  ph?: number;
  volatileAcidityGPerL?: number;
  ethylAcetateMgL?: number;
  dissolvedOxygenPreBottlingMgL?: number;
  freeSo2MgL?: number;
  molecularSo2MgL?: number;
  closureOtrRelative?: number;
  storageQuality?: number;
  nutrientAddition?: 'none' | 'organic' | 'dap' | 'mixed';
  fermentationStage?: 'pre-fermentation' | 'growth' | 'mid' | 'late' | 'complete';
  malolacticStatus?: 'none' | 'not-started' | 'active' | 'complete';
  daysUnsulfuredPostFermentation?: number;
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
    brettanomyces: number;
    oxidationLoad: number;
    prematureOxidation: number;
    reductiveDevelopment: number;
  };
  processEffects: {
    phenolicExtraction: number;
    fruitRetention: number;
    shelfLifePressure: number;
    reductiveAromaPressure: number;
    juiceOxidationPressure: number;
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
  let brettanomyces = 0.08;
  let oxidationLoad = 0.10;
  let prematureOxidation = 0.08;
  let reductiveDevelopment = 0.10;
  let phenolicExtraction = 0;
  let fruitRetention = 0;
  let shelfLifePressure = 0;
  let reductiveAromaPressure = 0;
  let juiceOxidationPressure = 0;

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
    if (input.yanMgL > 350 && input.nutrientAddition === 'dap') {
      ethylAcetate += 0.12;
      flags.push('High starting YAN plus inorganic supplementation carries an ester-taint/residual-nitrogen tradeoff in the model');
    }
  }

  if (typeof input.residualYanMgL === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-yan-2026');
    evidenceRefs.add('awri-brett-faq-current-2026');
    const residualPressure = ramp(input.residualYanMgL, 10, 100);
    microbialInstability += residualPressure * 0.18;
    brettanomyces += residualPressure * 0.14;
    if (residualPressure > 0.5) flags.push('Residual assimilable nitrogen adds spoilage-organism nutrient pressure; no universal residual-YAN danger threshold is asserted');
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

  if (typeof input.juiceTurbidityNtu === 'number' && input.color !== 'red') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-white-juice-solids-2026');
    const tooClear = clamp01((70 - input.juiceTurbidityNtu) / 70);
    const highSolids = ramp(input.juiceTurbidityNtu, 150, 350);
    const compromiseDistance = Math.abs(input.juiceTurbidityNtu - 100);
    fermentationStress += tooClear * 0.18;
    reductiveDevelopment += highSolids * 0.25;
    reductiveAromaPressure += highSolids * 0.35;
    juiceOxidationPressure += highSolids * 0.30;
    fruitRetention += clamp01(1 - compromiseDistance / 150) * 0.16 - highSolids * 0.08;
    if (input.juiceTurbidityNtu < 50) flags.push('Very low white-juice turbidity increases sluggish-fermentation pressure in the derived model');
    if (input.juiceTurbidityNtu > 200) flags.push('High white-juice solids increase reductive-character and oxidation-management pressure');
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
    evidenceRefs.add('awri-so2-revisited-2026');
    const lowReserve = ramp(25 - input.freeSo2MgL, 0, 25);
    oxidationLoad += lowReserve * 0.20;
    microbialInstability += lowReserve * 0.18;
  }

  if (typeof input.molecularSo2MgL === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-brett-faq-current-2026');
    evidenceRefs.add('awri-so2-revisited-2026');
    const belowBrettGuide = clamp01((0.6 - input.molecularSo2MgL) / 0.6);
    brettanomyces += belowBrettGuide * 0.42;
    microbialInstability += belowBrettGuide * 0.16;
    if (input.molecularSo2MgL >= 0.6) brettanomyces -= 0.16;
    else flags.push('Molecular SO₂ is below the 0.6 mg/L AWRI Brett-control guide used by the model');
  }

  if (typeof input.daysUnsulfuredPostFermentation === 'number') {
    evidenceInputs += 1;
    evidenceRefs.add('awri-brett-faq-current-2026');
    const openWindow = ramp(input.daysUnsulfuredPostFermentation, 0, 30);
    const mlfMultiplier = input.malolacticStatus === 'active' ? 1 : input.malolacticStatus === 'not-started' ? 0.8 : 0.55;
    brettanomyces += openWindow * 0.48 * mlfMultiplier;
    microbialInstability += openWindow * 0.18 * mlfMultiplier;
    if (openWindow > 0.4 && input.malolacticStatus === 'active') flags.push('Extended unsulfured active-MLF period is inside the AWRI Brett risk window');
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
      brettanomyces: clamp01(brettanomyces),
      oxidationLoad: clamp01(oxidationLoad),
      prematureOxidation: clamp01(prematureOxidation),
      reductiveDevelopment: clamp01(reductiveDevelopment),
    },
    processEffects: {
      phenolicExtraction: clampSigned(phenolicExtraction),
      fruitRetention: clampSigned(fruitRetention),
      shelfLifePressure: clamp01(shelfLifePressure),
      reductiveAromaPressure: clamp01(reductiveAromaPressure),
      juiceOxidationPressure: clamp01(juiceOxidationPressure),
    },
    flags,
    evidenceRefs: [...evidenceRefs],
    explanation: 'Derived chemistry risk model. Source-backed measurements guide the transform, but output values are bounded simulation indices rather than probabilities, laboratory results or fault diagnoses.',
  };
}

export type SmokeCultivar = 'Chardonnay' | 'Pinot Noir' | 'Shiraz';
export type SmokeMarkerName = 'guaiacol' | 'oCresol' | 'mCresol' | 'pCresol' | 'guaiacolRutinoside' | 'cresolRutinoside' | 'syringolGentiobioside';
export type SmokeMarkerInput = {
  cultivar: SmokeCultivar;
  markersUgKg: Partial<Record<SmokeMarkerName, number>>;
};

export type SmokeTaintAssessment = {
  derived: true;
  cultivar: SmokeCultivar;
  riskIndex: number;
  latentGlycosidePressure: number;
  ageingReleasePotential: number;
  markerAssessments: Array<{ marker: SmokeMarkerName; valueUgKg: number; moderateUgKg: number; highUgKg: number; risk: number }>;
  sensoryFamilies: string[];
  flags: string[];
  evidenceRefs: string[];
};

const smokeThresholds: Record<SmokeCultivar, Record<SmokeMarkerName, [number, number]>> = {
  Chardonnay: {
    guaiacol: [1, 9], oCresol: [0.5, 7], mCresol: [0.5, 7], pCresol: [0.5, 7],
    guaiacolRutinoside: [2, 8], cresolRutinoside: [3, 9], syringolGentiobioside: [32, 101],
  },
  'Pinot Noir': {
    guaiacol: [2, 3], oCresol: [3, 5], mCresol: [0.5, 1], pCresol: [0.5, 0.5],
    guaiacolRutinoside: [3, 4], cresolRutinoside: [6, 7], syringolGentiobioside: [22, 31],
  },
  Shiraz: {
    guaiacol: [4, 10], oCresol: [0.5, 3], mCresol: [0.5, 0.5], pCresol: [0.5, 0.5],
    guaiacolRutinoside: [6, 23], cresolRutinoside: [5, 12], syringolGentiobioside: [29, 164],
  },
};

const glycosideMarkers = new Set<SmokeMarkerName>(['guaiacolRutinoside', 'cresolRutinoside', 'syringolGentiobioside']);

/**
 * Derived interpretation of AWRI cultivar-specific grape marker risk tables.
 * Risk is only valid for these three cultivars and does not replace laboratory interpretation.
 */
export function assessSmokeTaintMarkers(input: SmokeMarkerInput): SmokeTaintAssessment {
  const markerAssessments: SmokeTaintAssessment['markerAssessments'] = [];
  const flags: string[] = [];
  const glycosideRisks: number[] = [];
  let maxRisk = 0;
  let sumRisk = 0;

  for (const [marker, value] of Object.entries(input.markersUgKg) as Array<[SmokeMarkerName, number | undefined]>) {
    if (typeof value !== 'number') continue;
    const [moderate, high] = smokeThresholds[input.cultivar][marker];
    const risk = value < moderate ? clamp01(value / Math.max(moderate, 0.01)) * 0.35 : 0.35 + ramp(value, moderate, high) * 0.65;
    markerAssessments.push({ marker, valueUgKg: value, moderateUgKg: moderate, highUgKg: high, risk: clamp01(risk) });
    maxRisk = Math.max(maxRisk, risk);
    sumRisk += risk;
    if (glycosideMarkers.has(marker)) glycosideRisks.push(risk);
    if (value >= high) flags.push(`${marker} meets or exceeds the AWRI high-risk grape-marker level for ${input.cultivar}`);
    else if (value >= moderate) flags.push(`${marker} meets or exceeds the AWRI moderate-risk grape-marker level for ${input.cultivar}`);
  }

  const meanRisk = markerAssessments.length ? sumRisk / markerAssessments.length : 0;
  const riskIndex = clamp01(maxRisk * 0.65 + meanRisk * 0.35);
  const latentGlycosidePressure = glycosideRisks.length ? clamp01(glycosideRisks.reduce((a, b) => a + b, 0) / glycosideRisks.length) : 0;
  const ageingReleasePotential = clamp01(latentGlycosidePressure * 0.80 + riskIndex * 0.20);
  const sensoryFamilies = riskIndex >= 0.35 ? ['smoky', 'burnt', 'ashy', 'medicinal'] : [];
  if (latentGlycosidePressure >= 0.45) flags.push('Elevated glycoside-marker pressure means smoke character can emerge or change during fermentation, ageing and in-mouth release');

  return {
    derived: true,
    cultivar: input.cultivar,
    riskIndex,
    latentGlycosidePressure,
    ageingReleasePotential,
    markerAssessments,
    sensoryFamilies,
    flags,
    evidenceRefs: ['awri-smoke-taint-current-2026', 'awri-smoke-aged-wine-2025'],
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
  return {
    records: wineChemistryRecords.length,
    passes: wineChemistryPassCount,
    domains: new Set(wineChemistryRecords.map((record) => record.domain)).size,
    issues,
  };
}
