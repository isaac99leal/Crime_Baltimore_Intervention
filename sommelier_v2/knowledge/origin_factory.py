"""Single constrained origin-creation path for v2 wine records.

All new v2 generators should construct origin metadata through this factory.
Protected-origin claims use sourced legal specifications when available and fail
closed when grape rules are absent or violated. Named-site identity is evaluated
separately from the legal right to put that site name on a protected-origin label.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .catalog import normalize_name
from .expanded_catalog import NamedSite, WorldWineKnowledgeCatalog
from .legal_rules import LegalAwareRegionGrapeRulebook
from .regional_rules import OriginConstraintError, OriginDecision, RegionGrapeRulebook
from .site_claims import SiteClaimRegistry
from .vineyard_engine import SiteRegistry


@dataclass(frozen=True)
class OriginRequest:
    country: str
    region: str
    grapes: Mapping[str, float] | Sequence[str] | str
    vintage_year: int
    label_scope: str
    sub_region: str | None = None
    appellation: str | None = None
    commune: str | None = None
    site_id: str | None = None
    producer: str | None = None
    experimental: bool = False
    wine_variant: str | None = None


@dataclass(frozen=True)
class ConstrainedOrigin:
    country: str
    region: str
    sub_region: str | None
    appellation: str | None
    commune: str | None
    canonical_grapes: tuple[str, ...]
    label_scope: str
    site: NamedSite | None
    site_claim_eligible: bool
    decision: OriginDecision
    site_claim_status: str = "site_claim_not_requested"
    site_claim_rule_id: str | None = None
    site_claim_evidence: tuple[str, ...] = ()


class WineOriginFactory:
    def __init__(
        self,
        *,
        catalog: WorldWineKnowledgeCatalog | None = None,
        rulebook: RegionGrapeRulebook | None = None,
        site_claims: SiteClaimRegistry | None = None,
    ) -> None:
        self.catalog = catalog or WorldWineKnowledgeCatalog()
        self.rulebook = rulebook or LegalAwareRegionGrapeRulebook(catalog=self.catalog)
        self.sites = SiteRegistry(self.catalog.named_sites)
        self.site_claims = site_claims or SiteClaimRegistry()

    def create(self, request: OriginRequest) -> ConstrainedOrigin:
        if request.vintage_year < 1800 or request.vintage_year > 2200:
            raise OriginConstraintError("Vintage year is outside the supported simulation range.")

        site = self.sites.resolve(site_id=request.site_id) if request.site_id else None
        if request.site_id and site is None:
            raise OriginConstraintError(f"Unknown site ID {request.site_id}")
        if site is not None:
            if normalize_name(site.country) != normalize_name(request.country):
                raise OriginConstraintError(f"{site.name} is in {site.country}, not {request.country}.")
            if normalize_name(site.region) != normalize_name(request.region):
                raise OriginConstraintError(f"{site.name} belongs to {site.region}, not {request.region}.")

        appellation = request.appellation
        if site is not None and appellation is None:
            appellation = site.parent or site.region
        if (
            site is not None
            and request.appellation
            and site.parent
            and normalize_name(site.parent) != normalize_name(request.appellation)
        ):
            raise OriginConstraintError(
                f"Site {site.name} is tied to {site.parent}; it cannot be attached to {request.appellation}."
            )

        kwargs = dict(
            country=request.country,
            region=request.region,
            sub_region=request.sub_region,
            commune=request.commune,
            appellation=appellation,
            grapes=request.grapes,
            label_scope=request.label_scope,
            vintage_year=request.vintage_year,
            experimental=request.experimental,
        )
        if isinstance(self.rulebook, LegalAwareRegionGrapeRulebook):
            kwargs["wine_variant"] = request.wine_variant
        decision = self.rulebook.evaluate(**kwargs)
        decision.require()

        # Legal site-claim eligibility must be established before label-ownership
        # enforcement. A catalog can contain physical sites (including owned
        # monopoles or research-only discrepancies) that have no positive rule for
        # the requested appellation/variant. Such sites are evidence, not label
        # claims, and must fail closed without aborting generation of the parent GI.
        site_claim = self.site_claims.evaluate(
            site=site,
            origin_decision=decision,
            appellation=appellation,
            wine_variant=request.wine_variant,
        )
        if site is not None and site_claim.eligible:
            self.sites.validate_ownership(site, request.producer)

        return ConstrainedOrigin(
            country=request.country,
            region=request.region,
            sub_region=request.sub_region,
            appellation=appellation,
            commune=request.commune,
            canonical_grapes=decision.canonical_grapes,
            label_scope=request.label_scope,
            site=site,
            site_claim_eligible=site_claim.eligible,
            decision=decision,
            site_claim_status=site_claim.status,
            site_claim_rule_id=site_claim.rule_id,
            site_claim_evidence=site_claim.evidence,
        )

    def declassification_options(self, request: OriginRequest) -> tuple[OriginDecision, ...]:
        """Return safe alternatives without silently changing the label."""
        options: list[OriginDecision] = []
        for scope, experimental in (("country_wine", False), ("experimental", True)):
            decision = self.rulebook.evaluate(
                country=request.country,
                region=request.region,
                grapes=request.grapes,
                label_scope=scope,
                vintage_year=request.vintage_year,
                experimental=experimental,
            )
            if decision.eligible:
                options.append(decision)
        return tuple(options)
