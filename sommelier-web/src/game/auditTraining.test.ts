import { describe, expect, it } from 'vitest';
import { createAuditChallenge } from './audit';
import { resolveAuditTraining } from './auditTraining';
import { wineCatalog } from './catalog';
import { createInitialGame } from './engine';

describe('provenance audit training', () => {
  it('spends study time and awards more progress for a correct audit decision', () => {
    const state = createInitialGame();
    const wine = wineCatalog.find((candidate) => candidate.productResolutionStatus === 'unresolved') ?? wineCatalog[0];
    const challenge = createAuditChallenge(wine);
    const correct = resolveAuditTraining(state, challenge, challenge.correctOption);
    const wrongOption = challenge.options.find((option) => option !== challenge.correctOption) ?? challenge.correctOption;
    const wrong = resolveAuditTraining(state, challenge, wrongOption);

    expect(correct.correct).toBe(true);
    expect(correct.hoursSpent).toBe(1);
    expect(correct.state.time.study).toBe(state.time.study + 1);
    expect(correct.state.time.committed).toBe(state.time.committed + 1);
    expect(correct.xpGain).toBeGreaterThan(wrong.xpGain);
    expect(correct.knowledgeGain).toBeGreaterThan(wrong.knowledgeGain);
  });

  it('does not award progress when the weekly time budget is exhausted', () => {
    const base = createInitialGame();
    const state = { ...base, time: { ...base.time, committed: base.time.available } };
    const challenge = createAuditChallenge(wineCatalog[0]);
    const result = resolveAuditTraining(state, challenge, challenge.correctOption);

    expect(result.hoursSpent).toBe(0);
    expect(result.xpGain).toBe(0);
    expect(result.knowledgeGain).toBe(0);
    expect(result.state).toEqual(state);
  });
});
