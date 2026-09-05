import { useEffect, useMemo, useState } from 'react';
import { wineById, wineCatalog } from './game/catalog';
import {
  advanceWeek,
  buyWine,
  changePrice,
  createInitialGame,
  generateServiceScenario,
  makeTastingChallenge,
  recommendWine,
  resolveTasting,
  toggleListing,
} from './game/engine';
import type { GameState, ServiceResult, TastingChallenge } from './game/types';

const SAVE_KEY = 'sommelier-web-v2-save';
type View = 'service' | 'cellar' | 'market' | 'tasting' | 'office';

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

function loadGame(): GameState {
  try {
    const saved = localStorage.getItem(SAVE_KEY);
    return saved ? JSON.parse(saved) as GameState : createInitialGame();
  } catch {
    return createInitialGame();
  }
}

export default function App() {
  const [game, setGame] = useState<GameState>(loadGame);
  const [view, setView] = useState<View>('service');
  const [scenario, setScenario] = useState(generateServiceScenario);
  const [serviceResult, setServiceResult] = useState<ServiceResult | null>(null);
  const [challenge, setChallenge] = useState<TastingChallenge>(makeTastingChallenge);
  const [tastingVerdict, setTastingVerdict] = useState<string | null>(null);
  const [weekNote, setWeekNote] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem(SAVE_KEY, JSON.stringify(game));
  }, [game]);

  const listed = useMemo(() => game.inventory.filter((item) => item.listed && item.bottles > 0), [game.inventory]);
  const cellarValue = game.inventory.reduce((sum, item) => sum + (wineById.get(item.wineId)?.cost ?? 0) * item.bottles, 0);
  const tastingPct = game.tastingTotal ? Math.round((game.tastingCorrect / game.tastingTotal) * 100) : 0;

  const newTable = () => {
    setScenario(generateServiceScenario());
    setServiceResult(null);
  };

  const serve = (wineId: string) => {
    const outcome = recommendWine(game, scenario, wineId);
    setGame(outcome.state);
    setServiceResult(outcome.result);
  };

  const answerTasting = (answer: string) => {
    if (tastingVerdict) return;
    const outcome = resolveTasting(game, challenge, answer);
    setGame(outcome.state);
    setTastingVerdict(outcome.correct ? `Correct — ${challenge.wine.grape}.` : `Not quite. This was ${challenge.wine.grape}.`);
  };

  const nextTasting = () => {
    setChallenge(makeTastingChallenge());
    setTastingVerdict(null);
  };

  const closeWeek = () => {
    const outcome = advanceWeek(game);
    setGame(outcome.state);
    setWeekNote(`Week ${game.week} closed. Operating overhead: ${money(outcome.overhead)}.`);
  };

  const resetGame = () => {
    const next = createInitialGame();
    setGame(next);
    setScenario(generateServiceScenario());
    setServiceResult(null);
    setTastingVerdict(null);
    setWeekNote(null);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Beverage director simulation</p>
          <h1>Sommelier</h1>
        </div>
        <div className="stat-strip" aria-label="Game statistics">
          <Stat label="Week" value={String(game.week)} />
          <Stat label="Cash" value={money(game.cash)} />
          <Stat label="Reputation" value={`${Math.round(game.reputation)}/100`} />
          <Stat label="Knowledge" value={game.knowledge.toFixed(1)} />
        </div>
      </header>

      <nav className="nav-tabs" aria-label="Game sections">
        {([
          ['service', 'Dining Room'],
          ['cellar', 'Cellar'],
          ['market', 'Wine Market'],
          ['tasting', 'Blind Tasting'],
          ['office', 'Office'],
        ] as [View, string][]).map(([id, label]) => (
          <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>{label}</button>
        ))}
      </nav>

      <main>
        {view === 'service' && (
          <section className="page-grid">
            <div className="panel brief-panel">
              <p className="eyebrow">Table brief</p>
              <h2>{scenario.guest.name}</h2>
              <p>{scenario.guest.description}</p>
              <dl className="brief-grid">
                <div><dt>Budget ceiling</dt><dd>{money(scenario.guest.budget)}</dd></div>
                <div><dt>Dish</dt><dd>{scenario.dish.name}</dd></div>
                <div className="wide"><dt>Plate</dt><dd>{scenario.dish.detail}</dd></div>
                <div className="wide"><dt>Guest cue</dt><dd>“{scenario.guest.hint}”</dd></div>
              </dl>
              {serviceResult ? (
                <div className={`result-card score-${Math.floor(serviceResult.score / 20)}`}>
                  <strong>{serviceResult.score}/100</strong>
                  <p>{serviceResult.summary}</p>
                  <small>{money(serviceResult.revenue)} revenue · {money(serviceResult.tip)} tip · reputation {serviceResult.reputationDelta >= 0 ? '+' : ''}{serviceResult.reputationDelta}</small>
                  <button className="primary" onClick={newTable}>Seat next table</button>
                </div>
              ) : (
                <p className="instruction">Choose one bottle from your active list. Pairing, budget, guest preference, and bottle prestige all affect the result.</p>
              )}
            </div>

            <div className="panel">
              <div className="section-heading">
                <div><p className="eyebrow">Active list</p><h2>Recommend a bottle</h2></div>
                <span className="badge">{listed.length} available</span>
              </div>
              <div className="wine-list">
                {listed.map((item) => {
                  const wine = wineById.get(item.wineId)!;
                  return (
                    <article className="wine-card" key={wine.id}>
                      <div><h3>{wine.label}</h3><p>{wine.grape} · {wine.region}</p></div>
                      <div className="wine-meta"><span>{money(item.listPrice)}</span><span>{item.bottles} btls</span></div>
                      <p className="aromas">{wine.aromas.slice(0, 3).join(' · ')}</p>
                      <button className="primary" disabled={Boolean(serviceResult)} onClick={() => serve(wine.id)}>Recommend</button>
                    </article>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {view === 'cellar' && (
          <section className="panel">
            <div className="section-heading">
              <div><p className="eyebrow">Inventory control</p><h2>Cellar</h2></div>
              <span className="badge">Cost value {money(cellarValue)}</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Wine</th><th>Stock</th><th>List price</th><th>Status</th><th>Controls</th></tr></thead>
                <tbody>
                  {game.inventory.map((item) => {
                    const wine = wineById.get(item.wineId)!;
                    return (
                      <tr key={item.wineId}>
                        <td><strong>{wine.label}</strong><small>{wine.grape} · {wine.region}</small></td>
                        <td>{item.bottles}</td>
                        <td>{money(item.listPrice)}</td>
                        <td><span className={item.listed ? 'status on' : 'status'}>{item.listed ? 'Listed' : 'Cellar'}</span></td>
                        <td className="controls">
                          <button onClick={() => setGame((state) => changePrice(state, item.wineId, -5))}>− $5</button>
                          <button onClick={() => setGame((state) => changePrice(state, item.wineId, 5))}>+ $5</button>
                          <button onClick={() => setGame((state) => toggleListing(state, item.wineId))}>{item.listed ? 'Pull' : 'List'}</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {view === 'market' && (
          <section className="panel">
            <div className="section-heading">
              <div><p className="eyebrow">Wholesale allocation</p><h2>Wine Market</h2></div>
              <span className="badge">Buying power {money(game.cash)}</span>
            </div>
            <div className="market-grid">
              {wineCatalog.map((wine) => (
                <article className="market-card" key={wine.id}>
                  <p className="country">{wine.country} · {wine.region}</p>
                  <h3>{wine.label}</h3>
                  <p>{wine.grape}</p>
                  <div className="profile-row"><span>Body {wine.profile.body.toFixed(1)}</span><span>Acid {wine.profile.acidity.toFixed(1)}</span><span>Tannin {wine.profile.tannin.toFixed(1)}</span></div>
                  <p className="aromas">{wine.aromas.slice(0, 4).join(' · ')}</p>
                  <div className="buy-row"><span>{money(wine.cost)} wholesale</span><button className="primary" disabled={game.cash < wine.cost * 3} onClick={() => setGame((state) => buyWine(state, wine.id, 3))}>Buy 3 · {money(wine.cost * 3)}</button></div>
                </article>
              ))}
            </div>
          </section>
        )}

        {view === 'tasting' && (
          <section className="page-grid tasting-layout">
            <div className="panel tasting-glass">
              <p className="eyebrow">Blind flight</p>
              <h2>Identify the grape</h2>
              <div className="glass-mark" aria-hidden="true">◯</div>
              <dl className="brief-grid">
                <div><dt>Acidity</dt><dd>{challenge.wine.profile.acidity.toFixed(1)}/5</dd></div>
                <div><dt>Body</dt><dd>{challenge.wine.profile.body.toFixed(1)}/5</dd></div>
                <div><dt>Tannin</dt><dd>{challenge.wine.profile.tannin.toFixed(1)}/5</dd></div>
                <div><dt>Sweetness</dt><dd>{challenge.wine.profile.sweetness.toFixed(1)}/5</dd></div>
                <div className="wide"><dt>Aromas</dt><dd>{challenge.wine.aromas.join(', ')}</dd></div>
              </dl>
            </div>
            <div className="panel">
              <div className="section-heading"><div><p className="eyebrow">Deduction</p><h2>Your call</h2></div><span className="badge">{game.tastingCorrect}/{game.tastingTotal} · {tastingPct}%</span></div>
              <div className="answer-grid">
                {challenge.options.map((option) => <button key={option} disabled={Boolean(tastingVerdict)} onClick={() => answerTasting(option)}>{option}</button>)}
              </div>
              {tastingVerdict && <div className="result-card"><strong>{tastingVerdict}</strong><p>{challenge.wine.story}</p><button className="primary" onClick={nextTasting}>Next wine</button></div>}
            </div>
          </section>
        )}

        {view === 'office' && (
          <section className="page-grid">
            <div className="panel">
              <p className="eyebrow">P&L and progression</p>
              <h2>Beverage office</h2>
              <div className="metric-grid">
                <Metric label="Lifetime revenue" value={money(game.lifetimeRevenue)} />
                <Metric label="Tables served" value={String(game.serviceCount)} />
                <Metric label="Experience" value={`${game.xp} XP`} />
                <Metric label="Cellar at cost" value={money(cellarValue)} />
              </div>
              <p className="instruction">Closing the week pays operating overhead. Future versions will add labor, allocations, critic visits, producer relationships, menu changes, debt, and restaurant growth.</p>
              <button className="primary large" onClick={closeWeek}>Close week {game.week}</button>
              {weekNote && <p className="notice">{weekNote}</p>}
            </div>
            <div className="panel">
              <p className="eyebrow">Career targets</p>
              <h2>Path to the top</h2>
              <Progress label="Reputation" value={game.reputation} target={100} />
              <Progress label="Knowledge" value={Math.min(game.knowledge * 10, 100)} target={100} />
              <Progress label="Service volume" value={Math.min(game.serviceCount * 2, 100)} target={100} />
              <hr />
              <button className="danger" onClick={resetGame}>Start a fresh career</button>
            </div>
          </section>
        )}
      </main>

      <footer>Prototype v0.1 · Browser save is automatic · Original Pygame version remains untouched</footer>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="stat"><span>{label}</span><strong>{value}</strong></div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function Progress({ label, value, target }: { label: string; value: number; target: number }) {
  const pct = Math.round(Math.min(100, (value / target) * 100));
  return <div className="progress-block"><div><span>{label}</span><strong>{pct}%</strong></div><div className="progress-track"><div style={{ width: `${pct}%` }} /></div></div>;
}
