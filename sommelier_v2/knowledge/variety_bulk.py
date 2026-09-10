"""Bulk operational integration for the world grape universe.

This layer is intentionally more permissive than protected-origin law.

Every Adelaide source name is operationally usable. Botanical identity confidence,
commercial observation, label-name approval, agronomic plausibility, and legal GI
entitlement remain separate axes.

The purpose is to let the simulator work with obscure and experimental varieties
without requiring a bespoke legal review for every grape.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from .catalog import normalize_name
from .expanded_catalog import WorldWineKnowledgeCatalog
from .schema import GrapeKnowledge, NumericRange
from .variety_identity import VarietyIdentityRegistry

DATA_DIR = Path(__file__).resolve().parent / "data"

NEW_WORLD_COUNTRIES = {
    "Argentina", "Australia", "Brazil", "Canada", "Chile", "Mexico",
    "New Zealand", "South Africa", "United States", "Uruguay",
}

# Broad country-climate priors used only when no variety-specific phenotype exists.
# These are deliberately coarse and are never legal or observed site claims.
COOL_COUNTRIES = {
    "Austria", "Belgium", "Canada", "Czech Republic", "Denmark", "England",
    "Estonia", "Germany", "Ireland", "Latvia", "Lithuania", "Luxembourg",
    "Netherlands", "New Zealand", "Poland", "Slovakia", "Slovenia", "Sweden",
    "Switzerland", "United Kingdom",
}
WARM_COUNTRIES = {
    "Algeria", "Argentina", "Australia", "Brazil", "Chile", "Cyprus", "Greece",
    "Israel", "Italy", "Lebanon", "Mexico", "Morocco", "Portugal", "South Africa",
    "Spain", "Tunisia", "Turkey", "Uruguay",
}


def _exact(value: str) -> str:
    return value.strip().casefold()


def _parse_ttb_line(line: str) -> tuple[str, tuple[str, ...]] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", line)
    if not m:
        return line, ()
    primary = m.group(1).strip()
    aliases = tuple(part.strip() for part in m.group(2).split(",") if part.strip())
    return primary, aliases


@dataclass(frozen=True)
class TTBDesignation:
    name: str
    status: str  # approved_regulation | administrative
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperationalTraitPriors:
    """Broad distributions for simulation when measured variety data are absent."""

    acidity: NumericRange
    tannin: NumericRange
    body: NumericRange
    alcohol_pct: NumericRange
    fermentation_temp_c: NumericRange
    maceration_days: NumericRange
    malolactic_probability: float
    oak_affinity: NumericRange
    aromatic_intensity: NumericRange
    source: str
    confidence: str


@dataclass(frozen=True)
class GrowthPlausibilityDecision:
    target_country: str
    state: str
    confidence: str
    evidence: tuple[str, ...]
    legal_entitlement_inferred: bool = False


@dataclass(frozen=True)
class VarietyCountryEvidence:
    """A recorded source assertion, not a current legal eligibility decision."""

    registry_file: str
    source_name: str
    matched_name: str
    country: str | None
    status: str | None
    effective_from: str | None
    source_ids: tuple[str, ...]
    source_urls: tuple[str, ...]


@dataclass(frozen=True)
class VarietyOperationalRecord:
    source_name: str
    source_id: str
    style_family: str
    fermentation_archetype: str
    identity_status: str
    identity_level: str
    canonical_id: str | None
    candidate_ids: tuple[str, ...]
    identity_confirmed: bool
    observed_countries: tuple[str, ...]
    new_world_observed_countries: tuple[str, ...]
    world_area_2023_ha: float
    ttb_status: str | None
    ttb_designation: str | None
    us_commercial_plausibility: str
    spatial_state_us: str
    simulation_enabled: bool
    legal_gi_entitlement_inferred: bool
    traits: OperationalTraitPriors
    evidence_tags: tuple[str, ...] = ()
    classification_countries: tuple[str, ...] = ()
    piwi_countries: tuple[str, ...] = ()
    piwi_documented: bool = False
    classification_evidence: tuple[VarietyCountryEvidence, ...] = ()
    piwi_evidence: tuple[VarietyCountryEvidence, ...] = ()


class BulkVarietyRegistry:
    """Materialize the full Adelaide universe into operational simulator records."""

    def __init__(
        self,
        catalog: WorldWineKnowledgeCatalog | None = None,
        identities: VarietyIdentityRegistry | None = None,
    ) -> None:
        self.catalog = catalog or WorldWineKnowledgeCatalog()
        self.identities = identities or VarietyIdentityRegistry()
        self.ttb = self._load_ttb()
        self._base_exact = self._build_base_index()
        self._national_classifications = self._load_named_country_index(
            "national_variety_classifications_2026.json", "variety"
        )
        self._piwi = self._load_named_country_index("piwi_registry.json", "name")
        self._classification_evidence = self._load_named_evidence_index(
            "national_variety_classifications_2026.json", "variety"
        )
        self._piwi_evidence = self._load_named_evidence_index("piwi_registry.json", "name")

    def _build_base_index(self) -> dict[str, GrapeKnowledge]:
        index: dict[str, GrapeKnowledge] = {}
        collisions: set[str] = set()
        for grape in self.catalog.base.grapes:
            for name in (grape.name, *grape.aliases):
                key = _exact(name)
                if key in index and index[key].id != grape.id:
                    collisions.add(key)
                else:
                    index[key] = grape
        for key in collisions:
            index.pop(key, None)
        return index

    @staticmethod
    def _load_named_evidence_index(
        filename: str, name_field: str,
    ) -> dict[str, tuple[VarietyCountryEvidence, ...]]:
        path = DATA_DIR / filename
        if not path.exists():
            return {}
        doc = json.loads(path.read_text(encoding="utf-8"))
        sources = doc.get("sources", {})
        index: dict[str, list[VarietyCountryEvidence]] = {}
        for row in doc.get("records", []):
            name = str(row.get(name_field) or "").strip()
            if not name:
                continue
            source_ids = tuple(dict.fromkeys([
                *row.get("source_ids", []),
                *([row["source_id"]] if row.get("source_id") else []),
            ]))
            urls = []
            for source_id in source_ids:
                source = sources.get(source_id)
                url = source.get("url") if isinstance(source, dict) else source
                if url and url not in urls:
                    urls.append(url)
            names = [name, *(str(v).strip() for v in row.get("aliases", []) if v)]
            seen = set()
            for candidate in names:
                key = _exact(candidate)
                if not key or key in seen:
                    continue
                seen.add(key)
                evidence = VarietyCountryEvidence(
                    registry_file=filename, source_name=name, matched_name=candidate,
                    country=row.get("country") or None, status=row.get("status") or None,
                    effective_from=row.get("effective_from") or None,
                    source_ids=source_ids, source_urls=tuple(urls),
                )
                index.setdefault(key, []).append(evidence)
        return {key: tuple(values) for key, values in index.items()}

    @staticmethod
    def _load_named_country_index(filename: str, name_field: str) -> dict[str, tuple[str, ...]]:
        # Country summaries derive from the same literal-name evidence as the details.
        return {
            key: tuple(sorted({row.country for row in rows if row.country}))
            for key, rows in BulkVarietyRegistry._load_named_evidence_index(filename, name_field).items()
        }

    @staticmethod
    def _load_ttb() -> dict[str, TTBDesignation]:
        result: dict[str, TTBDesignation] = {}
        for filename, status in (
            ("ttb_approved_grape_designations.txt", "approved_regulation"),
            ("ttb_administrative_grape_designations.txt", "administrative"),
        ):
            path = DATA_DIR / filename
            if not path.exists():
                continue
            for raw in path.read_text(encoding="utf-8").splitlines():
                parsed = _parse_ttb_line(raw)
                if parsed is None:
                    continue
                primary, aliases = parsed
                designation = TTBDesignation(primary, status, aliases)
                for name in (primary, *aliases):
                    key = normalize_name(name)
                    # Regulation outranks administrative duplicate if both exist.
                    old = result.get(key)
                    if old is None or old.status == "administrative":
                        result[key] = designation
        return result

    def _countries_for(self, source_name: str) -> tuple[str, ...]:
        key = _exact(source_name)
        rows = [
            row for row in self.catalog.country_area
            if _exact(row.prime_name) == key and row.country
            and (row.latest_positive_area_ha or 0) > 0
        ]
        return tuple(sorted({row.country for row in rows if row.country}))

    def _world_area_2023(self, source_name: str) -> float:
        key = _exact(source_name)
        return sum(
            float(row.area_2023_ha or 0)
            for row in self.catalog.world_area
            if _exact(row.prime_name) == key
        )

    def _legacy_profile(self, source_name: str) -> GrapeKnowledge | None:
        return self._base_exact.get(_exact(source_name))

    @staticmethod
    def _mid(value: float | None, default: float) -> float:
        return default if value is None else float(value)

    def _traits(
        self,
        source_name: str,
        countries: tuple[str, ...],
        identity_level: str,
        canonical_id: str | None,
    ) -> OperationalTraitPriors:
        legacy = self._legacy_profile(source_name)
        if legacy is not None:
            sensory = legacy.sensory
            color = (legacy.color or "").casefold()
            acidity = self._mid(sensory.acidity, 3.0)
            tannin = self._mid(sensory.tannin, 2.5 if color in {"red", "black"} else 0.4)
            body = self._mid(sensory.body, 3.0)
            alc = sensory.alcohol_pct
            alcohol = NumericRange(
                alc.low if alc.low is not None else 11.5,
                alc.typical if alc.typical is not None else 13.0,
                alc.high if alc.high is not None else 15.0,
                "% abv",
            )
            aromatic = mean([
                self._mid(sensory.fruit_intensity, 2.5),
                self._mid(sensory.floral_intensity, 1.5),
                self._mid(sensory.herbal_intensity, 1.5),
                self._mid(sensory.spice_intensity, 1.5),
            ])
            red = color in {"red", "black"}
            return OperationalTraitPriors(
                acidity=NumericRange(max(0, acidity - 0.7), acidity, min(5, acidity + 0.7), "index_0_5"),
                tannin=NumericRange(max(0, tannin - 0.8), tannin, min(5, tannin + 0.8), "index_0_5"),
                body=NumericRange(max(0, body - 0.7), body, min(5, body + 0.7), "index_0_5"),
                alcohol_pct=alcohol,
                fermentation_temp_c=NumericRange(20 if red else 12, 26 if red else 16, 31 if red else 21, "°C"),
                maceration_days=NumericRange(3 if red else 0, 12 if red else 0.2, 30 if red else 2, "days"),
                malolactic_probability=0.9 if red else 0.35,
                oak_affinity=NumericRange(
                    max(0, self._mid(sensory.oak_affinity, 2.5) - 0.8),
                    self._mid(sensory.oak_affinity, 2.5),
                    min(5, self._mid(sensory.oak_affinity, 2.5) + 0.8),
                    "index_0_5",
                ),
                aromatic_intensity=NumericRange(max(0, aromatic - 1), aromatic, min(5, aromatic + 1), "index_0_5"),
                source="legacy_explicit_profile",
                confidence="medium_high",
            )

        identity = self.identities.identities.get(canonical_id or "", {})
        color = str(identity.get("color") or "").casefold()
        red = color in {"red", "black", "noir", "blue"}
        white = color in {"white", "blanc", "green", "yellow"}
        cool_share = sum(country in COOL_COUNTRIES for country in countries)
        warm_share = sum(country in WARM_COUNTRIES for country in countries)
        climate_shift = 0.0
        if cool_share > warm_share:
            climate_shift = 0.35
        elif warm_share > cool_share:
            climate_shift = -0.2

        # Wide defaults: operational priors, not measured varietal chemistry.
        acid_typ = 3.1 + climate_shift
        tannin_typ = 2.7 if red else (0.4 if white else 1.5)
        body_typ = 3.2 if red else (2.6 if white else 2.8)
        return OperationalTraitPriors(
            acidity=NumericRange(max(0.5, acid_typ - 1.0), acid_typ, min(5, acid_typ + 1.0), "index_0_5"),
            tannin=NumericRange(max(0, tannin_typ - 1.3), tannin_typ, min(5, tannin_typ + 1.3), "index_0_5"),
            body=NumericRange(max(0.5, body_typ - 1.1), body_typ, min(5, body_typ + 1.1), "index_0_5"),
            alcohol_pct=NumericRange(10.5, 12.8 if cool_share > warm_share else 13.3, 16.0, "% abv"),
            fermentation_temp_c=NumericRange(19 if red else 11, 26 if red else 17, 32 if red else 23, "°C"),
            maceration_days=NumericRange(2 if red else 0, 10 if red else 0.2, 35 if red else 3, "days"),
            malolactic_probability=0.85 if red else (0.35 if white else 0.55),
            oak_affinity=NumericRange(0.5, 2.7 if red else 1.8, 5.0, "index_0_5"),
            aromatic_intensity=NumericRange(0.5, 2.5, 4.5, "index_0_5"),
            source="identity_and_geography_simulation_prior" if canonical_id else "generic_commercial_simulation_prior",
            confidence="medium" if identity_level in {"R4", "R5"} else "low",
        )

    def _style_family(self, source_name: str, canonical_id: str | None, traits: OperationalTraitPriors) -> tuple[str, str]:
        legacy = self._legacy_profile(source_name)
        identity = self.identities.identities.get(canonical_id or "", {})
        color = str((legacy.color if legacy is not None else None) or identity.get("color") or "").casefold()
        tannin = float(traits.tannin.typical or 0)
        body = float(traits.body.typical or 0)
        aromatic = float(traits.aromatic_intensity.typical or 0)

        if color in {"red", "black", "noir", "blue"}:
            if tannin >= 3.5 or body >= 4.0:
                return "red_structured", "red_extractive"
            if tannin <= 1.8 and body <= 3.0:
                return "red_light", "red_gentle"
            return "red_medium", "red_standard"
        if color in {"white", "blanc", "green", "yellow"}:
            if aromatic >= 3.2 or "muscat" in normalize_name(source_name):
                return "white_aromatic", "white_cool_aromatic"
            if body >= 3.5:
                return "white_structured", "white_textural"
            return "white_fresh", "white_cool"
        if color in {"rose", "rosé", "gris", "pink"}:
            return "rose_or_gray_skin", "rose_flexible"
        return "broad_unknown_style", "flexible_unknown"

    @staticmethod
    def _climate_class(country: str) -> str:
        if country in COOL_COUNTRIES:
            return "cool"
        if country in WARM_COUNTRIES:
            return "warm"
        return "moderate_or_mixed"

    def assess_country_plausibility(
        self,
        source_name: str,
        target_country: str,
    ) -> GrowthPlausibilityDecision:
        record = self.record(source_name)
        if target_country in record.observed_countries:
            return GrowthPlausibilityDecision(
                target_country=target_country,
                state="OBSERVED",
                confidence="high",
                evidence=(f"adelaide_country_observation:{target_country}",),
            )

        if target_country == "United States" and record.ttb_status is not None:
            return GrowthPlausibilityDecision(
                target_country=target_country,
                state="LABEL_DESIGNATION_SUPPORTED",
                confidence="high",
                evidence=(f"ttb_label_designation:{record.ttb_status}:{record.ttb_designation}",),
            )

        observed_classes = {
            self._climate_class(country) for country in record.observed_countries
        }
        target_class = self._climate_class(target_country)
        if observed_classes and target_class in observed_classes:
            return GrowthPlausibilityDecision(
                target_country=target_country,
                state="AGRONOMICALLY_PLAUSIBLE",
                confidence="medium",
                evidence=(
                    f"climate_analogue:{target_class}",
                    "based_on_observed_country_distribution",
                ),
            )

        if record.new_world_observed_countries and target_country in NEW_WORLD_COUNTRIES:
            return GrowthPlausibilityDecision(
                target_country=target_country,
                state="UNASSESSED",
                confidence="low",
                evidence=(
                    "cultivated_in_other_new_world_country",
                    "country_group_membership_is_not_agronomic_evidence",
                ),
            )

        return GrowthPlausibilityDecision(
            target_country=target_country,
            state="UNASSESSED",
            confidence="low",
            evidence=("insufficient_site_or_climate_evidence",),
        )

    def record(self, source_name: str) -> VarietyOperationalRecord:
        decision = self.identities.resolve(source_name, source_id="adelaide_2025")
        countries = self._countries_for(source_name)
        new_world = tuple(sorted(set(countries) & NEW_WORLD_COUNTRIES))
        normalized = normalize_name(source_name)
        ttb = self.ttb.get(normalized)
        classification_countries = self._national_classifications.get(_exact(source_name), ())
        piwi_countries = self._piwi.get(_exact(source_name), ())

        if ttb is not None:
            us_plausibility = "ttb_label_designation_supported"
            spatial_state_us = "LABEL_DESIGNATION_SUPPORTED"
        elif "United States" in countries:
            us_plausibility = "observed_cultivation"
            spatial_state_us = "OBSERVED"
        elif new_world:
            us_plausibility = "cultivated_in_other_new_world_country"
            spatial_state_us = "UNASSESSED"
        else:
            us_plausibility = "unverified"
            spatial_state_us = "UNASSESSED"

        traits = self._traits(
            source_name,
            countries,
            decision.level,
            decision.canonical_id or (decision.candidate_ids[0] if len(decision.candidate_ids) == 1 else None),
        )
        style_family, fermentation_archetype = self._style_family(
            source_name,
            decision.canonical_id or (decision.candidate_ids[0] if len(decision.candidate_ids) == 1 else None),
            traits,
        )

        tags = {
            f"identity:{decision.level}",
            f"spatial_us:{spatial_state_us}",
            f"trait_source:{traits.source}",
        }
        if ttb:
            tags.add(f"ttb:{ttb.status}")
        if classification_countries:
            tags.add("national_variety_classification")
        if piwi_countries:
            tags.add("piwi_documented")
        if new_world:
            tags.add("observed_new_world")
        if decision.status == "CONFLICT":
            tags.add("identity_conflict")

        return VarietyOperationalRecord(
            source_name=source_name,
            source_id="adelaide_2025",
            style_family=style_family,
            fermentation_archetype=fermentation_archetype,
            identity_status=decision.status,
            identity_level=decision.level,
            canonical_id=decision.canonical_id,
            candidate_ids=decision.candidate_ids,
            identity_confirmed=decision.identity_confirmed,
            observed_countries=countries,
            new_world_observed_countries=new_world,
            world_area_2023_ha=self._world_area_2023(source_name),
            ttb_status=ttb.status if ttb else None,
            ttb_designation=ttb.name if ttb else None,
            us_commercial_plausibility=us_plausibility,
            spatial_state_us=spatial_state_us,
            simulation_enabled=True,
            legal_gi_entitlement_inferred=False,
            traits=traits,
            evidence_tags=tuple(sorted(tags)),
            classification_countries=classification_countries,
            piwi_countries=piwi_countries,
            piwi_documented=bool(piwi_countries),
            classification_evidence=self._classification_evidence.get(_exact(source_name), ()),
            piwi_evidence=self._piwi_evidence.get(_exact(source_name), ()),
        )

    def all_records(self) -> list[VarietyOperationalRecord]:
        # Preserve every unique literal Adelaide source spelling. Duplicate census
        # rows remain observations aggregated into the operational source record.
        names = sorted({_exact(row.prime_name): row.prime_name for row in self.catalog.world_area}.values(), key=str.casefold)
        return [self.record(name) for name in names]

    def vivc_only_records(self) -> list[VarietyOperationalRecord]:
        adelaide_keys = {_exact(row.prime_name) for row in self.catalog.world_area}
        records: list[VarietyOperationalRecord] = []
        for canonical_id, identity in sorted(self.identities.identities.items()):
            prime = str(identity.get("prime_name") or "").strip()
            if not prime or _exact(prime) in adelaide_keys:
                continue
            traits = self._traits(prime, (), "R5", canonical_id)
            style_family, fermentation_archetype = self._style_family(prime, canonical_id, traits)
            normalized = normalize_name(prime)
            ttb = self.ttb.get(normalized)
            classification_countries = self._national_classifications.get(_exact(prime), ())
            piwi_countries = self._piwi.get(_exact(prime), ())
            records.append(
                VarietyOperationalRecord(
                    source_name=prime,
                    source_id="vivc_registry",
                    style_family=style_family,
                    fermentation_archetype=fermentation_archetype,
                    identity_status="CANONICAL_IDENTITY",
                    identity_level="R5",
                    canonical_id=canonical_id,
                    candidate_ids=(),
                    identity_confirmed=True,
                    observed_countries=(),
                    new_world_observed_countries=(),
                    world_area_2023_ha=0.0,
                    ttb_status=ttb.status if ttb else None,
                    ttb_designation=ttb.name if ttb else None,
                    us_commercial_plausibility=(
                        "ttb_label_designation_supported" if ttb else "unverified"
                    ),
                    spatial_state_us=(
                        "LABEL_DESIGNATION_SUPPORTED" if ttb else "UNASSESSED"
                    ),
                    simulation_enabled=True,
                    legal_gi_entitlement_inferred=False,
                    traits=traits,
                    evidence_tags=tuple(sorted({
                        "identity:R5",
                        "source:vivc_registry",
                        f"trait_source:{traits.source}",
                        *({f"ttb:{ttb.status}"} if ttb else set()),
                        *({"national_variety_classification"} if classification_countries else set()),
                        *({"piwi_documented"} if piwi_countries else set()),
                    })),
                    classification_countries=classification_countries,
                    piwi_countries=piwi_countries,
                    piwi_documented=bool(piwi_countries),
                    classification_evidence=self._classification_evidence.get(_exact(prime), ()),
                    piwi_evidence=self._piwi_evidence.get(_exact(prime), ()),
                )
            )
        return records

    def all_global_records(self) -> list[VarietyOperationalRecord]:
        records = [*self.all_records(), *self.vivc_only_records()]
        return sorted(records, key=lambda row: (row.source_name.casefold(), row.source_id))

    def stats(self) -> dict[str, int | float]:
        records = self.all_records()
        global_records = self.all_global_records()
        total_area = sum(row.world_area_2023_ha for row in records)
        strong_area = sum(row.world_area_2023_ha for row in records if row.identity_confirmed)
        return {
            "operational_adelaide_names": len(records),
            "vivc_identity_records_loaded": len(self.identities.identities),
            "vivc_only_operational_records": len(self.vivc_only_records()),
            "global_operational_records": len(global_records),
            "simulation_enabled": sum(row.simulation_enabled for row in global_records),
            "strong_identity_records": sum(row.identity_confirmed for row in records),
            "r3_candidates": sum(row.identity_level == "R3" for row in records),
            "r0_conflicts": sum(row.identity_level == "R0" for row in records),
            "ttb_supported_names": sum(row.ttb_status is not None for row in records),
            "nationally_classified_names": sum(bool(row.classification_countries) for row in global_records),
            "piwi_documented_names": sum(row.piwi_documented for row in global_records),
            "legacy_specific_trait_profiles": sum(row.traits.source == "legacy_explicit_profile" for row in records),
            "identity_geography_trait_priors": sum(row.traits.source == "identity_and_geography_simulation_prior" for row in records),
            "generic_trait_priors": sum(row.traits.source == "generic_commercial_simulation_prior" for row in records),
            "specific_style_families": sum(row.style_family != "broad_unknown_style" for row in records),
            "new_world_observed_names": sum(bool(row.new_world_observed_countries) for row in records),
            "us_observed_names": sum("United States" in row.observed_countries for row in records),
            "world_area_2023_ha": total_area,
            "strong_identity_area_2023_ha": strong_area,
            "strong_identity_area_2023_pct": (strong_area / total_area * 100.0) if total_area else 0.0,
        }
