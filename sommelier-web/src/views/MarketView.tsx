import { useMemo, useState } from 'react';
import { wineCatalog, worldWineBook } from '../game/catalog';
import { buyWine } from '../game/engine';
import { referenceCountries } from '../game/reference';
import type { GameState } from '../game/types';

const PAGE_SIZE = 48;

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

export function MarketView({ game, setGame }: { game: GameState; setGame: (updater: (state: GameState) => GameState) => void }) {
  const [query, setQuery] = useState('');
  const [country, setCountry] = useState('All');
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return wineCatalog.filter((wine) => {
      if (country !== 'All' && wine.country !== country) return false;
      if (!q) return true;
      return [wine.label, wine.producer, wine.grape, wine.region, wine.appellation, wine.vineyard, wine.country, wine.classification]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(q));
    });
  }, [country, query]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const visible = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  return (
    <section className="panel market-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Global buying book</p>
          <h2>Market</h2>
          <p>{worldWineBook.length.toLocaleString()} generated commercial offers inside the validated real-world reference framework.</p>
        </div>
        <div className="metric-inline"><span>Buying power</span><strong>{money(game.cash)}</strong></div>
      </div>

      <div className="market-toolbar">
        <input value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} placeholder="Search producer, grape, appellation, vineyard…" aria-label="Search wine market" />
        <select value={country} onChange={(event) => { setCountry(event.target.value); setPage(0); }} aria-label="Filter by country">
          <option>All</option>
          {referenceCountries.map((name) => <option key={name}>{name}</option>)}
        </select>
        <span className="result-count">{filtered.length.toLocaleString()} offers</span>
      </div>

      <div className="market-grid">
        {visible.map((wine) => (
          <article className="market-card" key={wine.id}>
            <div className="card-topline">
              <span>{wine.country}</span>
              <span>{wine.vintage ?? 'NV'}</span>
            </div>
            <h3>{wine.label}</h3>
            <p className="identity-line">{wine.grape} · {wine.appellation ?? wine.region}</p>
            {wine.classification && <p className="fine-print">{wine.classification}</p>}
            <div className="profile-row"><span>Body {wine.profile.body.toFixed(1)}</span><span>Acid {wine.profile.acidity.toFixed(1)}</span><span>Tannin {wine.profile.tannin.toFixed(1)}</span></div>
            <p className="aromas">{wine.aromas.slice(0, 5).join(' · ') || 'Reference profile pending additional tasting descriptors'}</p>
            <div className="card-facts"><span>Prestige {wine.prestige}</span><span>Rarity {wine.rarity ?? '—'}</span><span>{wine.productionCases?.toLocaleString() ?? '—'} cases</span></div>
            <div className="buy-row"><span><strong>{money(wine.cost)}</strong> wholesale</span><button className="primary" disabled={game.cash < wine.cost * 3} onClick={() => setGame((state) => buyWine(state, wine.id, 3))}>Buy 3 · {money(wine.cost * 3)}</button></div>
            {wine.fictional && <small className="provenance">Fictional producer · real reference geography and grape</small>}
          </article>
        ))}
      </div>

      <div className="pagination">
        <button disabled={safePage === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>Previous</button>
        <span>Page {safePage + 1} / {pages}</span>
        <button disabled={safePage >= pages - 1} onClick={() => setPage((value) => Math.min(pages - 1, value + 1))}>Next</button>
      </div>
    </section>
  );
}
