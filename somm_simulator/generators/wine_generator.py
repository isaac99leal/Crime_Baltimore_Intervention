"""Procedural wine generation engine.

Generates tens of thousands of unique wines based on real-world region data,
grape varieties, and vintage characteristics. No real producer names.
"""

from __future__ import annotations
import random
import uuid
from typing import Optional

from somm_simulator.models.wine import Wine, TastingProfile, GrapeBlend
from somm_simulator.models.region import RegionDatabase, Commune
from somm_simulator.models.grape import GrapeDatabase, GrapeVariety
from somm_simulator.models.producer import Producer
from somm_simulator.generators.name_generator import generate_producer, reset_used_names
from somm_simulator.config import OLDEST_VINTAGE, NEWEST_VINTAGE


# Vintage quality by region (simplified — higher = better vintage)
# In a full game this would be a massive table
VINTAGE_QUALITY = {
    # Bordeaux
    ("France", "Bordeaux"): {
        2023: 0.80, 2022: 0.88, 2021: 0.70, 2020: 0.90, 2019: 0.92,
        2018: 0.91, 2017: 0.72, 2016: 0.93, 2015: 0.94, 2014: 0.78,
        2013: 0.60, 2012: 0.72, 2011: 0.73, 2010: 0.98, 2009: 0.97,
        2008: 0.75, 2007: 0.72, 2006: 0.80, 2005: 0.96, 2004: 0.78,
        2003: 0.85, 2002: 0.72, 2001: 0.82, 2000: 0.95, 1999: 0.78,
        1998: 0.82, 1997: 0.70, 1996: 0.90, 1995: 0.88, 1990: 0.95,
        1989: 0.93, 1988: 0.85, 1986: 0.88, 1985: 0.85, 1982: 0.97,
    },
    # Burgundy
    ("France", "Burgundy"): {
        2023: 0.82, 2022: 0.85, 2021: 0.80, 2020: 0.91, 2019: 0.90,
        2018: 0.85, 2017: 0.82, 2016: 0.88, 2015: 0.92, 2014: 0.80,
        2013: 0.75, 2012: 0.82, 2011: 0.78, 2010: 0.93, 2009: 0.90,
        2008: 0.78, 2007: 0.75, 2006: 0.82, 2005: 0.95, 2004: 0.78,
        2003: 0.80, 2002: 0.88, 2001: 0.78, 2000: 0.82, 1999: 0.90,
    },
    # Napa
    ("United States", "Napa Valley"): {
        2023: 0.82, 2022: 0.85, 2021: 0.88, 2020: 0.75, 2019: 0.90,
        2018: 0.92, 2017: 0.80, 2016: 0.93, 2015: 0.90, 2014: 0.88,
        2013: 0.92, 2012: 0.90, 2011: 0.78, 2010: 0.85, 2009: 0.82,
        2008: 0.78, 2007: 0.88, 2006: 0.85, 2005: 0.88, 2004: 0.85,
    },
    # Piedmont
    ("Italy", "Piedmont"): {
        2023: 0.80, 2022: 0.85, 2021: 0.78, 2020: 0.90, 2019: 0.88,
        2018: 0.82, 2017: 0.78, 2016: 0.95, 2015: 0.88, 2014: 0.82,
        2013: 0.92, 2012: 0.80, 2011: 0.85, 2010: 0.96, 2009: 0.78,
        2008: 0.82, 2007: 0.85, 2006: 0.90, 2005: 0.88, 2004: 0.90,
    },
    # Rioja
    ("Spain", "Rioja"): {
        2023: 0.80, 2022: 0.82, 2021: 0.85, 2020: 0.88, 2019: 0.85,
        2018: 0.82, 2017: 0.78, 2016: 0.90, 2015: 0.85, 2014: 0.88,
        2013: 0.78, 2012: 0.82, 2011: 0.90, 2010: 0.92, 2009: 0.85,
        2008: 0.80, 2007: 0.82, 2006: 0.78, 2005: 0.95, 2004: 0.90,
    },
    # Tuscany
    ("Italy", "Tuscany"): {
        2023: 0.78, 2022: 0.82, 2021: 0.75, 2020: 0.85, 2019: 0.90,
        2018: 0.82, 2017: 0.72, 2016: 0.95, 2015: 0.93, 2014: 0.70,
        2013: 0.85, 2012: 0.82, 2011: 0.78, 2010: 0.96, 2009: 0.80,
        2008: 0.75, 2007: 0.88, 2006: 0.92, 2005: 0.78, 2004: 0.90,
    },
    # Rhône Valley
    ("France", "Rhône Valley"): {
        2023: 0.80, 2022: 0.85, 2021: 0.78, 2020: 0.90, 2019: 0.92,
        2018: 0.88, 2017: 0.90, 2016: 0.88, 2015: 0.95, 2014: 0.78,
        2013: 0.75, 2012: 0.88, 2011: 0.82, 2010: 0.97, 2009: 0.90,
        2008: 0.78, 2007: 0.85, 2006: 0.82, 2005: 0.88, 2004: 0.78,
    },
    # Loire Valley
    ("France", "Loire Valley"): {
        2023: 0.82, 2022: 0.88, 2021: 0.80, 2020: 0.85, 2019: 0.90,
        2018: 0.92, 2017: 0.75, 2016: 0.82, 2015: 0.88, 2014: 0.90,
    },
    # Champagne
    ("France", "Champagne"): {
        2023: 0.78, 2022: 0.85, 2021: 0.72, 2020: 0.88, 2019: 0.90,
        2018: 0.85, 2017: 0.78, 2016: 0.88, 2015: 0.85, 2014: 0.72,
        2013: 0.80, 2012: 0.92, 2011: 0.70, 2010: 0.78, 2009: 0.88,
        2008: 0.95, 2007: 0.72, 2006: 0.82, 2005: 0.78, 2004: 0.88,
        2002: 0.97, 1996: 0.95, 1990: 0.92, 1989: 0.85, 1988: 0.90,
    },
    # Alsace
    ("France", "Alsace"): {
        2023: 0.80, 2022: 0.82, 2021: 0.78, 2020: 0.90, 2019: 0.85,
        2018: 0.82, 2017: 0.88, 2016: 0.85, 2015: 0.90, 2014: 0.78,
    },
    # Mosel
    ("Germany", "Mosel"): {
        2023: 0.82, 2022: 0.85, 2021: 0.90, 2020: 0.88, 2019: 0.92,
        2018: 0.85, 2017: 0.82, 2016: 0.88, 2015: 0.90, 2014: 0.78,
        2013: 0.82, 2012: 0.85, 2011: 0.80, 2010: 0.88, 2009: 0.90,
        2008: 0.78, 2007: 0.92, 2006: 0.80, 2005: 0.90, 2004: 0.82,
    },
    # Douro Valley
    ("Portugal", "Douro Valley"): {
        2023: 0.82, 2022: 0.78, 2021: 0.80, 2020: 0.85, 2019: 0.88,
        2018: 0.82, 2017: 0.92, 2016: 0.90, 2015: 0.85, 2014: 0.78,
        2011: 0.95, 2009: 0.82, 2007: 0.90, 2003: 0.88, 2000: 0.90,
    },
    # Barossa Valley
    ("Australia", "Barossa Valley"): {
        2023: 0.82, 2022: 0.85, 2021: 0.88, 2020: 0.80, 2019: 0.85,
        2018: 0.82, 2017: 0.78, 2016: 0.88, 2015: 0.82, 2014: 0.85,
        2013: 0.80, 2012: 0.90, 2011: 0.78, 2010: 0.92, 2009: 0.78,
    },
    # Wachau
    ("Austria", "Wachau"): {
        2023: 0.82, 2022: 0.85, 2021: 0.80, 2020: 0.88, 2019: 0.92,
        2018: 0.82, 2017: 0.88, 2016: 0.85, 2015: 0.90, 2014: 0.78,
    },
    # Sonoma
    ("United States", "Sonoma"): {
        2023: 0.82, 2022: 0.85, 2021: 0.88, 2020: 0.75, 2019: 0.90,
        2018: 0.88, 2017: 0.80, 2016: 0.90, 2015: 0.88, 2014: 0.85,
    },
    # Oregon
    ("United States", "Oregon"): {
        2023: 0.80, 2022: 0.78, 2021: 0.90, 2020: 0.75, 2019: 0.88,
        2018: 0.90, 2017: 0.82, 2016: 0.85, 2015: 0.92, 2014: 0.88,
    },
    # Mendoza
    ("Argentina", "Mendoza"): {
        2023: 0.82, 2022: 0.80, 2021: 0.78, 2020: 0.85, 2019: 0.90,
        2018: 0.82, 2017: 0.92, 2016: 0.78, 2015: 0.88, 2014: 0.85,
    },
    # Stellenbosch
    ("South Africa", "Stellenbosch"): {
        2023: 0.80, 2022: 0.82, 2021: 0.78, 2020: 0.85, 2019: 0.88,
        2018: 0.90, 2017: 0.85, 2016: 0.82, 2015: 0.92, 2014: 0.78,
    },
    # Tokaj
    ("Hungary", "Tokaj"): {
        2023: 0.78, 2022: 0.82, 2021: 0.80, 2020: 0.78, 2019: 0.88,
        2018: 0.82, 2017: 0.90, 2016: 0.85, 2015: 0.78, 2014: 0.82,
        2013: 0.92, 2012: 0.78, 2011: 0.85, 2010: 0.80, 2009: 0.78,
        2008: 0.88, 2007: 0.82, 2006: 0.78, 2005: 0.80, 2003: 0.85,
        2000: 0.90, 1999: 0.92, 1993: 0.88,
    },
    # Ningxia (China)
    ("China", "Ningxia"): {
        2023: 0.80, 2022: 0.82, 2021: 0.78, 2020: 0.85, 2019: 0.88,
        2018: 0.82, 2017: 0.85, 2016: 0.90, 2015: 0.78, 2014: 0.82,
    },
    # Sussex (England)
    ("England", "Sussex"): {
        2023: 0.78, 2022: 0.90, 2021: 0.72, 2020: 0.75, 2019: 0.80,
        2018: 0.88, 2017: 0.78, 2016: 0.72, 2015: 0.82, 2014: 0.85,
    },
    # Niagara Peninsula (Canada)
    ("Canada", "Niagara Peninsula"): {
        2023: 0.78, 2022: 0.82, 2021: 0.80, 2020: 0.78, 2019: 0.85,
        2018: 0.82, 2017: 0.88, 2016: 0.80, 2015: 0.85, 2014: 0.90,
    },
    # Okanagan Valley (Canada)
    ("Canada", "Okanagan Valley"): {
        2023: 0.82, 2022: 0.85, 2021: 0.78, 2020: 0.88, 2019: 0.90,
        2018: 0.85, 2017: 0.82, 2016: 0.88, 2015: 0.92, 2014: 0.85,
    },
    # Baja California (Mexico)
    ("Mexico", "Baja California"): {
        2023: 0.80, 2022: 0.82, 2021: 0.78, 2020: 0.85, 2019: 0.88,
        2018: 0.82, 2017: 0.80, 2016: 0.85, 2015: 0.82, 2014: 0.78,
    },
    # Galilee (Israel)
    ("Israel", "Galilee"): {
        2023: 0.80, 2022: 0.85, 2021: 0.78, 2020: 0.82, 2019: 0.90,
        2018: 0.88, 2017: 0.82, 2016: 0.85, 2015: 0.82, 2014: 0.88,
    },
}

# Price tier base costs (wholesale per bottle)
PRICE_TIER_RANGES = {
    "value": (5.0, 15.0),
    "moderate": (15.0, 35.0),
    "premium": (35.0, 80.0),
    "luxury": (80.0, 250.0),
    "ultra_luxury": (250.0, 2000.0),
}

# Classification tier price multipliers
CLASSIFICATION_MULTIPLIERS = {
    "Grand Cru": 4.0,
    "Premier Cru": 2.5,
    "First Growth": 8.0,
    "Second Growth": 4.0,
    "Third Growth": 2.5,
    "Fourth Growth": 2.0,
    "Fifth Growth": 1.8,
    "Cru Bourgeois": 1.3,
    "Village": 1.0,
    "Regional": 0.7,
    "Riserva": 1.5,
    "Gran Reserva": 2.0,
    "Reserva": 1.3,
    "DOCG": 1.4,
    "DOC": 1.0,
    "Smaragd": 1.5,
    "Federspiel": 1.0,
    "Steinfeder": 0.8,
    "Spätlese": 1.2,
    "Auslese": 1.8,
    "Beerenauslese": 3.0,
    "Trockenbeerenauslese": 5.0,
    "Eiswein": 3.5,
    "Kabinett": 1.0,
    "Single Vineyard": 1.8,
}

# Style determination based on grape color
STYLE_MAP = {
    "red": "Red",
    "white": "White",
}

# Aging potential by classification
AGING_YEARS = {
    "Grand Cru": (10, 40),
    "Premier Cru": (8, 25),
    "First Growth": (15, 50),
    "Second Growth": (10, 35),
    "Third Growth": (8, 25),
    "Fourth Growth": (8, 20),
    "Fifth Growth": (6, 18),
    "Village": (3, 10),
    "Regional": (1, 5),
    "Riserva": (5, 15),
    "Gran Reserva": (8, 25),
    "Reserva": (4, 12),
}

# Special designations by country
SPECIAL_DESIGNATIONS = {
    "France": ["", "", "", "Vieilles Vignes", "Cuvée Prestige", "Cuvée Spéciale"],
    "Italy": ["", "", "", "Riserva", "Superiore", "Classico"],
    "Spain": ["", "", "Crianza", "Reserva", "Gran Reserva"],
    "United States": ["", "", "", "Reserve", "Estate", "Single Vineyard"],
    "Australia": ["", "", "", "Reserve", "Single Vineyard", "Old Vine"],
    "Germany": ["", "", "Trocken", "Halbtrocken"],
    "Austria": ["", "", "Reserve", "Smaragd", "Federspiel"],
    "Portugal": ["", "", "", "Reserva", "Grande Reserva", "Garrafeira"],
    "Greece": ["", "", "", "Reserve", "Grand Reserve"],
    "Georgia": ["", "", "", "Qvevri"],
    "New Zealand": ["", "", "", "Reserve", "Single Vineyard"],
    "South Africa": ["", "", "", "Reserve", "Old Vine"],
    "Chile": ["", "", "", "Reserva", "Gran Reserva", "Ícono"],
    "Argentina": ["", "", "", "Reserva", "Gran Reserva", "Single Vineyard"],
    "Hungary": ["", "", "", "Superior", "Grand Superior"],
    "Croatia": ["", "", "", "Premium"],
    "Slovenia": ["", "", ""],
    "Lebanon": ["", "", "", "Réserve", "Grand Vin"],
    "England": ["", "", "", "Classic Cuvée", "Blanc de Blancs", "Rosé"],
    "Canada": ["", "", "", "Reserve", "Single Vineyard", "Icewine"],
    "Turkey": ["", "", "", "Reserve", "Grand Reserve"],
    "Israel": ["", "", "", "Reserve", "Single Vineyard", "Grand Vin"],
    "China": ["", "", "", "Reserve", "Grand Reserve"],
    "India": ["", "", "", "Reserve", "Limited Edition"],
    "Mexico": ["", "", "", "Reserva", "Gran Reserva"],
    "Brazil": ["", "", "", "Reserva", "Gran Reserva"],
    "Cyprus": ["", "", "", "Reserve", "Commandaria"],
    "Montenegro": ["", "", "", "Premium", "Reserve"],
    "Serbia": ["", "", "", "Premium", "Barrique"],
    "Romania": ["", "", "", "Rezervă", "DOC-CMD"],
    "Bulgaria": ["", "", "", "Reserve", "Special Reserve"],
    "Switzerland": ["", "", "", "Grand Cru", "Réserve"],
}

# Winemaking notes templates
OAK_NOTES = [
    "Aged {months} months in French oak barriques",
    "Aged {months} months in new French oak",
    "Aged {months} months in a mix of new and used French oak",
    "Aged {months} months in large Slavonian oak casks",
    "Aged {months} months in Hungarian oak",
    "Fermented and aged in stainless steel",
    "Aged {months} months in concrete eggs",
    "Aged {months} months in neutral oak",
    "Aged {months} months, 50% new French oak",
    "Aged {months} months in 500L French oak puncheons",
]

# Vineyard name components for procedural vineyard names
VINEYARD_PREFIXES_FR = [
    "Les", "Le", "La", "Aux", "En",
]
VINEYARD_WORDS_FR = [
    "Charmes", "Perrières", "Caillerets", "Rugiens", "Amoureuses",
    "Grèves", "Épots", "Suchots", "Malconsorts", "Beaumonts",
    "Cras", "Taillepieds", "Champans", "Clos", "Murgers",
    "Bressandes", "Cent Vignes", "Fèves", "Marconnets", "Gouttes",
    "Pruliers", "Vaucrains", "Porêts", "Roncerets", "Chaignots",
]


def _get_vintage_quality(country: str, region: str, vintage: int) -> float:
    """Get vintage quality score for a region/year. Returns 0.5-1.0."""
    key = (country, region)
    if key in VINTAGE_QUALITY and vintage in VINTAGE_QUALITY[key]:
        return VINTAGE_QUALITY[key][vintage]
    # Generate pseudo-random but consistent quality for unknown vintages
    seed = hash((country, region, vintage))
    rng = random.Random(seed)
    return rng.gauss(0.78, 0.10)


def _generate_profile(
    grape: GrapeVariety,
    vintage_quality: float,
    producer_quality: float,
    classification: str,
    style_bias: str,
) -> TastingProfile:
    """Generate a wine's tasting profile based on grape, vintage, and producer."""
    rng = random.Random()

    # Start from grape's typical profile with variance
    variance = 0.3
    acidity = grape.acidity + rng.gauss(0, variance)
    tannin = grape.tannin + rng.gauss(0, variance)
    body = grape.body + rng.gauss(0, variance)
    sweetness = grape.sweetness + rng.gauss(0, variance * 0.5)
    fruit = grape.fruit_intensity + rng.gauss(0, variance)
    earth = grape.earth_intensity + rng.gauss(0, variance)

    # Oak influence based on grape affinity and style
    oak = grape.oak_affinity * rng.gauss(0.8, 0.2)
    if style_bias == "modern":
        oak *= 1.3
    elif style_bias == "traditional":
        oak *= 0.8
        earth *= 1.2
    elif style_bias == "natural":
        oak *= 0.4
        earth *= 1.3
        fruit *= 1.1

    # Vintage quality affects intensity
    quality_mod = vintage_quality * 0.3
    fruit += quality_mod * 0.5
    body += quality_mod * 0.3

    # Higher classification = more concentration
    class_mod = CLASSIFICATION_MULTIPLIERS.get(classification, 1.0)
    if class_mod > 2.0:
        body += 0.3
        fruit += 0.2
        tannin += 0.2

    # Clamp all values
    def clamp(v, lo=1.0, hi=5.0):
        return max(lo, min(hi, v))

    alcohol = rng.uniform(grape.alcohol_low, grape.alcohol_high)
    alcohol += (vintage_quality - 0.8) * 1.5  # Warm vintages = higher alcohol

    # Select aromas (more from good vintages/producers)
    n_primary = min(len(grape.primary_aromas), rng.randint(2, 4))
    n_secondary = min(len(grape.secondary_aromas), rng.randint(1, 3))
    n_tertiary = min(len(grape.tertiary_aromas), rng.randint(0, 2))

    primary = rng.sample(grape.primary_aromas, n_primary) if grape.primary_aromas else []
    secondary = rng.sample(grape.secondary_aromas, n_secondary) if grape.secondary_aromas else []
    tertiary = rng.sample(grape.tertiary_aromas, n_tertiary) if grape.tertiary_aromas else []

    # Color from grape
    color = rng.choice(grape.color_descriptors) if grape.color_descriptors else (
        "medium ruby" if grape.color == "red" else "pale gold"
    )

    return TastingProfile(
        acidity=clamp(acidity),
        tannin=clamp(tannin),
        body=clamp(body),
        sweetness=clamp(sweetness),
        alcohol=round(clamp(alcohol, 8.0, 17.0), 1),
        fruit_intensity=clamp(fruit),
        earth_intensity=clamp(earth),
        oak_influence=clamp(oak),
        primary_aromas=primary,
        secondary_aromas=secondary,
        tertiary_aromas=tertiary,
        color=color,
    )


def _generate_vineyard_name(country: str) -> str:
    """Generate a fictional vineyard/cru name."""
    if country == "France":
        prefix = random.choice(VINEYARD_PREFIXES_FR)
        word = random.choice(VINEYARD_WORDS_FR)
        return f"{prefix} {word}"
    return ""


def generate_wine(
    commune_info: tuple[str, str, str, Commune],
    grape_db: GrapeDatabase,
    producer: Producer | None = None,
    vintage: int | None = None,
) -> Wine | None:
    """Generate a single wine for a given commune.

    Args:
        commune_info: (country, region, sub_region, commune) tuple
        grape_db: Grape variety database
        producer: Optional pre-generated producer
        vintage: Optional specific vintage year

    Returns:
        A Wine object, or None if the commune has no valid grapes
    """
    country, region_name, sub_region_name, commune = commune_info

    # Pick grapes for this wine
    available_grapes = []
    for grape_name in commune.primary_grapes:
        grape = grape_db.get(grape_name)
        if grape:
            available_grapes.append(grape)

    if not available_grapes:
        return None

    # Decide if it's a single varietal or blend
    if len(available_grapes) == 1 or random.random() < 0.4:
        # Single varietal
        primary = random.choice(available_grapes)
        grapes = [GrapeBlend(grape=primary.name, percentage=100.0)]
        grape_for_profile = primary
    else:
        # Blend
        num_grapes = random.randint(2, min(4, len(available_grapes)))
        selected = random.sample(available_grapes, num_grapes)
        percentages = _random_percentages(num_grapes)
        grapes = [
            GrapeBlend(grape=g.name, percentage=p)
            for g, p in zip(selected, percentages)
        ]
        grape_for_profile = selected[0]  # Primary grape drives profile

    # Generate or use producer
    if producer is None:
        producer = generate_producer(
            country, region_name, sub_region_name, commune.name
        )

    # Pick vintage
    if vintage is None:
        # Weight toward recent vintages
        weights = []
        vintages = list(range(OLDEST_VINTAGE, NEWEST_VINTAGE + 1))
        for v in vintages:
            age = NEWEST_VINTAGE - v
            weight = max(0.1, 1.0 - (age / 60.0))  # More recent = more likely
            weights.append(weight)
        vintage = random.choices(vintages, weights=weights)[0]

    vintage_quality = _get_vintage_quality(country, region_name, vintage)

    # Pick classification
    if commune.classification_tiers:
        # Weight toward lower tiers (more common)
        tiers = commune.classification_tiers
        weights = [1.0 / (i + 1) for i in range(len(tiers))]
        # Reverse so lower tiers are more common
        weights = list(reversed(weights))
        classification = random.choices(tiers, weights=weights)[0]
    else:
        classification = "Village" if commune.price_tier in ("moderate", "premium") else "Regional"

    # Determine style
    style = STYLE_MAP.get(grape_for_profile.color, "Red")
    # Some regions make specific styles
    style_lower = commune.style_notes.lower()
    if "sparkling" in style_lower or "champagne" in commune.name.lower():
        style = "Sparkling"
    elif "dessert" in style_lower or "sweet" in style_lower:
        style = "Dessert"
    elif "fortified" in style_lower or "port" in style_lower:
        style = "Fortified"
    elif "rosé" in style_lower:
        if random.random() < 0.3:
            style = "Rosé"

    # Generate tasting profile
    profile = _generate_profile(
        grape_for_profile, vintage_quality, producer.quality_tier,
        classification, producer.style_bias,
    )

    # Pricing
    base_low, base_high = PRICE_TIER_RANGES.get(commune.price_tier, (15, 35))
    base_cost = random.uniform(base_low, base_high)
    class_mult = CLASSIFICATION_MULTIPLIERS.get(classification, 1.0)
    producer_mult = producer.prestige_modifier
    vintage_mult = 0.7 + (vintage_quality * 0.6)
    age_mult = 1.0 + max(0, (NEWEST_VINTAGE - vintage - 5) * 0.03)

    wholesale = base_cost * class_mult * producer_mult * vintage_mult * age_mult
    wholesale = round(max(5.0, wholesale), 2)
    retail = round(wholesale * random.uniform(2.5, 3.5), 2)

    # Aging potential
    aging_range = AGING_YEARS.get(classification, (2, 8))
    aging_potential = random.randint(aging_range[0], aging_range[1])
    # Grape affects aging
    if grape_for_profile.aging_potential == "exceptional":
        aging_potential = int(aging_potential * 1.5)
    elif grape_for_profile.aging_potential == "low":
        aging_potential = max(1, aging_potential // 2)

    drink_start = max(1, aging_potential // 4)
    drink_end = aging_potential

    # Rarity
    rarity = 0.1
    if commune.price_tier == "luxury":
        rarity += 0.3
    elif commune.price_tier == "ultra_luxury":
        rarity += 0.5
    if class_mult > 2.0:
        rarity += 0.2
    rarity = min(0.99, rarity + random.gauss(0, 0.1))

    # Quantity available
    if rarity > 0.8:
        qty = random.randint(1, 6)
    elif rarity > 0.5:
        qty = random.randint(3, 24)
    else:
        qty = random.randint(12, 120)

    # Vineyard name for top classifications
    vineyard_name = ""
    if classification in ("Grand Cru", "Premier Cru", "First Growth", "Single Vineyard"):
        vineyard_name = _generate_vineyard_name(country)

    # Special designation
    designations = SPECIAL_DESIGNATIONS.get(country, [""])
    special = random.choice(designations)

    # Winemaking notes
    oak_months = random.choice([6, 8, 10, 12, 14, 16, 18, 20, 24])
    notes_template = random.choice(OAK_NOTES)
    winemaking = notes_template.format(months=oak_months)

    # Region path
    region_path = [country, region_name]
    if sub_region_name:
        region_path.append(sub_region_name)
    region_path.append(commune.name)

    wine_id = str(uuid.uuid4())[:12]

    # Current condition
    condition = "Young"
    age = NEWEST_VINTAGE - vintage
    if age > drink_end:
        condition = "Declining"
    elif age > drink_end - 2:
        condition = "Past Peak"
    elif age >= drink_start:
        condition = "Peak" if age > (drink_start + drink_end) // 2 else "Approaching Peak"
    elif age > 2:
        condition = "Developing"

    return Wine(
        id=wine_id,
        producer_name=producer.name,
        estate_name=producer.estate_name,
        region_path=region_path,
        appellation=commune.name,
        classification=classification,
        grapes=grapes,
        vintage=vintage,
        style=style,
        profile=profile,
        aging_potential_years=aging_potential,
        current_condition=condition,
        wholesale_cost=wholesale,
        suggested_retail=retail,
        rarity=rarity,
        quantity_available=qty,
        vineyard_name=vineyard_name,
        special_designation=special,
        winemaking_notes=winemaking,
        drink_window_start=drink_start,
        drink_window_end=drink_end,
    )


def _random_percentages(n: int) -> list[float]:
    """Generate n percentages that sum to 100, with the first being dominant."""
    if n == 1:
        return [100.0]
    # Primary grape is 50-85%
    primary = random.uniform(50, 85)
    remaining = 100.0 - primary
    others = []
    for i in range(n - 2):
        portion = random.uniform(0.1, remaining * 0.7)
        others.append(round(portion, 1))
        remaining -= portion
    others.append(round(remaining, 1))
    result = [round(primary, 1)] + others
    return result


def generate_wine_database(
    region_db: RegionDatabase,
    grape_db: GrapeDatabase,
    target_count: int = 5000,
    seed: int = 42,
) -> list[Wine]:
    """Generate a full wine database.

    Args:
        region_db: Region hierarchy data
        grape_db: Grape variety data
        target_count: Approximate number of wines to generate
        seed: Random seed for reproducibility

    Returns:
        List of generated Wine objects
    """
    random.seed(seed)
    reset_used_names()

    all_communes = region_db.all_communes()
    if not all_communes:
        return []

    wines: list[Wine] = []
    wines_per_commune = max(1, target_count // len(all_communes))

    for commune_info in all_communes:
        country, region_name, sub_region_name, commune = commune_info

        # Generate several producers per commune
        num_producers = random.randint(1, max(1, wines_per_commune // 3))
        producers = []
        for _ in range(num_producers):
            prod = generate_producer(country, region_name, sub_region_name, commune.name)
            producers.append(prod)

        # Generate wines
        for _ in range(wines_per_commune):
            producer = random.choice(producers)
            wine = generate_wine(commune_info, grape_db, producer)
            if wine:
                wines.append(wine)

    random.seed()  # Reset seed
    return wines
