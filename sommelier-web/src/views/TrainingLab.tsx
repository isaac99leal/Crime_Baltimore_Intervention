import { useMemo, useState } from 'react';
import { auditWineProvenance, createAuditChallenge } from '../game/audit';
import { resolveAuditTraining, type AuditTrainingResult } from '../game/auditTraining';
import { wineById } from '../game/catalog';
import { simulateStaffBtgBlindTasting, type StaffBlindResult } from '../game/staffBlindTasting';
import type { GameState } from '../game/types';

type Props = {
  game: GameState;
  setGame: (updater: (state: GameState) => GameState) => void;
};

export function TrainingLab({ game, setGame }: Props) {
  const btgWines = useMemo(() => game.inventory
    .filter((item) => item.btg && item.bottles > 0)
    .map((item) => ({ item, wine: wineById.get(item.wineId) }))
    .filter((entry): entry is { item: typeof entry.item; wine: NonNullable<typeof entry.wine> } => Boolean(entry.wine)), [game.inventory]);
  const auditWines = useMemo(() => game.inventory
    .filter((item) => item.bottles > 0)
    .map((item) => wineById.get(item.wineId))
    .filter((wine): wine is NonNullable<typeof wine> => Boolean(wine)), [game.inventory]);

  const [staffId, setStaffId] = useState(() => game.staff[0]?.id ?? '');
  const [btgWineId, setBtgWineId] = useState(() => btgWines[0]?.wine.id ?? '');
  const [blindResult, setBlindResult] = useState<StaffBlindResult | null>(null);
  const [auditWineId, setAuditWineId] = useState(() => auditWines[0]?.id ?? '');
  const [auditResult, setAuditResult] = useState<AuditTrainingResult | null>(null);

  const auditWine = wineById.get(auditWineId);
  const audit = auditWine ? auditWineProvenance(auditWine) : undefined;
  const challenge = auditWine ? createAuditChallenge(auditWine) : undefined;
  const remainingTime = game.time.available - game.time.committed;

  const runBlind = () => {
    const outcome = simulateStaffBtgBlindTasting(game, staffId, btgWineId);
    if (!outcome) return;
    setGame(() => outcome.state);
    setBlindResult(outcome);
  };

  const answerAudit = (answer: string) => {
    if (!challenge || auditResult) return;
    const outcome = resolveAuditTraining(game, challenge, answer);
    setGame(() => outcome.state);
    setAuditResult(outcome);
  };

  return (
    <>
      <div className="panel">
        <div className="section-heading">
          <div><p className="eyebrow">Floor laboratory</p><h2>BTG staff blind</h2></div>
          <span className="badge">1.5h · {remainingTime}h free</span>
        </div>
        <p className="fine-print">Train against bottles that are physically in stock and currently enabled by the glass. Difficulty responds to age, rarity, product specificity and provenance complexity.</p>
        <div className="brief-grid">
          <div className="wide">
            <dt>Staff member</dt>
            <dd><select value={staffId} onChange={(event) => { setStaffId(event.target.value); setBlindResult(null); }}>
              {game.staff.map((person) => <option key={person.id} value={person.id}>{person.name} · wine {Math.round(person.wineKnowledge)}</option>)}
            </select></dd>
          </div>
          <div className="wide">
            <dt>BTG bottle</dt>
            <dd><select value={btgWineId} onChange={(event) => { setBtgWineId(event.target.value); setBlindResult(null); }}>
              {btgWines.map(({ wine }) => <option key={wine.id} value={wine.id}>{wine.vintage ?? 'NV'} {wine.label}</option>)}
            </select></dd>
          </div>
        </div>
        <button className="primary" disabled={!staffId || !btgWineId || remainingTime < 1.5} onClick={runBlind}>Run staff blind · 1.5h</button>
        {!btgWines.length && <p className="notice">No stocked BTG wine is available. Enable a bottle by the glass in Program first.</p>}
        {blindResult && <div className="result-card">
          <div className="score-line"><strong>{blindResult.correct ? 'Correct' : 'Missed'}</strong><span>difficulty {Math.round(blindResult.challenge.difficulty)}/100</span></div>
          <p>{blindResult.challenge.clues.join(' · ')}</p>
          <p><strong>Staff call:</strong> {blindResult.selectedOption}</p>
          <p><strong>Reveal:</strong> {blindResult.challenge.correctOption}</p>
          <small>Modeled success chance {blindResult.chancePct.toFixed(0)}% · knowledge gain +{blindResult.learningGain.toFixed(2)}</small>
          {blindResult.feedback.map((line) => <p className="fine-print" key={line}>{line}</p>)}
        </div>}
      </div>

      <div className="panel">
        <div className="section-heading">
          <div><p className="eyebrow">Research discipline</p><h2>Provenance audit drill</h2></div>
          <span className="badge">1h · {remainingTime}h free</span>
        </div>
        <p className="fine-print">Audit the bottle before repeating a legal, geographic or historical claim. The engine distinguishes identity failures from unresolved product law and merely derived simulation values.</p>
        <div className="brief-grid">
          <div className="wide">
            <dt>Inventory bottle</dt>
            <dd><select value={auditWineId} onChange={(event) => { setAuditWineId(event.target.value); setAuditResult(null); }}>
              {auditWines.map((wine) => <option key={wine.id} value={wine.id}>{wine.vintage ?? 'NV'} {wine.label} · {wine.grape}</option>)}
            </select></dd>
          </div>
          {audit && <>
            <div><dt>Audit band</dt><dd>{audit.band}</dd></div>
            <div><dt>Risk score</dt><dd>{Math.round(audit.riskScore * 100)}/100</dd></div>
          </>}
        </div>
        {challenge && <>
          <p><strong>{challenge.prompt}</strong></p>
          <div className="answer-grid">
            {challenge.options.map((option) => <button key={option} disabled={Boolean(auditResult) || remainingTime < 1} onClick={() => answerAudit(option)}>{option}</button>)}
          </div>
        </>}
        {auditResult && <div className="result-card">
          <div className="score-line"><strong>{auditResult.correct ? 'Correct escalation' : 'Audit miss'}</strong><span>+{auditResult.xpGain} XP</span></div>
          <p>{auditResult.explanation}</p>
          <small>Knowledge +{auditResult.knowledgeGain.toFixed(2)} · study time {auditResult.hoursSpent}h</small>
        </div>}
      </div>
    </>
  );
}
