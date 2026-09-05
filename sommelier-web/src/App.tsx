import { useEffect, useMemo, useState } from 'react';
import { wineById, wineCatalog, worldWineBook } from './game/catalog';
import {
  advanceWeek,
  changePrice,
  createInitialGame,
  generateServiceScenario,
  makeTastingChallenge,
  recommendWine,
  resolveTasting,
  toggleListing,
} from './game/engine';
import { grapeReference, referenceCountries, referencePlaces, referenceVineyards } from './game/reference';
import type { GameState, ServiceResult, TastingChallenge } from './game/types';
import { MarketView } from './views/MarketView';
import { PeopleView } from './views/PeopleView';
import { ProgramView } from './views/ProgramView';

const SAVE_KEY = 'sommelier-web-v2-save';
type View = 'service' | 'cellar' | 'program' | 'market' | 'tasting' | 'people' | 'office';

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

function migrateGame(saved: Partial<GameState>): GameState {
  const base = createInitialGame();
  return {
    ...base,
    ...saved,
    restaurant: { ...base.restaurant, ...(saved.restaurant ?? {}) },
    wineList: { ...base.wineList, ...(saved.wineList ?? {}) },
    time: { ...base.time, ...(saved.time ?? {}) },
    inventory: Array.isArray(saved.inventory) ? saved.inventory : base.inventory,
    suppliers: Array.isArray(saved.suppliers) ? saved.suppliers : base.suppliers,
    allocations: Array.isArray(saved.allocations) ? saved.allocations : base.allocations,
    staff: Array.isArray(saved.staff) ? saved.staff : base.staff,
    equipment: Array.isArray(saved.equipment) ? saved.equipment : base.equipment,
    certifications: Array.isArray(saved.certifications) ? saved.certifications : base.certifications,
  };
}

function loadGame(): GameState {
  try {
    const saved = localStorage.getItem(SAVE_KEY);
    return saved ? migrateGame(JSON.parse(saved) as Partial<GameState>) : createInitialGame();
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
  const remainingHours = game.time.available - game.time.committed;

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
    setWeekNote(`Week ${game.week} closed. Payroll, maintenance, and overhead: ${money(outcome.overhead)}.`);
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
        <div className="brand-block">
          <p className="eyebrow">Beverage director simulation</p>
          <h1>Sommelier</h1>
          <p className="brand-subtitle">Build the program. Run service. Manage the cellar. Earn the list.</p>
        </div>
        <div className="stat-strip" aria-label="Game statistics">
          <Stat label="Week" value={String(game.week)} />
          <Stat label="Cash" value={money(game.cash)} />
          <Stat label="Reputation" value={`${Math.round(game.reputation)}/100`} />
          <Stat label="Free time" value={`${remainingHours}h`} />
        </div>
      </header>

      <nav className="nav-tabs" aria-label="Game sections">
        {([
          ['service', 'Service'],
          ['cellar', 'Cellar'],
          ['program', 'Program'],
          ['market', 'Market'],
          ['tasting', 'Blind Tasting'],
          ['people', 'People & Trade'],
          ['office', 'Office'],
        ] as [View, string][]).map(([id, label]) => (
          <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>{label}</button>
        ))}
      </nav>

      <main>
        {view === 'service' && (
          <section className="page-grid">
            <div className="panel brief-panel">
              <div className="section-heading"><div><p className="eyebrow">Table brief</p><h2>{scenario.guest.name}</h2></div>{scenario.guest.occasion && <span className="badge">{scenario.guest.occasion}</span>}</div>
              <p>{scenario.guest.description}</p>
              <dl className="brief-grid">
                <div><dt>Budget ceiling</dt><dd>{money(scenario.guest.budget)}</dd></div>
                <div><dt>Wine fluency</dt><dd>{Math.round((scenario.guest.wineKnowledge ?? 0.5) * 100)}/100</dd></div>
                <div className="wide"><dt>Dish</dt><dd><strong>{scenario.dish.name}</strong><br />{scenario.dish.detail}</dd></div>
                <div className="wide"><dt>Guest cue</dt><dd>“{scenario.guest.hint}”</dd></div>
              </dl>
              {serviceResult ? (
                <div className="result-card">
                  <div className="score-line"><strong>{serviceResult.score}/100</strong><span>service outcome</span></div>
                  <p>{serviceResult.summary}</p>
                  <small>{money(serviceResult.revenue)} revenue · {money(serviceResult.tip)} tip · reputation {serviceResult.reputationDelta >= 0 ? '+' : ''}{serviceResult.reputationDelta}</small>
                  <button className="primary" onClick={newTable}>Seat next table</button>
                </div>
              ) : (
                <p className="instruction">Choose one bottle from the published list. Pairing, budget, guest preference, structure, and prestige affect the result.</p>
              )}
            </div>

            <div className="panel">
              <div className="section-heading">
                <div><p className="eyebrow">Published list</p><h2>Recommend</h2></div>
                <span className="badge">{listed.length} available</span>
              </div>
              <div className="wine-list">
                {listed.map((item) => {
                  const wine = wineById.get(item.wineId);
                  if (!wine) return null;
                  return (
                    <article className="wine-card" key={wine.id}>
                      <div className="card-topline"><span>{wine.vintage ?? 'NV'} · {wine.country}</span><span>{money(item.listPrice)}</span></div>
                      <h3>{wine.label}</h3>
                      <p>{wine.grape} · {wine.appellation ?? wine.region}</p>
                      <div className="wine-meta"><span>{item.bottles} btls</span>{item.btg && <span>BTG {money(item.btgPrice ?? 0)}</span>}</div>
                      <p className="aromas">{wine.aromas.slice(0, 4).join(' · ')}</p>
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
              <div><p className="eyebrow">Physical inventory</p><h2>Cellar</h2></div>
              <div className="metric-inline"><span>Inventory at cost</span><strong>{money(cellarValue)}</strong></div>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Wine</th><th>Lot / bin</th><th>Storage</th><th>Stock</th><th>List price</th><th>Status</th><th>Quick controls</th></tr></thead>
                <tbody>
                  {game.inventory.map((item) => {
                    const wine = wineById.get(item.wineId);
                    if (!wine) return null;
                    return (
                      <tr key={item.wineId}>
                        <td><strong>{wine.vintage ?? ''} {wine.label}</strong><small>{wine.grape} · {wine.appellation ?? wine.region}</small></td>
                        <td>{item.lotId ?? 'legacy'}<small>{item.bin ?? 'unassigned'}</small></td>
                        <td>{item.storageZone ?? 'service-cellar'}<small>condition {Math.round(item.condition ?? 100)}%</small></td>
                        <td>{item.bottles}<small>par {item.par ?? '—'}</small></td>
                        <td>{money(item.listPrice)}</td>
                        <td><span className={item.listed ? 'status on' : 'status'}>{item.listed ? 'Listed' : item.offMenu ? 'Off-menu' : 'Cellar'}</span></td>
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

        {view === 'program' && <ProgramView game={game} setGame={setGame} />}
        {view === 'market' && <MarketView game={game} setGame={setGame} />}

        {view === 'tasting' && (
          <section className="page-grid tasting-layout">
            <div className="panel">
              <p className="eyebrow">Blind flight</p>
              <h2>Deduce the grape</h2>
              <dl className="brief-grid">
                <div><dt>Acidity</dt><dd>{challenge.wine.profile.acidity.toFixed(1)}/5</dd></div>
                <div><dt>Body</dt><dd>{challenge.wine.profile.body.toFixed(1)}/5</dd></div>
                <div><dt>Tannin</dt><dd>{challenge.wine.profile.tannin.toFixed(1)}/5</dd></div>
                <div><dt>Sweetness</dt><dd>{challenge.wine.profile.sweetness.toFixed(1)}/5</dd></div>
                <div className="wide"><dt>Aromas</dt><dd>{challenge.wine.aromas.join(', ')}</dd></div>
              </dl>
              <p className="fine-print">The current exercise tests variety recognition. Region, climate, vintage, quality, fault, and service deductions will become separate stages.</p>
            </div>
            <div className="panel">
              <div className="section-heading"><div><p className="eyebrow">Your call</p><h2>Identity</h2></div><span className="badge">{game.tastingCorrect}/{game.tastingTotal} · {tastingPct}%</span></div>
              <div className="answer-grid">
                {challenge.options.map((option) => <button key={option} disabled={Boolean(tastingVerdict)} onClick={() => answerTasting(option)}>{option}</button>)}
              </div>
              {tastingVerdict && <div className="result-card"><strong>{tastingVerdict}</strong><p>{challenge.wine.notes?.identity ?? challenge.wine.story}</p><button className="primary" onClick={nextTasting}>Next wine</button></div>}
            </div>
          </section>
        )}

        {view === 'people' && <PeopleView game={game} setGame={setGame} />}

        {view === 'office' && (
          <section className="stack-layout">
            <div className="panel">
              <div className="section-heading"><div><p className="eyebrow">Business</p><h2>Beverage office</h2></div><span className="badge">Trust {Math.round(game.restaurant.managementTrust)}/100</span></div>
              <div className="metric-grid four">
                <Metric label="Lifetime revenue" value={money(game.lifetimeRevenue)} />
                <Metric label="COGS" value={money(game.cogs)} />
                <Metric label="BTG revenue" value={money(game.btgSales)} />
                <Metric label="Tables served" value={String(game.serviceCount)} />
                <Metric label="Experience" value={`${game.xp} XP`} />
                <Metric label="Cellar at cost" value={money(cellarValue)} />
                <Metric label="List revisions" value={String(game.wineList.revision)} />
                <Metric label="Reprint spend" value={money(game.wineList.reprintSpend)} />
              </div>
              <button className="primary large" onClick={closeWeek}>Close week {game.week}</button>
              {weekNote && <p className="notice">{weekNote}</p>}
            </div>

            <div className="panel">
              <p className="eyebrow">Reference world</p><h2>Data depth</h2>
              <div className="metric-grid four">
                <Metric label="Real grape records" value={grapeReference.length.toLocaleString()} />
                <Metric label="Countries loaded" value={referenceCountries.length.toLocaleString()} />
                <Metric label="Places / appellations" value={referencePlaces.length.toLocaleString()} />
                <Metric label="Named vineyards / crus" value={referenceVineyards.length.toLocaleString()} />
                <Metric label="Commercial wine book" value={worldWineBook.length.toLocaleString()} />
                <Metric label="Total catalog objects" value={wineCatalog.length.toLocaleString()} />
              </div>
              <p className="fine-print">Real places and grapes come from the curated reference layer. Generated producers and cuvées are fictional. Historical vintage weather is not invented when no curated record exists.</p>
            </div>

            <div className="panel">
              <p className="eyebrow">Career</p><h2>Operating constraints</h2>
              <Progress label="Reputation" value={game.reputation} target={100} />
              <Progress label="Management trust" value={game.restaurant.managementTrust} target={100} />
              <Progress label="Knowledge" value={Math.min(game.knowledge * 10, 100)} target={100} />
              <Progress label="Weekly time committed" value={game.time.committed} target={game.time.available} />
              <hr />
              <button className="danger" onClick={resetGame}>Start a fresh career</button>
            </div>
          </section>
        )}
      </main>

      <footer>Development build · deterministic real-reference wine world · browser save is automatic</footer>
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
  return <div className="progress-block"><div><span>{label}</span><strong>{Math.round(value)} / {Math.round(target)}</strong></div><div className="progress-track"><div style={{ width: `${pct}%` }} /></div></div>;
}
