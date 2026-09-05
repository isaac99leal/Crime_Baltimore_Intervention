import { auditWineProvenance } from './audit';
import { wineById, wineCatalog } from './catalog';
import type { GameState, StaffMember, WineDefinition } from './types';

export type StaffBlindChallenge = {
  id: string;
  staffId: string;
  wineId: string;
  correctOption: string;
  options: string[];
  clues: string[];
  difficulty: number;
};

export type StaffBlindResult = {
  state: GameState;
  challenge: StaffBlindChallenge;
  selectedOption: string;
  correct: boolean;
  chancePct: number;
  rollPct: number;
  learningGain: number;
  feedback: string[];
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

function hash01(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967295;
}

function identityOption(wine: WineDefinition): string {
  return `${wine.grape} — ${wine.country}`;
}

function sameBlindFamily(a: WineDefinition, b: WineDefinition): boolean {
  if (a.id === b.id) return false;
  if (a.color && b.color) return a.color === b.color;
  return Math.abs(a.profile.body - b.profile.body) <= 1.2 && Math.abs(a.profile.acidity - b.profile.acidity) <= 1.2;
}

function distractorsFor(wine: WineDefinition): string[] {
  const correct = identityOption(wine);
  const seen = new Set([correct]);
  const options: string[] = [];
  for (const candidate of wineCatalog) {
    if (!sameBlindFamily(wine, candidate)) continue;
    const option = identityOption(candidate);
    if (seen.has(option)) continue;
    seen.add(option);
    options.push(option);
    if (options.length >= 8) break;
  }
  return options;
}

function tastingClues(wine: WineDefinition): string[] {
  const clues = [
    `Acidity ${wine.profile.acidity.toFixed(1)}/5; tannin ${wine.profile.tannin.toFixed(1)}/5; body ${wine.profile.body.toFixed(1)}/5`,
    `Fruit intensity ${wine.profile.fruitIntensity.toFixed(1)}/5; earth/savory ${wine.profile.earthIntensity.toFixed(1)}/5`,
  ];
  if (wine.profile.alcohol !== undefined) clues.push(`Approximate structural alcohol ${wine.profile.alcohol.toFixed(1)}%`);
  if (wine.aromas.length) clues.push(`Aromas: ${wine.aromas.slice(0, 4).join(', ')}`);
  if (wine.agePhase) clues.push(`Observed development phase: ${wine.agePhase}`);
  return clues;
}

function challengeDifficulty(wine: WineDefinition): number {
  const rarity = wine.rarity ?? 3;
  const age = Math.min(wine.ageYears ?? 0, 100);
  const provenance = wine.provenanceRisk ?? 0;
  const blendPenalty = wine.blend && wine.blend.length > 1 ? 6 : 0;
  const obscureProduct = wine.productResolutionStatus === 'resolved' && wine.productName ? 4 : 0;
  return clamp(24 + wine.prestige * 0.22 + rarity * 2.2 + age * 0.13 + provenance * 10 + blendPenalty + obscureProduct, 20, 92);
}

function staffAbility(staff: StaffMember): number {
  return clamp(staff.wineKnowledge * 0.78 + staff.service * 0.08 + Math.sqrt(Math.max(staff.trainingHours, 0)) * 1.5, 5, 98);
}

export function createStaffBtgBlindChallenge(state: GameState, staffId: string, wineId: string): StaffBlindChallenge | undefined {
  const staff = state.staff.find((person) => person.id === staffId);
  const item = state.inventory.find((candidate) => candidate.wineId === wineId);
  const wine = wineById.get(wineId);
  if (!staff || !item?.btg || !wine || item.bottles <= 0) return undefined;

  const correctOption = identityOption(wine);
  const distractors = distractorsFor(wine);
  if (distractors.length < 3) return undefined;
  const start = Math.floor(hash01(`${state.week}|${staffId}|${wineId}|options`) * Math.max(1, distractors.length - 2));
  const options = [correctOption, ...distractors.slice(start, start + 3)].sort((a, b) => a.localeCompare(b));
  return {
    id: `btg-blind:${state.week}:${staffId}:${wineId}`,
    staffId,
    wineId,
    correctOption,
    options,
    clues: tastingClues(wine),
    difficulty: challengeDifficulty(wine),
  };
}

function applyTrainingResult(state: GameState, staffId: string, correct: boolean, learningGain: number): GameState {
  const hours = 1.5;
  return {
    ...state,
    time: {
      ...state.time,
      committed: state.time.committed + hours,
      training: state.time.training + hours,
    },
    staff: state.staff.map((person) => person.id === staffId ? {
      ...person,
      wineKnowledge: clamp(person.wineKnowledge + learningGain, 0, 100),
      service: clamp(person.service + learningGain * 0.12, 0, 100),
      morale: clamp(person.morale + (correct ? 0.7 : -0.2), 0, 100),
      trainingHours: person.trainingHours + hours,
    } : person),
  };
}

export function simulateStaffBtgBlindTasting(state: GameState, staffId: string, wineId: string): StaffBlindResult | undefined {
  const trainingHours = 1.5;
  if (state.time.committed + trainingHours > state.time.available) return undefined;

  const challenge = createStaffBtgBlindChallenge(state, staffId, wineId);
  const staff = state.staff.find((person) => person.id === staffId);
  const wine = wineById.get(wineId);
  if (!challenge || !staff || !wine) return undefined;

  const ability = staffAbility(staff);
  const chancePct = clamp(50 + (ability - challenge.difficulty) * 0.72, 8, 97);
  const rollPct = hash01(`${challenge.id}|${staff.trainingHours}|result`) * 100;
  const correct = rollPct <= chancePct;
  const wrongOptions = challenge.options.filter((option) => option !== challenge.correctOption);
  const wrongIndex = Math.floor(hash01(`${challenge.id}|wrong`) * wrongOptions.length);
  const selectedOption = correct ? challenge.correctOption : wrongOptions[wrongIndex];
  const learningGain = clamp((correct ? 0.55 : 1.35) + challenge.difficulty / 100, 0.5, 2.4);
  const audit = auditWineProvenance(wine);
  const feedback = [
    correct ? 'Correct blind identification.' : `Missed: revealed identity is ${challenge.correctOption}.`,
    `Difficulty ${challenge.difficulty.toFixed(0)}/100; staff success chance ${chancePct.toFixed(0)}%.`,
  ];
  if (audit.band === 'high' || audit.band === 'critical') {
    feedback.push(`Post-reveal provenance audit: ${audit.band} research/audit risk; review before staff repeats product-law claims.`);
  }
  if (wine.productName) feedback.push(`Post-reveal product: ${wine.productName}.`);

  return {
    state: applyTrainingResult(state, staffId, correct, learningGain),
    challenge,
    selectedOption,
    correct,
    chancePct,
    rollPct,
    learningGain,
    feedback,
  };
}
