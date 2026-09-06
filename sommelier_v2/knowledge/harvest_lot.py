"""Create physical winery inventory from the harvest-to-must process boundary.

The vineyard engine's hL/ha output is not the same thing as recovered cellar
must. Sorting, juice yield, and clarification can remove substantial mass or
volume before fermentation. This module therefore creates opening winery
inventory from ``HarvestMustProfile.must_volume_l`` rather than recalculating
liters from vineyard yield.
"""
from __future__ import annotations

from .harvest_must import HarvestMustProfile
from .winery_provenance import ProvenanceSlice, WineryLot, WineryProvenanceError


def lot_from_harvest_must(
    profile: HarvestMustProfile,
    *,
    lot_id: str,
    block,
    vintage_year: int,
    stage: str = "processed_must",
) -> WineryLot:
    """Create an opening physical lot from an already processed harvest profile.

    Geographic identity comes from the vineyard block. Physical volume comes
    only from the harvest-to-must profile. The function refuses mismatched block
    or grape identities so a valid chemistry profile cannot be attached to the
    wrong physical site.
    """
    if not lot_id.strip():
        raise WineryProvenanceError("Lot ID is required.")
    if not stage.strip():
        raise WineryProvenanceError("Lot stage is required.")
    if not 1600 <= int(vintage_year) <= 3000:
        raise WineryProvenanceError("vintage_year must be within 1600..3000")

    block_id = str(getattr(block, "id", ""))
    if not block_id or block_id != str(profile.source_block_id):
        raise WineryProvenanceError(
            "Harvest-must source block does not match the physical vineyard block."
        )
    block_grape = str(getattr(block, "grape", ""))
    if not block_grape or block_grape.casefold() != str(profile.source_grape).casefold():
        raise WineryProvenanceError(
            "Harvest-must source grape does not match the physical vineyard block grape."
        )

    profile_volume = float(profile.must_volume_l)
    must_volume = float(profile.must.volume_l)
    tolerance = max(0.001, profile_volume * 1e-8)
    if profile_volume <= 0.0:
        raise WineryProvenanceError("Harvest-must profile has no recovered must volume.")
    if abs(profile_volume - must_volume) > tolerance:
        raise WineryProvenanceError(
            "HarvestMustProfile.must_volume_l does not match MustComposition.volume_l."
        )

    country = str(getattr(block, "country", ""))
    region = str(getattr(block, "region", ""))
    if not country or not region:
        raise WineryProvenanceError(
            "Physical vineyard block requires country and region provenance."
        )
    origins = [region]
    appellation = getattr(block, "appellation", None)
    if appellation and str(appellation) not in origins:
        origins.append(str(appellation))
    site_id = getattr(block, "site_id", None)
    if site_id and str(site_id) not in origins:
        origins.append(str(site_id))

    return WineryLot(
        id=lot_id,
        stage=stage,
        volume_l=profile_volume,
        provenance=(
            ProvenanceSlice(
                volume_l=profile_volume,
                grape=profile.source_grape,
                country=country,
                origins=tuple(origins),
                vintage=int(vintage_year),
                block_ids=(block_id,),
                source_lot_ids=(lot_id,),
            ),
        ),
    )
