"""Procedural producer/estate name generator — no real winery names."""

import random
from somm_simulator.models.producer import Producer


# Name components by country/style
FRENCH_PREFIXES = [
    "Domaine", "Château", "Maison", "Clos", "Domaine du", "Domaine de la",
    "Domaine des", "Château de", "Mas", "Château du",
]
FRENCH_FAMILY_NAMES = [
    "Beaumont", "Delacroix", "Fontaine", "Lafleur", "Montrose", "Dubois",
    "Laurent", "Rousseau", "Lefèvre", "Moreau", "Blanchard", "Gauthier",
    "Perrin", "Renard", "Vaillant", "Colbert", "Dumas", "Marchand",
    "Chevalier", "Bonneau", "Girard", "Leblanc", "Picard", "Roux",
    "Berger", "Duval", "Leroy", "Martin", "Bertrand", "Clément",
    "Fournier", "Lagrange", "Petit", "Richard", "Arnaud", "Boisset",
    "Chapoutier", "Fabre", "Gaillard", "Héritier", "Janin", "Lapierre",
]
FRENCH_PLACE_WORDS = [
    "Roche", "Pierre", "Moulin", "Tour", "Croix", "Terre", "Colline",
    "Vigne", "Bois", "Pré", "Vallée", "Source", "Combe", "Côte",
    "Mont", "Lac", "Rivière", "Chêne", "Orme", "Saule", "Tilleul",
    "Bruyère", "Garenne", "Perdrix", "Alouette", "Faisan", "Lièvre",
]
FRENCH_ADJECTIVES = [
    "Haute", "Basse", "Grande", "Petite", "Vieille", "Belle", "Noble",
    "Blanche", "Noire", "Dorée", "Ancienne", "Neuve",
]

ITALIAN_PREFIXES = [
    "Tenuta", "Podere", "Cantina", "Azienda", "Fattoria", "Cascina",
    "Villa", "Casa", "Masseria", "Poggio",
]
ITALIAN_FAMILY_NAMES = [
    "Rossi", "Bianchi", "Conti", "Ferrari", "Moretti", "Marchetti",
    "Barbieri", "Colombo", "De Luca", "Ferrara", "Gallo", "Leone",
    "Mancini", "Neri", "Pellegrini", "Ricci", "Santini", "Vitali",
    "Alberti", "Bellini", "Caruso", "Donati", "Esposito", "Fabbri",
    "Grassi", "Innocenti", "Lombardi", "Montanari", "Orlandi", "Pagani",
]
ITALIAN_PLACE_WORDS = [
    "Pietra", "Rocca", "Monte", "Valle", "Vigna", "Bosco", "Campo",
    "Colle", "Torre", "Fonte", "Prato", "Lago", "Quercia", "Olivo",
    "Sole", "Luna", "Stella", "Angelo", "Antico", "Sacro",
]

SPANISH_PREFIXES = [
    "Bodegas", "Viñedos", "Finca", "Hacienda", "Casa", "Dominio",
    "Pago de", "Celler", "Bodega",
]
SPANISH_FAMILY_NAMES = [
    "García", "Fernández", "López", "Martínez", "Sánchez", "Torres",
    "Álvarez", "Romero", "Navarro", "Ruiz", "Moreno", "Jiménez",
    "Castillo", "Delgado", "Herrera", "Ibáñez", "Lara", "Mendoza",
    "Ortega", "Peña", "Quintana", "Ramos", "Serrano", "Vega",
]
SPANISH_PLACE_WORDS = [
    "Piedra", "Roca", "Monte", "Valle", "Viña", "Campo", "Sierra",
    "Río", "Sol", "Luna", "Torre", "Cruz", "Fuente", "Encina",
]

GERMAN_PREFIXES = [
    "Weingut", "Schloss", "Stift",
]
GERMAN_FAMILY_NAMES = [
    "Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Wagner",
    "Becker", "Hoffmann", "Schäfer", "Koch", "Richter", "Klein",
    "Wolf", "Neumann", "Braun", "Zimmermann", "Hartmann", "Krüger",
    "Werner", "Lange", "Schmitt", "Meier", "Lehmann", "Huber",
]

AMERICAN_PREFIXES = [
    "", "Estate", "Vineyard", "Cellars", "Winery", "Ridge", "Hill",
]
AMERICAN_FAMILY_NAMES = [
    "Anderson", "Baker", "Carter", "Davis", "Edwards", "Foster",
    "Graham", "Hamilton", "Jackson", "Kelly", "Lawrence", "Mitchell",
    "Nelson", "Owens", "Parker", "Quinn", "Reynolds", "Sullivan",
    "Thompson", "Walker", "Young", "Armstrong", "Bennett", "Collins",
    "Douglas", "Ellis", "Franklin", "Gordon", "Hayes", "Irving",
]
AMERICAN_PLACE_WORDS = [
    "Ridge", "Hill", "Creek", "Valley", "Mountain", "Oak", "Pine",
    "Stone", "Hawk", "Eagle", "Bear", "Fox", "Elk", "Cedar",
    "Willow", "Spring", "Shadow", "Iron", "Silver", "Gold",
]

PORTUGUESE_PREFIXES = ["Quinta", "Herdade", "Casa", "Solar", "Adega"]
PORTUGUESE_FAMILY_NAMES = [
    "Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa",
    "Rodrigues", "Martins", "Sousa", "Fernandes", "Gonçalves", "Gomes",
    "Lopes", "Marques", "Alves", "Carvalho",
]

GREEK_PREFIXES = ["Ktima", "Domaine", "Estate"]
GREEK_FAMILY_NAMES = [
    "Papagiannakos", "Lazaridis", "Sigalas", "Boutaris", "Karamolegos",
    "Argyros", "Hatzidakis", "Tselepos", "Parparoussis", "Gaia",
    "Gerovassiliou", "Katsaros", "Manousakis", "Diamantakos", "Thalassitis",
    "Lyrarakis", "Economou", "Zacharioudakis", "Skouras", "Paterianakis",
]

GEORGIAN_PREFIXES = ["Marani", "Winery", "Cellar"]
GEORGIAN_FAMILY_NAMES = [
    "Khareba", "Tsinandali", "Vinoterra", "Alaverdi", "Pheasant's Tears",
    "Lapati", "Shavnabada", "Tchotiashvili", "Dakishvili", "Okro",
    "Lagvinari", "Baia", "Archil Guniava", "Zurab Topuridze", "Kakabadze",
    "Gotsa", "Nikoladze", "Ramaz Nikoladze", "Iago Bitarishvili", "Chkhaveri",
]

HUNGARIAN_PREFIXES = ["Pince", "Szőlőbirtok", "Borászat"]
HUNGARIAN_FAMILY_NAMES = [
    "Szepsy", "Királyudvar", "Oremus", "Tokaj", "Disznókő",
    "Gere", "Vylyan", "Bock", "Heimann", "Takler",
    "Dobogó", "Béres", "Demeter", "Holdvölgy", "Patricius",
    "Csányi", "Thummerer", "Figula", "Sauska", "Koch",
]

CROATIAN_PREFIXES = ["Vinarija", "Podrum"]
CROATIAN_FAMILY_NAMES = [
    "Cattunar", "Kozlović", "Matošević", "Clai", "Coronica",
    "Stina", "Saints Hills", "Bibich", "Krauthaker", "Galić",
    "Tomac", "Miloš", "Boškinac", "Benvenuti", "Degrassi",
    "Trapan", "Kabola", "Roxanich", "Meneghetti", "Zlatan Otok",
]

SLOVENIAN_PREFIXES = ["Vinska Klet", "Kmetija"]
SLOVENIAN_FAMILY_NAMES = [
    "Movia", "Kabaj", "Klinec", "Čotar", "Batič",
    "Marjan Simčič", "Edi Simčič", "Kristančič", "Štoka", "Bjana",
    "Burja", "Guerila", "Aci Urbajs", "Jazbec", "Princic",
]

LEBANESE_PREFIXES = ["Château", "Domaine", "Clos"]
LEBANESE_FAMILY_NAMES = [
    "Musar", "Kefraya", "Ksara", "Massaya", "Marsyas",
    "Wardy", "Karam", "El Ixsir", "Adyar", "Batroun",
    "Atibaia", "Sept", "Nabise", "Vertical33", "Aurora",
]

JAPANESE_PREFIXES = ["", ""]
JAPANESE_FAMILY_NAMES = [
    "Katsunuma", "Suntory", "Mercian", "Grace", "Lumière",
    "Marquis", "Beau Paysage", "Coco Farm", "Takeda", "Domaine Sogga",
    "Château Jun", "Tsuno", "Diamond", "Izutsu", "Haramo",
]

SOUTH_AFRICAN_PREFIXES = ["", "Estate"]
SOUTH_AFRICAN_FAMILY_NAMES = [
    "Van der Merwe", "Botha", "Du Plessis", "Joubert", "Swart",
    "Mullineux", "Sadie", "Boekenhoutskloof", "Badenhorst", "Porseleinberg",
    "Crystallum", "Newton Johnson", "Storm", "Savage", "Alheit",
    "Thorne", "Reyneke", "Raats", "De Trafford", "Kanonkop",
]
SOUTH_AFRICAN_PLACE_WORDS = [
    "Kloof", "Berg", "Rivier", "Rots", "Veld", "Kaap",
    "Drakensberg", "Stellenberg", "Tafelberg", "Helderberg",
]

ENGLISH_FAMILY_NAMES = [
    "Gusbourne", "Ridgeview", "Nyetimber", "Hattingley", "Digby",
    "Exton", "Wiston", "Rathfinny", "Balfour", "Henners",
    "Coates", "Langham", "Camel Valley", "Breaky Bottom", "Bolney",
]
ENGLISH_PLACE_WORDS = [
    "Downs", "Chalk", "Flint", "Weald", "Hill", "Vale",
    "Ridge", "Hundred", "Green", "Manor",
]

CANADIAN_FAMILY_NAMES = [
    "Tawse", "Le Clos", "Stoneboat", "Burrowing Owl", "Painted Rock",
    "Moon Curser", "Blue Mountain", "Culmina", "Quails Gate", "Clos du Soleil",
    "Hidden Bench", "Malivoire", "Featherstone", "Stratus", "Pearl Morissette",
    "Domaine Queylus", "Flat Rock", "Norman Hardie", "Trail Estate", "Rosehall Run",
]

TURKISH_PREFIXES = ["Şarapevi", "Bağları"]
TURKISH_FAMILY_NAMES = [
    "Kayra", "Urla", "Pamukkale", "Sevilen", "Doluca",
    "Kavaklidere", "Kocabağ", "Likya", "Vinkara", "Chamlija",
    "Gülor", "Selendi", "Prodom", "Barel", "Arcadia",
]

ISRAELI_PREFIXES = ["Yekev", "Kerem"]
ISRAELI_FAMILY_NAMES = [
    "Margalit", "Castel", "Flam", "Yarden", "Recanati",
    "Tzora", "Vitkin", "Pelter", "Clos de Gat", "Domaine du Castel",
    "Sphera", "Galil Mountain", "Agur", "Barkan", "Ella Valley",
]

CHINESE_FAMILY_NAMES = [
    "Helan", "Kanaan", "Silver Heights", "Jade", "Dragon",
    "Phoenix", "Tiansai", "Puchang", "Legacy Peak", "Xige",
    "Zhangyu", "Greatwall", "Changyu", "Leirenshou", "Hansen",
]
CHINESE_PLACE_WORDS = [
    "Mountain", "Dragon", "Phoenix", "Jade", "Cloud", "Moon",
    "Sand", "Star", "Pearl", "Golden",
]

INDIAN_FAMILY_NAMES = [
    "Sula", "Grover", "Fratelli", "Charosa", "Vallonné",
    "York", "Four Seasons", "Myra", "Krsma", "Alchemy",
    "Good Earth", "Reveilo", "Zampa", "Soma", "Chandon India",
]

MEXICAN_FAMILY_NAMES = [
    "Monte Xanic", "Adobe", "Barón Balché", "Bichi", "Bruma",
    "Decantos", "Encuentro", "Lechuza", "Magoni", "Mogor Badán",
    "Parvada", "Solar Fortun", "Tres Valles", "Vena Cava", "Viñas de Garza",
]
MEXICAN_PREFIXES = ["Bodega", "Viñedos", "Casa", "Hacienda"]

BRAZILIAN_FAMILY_NAMES = [
    "Miolo", "Lidio Carraro", "Pizzato", "Salton", "Guaspari",
    "Casa Perini", "Don Laurindo", "Boscato", "Lídio", "Aurora",
    "Cave Geisse", "Villa Francioni", "Vinícola Thera", "Luiz Argenta", "Dal Pizzol",
]
BRAZILIAN_PREFIXES = ["Vinícola", "Casa", "Fazenda"]

BOSNIAN_FAMILY_NAMES = [
    "Brkić", "Čitluk", "Tvrdoš", "Andrija", "Nuić",
    "Buntić", "Škegro", "Ljubuški", "Vukoje", "Begić",
]

ROMANIAN_FAMILY_NAMES = [
    "Liliac", "Bauer", "Davino", "Nachbil", "Crama Oprișor",
    "Budureasca", "Cramele Recaș", "Serve", "Avincis", "Domeniul Bogdan",
]

BULGARIAN_FAMILY_NAMES = [
    "Bessa Valley", "Bratanov", "Karabunar", "Midalidare", "Rossidi",
    "Castra Rubra", "Enira", "Orbelus", "Terra Tangra", "Zagreus",
]

GENERIC_FAMILY_NAMES = [
    "Berg", "Stein", "Kowalski", "Novak", "Popov", "Ivanov", "Petrov",
    "Radović", "Stanković", "Jovanović",
]


def _pick(lst: list) -> str:
    return random.choice(lst)


def _generate_french_name() -> tuple[str, str]:
    """Returns (producer_name, estate_name)."""
    style = random.randint(1, 4)
    family = _pick(FRENCH_FAMILY_NAMES)
    if style == 1:
        prefix = _pick(["Domaine", "Maison"])
        return f"{prefix} {family}", f"{prefix} {family}"
    elif style == 2:
        prefix = _pick(["Château", "Clos"])
        place = _pick(FRENCH_PLACE_WORDS)
        adj = _pick(FRENCH_ADJECTIVES)
        estate = f"{prefix} {place} {adj}"
        return family, estate
    elif style == 3:
        prefix = _pick(["Domaine de la", "Domaine du", "Domaine des"])
        place = _pick(FRENCH_PLACE_WORDS)
        return family, f"{prefix} {place}"
    else:
        prefix = _pick(["Château"])
        return family, f"{prefix} {family}"


def _generate_italian_name() -> tuple[str, str]:
    style = random.randint(1, 3)
    family = _pick(ITALIAN_FAMILY_NAMES)
    if style == 1:
        prefix = _pick(ITALIAN_PREFIXES)
        return family, f"{prefix} {family}"
    elif style == 2:
        prefix = _pick(["Podere", "Poggio", "Tenuta"])
        place = _pick(ITALIAN_PLACE_WORDS)
        return family, f"{prefix} {place}"
    else:
        prefix = _pick(ITALIAN_PREFIXES)
        place = _pick(ITALIAN_PLACE_WORDS)
        return family, f"{prefix} {place} di {family}"


def _generate_spanish_name() -> tuple[str, str]:
    style = random.randint(1, 3)
    family = _pick(SPANISH_FAMILY_NAMES)
    if style == 1:
        prefix = _pick(SPANISH_PREFIXES)
        return family, f"{prefix} {family}"
    elif style == 2:
        prefix = _pick(["Finca", "Pago de"])
        place = _pick(SPANISH_PLACE_WORDS)
        return family, f"{prefix} {place}"
    else:
        prefix = _pick(SPANISH_PREFIXES)
        return family, f"{prefix} {family}"


def _generate_german_name() -> tuple[str, str]:
    family = _pick(GERMAN_FAMILY_NAMES)
    prefix = _pick(GERMAN_PREFIXES)
    return family, f"{prefix} {family}"


def _generate_american_name() -> tuple[str, str]:
    style = random.randint(1, 3)
    family = _pick(AMERICAN_FAMILY_NAMES)
    if style == 1:
        suffix = _pick(["Cellars", "Vineyards", "Wines", "Winery", "Estate"])
        return family, f"{family} {suffix}"
    elif style == 2:
        place = _pick(AMERICAN_PLACE_WORDS)
        suffix = _pick(["Vineyards", "Cellars", "Ridge", "Estate"])
        return family, f"{place} {suffix}"
    else:
        place1 = _pick(AMERICAN_PLACE_WORDS)
        place2 = _pick(AMERICAN_PLACE_WORDS)
        while place2 == place1:
            place2 = _pick(AMERICAN_PLACE_WORDS)
        return family, f"{place1} {place2}"


def _generate_portuguese_name() -> tuple[str, str]:
    family = _pick(PORTUGUESE_FAMILY_NAMES)
    prefix = _pick(PORTUGUESE_PREFIXES)
    return family, f"{prefix} {family}"


def _generate_greek_name() -> tuple[str, str]:
    family = _pick(GREEK_FAMILY_NAMES)
    prefix = _pick(GREEK_PREFIXES)
    return family, f"{prefix} {family}"


def _generate_georgian_name() -> tuple[str, str]:
    family = _pick(GEORGIAN_FAMILY_NAMES)
    prefix = _pick(GEORGIAN_PREFIXES)
    if random.random() < 0.5:
        return family, f"{family}'s {prefix}"
    return family, f"{prefix} {family}"


def _generate_hungarian_name() -> tuple[str, str]:
    family = _pick(HUNGARIAN_FAMILY_NAMES)
    prefix = _pick(HUNGARIAN_PREFIXES)
    return family, f"{family} {prefix}"


def _generate_croatian_name() -> tuple[str, str]:
    family = _pick(CROATIAN_FAMILY_NAMES)
    prefix = _pick(CROATIAN_PREFIXES)
    if random.random() < 0.5:
        return family, f"{prefix} {family}"
    return family, family


def _generate_slovenian_name() -> tuple[str, str]:
    family = _pick(SLOVENIAN_FAMILY_NAMES)
    return family, family


def _generate_lebanese_name() -> tuple[str, str]:
    family = _pick(LEBANESE_FAMILY_NAMES)
    prefix = _pick(LEBANESE_PREFIXES)
    return family, f"{prefix} {family}"


def _generate_japanese_name() -> tuple[str, str]:
    family = _pick(JAPANESE_FAMILY_NAMES)
    suffix = _pick(["Winery", "Wine", "Vineyards"])
    return family, f"{family} {suffix}"


def _generate_south_african_name() -> tuple[str, str]:
    style = random.randint(1, 3)
    family = _pick(SOUTH_AFRICAN_FAMILY_NAMES)
    if style == 1:
        suffix = _pick(["Wines", "Estate", "Vineyards"])
        return family, f"{family} {suffix}"
    elif style == 2:
        place = _pick(SOUTH_AFRICAN_PLACE_WORDS)
        suffix = _pick(["Wines", "Estate"])
        return family, f"{place} {suffix}"
    else:
        return family, family


def _generate_english_name() -> tuple[str, str]:
    family = _pick(ENGLISH_FAMILY_NAMES)
    style = random.randint(1, 3)
    if style == 1:
        place = _pick(ENGLISH_PLACE_WORDS)
        return family, f"{place} {_pick(['Estate', 'Vineyard', 'Wine Estate'])}"
    elif style == 2:
        return family, f"{family} {_pick(['Estate', 'Vineyard', 'Wines'])}"
    else:
        return family, family


def _generate_canadian_name() -> tuple[str, str]:
    family = _pick(CANADIAN_FAMILY_NAMES)
    if random.random() < 0.5:
        suffix = _pick(["Cellars", "Vineyards", "Wines", "Estate Winery"])
        return family, f"{family} {suffix}"
    return family, family


def _generate_turkish_name() -> tuple[str, str]:
    family = _pick(TURKISH_FAMILY_NAMES)
    if random.random() < 0.5:
        prefix = _pick(TURKISH_PREFIXES)
        return family, f"{family} {prefix}"
    return family, family


def _generate_israeli_name() -> tuple[str, str]:
    family = _pick(ISRAELI_FAMILY_NAMES)
    if random.random() < 0.5:
        prefix = _pick(ISRAELI_PREFIXES)
        return family, f"{prefix} {family}"
    return family, family


def _generate_chinese_name() -> tuple[str, str]:
    family = _pick(CHINESE_FAMILY_NAMES)
    style = random.randint(1, 3)
    if style == 1:
        place = _pick(CHINESE_PLACE_WORDS)
        return family, f"{place} {_pick(['Vineyard', 'Winery', 'Estate'])}"
    elif style == 2:
        return family, f"{family} {_pick(['Winery', 'Vineyards', 'Wine'])}"
    else:
        return family, family


def _generate_indian_name() -> tuple[str, str]:
    family = _pick(INDIAN_FAMILY_NAMES)
    suffix = _pick(["Vineyards", "Wines", "Winery"])
    return family, f"{family} {suffix}"


def _generate_mexican_name() -> tuple[str, str]:
    family = _pick(MEXICAN_FAMILY_NAMES)
    if random.random() < 0.4:
        prefix = _pick(MEXICAN_PREFIXES)
        return family, f"{prefix} {family}"
    return family, family


def _generate_brazilian_name() -> tuple[str, str]:
    family = _pick(BRAZILIAN_FAMILY_NAMES)
    if random.random() < 0.5:
        prefix = _pick(BRAZILIAN_PREFIXES)
        return family, f"{prefix} {family}"
    return family, family


def _generate_generic_name(country: str) -> tuple[str, str]:
    family = _pick(GENERIC_FAMILY_NAMES + FRENCH_FAMILY_NAMES)
    return family, f"{family} Estate"


# Country → generator function mapping
_GENERATORS = {
    "France": _generate_french_name,
    "Italy": _generate_italian_name,
    "Spain": _generate_spanish_name,
    "Germany": _generate_german_name,
    "Austria": _generate_german_name,
    "United States": _generate_american_name,
    "Australia": _generate_american_name,
    "New Zealand": _generate_american_name,
    "South Africa": _generate_south_african_name,
    "Argentina": _generate_spanish_name,
    "Chile": _generate_spanish_name,
    "Portugal": _generate_portuguese_name,
    "Greece": _generate_greek_name,
    "Georgia": _generate_georgian_name,
    "Hungary": _generate_hungarian_name,
    "Croatia": _generate_croatian_name,
    "Slovenia": _generate_slovenian_name,
    "Lebanon": _generate_lebanese_name,
    "Japan": _generate_japanese_name,
    "North Macedonia": _generate_generic_name,
    "Romania": _generate_generic_name,
    "Bulgaria": _generate_generic_name,
    "Serbia": _generate_generic_name,
    "Switzerland": _generate_german_name,
    "Uruguay": _generate_spanish_name,
    "Egypt": _generate_generic_name,
    "England": _generate_english_name,
    "Canada": _generate_canadian_name,
    "Turkey": _generate_turkish_name,
    "Israel": _generate_israeli_name,
    "China": _generate_chinese_name,
    "India": _generate_indian_name,
    "Mexico": _generate_mexican_name,
    "Brazil": _generate_brazilian_name,
    "Bosnia": _generate_generic_name,
    "Peru": _generate_spanish_name,
}

# Track used names to avoid duplicates
_used_names: set[str] = set()


def generate_producer(
    country: str,
    region: str,
    sub_region: str = "",
    commune: str = "",
    seed: int | None = None,
) -> Producer:
    """Generate a fictional producer for a given country/region."""
    if seed is not None:
        random.seed(seed)

    gen_fn = _GENERATORS.get(country, _generate_generic_name)

    # Try to generate unique name
    for _ in range(50):
        if gen_fn == _generate_generic_name:
            name, estate = gen_fn(country)
        else:
            name, estate = gen_fn()
        if estate not in _used_names:
            _used_names.add(estate)
            break

    quality = random.gauss(0.5, 0.2)
    quality = max(0.05, min(0.98, quality))
    reputation = random.gauss(quality, 0.15)
    reputation = max(0.05, min(0.98, reputation))

    style = random.choice(["traditional", "modern", "balanced", "balanced", "natural"])
    size = random.choices(
        ["micro", "small", "medium", "large", "negociant"],
        weights=[10, 30, 30, 20, 10],
    )[0]

    producer_id = f"prod_{hash(estate) % 1000000:06d}"

    return Producer(
        id=producer_id,
        name=name,
        estate_name=estate,
        country=country,
        region=region,
        sub_region=sub_region,
        commune=commune,
        founded_year=random.randint(1750, 2015),
        quality_tier=quality,
        reputation=reputation,
        style_bias=style,
        production_size=size,
    )


def reset_used_names():
    """Clear the used names tracker (for testing or new game)."""
    _used_names.clear()
