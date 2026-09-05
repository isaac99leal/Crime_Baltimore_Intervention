import winemakingData from '../data/research/winemaking_decisions.json';
import { researchSourceById } from './research';
import type { WineProfile } from './types';

export type WinemakingAxis =
  | 'acidity' | 'tannin' | 'body' | 'sweetness' | 'fruitIntensity' | 'earthIntensity'
  | 'aromaticFreshness' | 'oakInfluence' | 'oxidativeDevelopment' | 'reductiveRisk'
  | 'autolysis' | 'colorExtraction' | 'phenolicExtraction' | 'volatileAcidityRisk'
  | 'microbialRisk' | 'ageability';

export type DecisionOption = {
  id: string;
  label: string;
  matrix: Partial<Record<WinemakingAxis, number>>;
};

export type WinemakingDecision = {
  id: string;
  stage: string;
  name: string;
  requiresDesignationCheck: boolean;
  sourceRefs?: string[];
  options: DecisionOption[];
};

type WinemakingFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  matrixScale: string;
  axes: WinemakingAxis[];
  decisions: WinemakingDecision[];
};

const file = winemakingData as unknown as WinemakingFile;
export const winemakingResearchMethod = file.method;
export const winemakingAxes = file.axes;
export const winemakingDecisions = file.decisions;
export const winemakingDecisionById = new Map(winemakingDecisions.map((decision) => [decision.id, decision]));

export type WinemakingSelection = { decisionId: string; optionId: string };
export type WinemakingLegalCheck = (decision: WinemakingDecision, option: DecisionOption) => boolean;

export type WinemakingResult = {
  profile: WineProfile;
  derived: true;
  selected: Array<{ decisionId: string; optionId: string; label: string }>;
  blocked: Array<{ decisionId: string; optionId: string; reason: string }>;
  extraAxes: Record<Exclude<WinemakingAxis, keyof WineProfile>, number>;
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export function decisionOption(decisionId: string, optionId: string): DecisionOption | undefined {
  return winemakingDecisionById.get(decisionId)?.options.find((option) => option.id === optionId);
}

export function applyWinemakingDecisions(
  base: WineProfile,
  selections: WinemakingSelection[],
  legalCheck?: WinemakingLegalCheck,
): WinemakingResult {
  const profile = { ...base };
  const extraAxes = {
    aromaticFreshness: 0,
    oakInfluence: 0,
    oxidativeDevelopment: 0,
    reductiveRisk: 0,
    autolysis: 0,
    colorExtraction: 0,
    phenolicExtraction: 0,
    volatileAcidityRisk: 0,
    microbialRisk: 0,
    ageability: 0,
  };
  const selected: WinemakingResult['selected'] = [];
  const blocked: WinemakingResult['blocked'] = [];

  for (const selection of selections) {
    const decision = winemakingDecisionById.get(selection.decisionId);
    const option = decision?.options.find((candidate) => candidate.id === selection.optionId);
    if (!decision || !option) {
      blocked.push({ ...selection, reason: 'unknown decision or option' });
      continue;
    }
    if (decision.requiresDesignationCheck && !legalCheck) {
      blocked.push({ ...selection, reason: 'designation/product legality has not been resolved' });
      continue;
    }
    if (decision.requiresDesignationCheck && legalCheck && !legalCheck(decision, option)) {
      blocked.push({ ...selection, reason: 'not permitted by resolved designation/product rule' });
      continue;
    }

    selected.push({ ...selection, label: option.label });
    for (const [axis, raw] of Object.entries(option.matrix) as Array<[WinemakingAxis, number]>) {
      const value = raw * 0.55;
      if (axis === 'acidity') profile.acidity = clamp(profile.acidity + value, 1, 5);
      else if (axis === 'tannin') profile.tannin = clamp(profile.tannin + value, 0.5, 5);
      else if (axis === 'body') profile.body = clamp(profile.body + value, 1, 5);
      else if (axis === 'sweetness') profile.sweetness = clamp(profile.sweetness + value, 0.5, 5);
      else if (axis === 'fruitIntensity') profile.fruitIntensity = clamp(profile.fruitIntensity + value, 0.5, 5);
      else if (axis === 'earthIntensity') profile.earthIntensity = clamp(profile.earthIntensity + value, 0.5, 5);
      else extraAxes[axis] = clamp(extraAxes[axis] + value, -1, 1);
    }
  }

  return { profile, derived: true, selected, blocked, extraAxes };
}

export function validateWinemakingResearch() {
  const issues: string[] = [];
  const ids = new Set<string>();
  const allowedAxes = new Set(winemakingAxes);

  for (const decision of winemakingDecisions) {
    if (ids.has(decision.id)) issues.push(`Duplicate winemaking decision: ${decision.id}`);
    ids.add(decision.id);
    if (!decision.stage || !decision.name || decision.options.length < 2) issues.push(`Incomplete winemaking decision: ${decision.id}`);
    for (const source of decision.sourceRefs ?? []) if (!researchSourceById.has(source)) issues.push(`Unknown source ${source} in ${decision.id}`);
    const optionIds = new Set<string>();
    for (const option of decision.options) {
      if (optionIds.has(option.id)) issues.push(`Duplicate option ${option.id} in ${decision.id}`);
      optionIds.add(option.id);
      for (const [axis, value] of Object.entries(option.matrix)) {
        if (!allowedAxes.has(axis as WinemakingAxis)) issues.push(`Unknown matrix axis ${axis} in ${decision.id}/${option.id}`);
        if (typeof value !== 'number' || value < -1 || value > 1) issues.push(`Invalid matrix value ${axis}=${String(value)} in ${decision.id}/${option.id}`);
      }
    }
  }

  return {
    decisions: winemakingDecisions.length,
    stages: new Set(winemakingDecisions.map((decision) => decision.stage)).size,
    options: winemakingDecisions.reduce((sum, decision) => sum + decision.options.length, 0),
    issues,
  };
}
