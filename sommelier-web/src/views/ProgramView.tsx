import { wineById } from '../game/catalog';
import { changePrice, toggleListing } from '../game/engine';
import { changeBtgPrice, reprintWineList, sellBtgPour, toggleBtg } from '../game/systems';
import type { GameState } from '../game/types';

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

export function ProgramView({ game, setGame }: { game: GameState; setGame: (updater: (state: GameState) => GameState) => void }) {
  const btg = game.inventory.filter((item) => item.btg && item.bottles > 0);
  const bottles = game.inventory.reduce((sum, item) => sum + item.bottles, 0);
  const remainingTime = game.time.available - game.time.committed;

  return (
    <section className="stack-layout">
      <div className="panel">
        <div className="section-heading">
          <div><p className="eyebrow">Published program</p><h2>Wine list & BTG</h2></div>
          <span className={`status ${game.wineList.dirty ? 'warn' : 'on'}`}>{game.wineList.dirty ? 'Reprint required' : `Revision ${game.wineList.revision}`}</span>
        </div>
        <div className="metric-grid four">
          <Metric label="Bottles in house" value={bottles.toLocaleString()} />
          <Metric label="BTG selections" value={String(btg.length)} />
          <Metric label="List pages" value={String(game.wineList.pages)} />
          <Metric label="Hours uncommitted" value={String(remainingTime)} />
        </div>
        <div className="action-row">
          <button className="primary" disabled={!game.wineList.dirty} onClick={() => setGame((state) => reprintWineList(state).state)}>Publish & reprint list</button>
          <span className="fine-print">Printing has a cash cost and consumes admin time. Price/list/BTG changes mark the current list stale.</span>
        </div>
      </div>

      <div className="panel">
        <div className="section-heading"><div><p className="eyebrow">Cellar operations</p><h2>Inventory controls</h2></div><span className="badge">{game.inventory.length} SKUs</span></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Wine</th><th>Location</th><th>Stock</th><th>Bottle</th><th>BTG</th><th>Program controls</th></tr></thead>
            <tbody>
              {game.inventory.map((item) => {
                const wine = wineById.get(item.wineId);
                if (!wine) return null;
                return <tr key={item.wineId}>
                  <td><strong>{wine.vintage ?? ''} {wine.label}</strong><small>{wine.grape} · {wine.appellation ?? wine.region}</small></td>
                  <td>{item.bin ?? '—'}<small>{item.storageZone ?? 'unassigned'}</small></td>
                  <td>{item.bottles}<small>{item.openBottleMl ? `${item.openBottleMl} ml open` : 'no open bottle'}</small></td>
                  <td>{money(item.listPrice)}<small>{item.listed ? 'on list' : item.offMenu ? 'off-menu' : 'cellar only'}</small></td>
                  <td>{item.btg ? `${money(item.btgPrice ?? 0)} / ${(item.btgPourMl ?? 150)}ml` : '—'}</td>
                  <td className="controls">
                    <button onClick={() => setGame((state) => toggleListing(state, item.wineId))}>{item.listed ? 'Pull' : 'List'}</button>
                    <button onClick={() => setGame((state) => changePrice(state, item.wineId, 5))}>Bottle +$5</button>
                    <button onClick={() => setGame((state) => toggleBtg(state, item.wineId))}>{item.btg ? 'Remove BTG' : 'Add BTG'}</button>
                    {item.btg && <button onClick={() => setGame((state) => changeBtgPrice(state, item.wineId, 1))}>Glass +$1</button>}
                    {item.btg && <button onClick={() => setGame((state) => sellBtgPour(state, item.wineId).state)}>Ring 1 glass</button>}
                  </td>
                </tr>;
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}
