import { studyCertification, takeCertificationExam, trainStaff, upgradeEquipment, workSupplierRelationship } from '../game/systems';
import type { GameState } from '../game/types';

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

export function PeopleView({ game, setGame }: { game: GameState; setGame: (updater: (state: GameState) => GameState) => void }) {
  const remainingTime = game.time.available - game.time.committed;
  return (
    <section className="people-grid">
      <div className="panel">
        <div className="section-heading"><div><p className="eyebrow">Trade</p><h2>Relationships</h2></div><span className="badge">{remainingTime}h free</span></div>
        <div className="card-stack">
          {game.suppliers.map((supplier) => <article className="ops-card" key={supplier.id}>
            <div className="card-topline"><strong>{supplier.name}</strong><span>Relationship {Math.round(supplier.relationship)}</span></div>
            <p>{supplier.specialty}</p>
            <div className="progress-track"><div style={{ width: `${supplier.relationship}%` }} /></div>
            <div className="card-facts"><span>Reliability {supplier.reliability}</span><span>Allocation {Math.round(supplier.allocationAccess)}</span><span>Terms {supplier.paymentTermsDays}d</span></div>
            <button disabled={remainingTime < 3} onClick={() => setGame((state) => workSupplierRelationship(state, supplier.id))}>Taste / meet · 3h</button>
          </article>)}
        </div>
      </div>

      <div className="panel">
        <p className="eyebrow">Floor team</p><h2>Staff development</h2>
        <div className="card-stack">
          {game.staff.map((person) => <article className="ops-card" key={person.id}>
            <div className="card-topline"><strong>{person.name}</strong><span>{person.role}</span></div>
            <div className="card-facts"><span>Wine {Math.round(person.wineKnowledge)}</span><span>Service {Math.round(person.service)}</span><span>Sales {Math.round(person.sales)}</span><span>Morale {Math.round(person.morale)}</span></div>
            <div className="controls"><button onClick={() => setGame((state) => trainStaff(state, person.id, 'wine'))}>Wine · 4h</button><button onClick={() => setGame((state) => trainStaff(state, person.id, 'service'))}>Service · 4h</button><button onClick={() => setGame((state) => trainStaff(state, person.id, 'sales'))}>Sales · 4h</button></div>
          </article>)}
        </div>
      </div>

      <div className="panel">
        <p className="eyebrow">Capex</p><h2>Equipment</h2>
        <div className="card-stack">
          {game.equipment.map((item) => {
            const cost = Math.round(item.baseCost * Math.pow(1.7, item.level));
            return <article className="ops-card" key={item.id}>
              <div className="card-topline"><strong>{item.name}</strong><span>Level {item.level}/{item.maxLevel}</span></div>
              <p>{item.benefit}</p>
              <button disabled={item.level >= item.maxLevel || game.cash < cost} onClick={() => setGame((state) => upgradeEquipment(state, item.id))}>Upgrade · {money(cost)}</button>
            </article>;
          })}
        </div>
      </div>

      <div className="panel">
        <p className="eyebrow">Career capital</p><h2>Credentials</h2>
        <p className="fine-print">These are fictional game institutions inspired by professional service and wine-education pathways. They are not CMS or WSET credentials.</p>
        <div className="card-stack">
          {game.certifications.map((track) => <article className="ops-card" key={track.id}>
            <div className="card-topline"><strong>{track.school}</strong><span>Level {track.level}/{track.maxLevel}</span></div>
            <p>{track.title}</p>
            <div className="progress-track"><div style={{ width: `${track.progress}%` }} /></div>
            <div className="action-row"><button onClick={() => setGame((state) => studyCertification(state, track.id, 4))}>Study · 4h</button><button disabled={track.progress < 100} onClick={() => setGame((state) => takeCertificationExam(state, track.id).state)}>Exam · {money(track.examFee)}</button></div>
          </article>)}
        </div>
      </div>
    </section>
  );
}
