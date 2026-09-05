"""Authoritative catalog generation for Sommelier Simulator v2.

The default v2 catalog is generated from reviewed legal wine specifications and
verified named-site claim rules. The legacy procedural generator is not used for
origin, grape authorization, classification, site names, production rules, or
release rules.

Game-only values such as synthetic producer names, wholesale prices, and fallback
sensory values are explicitly tracked as simulation priors. They must not be
mistaken for factual producer or market data.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Mapping, Sequence

from .domain import WineRecord, WineStyle
from .generation import ConstrainedWineBuilder, GeneratedWine, WineBuildRequest
from .knowledge.catalog import normalize_name
from .knowledge.expanded_catalog import NamedSite, WorldWineKnowledgeCatalog
from .knowledge.legal_specs import LegalSpecRegistry, LegalWineSpec
from .knowledge.origin_factory import OriginRequest, WineOriginFactory


LEGAL_SNAPSHOT_AS_OF_YEAR = 2026


_STYLE_MAP = {
    "red": WineStyle.RED,
    "white": WineStyle.WHITE,
    "rose": WineStyle.ROSE,
    "rosé": WineStyle.ROSE,
    "sparkling": WineStyle.SPARKLING,
    "sparkling rose": WineStyle.SPARKLING,
    "sparkling rosé": WineStyle.SPARKLING,
    "dessert": WineStyle.DESSERT,
    "fortified": WineStyle.FORTIFIED,
    "orange": WineStyle.ORANGE,
}


@dataclass(frozen=True)
class AuthoritativeCatalogItem:
    generated: GeneratedWine
    legal_spec_id: str
    blend_percentages: tuple[tuple[str, float], ...]
    simulation_prior_fields: tuple[str, ...] = ()

    @property
    def wine(self) -> WineRecord:
        return self.generated.wine


@dataclass(frozen=True)
class AuthoritativeCatalogReport:
    records: int
    strict_specs_used: int
    appellations: int
    site_claim_records: int
    base_appellation_records: int
    grape_identities_used: int
    vintages: tuple[int, ...]


class AuthoritativeCatalogGenerator:
    """Generate only records that pass strict origin, production, and release gates."""

    def __init__(
        self,
        *,
        catalog: WorldWineKnowledgeCatalog | None = None,
        legal_specs: LegalSpecRegistry | None = None,
        origin_factory: WineOriginFactory | None = None,
        builder: ConstrainedWineBuilder | None = None,
    ) -> None:
        self.catalog = catalog or WorldWineKnowledgeCatalog()
        self.origin_factory = origin_factory or WineOriginFactory(catalog=self.catalog)
        self.builder = builder or ConstrainedWineBuilder(origin_factory=self.origin_factory)
        if legal_specs is not None:
            self.legal_specs = legal_specs
        else:
            rulebook = getattr(self.origin_factory, "rulebook", None)
            self.legal_specs = getattr(rulebook, "legal_specs", None) or LegalSpecRegistry()

    @staticmethod
    def _style(spec: LegalWineSpec) -> WineStyle:
        return _STYLE_MAP.get(normalize_name(spec.wine_style or ""), WineStyle.OTHER)

    def _legal_blends(self, spec: LegalWineSpec) -> tuple[dict[str, float], ...]:
        """Return deterministic positive blend paths verified by the same legal registry."""
        blends: list[dict[str, float]] = []

        # Prefer every individually legal 100% path. This gives broad varietal
        # representation for specifications such as Rioja and Champagne without
        # inventing blend ratios.
        for grape in spec.allowed_grapes:
            candidate = {grape: 100.0}
            if self.legal_specs.evaluate_blend(spec, candidate).eligible:
                blends.append(candidate)

        if blends:
            return tuple(blends)

        # If no single-variety path is legal, construct the most conservative
        # constrained blend: start at every minimum and allocate the remainder
        # only within explicit maxima. The candidate is accepted only if the legal
        # evaluator independently verifies it.
        if not spec.grape_constraints:
            return ()

        candidate: dict[str, float] = {
            row.grape: float(row.min_pct)
            for row in spec.grape_constraints
            if row.min_pct > 0
        }
        total = sum(candidate.values())
        remaining = 100.0 - total
        if remaining < -1e-9:
            return ()

        for constraint in spec.grape_constraints:
            if remaining <= 1e-9:
                break
            current = candidate.get(constraint.grape, 0.0)
            capacity = max(0.0, float(constraint.max_pct) - current)
            addition = min(remaining, capacity)
            if addition > 0:
                candidate[constraint.grape] = current + addition
                remaining -= addition

        if remaining > 1e-6:
            return ()
        if self.legal_specs.evaluate_blend(spec, candidate).eligible:
            return (candidate,)
        return ()

    @staticmethod
    def _default_vintage(spec: LegalWineSpec, as_of_year: int) -> int:
        aging_years = ceil((spec.min_total_aging_months or 0) / 12.0)
        legal_delay = max(1, aging_years, spec.release_year_offset or 0)
        return as_of_year - legal_delay

    @staticmethod
    def _production_values(spec: LegalWineSpec, vintage: int, as_of_year: int) -> dict[str, object]:
        wood = spec.min_wood_aging_months or 0
        bottle = spec.min_bottle_aging_months or 0
        total = max(spec.min_total_aging_months or 0, wood + bottle)
        return {
            "vineyard_yield_t_ha": (
                round(spec.max_yield_t_ha * 0.90, 3)
                if spec.max_yield_t_ha is not None
                else None
            ),
            "actual_grape_to_wine_yield_pct": (
                round(spec.grape_to_wine_yield_pct * 0.95, 3)
                if spec.grape_to_wine_yield_pct is not None
                else None
            ),
            "potential_alcohol_pct": (
                round(spec.min_potential_alcohol_pct + 0.5, 2)
                if spec.min_potential_alcohol_pct is not None
                else None
            ),
            "bottled_in_origin": True if spec.bottling_in_origin_required else None,
            "total_aging_months": total,
            "wood_aging_months": wood,
            "bottle_aging_months": bottle,
            "method": spec.required_method,
            "manual_harvest": True if spec.manual_harvest_required else None,
            "total_acidity_g_l": (
                round(spec.min_total_acidity_g_l + 0.5, 2)
                if spec.min_total_acidity_g_l is not None
                else None
            ),
            "dry_extract_g_l": (
                round(spec.min_dry_extract_g_l + 2.0, 2)
                if spec.min_dry_extract_g_l is not None
                else None
            ),
            "release_year": as_of_year,
        }

    @staticmethod
    def _weighted(values: list[tuple[float | None, float]], default: float) -> tuple[float, bool]:
        observed = [(float(value), weight) for value, weight in values if value is not None]
        if not observed:
            return default, True
        denominator = sum(weight for _, weight in observed)
        if denominator <= 0:
            return default, True
        return sum(value * weight for value, weight in observed) / denominator, False

    def _sensory_values(
        self,
        spec: LegalWineSpec,
        blend: Mapping[str, float],
    ) -> tuple[dict[str, object], tuple[str, ...]]:
        style = self._style(spec)
        defaults = {
            WineStyle.RED: dict(acidity=3.4, tannin=3.4, body=3.6, sweetness=1.0, fruit_intensity=3.1, earth_intensity=2.7, oak_influence=2.4, alcohol=13.5),
            WineStyle.WHITE: dict(acidity=3.8, tannin=1.0, body=2.8, sweetness=1.1, fruit_intensity=3.2, earth_intensity=1.8, oak_influence=1.7, alcohol=12.5),
            WineStyle.SPARKLING: dict(acidity=4.2, tannin=1.0, body=2.4, sweetness=1.2, fruit_intensity=2.9, earth_intensity=1.7, oak_influence=1.2, alcohol=12.0),
            WineStyle.ROSE: dict(acidity=3.8, tannin=1.3, body=2.3, sweetness=1.1, fruit_intensity=3.2, earth_intensity=1.4, oak_influence=1.0, alcohol=12.5),
        }.get(style, dict(acidity=3.2, tannin=2.0, body=3.0, sweetness=1.2, fruit_intensity=3.0, earth_intensity=2.0, oak_influence=1.8, alcohol=13.0))

        grapes = []
        for name, pct in blend.items():
            grape = self.catalog.grape(name)
            grapes.append((grape, float(pct) / 100.0))

        prior_fields: list[str] = []
        values: dict[str, object] = {}
        for field_name, grape_attr in (
            ("acidity", "acidity"),
            ("tannin", "tannin"),
            ("body", "body"),
            ("sweetness", "sweetness"),
            ("fruit_intensity", "fruit_intensity"),
            ("earth_intensity", "earth_intensity"),
            ("oak_influence", "oak_affinity"),
        ):
            value, used_prior = self._weighted(
                [
                    (
                        getattr(grape.sensory, grape_attr, None) if grape is not None else None,
                        weight,
                    )
                    for grape, weight in grapes
                ],
                float(defaults[field_name]),
            )
            values[field_name] = round(value, 3)
            if used_prior:
                prior_fields.append(field_name)

        alcohol_candidates: list[tuple[float | None, float]] = []
        for grape, weight in grapes:
            typical = None
            if grape is not None:
                typical = grape.sensory.alcohol_pct.typical
            alcohol_candidates.append((typical, weight))
        alcohol, alcohol_prior = self._weighted(
            alcohol_candidates,
            float(defaults["alcohol"]),
        )
        if spec.min_final_alcohol_pct is not None:
            alcohol = max(alcohol, spec.min_final_alcohol_pct + 0.5)
        values["alcohol"] = round(alcohol, 2)
        if alcohol_prior:
            prior_fields.append("alcohol")

        aromas: list[str] = []
        for grape, _ in grapes:
            if grape is None:
                continue
            for aroma in grape.sensory.primary_aromas:
                if aroma not in aromas:
                    aromas.append(aroma)
                if len(aromas) >= 6:
                    break
            if len(aromas) >= 6:
                break
        values["aromas"] = tuple(aromas)
        if not aromas:
            prior_fields.append("aromas")

        return values, tuple(prior_fields)

    @staticmethod
    def _pricing_prior(spec: LegalWineSpec, *, site: NamedSite | None) -> tuple[float, float]:
        aging = spec.min_total_aging_months or 0
        wholesale = 18.0 + 0.45 * aging
        if normalize_name(spec.variant) not in {"", "standard"}:
            wholesale += 8.0
        if site is not None:
            wholesale += 12.0
        if normalize_name(spec.wine_style or "") == "sparkling":
            wholesale += 4.0
        rarity = min(0.92, 0.18 + aging / 240.0 + (0.20 if site is not None else 0.0))
        return round(wholesale, 2), round(rarity, 3)

    @staticmethod
    def _legal_notes(spec: LegalWineSpec) -> str:
        parts: list[str] = []
        if spec.min_total_aging_months is not None:
            parts.append(f">={spec.min_total_aging_months} months total aging")
        if spec.min_wood_aging_months is not None:
            parts.append(f">={spec.min_wood_aging_months} months wood")
        if spec.min_bottle_aging_months is not None:
            parts.append(f">={spec.min_bottle_aging_months} months bottle")
        if spec.required_method:
            parts.append(spec.required_method)
        return "; ".join(parts)

    def _build_item(
        self,
        *,
        spec: LegalWineSpec,
        blend: Mapping[str, float],
        vintage: int,
        as_of_year: int,
        serial: int,
        site: NamedSite | None,
    ) -> AuthoritativeCatalogItem:
        sensory, sensory_priors = self._sensory_values(spec, blend)
        wholesale, rarity = self._pricing_prior(spec, site=site)
        production = self._production_values(spec, vintage, as_of_year)
        producer = f"Simulation Producer {serial:05d}"
        site_suffix = f" · {site.name}" if site is not None else ""
        variant_suffix = "" if normalize_name(spec.variant) == "standard" else f" · {spec.variant.title()}"

        request = WineBuildRequest(
            id=f"strict:{spec.id}:{vintage}:{serial:05d}",
            producer=producer,
            label=f"{spec.appellation}{variant_suffix}{site_suffix}",
            origin=OriginRequest(
                country=spec.country,
                region=site.region if site is not None else spec.appellation,
                appellation=spec.appellation,
                grapes=dict(blend),
                vintage_year=vintage,
                label_scope="regulated_gi",
                site_id=site.id if site is not None else None,
                wine_variant=spec.variant,
            ),
            style=self._style(spec),
            classification=spec.variant,
            wholesale_cost=wholesale,
            rarity=rarity,
            winemaking_notes=self._legal_notes(spec),
            farming_notes=(
                f"Modeled legal-compliant vineyard yield {production['vineyard_yield_t_ha']} t/ha"
                if production["vineyard_yield_t_ha"] is not None
                else ""
            ),
            **sensory,
            **production,
        )
        generated = self.builder.build(request)
        if site is not None and not generated.evidence.site_claim_eligible:
            raise ValueError(
                f"Site {site.id} was proposed for authoritative catalog generation but its legal claim did not pass"
            )
        priors = tuple(sorted(set(("producer", "wholesale_cost", "rarity", *sensory_priors))))
        return AuthoritativeCatalogItem(
            generated=generated,
            legal_spec_id=spec.id,
            blend_percentages=tuple((name, float(pct)) for name, pct in blend.items()),
            simulation_prior_fields=priors,
        )

    def generate(
        self,
        *,
        as_of_year: int = LEGAL_SNAPSHOT_AS_OF_YEAR,
        vintages: Sequence[int] | None = None,
        include_site_claims: bool = True,
        max_sites_per_spec: int | None = None,
    ) -> list[AuthoritativeCatalogItem]:
        if as_of_year < 1800 or as_of_year > 2200:
            raise ValueError("as_of_year is outside the supported range")
        if max_sites_per_spec is not None and max_sites_per_spec < 0:
            raise ValueError("max_sites_per_spec cannot be negative")

        items: list[AuthoritativeCatalogItem] = []
        serial = 0
        for spec in self.legal_specs.specs:
            if normalize_name(spec.regulatory_status) not in {"", "current"}:
                continue
            blends = self._legal_blends(spec)
            if not blends:
                continue
            spec_vintages = tuple(vintages) if vintages is not None else (
                self._default_vintage(spec, as_of_year),
            )

            matching_sites = [
                site for site in self.catalog.named_sites
                if normalize_name(site.country) == normalize_name(spec.country)
                and normalize_name(site.parent or "") == normalize_name(spec.appellation)
            ]
            if max_sites_per_spec is not None:
                matching_sites = matching_sites[:max_sites_per_spec]

            for vintage in spec_vintages:
                for blend in blends:
                    serial += 1
                    items.append(self._build_item(
                        spec=spec,
                        blend=blend,
                        vintage=int(vintage),
                        as_of_year=as_of_year,
                        serial=serial,
                        site=None,
                    ))
                    if not include_site_claims:
                        continue
                    for site in matching_sites:
                        try:
                            serial += 1
                            item = self._build_item(
                                spec=spec,
                                blend=blend,
                                vintage=int(vintage),
                                as_of_year=as_of_year,
                                serial=serial,
                                site=site,
                            )
                        except ValueError as exc:
                            # Only verified site claims belong in the authoritative
                            # catalog. A documented but non-claimable site is not an
                            # error in the site registry itself.
                            if "legal claim did not pass" in str(exc):
                                continue
                            raise
                        items.append(item)
        return items

    @staticmethod
    def report(items: Sequence[AuthoritativeCatalogItem]) -> AuthoritativeCatalogReport:
        specs = {item.legal_spec_id for item in items}
        appellations = {
            (normalize_name(item.wine.country), normalize_name(item.wine.appellation))
            for item in items
        }
        grapes = {grape for item in items for grape in item.wine.grapes}
        vintages = tuple(sorted({item.wine.vintage for item in items}))
        site_count = sum(bool(item.wine.vineyard) for item in items)
        return AuthoritativeCatalogReport(
            records=len(items),
            strict_specs_used=len(specs),
            appellations=len(appellations),
            site_claim_records=site_count,
            base_appellation_records=len(items) - site_count,
            grape_identities_used=len(grapes),
            vintages=vintages,
        )


def load_authoritative_catalog(
    *,
    as_of_year: int = LEGAL_SNAPSHOT_AS_OF_YEAR,
    vintages: Sequence[int] | None = None,
    include_site_claims: bool = True,
    max_sites_per_spec: int | None = None,
) -> list[WineRecord]:
    """Return the default v2 game catalog without legacy procedural wine generation."""
    generator = AuthoritativeCatalogGenerator()
    return [
        item.wine
        for item in generator.generate(
            as_of_year=as_of_year,
            vintages=vintages,
            include_site_claims=include_site_claims,
            max_sites_per_spec=max_sites_per_spec,
        )
    ]
