"""Automatic physical provenance through winery lots and blending.

Provenance is stored in absolute liters while wine is in the winery. Processing
losses scale every component proportionally. Only at finished-wine assembly are
those liters normalized into the percentage ledger consumed by label-law rules.

The ledger is inventory-conserving. Historical lots remain immutable, but each
stored lot has a mutable available balance. Transfers, blends, and discards
consume source balances atomically so the same physical liters cannot appear in
multiple live descendants.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Sequence

from ..domain import WineRecord
from .finished_wine import FinishedWineAssembler, ValidatedWineRecord
from .jurisdiction_labels import BlendComponent, LabelClaims


class WineryProvenanceError(ValueError):
    pass


@dataclass(frozen=True)
class ProvenanceSlice:
    volume_l: float
    grape: str
    country: str
    origins: tuple[str, ...]
    vintage: int | None
    block_ids: tuple[str, ...] = ()
    source_lot_ids: tuple[str, ...] = ()

    def scaled(self, factor: float, *, source_lot_id: str | None = None) -> "ProvenanceSlice":
        lots = self.source_lot_ids
        if source_lot_id and source_lot_id not in lots:
            lots = (*lots, source_lot_id)
        return replace(self, volume_l=self.volume_l * factor, source_lot_ids=lots)


@dataclass(frozen=True)
class WineryLot:
    id: str
    stage: str
    volume_l: float
    provenance: tuple[ProvenanceSlice, ...]
    parent_lot_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise WineryProvenanceError("Lot ID is required.")
        if not self.stage.strip():
            raise WineryProvenanceError("Lot stage is required.")
        if self.volume_l <= 0:
            raise WineryProvenanceError("Winery lot volume must be positive.")
        if not self.provenance:
            raise WineryProvenanceError("Winery lot requires physical provenance.")
        if any(row.volume_l <= 0 for row in self.provenance):
            raise WineryProvenanceError("Every provenance slice must have positive volume.")
        total = sum(row.volume_l for row in self.provenance)
        tolerance = max(0.001, self.volume_l * 1e-8)
        if abs(total - self.volume_l) > tolerance:
            raise WineryProvenanceError(
                f"Provenance liters ({total:.6f}) do not match lot volume ({self.volume_l:.6f})."
            )

    @classmethod
    def from_vineyard(
        cls,
        *,
        lot_id: str,
        block,
        outcome,
        vintage_year: int,
        recovered_volume_l: float | None = None,
    ) -> "WineryLot":
        if not getattr(outcome, "harvestable", False):
            raise WineryProvenanceError(
                f"Vineyard block {getattr(block, 'id', '<unknown>')} is not harvestable."
            )
        modeled_volume_l = (
            float(getattr(outcome, "yield_hl_ha"))
            * float(getattr(block, "area_ha"))
            * 100.0
        )
        volume_l = modeled_volume_l if recovered_volume_l is None else float(recovered_volume_l)
        if volume_l <= 0 or volume_l > modeled_volume_l * 1.001:
            raise WineryProvenanceError(
                "Recovered must volume must be positive and cannot exceed modeled vineyard output."
            )
        origins = [str(getattr(block, "region"))]
        appellation = getattr(block, "appellation", None)
        if appellation and appellation not in origins:
            origins.append(str(appellation))
        site_id = getattr(block, "site_id", None)
        if site_id and site_id not in origins:
            origins.append(str(site_id))
        block_id = str(getattr(block, "id"))
        return cls(
            id=lot_id,
            stage="harvest_must",
            volume_l=volume_l,
            provenance=(
                ProvenanceSlice(
                    volume_l=volume_l,
                    grape=str(getattr(outcome, "grape", getattr(block, "grape"))),
                    country=str(getattr(block, "country")),
                    origins=tuple(origins),
                    vintage=int(vintage_year),
                    block_ids=(block_id,),
                    source_lot_ids=(lot_id,),
                ),
            ),
        )

    def process(
        self,
        *,
        new_id: str,
        stage: str,
        output_volume_l: float | None = None,
    ) -> "WineryLot":
        volume = self.volume_l if output_volume_l is None else float(output_volume_l)
        if volume <= 0 or volume > self.volume_l + 1e-9:
            raise WineryProvenanceError(
                "A processing transfer must retain a positive volume and cannot create wine volume."
            )
        factor = volume / self.volume_l
        rows = tuple(row.scaled(factor, source_lot_id=self.id) for row in self.provenance)
        return WineryLot(
            id=new_id,
            stage=stage,
            volume_l=volume,
            provenance=rows,
            parent_lot_ids=(self.id,),
        )

    @classmethod
    def blend(
        cls,
        *,
        lot_id: str,
        lots: Sequence["WineryLot"],
        draws_l: Sequence[float] | None = None,
        stage: str = "blend",
    ) -> "WineryLot":
        if not lots:
            raise WineryProvenanceError("At least one source lot is required for a blend.")
        draws = list(draws_l) if draws_l is not None else [lot.volume_l for lot in lots]
        if len(draws) != len(lots):
            raise WineryProvenanceError("draws_l must have one volume for each source lot.")

        rows: list[ProvenanceSlice] = []
        parents: list[str] = []
        for lot, draw in zip(lots, draws):
            draw = float(draw)
            if draw <= 0 or draw > lot.volume_l + 1e-9:
                raise WineryProvenanceError(
                    f"Blend draw from {lot.id} must be >0 and <= source-lot volume."
                )
            factor = draw / lot.volume_l
            rows.extend(row.scaled(factor, source_lot_id=lot.id) for row in lot.provenance)
            parents.append(lot.id)
        rows = cls._coalesce(rows)
        volume = sum(row.volume_l for row in rows)
        return cls(
            id=lot_id,
            stage=stage,
            volume_l=volume,
            provenance=rows,
            parent_lot_ids=tuple(parents),
        )

    @staticmethod
    def _coalesce(rows: Iterable[ProvenanceSlice]) -> tuple[ProvenanceSlice, ...]:
        grouped: dict[tuple, ProvenanceSlice] = {}
        for row in rows:
            key = (row.grape, row.country, row.origins, row.vintage, row.block_ids)
            current = grouped.get(key)
            if current is None:
                grouped[key] = row
            else:
                grouped[key] = replace(
                    current,
                    volume_l=current.volume_l + row.volume_l,
                    source_lot_ids=tuple(
                        dict.fromkeys((*current.source_lot_ids, *row.source_lot_ids))
                    ),
                )
        return tuple(grouped.values())

    def to_blend_components(self) -> tuple[BlendComponent, ...]:
        if self.volume_l <= 0:
            raise WineryProvenanceError("Cannot normalize an empty winery lot.")
        grouped: dict[tuple, float] = {}
        for row in self.provenance:
            key = (row.grape, row.country, row.origins, row.vintage)
            grouped[key] = grouped.get(key, 0.0) + row.volume_l
        return tuple(
            BlendComponent(
                volume_pct=(liters / self.volume_l) * 100.0,
                grape=grape,
                country=country,
                origins=origins,
                vintage=vintage,
            )
            for (grape, country, origins, vintage), liters in grouped.items()
        )

    def assemble_finished_wine(
        self,
        prototype: WineRecord,
        *,
        claims: LabelClaims,
        assembler: FinishedWineAssembler | None = None,
    ) -> ValidatedWineRecord:
        engine = assembler or FinishedWineAssembler()
        return engine.assemble(
            prototype,
            components=self.to_blend_components(),
            claims=claims,
        )


@dataclass(frozen=True)
class LotBalance:
    lot_id: str
    original_volume_l: float
    consumed_volume_l: float
    available_volume_l: float


@dataclass(frozen=True)
class LotMovement:
    operation: str
    source_lot_ids: tuple[str, ...]
    source_draws_l: tuple[float, ...]
    output_lot_id: str | None
    output_volume_l: float
    loss_volume_l: float
    reason: str = ""

    def __post_init__(self) -> None:
        if len(self.source_lot_ids) != len(self.source_draws_l):
            raise WineryProvenanceError("LotMovement source IDs and draws must align.")
        if any(draw <= 0 for draw in self.source_draws_l):
            raise WineryProvenanceError("LotMovement source draws must be positive.")
        if self.output_volume_l < 0 or self.loss_volume_l < 0:
            raise WineryProvenanceError("LotMovement output/loss volumes cannot be negative.")
        total_input = sum(self.source_draws_l)
        if abs(total_input - self.output_volume_l - self.loss_volume_l) > max(0.001, total_input * 1e-8):
            raise WineryProvenanceError("LotMovement input must equal output plus loss.")


class WineryProvenanceLedger:
    """Inventory-conserving lot ledger with immutable historical lot records."""

    def __init__(self) -> None:
        self.lots: dict[str, WineryLot] = {}
        self._consumed_l: dict[str, float] = {}
        self.movements: list[LotMovement] = []

    def _require_lot(self, lot_id: str) -> WineryLot:
        try:
            return self.lots[lot_id]
        except KeyError as exc:
            raise WineryProvenanceError(f"Unknown winery lot ID: {lot_id}") from exc

    def _require_new_id(self, lot_id: str) -> None:
        if lot_id in self.lots:
            raise WineryProvenanceError(f"Duplicate winery lot ID: {lot_id}")

    def add(self, lot: WineryLot) -> WineryLot:
        """Add opening/root inventory.

        Derived lots whose parents are already present must be created through
        ``transfer`` or ``blend`` so the source balances are consumed. A
        historical derived lot can still be imported when none of its parent IDs
        are present in this ledger snapshot.
        """
        self._require_new_id(lot.id)
        present_parents = [parent for parent in lot.parent_lot_ids if parent in self.lots]
        if present_parents:
            raise WineryProvenanceError(
                "Derived lots with parents already in the ledger must be created through transfer/blend; "
                f"present parents: {present_parents}"
            )
        self.lots[lot.id] = lot
        self._consumed_l[lot.id] = 0.0
        return lot

    def _store_derived(self, lot: WineryLot) -> WineryLot:
        self._require_new_id(lot.id)
        self.lots[lot.id] = lot
        self._consumed_l[lot.id] = 0.0
        return lot

    def balance(self, lot_id: str) -> LotBalance:
        lot = self._require_lot(lot_id)
        consumed = self._consumed_l.get(lot_id, 0.0)
        available = max(0.0, lot.volume_l - consumed)
        return LotBalance(lot_id, lot.volume_l, consumed, available)

    def available_volume_l(self, lot_id: str) -> float:
        return self.balance(lot_id).available_volume_l

    def _validate_draw(self, lot_id: str, draw_l: float) -> None:
        draw = float(draw_l)
        if draw <= 0:
            raise WineryProvenanceError(f"Draw from {lot_id} must be positive.")
        available = self.available_volume_l(lot_id)
        if draw > available + 1e-9:
            raise WineryProvenanceError(
                f"Draw from {lot_id} ({draw:g} L) exceeds available volume ({available:g} L)."
            )

    def _consume(self, lot_id: str, draw_l: float) -> None:
        self._consumed_l[lot_id] = self._consumed_l.get(lot_id, 0.0) + float(draw_l)

    def transfer(
        self,
        source_lot_id: str,
        *,
        new_id: str,
        stage: str,
        input_volume_l: float | None = None,
        output_volume_l: float | None = None,
    ) -> WineryLot:
        """Consume a source draw and create one processed descendant.

        ``input_volume_l`` defaults to all currently available source wine.
        ``output_volume_l`` defaults to the input volume. A smaller output is an
        explicit processing loss and is recorded in the movement ledger.
        """
        source = self._require_lot(source_lot_id)
        self._require_new_id(new_id)
        available = self.available_volume_l(source_lot_id)
        input_volume = available if input_volume_l is None else float(input_volume_l)
        self._validate_draw(source_lot_id, input_volume)
        output_volume = input_volume if output_volume_l is None else float(output_volume_l)
        if output_volume <= 0 or output_volume > input_volume + 1e-9:
            raise WineryProvenanceError(
                "Transfer output must be positive and cannot exceed the consumed input volume."
            )

        child = source.process(
            new_id=new_id,
            stage=stage,
            output_volume_l=output_volume,
        )
        movement = LotMovement(
            operation="transfer",
            source_lot_ids=(source_lot_id,),
            source_draws_l=(input_volume,),
            output_lot_id=new_id,
            output_volume_l=output_volume,
            loss_volume_l=max(0.0, input_volume - output_volume),
        )
        self._consume(source_lot_id, input_volume)
        self._store_derived(child)
        self.movements.append(movement)
        return child

    def blend(
        self,
        source_lot_ids: Sequence[str],
        *,
        new_id: str,
        draws_l: Sequence[float] | None = None,
        stage: str = "blend",
    ) -> WineryLot:
        if not source_lot_ids:
            raise WineryProvenanceError("At least one source lot is required for a blend.")
        if len(set(source_lot_ids)) != len(source_lot_ids):
            raise WineryProvenanceError("A source lot may appear only once in one blend operation.")
        self._require_new_id(new_id)
        sources = [self._require_lot(lot_id) for lot_id in source_lot_ids]
        draws = (
            [self.available_volume_l(lot_id) for lot_id in source_lot_ids]
            if draws_l is None
            else [float(value) for value in draws_l]
        )
        if len(draws) != len(sources):
            raise WineryProvenanceError("draws_l must have one volume for each source lot.")
        for lot_id, draw in zip(source_lot_ids, draws):
            self._validate_draw(lot_id, draw)

        child = WineryLot.blend(
            lot_id=new_id,
            lots=sources,
            draws_l=draws,
            stage=stage,
        )
        movement = LotMovement(
            operation="blend",
            source_lot_ids=tuple(source_lot_ids),
            source_draws_l=tuple(draws),
            output_lot_id=new_id,
            output_volume_l=child.volume_l,
            loss_volume_l=0.0,
        )
        for lot_id, draw in zip(source_lot_ids, draws):
            self._consume(lot_id, draw)
        self._store_derived(child)
        self.movements.append(movement)
        return child

    def discard(self, lot_id: str, *, volume_l: float | None = None, reason: str = "") -> LotMovement:
        """Remove wine from live inventory without creating a descendant lot."""
        self._require_lot(lot_id)
        available = self.available_volume_l(lot_id)
        volume = available if volume_l is None else float(volume_l)
        self._validate_draw(lot_id, volume)
        movement = LotMovement(
            operation="discard",
            source_lot_ids=(lot_id,),
            source_draws_l=(volume,),
            output_lot_id=None,
            output_volume_l=0.0,
            loss_volume_l=volume,
            reason=reason,
        )
        self._consume(lot_id, volume)
        self.movements.append(movement)
        return movement

    def total_available_volume_l(self) -> float:
        return sum(self.available_volume_l(lot_id) for lot_id in self.lots)

    def total_recorded_loss_l(self) -> float:
        return sum(movement.loss_volume_l for movement in self.movements)

    def stats(self) -> dict[str, int | float]:
        return {
            "winery_provenance_lots": len(self.lots),
            "winery_provenance_stages": len({lot.stage for lot in self.lots.values()}),
            "winery_provenance_movements": len(self.movements),
            "winery_provenance_available_l": self.total_available_volume_l(),
            "winery_provenance_recorded_loss_l": self.total_recorded_loss_l(),
        }
