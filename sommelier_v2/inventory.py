"""Inventory operations, including BTG open-bottle depletion and spoilage."""

from __future__ import annotations

from dataclasses import dataclass

from .domain import BeverageProgram, InventoryLot, OpenBottleState


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
        if lot.bottle_ml <= 0 or lot.glass_ml <= 0 or lot.glass_ml > lot.bottle_ml:
            raise ValueError("invalid bottle/glass volume")
        if lot.open_bottle_life_days <= 0:
            raise ValueError("open_bottle_life_days must be positive")
        self._ensure_open_bottle_state(lot)
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
        self._ensure_open_bottle_state(lot)
        sale_price = price if price is not None else lot.list_price_glass
        if sale_price <= 0:
            return SaleResult(False, "btg", message="BTG wine is not priced")

        available_open = sum(bottle.remaining_ml for bottle in lot.open_bottles)
        if available_open < lot.glass_ml:
            if lot.available_sealed_bottles < 1:
                return SaleResult(False, "btg", message="No bottle available to open")
            lot.sealed_bottles -= 1
            lot.open_bottles.append(
                OpenBottleState(remaining_ml=lot.bottle_ml, opened_day=self.program.day)
            )

        remaining = lot.glass_ml
        while remaining > 0:
            if not lot.open_bottles:
                raise RuntimeError("BTG open-bottle state exhausted unexpectedly")
            bottle = lot.open_bottles[0]
            draw = min(remaining, bottle.remaining_ml)
            bottle.remaining_ml -= draw
            remaining -= draw
            if bottle.remaining_ml == 0:
                lot.open_bottles.pop(0)

        self._sync_legacy_open_state(lot)
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
            self._ensure_open_bottle_state(lot)
            if not lot.open_bottles:
                continue
            kept: list[OpenBottleState] = []
            lot_spoiled = False
            for bottle in lot.open_bottles:
                if bottle.opened_day is None:
                    kept.append(bottle)
                    continue
                age = self.program.day - bottle.opened_day
                if age >= lot.open_bottle_life_days:
                    waste = bottle.remaining_ml
                    spoiled_ml += waste
                    spoilage_cost += lot.unit_cost * (waste / lot.bottle_ml)
                    lot_spoiled = True
                else:
                    kept.append(bottle)
            lot.open_bottles[:] = kept
            self._sync_legacy_open_state(lot)
            if lot_spoiled:
                lots_spoiled += 1
        return DayCloseInventoryResult(spoiled_ml, spoilage_cost, lots_spoiled)

    def _ensure_open_bottle_state(self, lot: InventoryLot) -> None:
        """Normalize old aggregate state into independent bottles once.

        Old saves do not identify which milliliters belonged to which bottle.
        The migration therefore splits the aggregate into bottle-sized chunks but
        preserves the only opening date supplied by the old representation. If
        that date is unknown, it remains unknown instead of being guessed.
        """
        if lot.open_bottles:
            for bottle in lot.open_bottles:
                if bottle.remaining_ml <= 0 or bottle.remaining_ml > lot.bottle_ml:
                    raise ValueError("open bottle volume must be within one bottle")
                if bottle.opened_day is not None and bottle.opened_day > self.program.day:
                    raise ValueError("open bottle cannot have a future opened_day")
            self._sync_legacy_open_state(lot)
            return

        legacy_ml = max(0, int(lot.open_bottle_ml))
        if legacy_ml == 0:
            lot.open_bottle_ml = 0
            lot.opened_day = None
            return
        if lot.opened_day is not None and lot.opened_day > self.program.day:
            raise ValueError("legacy open bottle cannot have a future opened_day")

        remaining = legacy_ml
        while remaining > 0:
            chunk = min(lot.bottle_ml, remaining)
            lot.open_bottles.append(
                OpenBottleState(remaining_ml=chunk, opened_day=lot.opened_day)
            )
            remaining -= chunk
        self._sync_legacy_open_state(lot)

    @staticmethod
    def _sync_legacy_open_state(lot: InventoryLot) -> None:
        lot.open_bottle_ml = sum(bottle.remaining_ml for bottle in lot.open_bottles)
        known_dates = [
            bottle.opened_day for bottle in lot.open_bottles if bottle.opened_day is not None
        ]
        lot.opened_day = min(known_dates) if known_dates else None

    def _lot(self, lot_id: str) -> InventoryLot:
        try:
            return self.program.inventory[lot_id]
        except KeyError as exc:
            raise KeyError(f"unknown lot_id: {lot_id}") from exc
