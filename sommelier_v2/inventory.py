"""Inventory operations, including BTG open-bottle depletion and spoilage."""

from __future__ import annotations

from dataclasses import dataclass

from .domain import BeverageProgram, InventoryLot


@dataclass(frozen=True)
class SaleResult:
    success: bool
    channel: str
    revenue: float = 0.0
    cogs: float = 0.0
    waste_ml: int = 0
    message: str = ""


@dataclass(frozen=True)
class DayCloseInventoryResult:
    spoiled_ml: int
    spoilage_cost: float
    lots_spoiled: int


class InventoryManager:
    def __init__(self, program: BeverageProgram):
        self.program = program

    def receive(self, lot: InventoryLot) -> None:
        if lot.sealed_bottles < 0 or lot.unit_cost < 0:
            raise ValueError("invalid inventory lot")
        if lot.bottle_equivalents > self.program.cellar_space_remaining + 1e-9:
            raise ValueError("cellar capacity exceeded")
        if lot.lot_id in self.program.inventory:
            raise ValueError(f"duplicate lot_id: {lot.lot_id}")
        purchase_cost = lot.sealed_bottles * lot.unit_cost
        if purchase_cost > self.program.cash + 1e-9:
            raise ValueError("insufficient cash")
        self.program.cash -= purchase_cost
        self.program.inventory[lot.lot_id] = lot

    def sell_bottle(self, lot_id: str, price: float | None = None) -> SaleResult:
        lot = self._lot(lot_id)
        if lot.available_sealed_bottles < 1:
            return SaleResult(False, "bottle", message="No sealed bottle available")
        sale_price = price if price is not None else lot.list_price_bottle
        if sale_price <= 0:
            return SaleResult(False, "bottle", message="Bottle is not priced")
        lot.sealed_bottles -= 1
        self.program.cash += sale_price
        return SaleResult(True, "bottle", revenue=sale_price, cogs=lot.unit_cost)

    def sell_glass(self, lot_id: str, price: float | None = None) -> SaleResult:
        lot = self._lot(lot_id)
        sale_price = price if price is not None else lot.list_price_glass
        if sale_price <= 0:
            return SaleResult(False, "btg", message="BTG wine is not priced")

        if lot.open_bottle_ml < lot.glass_ml:
            if lot.available_sealed_bottles < 1:
                return SaleResult(False, "btg", message="No bottle available to open")
            lot.sealed_bottles -= 1
            lot.open_bottle_ml += lot.bottle_ml
            lot.opened_day = self.program.day

        lot.open_bottle_ml -= lot.glass_ml
        if lot.open_bottle_ml < 0:
            lot.open_bottle_ml = 0
        self.program.cash += sale_price
        cogs = lot.unit_cost * (lot.glass_ml / lot.bottle_ml)
        return SaleResult(True, "btg", revenue=sale_price, cogs=cogs)

    def reserve(self, lot_id: str, bottles: int) -> None:
        if bottles < 0:
            raise ValueError("bottles must be non-negative")
        lot = self._lot(lot_id)
        if bottles > lot.sealed_bottles:
            raise ValueError("cannot reserve more bottles than are on hand")
        lot.reserved_bottles = bottles

    def close_day(self) -> DayCloseInventoryResult:
        spoiled_ml = 0
        spoilage_cost = 0.0
        lots_spoiled = 0
        for lot in self.program.inventory.values():
            if lot.open_bottle_ml <= 0 or lot.opened_day is None:
                continue
            age = self.program.day - lot.opened_day
            if age >= lot.open_bottle_life_days:
                waste = lot.open_bottle_ml
                spoiled_ml += waste
                spoilage_cost += lot.unit_cost * (waste / lot.bottle_ml)
                lots_spoiled += 1
                lot.open_bottle_ml = 0
                lot.opened_day = None
        return DayCloseInventoryResult(spoiled_ml, spoilage_cost, lots_spoiled)

    def _lot(self, lot_id: str) -> InventoryLot:
        try:
            return self.program.inventory[lot_id]
        except KeyError as exc:
            raise KeyError(f"unknown lot_id: {lot_id}") from exc
