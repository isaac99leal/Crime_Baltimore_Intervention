"""Simulation facade that coordinates inventory, service, relationships, and cash."""

from __future__ import annotations

from dataclasses import dataclass, field

from .domain import BeverageProgram, InventoryLot, RelationshipAccount
from .inventory import DayCloseInventoryResult, InventoryManager
from .relationships import RelationshipManager
from .service import ServiceEngine


@dataclass(frozen=True)
class LedgerEntry:
    day: int
    category: str
    amount: float
    note: str = ""


@dataclass
class BusinessLedger:
    entries: list[LedgerEntry] = field(default_factory=list)

    def post(self, day: int, category: str, amount: float, note: str = "") -> None:
        self.entries.append(LedgerEntry(day, category, amount, note))

    def total(self, category: str) -> float:
        return sum(e.amount for e in self.entries if e.category == category)

    @property
    def revenue(self) -> float:
        return self.total("revenue")

    @property
    def cogs(self) -> float:
        return self.total("cogs")

    @property
    def spoilage(self) -> float:
        return self.total("spoilage")

    @property
    def gross_profit(self) -> float:
        return self.revenue - self.cogs - self.spoilage


@dataclass(frozen=True)
class DayCloseResult:
    day: int
    inventory: DayCloseInventoryResult
    cash: float
    inventory_value: float
    gross_profit_to_date: float


class RestaurantSimulation:
    def __init__(self, program: BeverageProgram):
        self.program = program
        self.inventory = InventoryManager(program)
        self.relationships = RelationshipManager(program)
        self.service = ServiceEngine(self.inventory)
        self.ledger = BusinessLedger()

    def add_relationship(self, relationship: RelationshipAccount) -> None:
        self.program.relationships[relationship.id] = relationship

    def buy_lot(self, lot: InventoryLot) -> None:
        cost = lot.sealed_bottles * lot.unit_cost
        self.inventory.receive(lot)
        self.ledger.post(self.program.day, "purchases", -cost, lot.wine.display_name)
        if lot.supplier_id and lot.supplier_id in self.program.relationships:
            self.relationships.record_purchase(lot.supplier_id, cost)

    def record_sale(self, revenue: float, cogs: float, note: str = "") -> None:
        if revenue:
            self.ledger.post(self.program.day, "revenue", revenue, note)
        if cogs:
            self.ledger.post(self.program.day, "cogs", cogs, note)

    def close_day(self) -> DayCloseResult:
        closed = self.inventory.close_day()
        if closed.spoilage_cost:
            self.ledger.post(self.program.day, "spoilage", closed.spoilage_cost, f"{closed.spoiled_ml} ml BTG spoilage")
        current_day = self.program.day
        result = DayCloseResult(current_day, closed, self.program.cash, self.program.inventory_value, self.ledger.gross_profit)
        self.program.reset_day()
        return result
