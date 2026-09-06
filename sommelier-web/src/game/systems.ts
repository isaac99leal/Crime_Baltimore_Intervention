import { wineById } from './catalog';
import type { GameState } from './types';

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

function spendTime(state: GameState, hours: number, bucket: keyof Pick<GameState['time'], 'admin' | 'study' | 'relationships' | 'training'>): GameState | undefined {
  if (hours <= 0 || state.time.committed + hours > state.time.available) return undefined;
  return {
    ...state,
    time: {
      ...state.time,
      committed: state.time.committed + hours,
      [bucket]: state.time[bucket] + hours,
    },
  };
}

export function toggleBtg(state: GameState, wineId: string): GameState {
  const target = state.inventory.find((item) => item.wineId === wineId);
  if (!target) return state;
  const wine = wineById.get(wineId);
  const defaultPrice = Math.max(8, Math.round((target.listPrice || wine?.suggestedPrice || 40) / 4.2));
  return {
    ...state,
    wineList: { ...state.wineList, dirty: true },
    inventory: state.inventory.map((item) => item.wineId === wineId ? {
      ...item,
      btg: !item.btg,
      btgPrice: item.btgPrice ?? defaultPrice,
      btgPourMl: item.btgPourMl ?? 150,
      storageZone: !item.btg ? 'bar' : item.storageZone,
    } : item),
  };
}

export function changeBtgPrice(state: GameState, wineId: string, delta: number): GameState {
  return {
    ...state,
    wineList: { ...state.wineList, dirty: true },
    inventory: state.inventory.map((item) => item.wineId === wineId ? { ...item, btgPrice: Math.max(5, (item.btgPrice ?? 12) + delta) } : item),
  };
}

export function sellBtgPour(state: GameState, wineId: string): { state: GameState; revenue: number; wasteMl: number } {
  const item = state.inventory.find((candidate) => candidate.wineId === wineId);
  const wine = wineById.get(wineId);
  if (!item?.btg || !wine || item.bottles <= 0) return { state, revenue: 0, wasteMl: 0 };
  const pour = item.btgPourMl ?? 150;
  let bottles = item.bottles;
  let open = item.openBottleMl ?? 0;
  if (open < pour) {
    if (bottles <= 0) return { state, revenue: 0, wasteMl: 0 };
    bottles -= 1;
    open += 750;
  }
  open -= pour;
  const revenue = item.btgPrice ?? 12;
  return {
    revenue,
    wasteMl: 0,
    state: {
      ...state,
      cash: state.cash + revenue,
      lifetimeRevenue: state.lifetimeRevenue + revenue,
      btgSales: state.btgSales + revenue,
      inventory: state.inventory.map((candidate) => candidate.wineId === wineId ? { ...candidate, bottles, openBottleMl: open } : candidate),
    },
  };
}

export function reprintWineList(state: GameState): { state: GameState; cost: number } {
  if (!state.wineList.dirty) return { state, cost: 0 };
  const copies = Math.ceil(state.restaurant.seats * 1.6);
  const cost = Math.round(copies * state.wineList.pages * 0.22 + 18);
  if (state.cash < cost) return { state, cost: 0 };
  const timed = spendTime(state, 2, 'admin') ?? state;
  return {
    cost,
    state: {
      ...timed,
      cash: timed.cash - cost,
      wineList: {
        ...timed.wineList,
        revision: timed.wineList.revision + 1,
        dirty: false,
        lastPrintedWeek: timed.week,
        reprintSpend: timed.wineList.reprintSpend + cost,
      },
    },
  };
}

export function workSupplierRelationship(state: GameState, supplierId: string): GameState {
  const timed = spendTime(state, 3, 'relationships');
  if (!timed) return state;
  return {
    ...timed,
    suppliers: timed.suppliers.map((supplier) => supplier.id === supplierId ? {
      ...supplier,
      relationship: clamp(supplier.relationship + 3, 0, 100),
      allocationAccess: clamp(supplier.allocationAccess + 1.2, 0, 100),
      lastContactWeek: timed.week,
    } : supplier),
  };
}

export function trainStaff(state: GameState, staffId: string, focus: 'wine' | 'service' | 'sales'): GameState {
  const timed = spendTime(state, 4, 'training');
  if (!timed) return state;
  return {
    ...timed,
    staff: timed.staff.map((person) => person.id === staffId ? {
      ...person,
      wineKnowledge: clamp(person.wineKnowledge + (focus === 'wine' ? 4 : 1), 0, 100),
      service: clamp(person.service + (focus === 'service' ? 4 : 1), 0, 100),
      sales: clamp(person.sales + (focus === 'sales' ? 4 : 1), 0, 100),
      morale: clamp(person.morale + 1.5, 0, 100),
      trainingHours: person.trainingHours + 4,
    } : person),
  };
}

export function upgradeEquipment(state: GameState, equipmentId: string): GameState {
  const item = state.equipment.find((candidate) => candidate.id === equipmentId);
  if (!item || item.level >= item.maxLevel) return state;
  const cost = Math.round(item.baseCost * Math.pow(1.7, item.level));
  if (state.cash < cost) return state;
  return {
    ...state,
    cash: state.cash - cost,
    equipment: state.equipment.map((candidate) => candidate.id === equipmentId ? { ...candidate, level: candidate.level + 1 } : candidate),
  };
}

export function studyCertification(state: GameState, certificationId: string, hours = 4): GameState {
  const timed = spendTime(state, hours, 'study');
  if (!timed) return state;
  return {
    ...timed,
    certifications: timed.certifications.map((track) => track.id === certificationId ? {
      ...track,
      progress: clamp(track.progress + (hours / track.studyHoursRequired) * 100, 0, 100),
    } : track),
  };
}

export function takeCertificationExam(state: GameState, certificationId: string): { state: GameState; passed: boolean } {
  const track = state.certifications.find((candidate) => candidate.id === certificationId);
  if (!track || track.progress < 100 || track.level >= track.maxLevel || state.cash < track.examFee) return { state, passed: false };
  const readiness = clamp((state.knowledge * 8 + state.reputation * 0.15 + track.progress * 0.45) / 100, 0.35, 0.96);
  const roll = ((state.week * 37 + state.xp * 13 + track.level * 17) % 100) / 100;
  const passed = roll <= readiness;
  return {
    passed,
    state: {
      ...state,
      cash: state.cash - track.examFee,
      reputation: clamp(state.reputation + (passed ? track.reputationBonus : -1), 0, 100),
      certifications: state.certifications.map((candidate) => candidate.id === certificationId ? {
        ...candidate,
        level: passed ? candidate.level + 1 : candidate.level,
        progress: passed ? 0 : 45,
      } : candidate),
    },
  };
}
