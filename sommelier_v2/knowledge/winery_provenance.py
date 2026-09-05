"""Automatic physical provenance through winery lots and blending.

Provenance is stored in absolute liters while wine is in the winery.  Processing
losses scale every component proportionally.  Only at finished-wine assembly are
those liters normalized into the percentage ledger consumed by label-law rules.
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


class WineryProvenanceLedger:
    """Mutable lot index; each stored lot remains immutable and auditable."""

    def __init__(self) -> None:
        self.lots: dict[str, WineryLot] = {}

    def add(self, lot: WineryLot) -> WineryLot:
        if lot.id in self.lots:
            raise WineryProvenanceError(f"Duplicate winery lot ID: {lot.id}")
        self.lots[lot.id] = lot
        return lot

    def transfer(
        self,
        source_lot_id: str,
        *,
        new_id: str,
        stage: str,
        output_volume_l: float | None = None,
    ) -> WineryLot:
        source = self.lots[source_lot_id]
        return self.add(
            source.process(new_id=new_id, stage=stage, output_volume_l=output_volume_l)
        )

    def blend(
        self,
        source_lot_ids: Sequence[str],
        *,
        new_id: str,
        draws_l: Sequence[float] | None = None,
        stage: str = "blend",
    ) -> WineryLot:
        sources = [self.lots[lot_id] for lot_id in source_lot_ids]
        return self.add(
            WineryLot.blend(
                lot_id=new_id, lots=sources, draws_l=draws_l, stage=stage
            )
        )

    def stats(self) -> dict[str, int]:
        return {
            "winery_provenance_lots": len(self.lots),
            "winery_provenance_stages": len({lot.stage for lot in self.lots.values()}),
        }
