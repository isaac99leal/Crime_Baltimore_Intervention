import type { AuditChallenge } from './audit';
import type { GameState } from './types';

export type AuditTrainingResult = {
  state: GameState;
  correct: boolean;
  selectedOption: string;
  explanation: string;
  hoursSpent: number;
  xpGain: number;
  knowledgeGain: number;
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export function resolveAuditTraining(
  state: GameState,
  challenge: AuditChallenge,
  selectedOption: string,
): AuditTrainingResult {
  const correct = selectedOption === challenge.correctOption;
  const hours = 1;
  const canSpendTime = state.time.committed + hours <= state.time.available;
  const hoursSpent = canSpendTime ? hours : 0;
  const xpGain = canSpendTime ? (correct ? 14 : 5) : 0;
  const knowledgeGain = canSpendTime ? (correct ? 0.28 : 0.10) : 0;

  const next: GameState = canSpendTime ? {
    ...state,
    xp: state.xp + xpGain,
    knowledge: clamp(state.knowledge + knowledgeGain, 0, 10),
    time: {
      ...state.time,
      committed: state.time.committed + hours,
      study: state.time.study + hours,
    },
  } : state;

  return {
    state: next,
    correct,
    selectedOption,
    explanation: canSpendTime
      ? challenge.explanation
      : 'No free weekly time remained, so the audit was reviewed without awarding training progress.',
    hoursSpent,
    xpGain,
    knowledgeGain,
  };
}
