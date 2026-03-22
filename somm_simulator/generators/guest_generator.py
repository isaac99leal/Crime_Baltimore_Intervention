"""Guest/diner procedural generation."""

from __future__ import annotations
import json
import random
import uuid
from pathlib import Path

from somm_simulator.models.guest import Guest, GuestPreferences


# Guest name pools
FIRST_NAMES = [
    "Alexander", "Benjamin", "Caroline", "Diana", "Edward", "Frances",
    "George", "Helena", "Isaac", "Julia", "Katherine", "Lawrence",
    "Margaret", "Nathaniel", "Olivia", "Patrick", "Rachel", "Sebastian",
    "Theodore", "Victoria", "William", "Charlotte", "Eleanor", "Frederick",
    "Grace", "Henry", "Isabelle", "James", "Leonora", "Michael",
    "Nadia", "Oliver", "Philippe", "Renata", "Samuel", "Thomas",
    "Valentina", "Xavier", "Yuki", "Zara", "Antonio", "Beatrice",
    "Chen", "Dmitri", "Elena", "Farid", "Gabrielle", "Hugo",
    "Ingrid", "Jean-Pierre", "Kenji", "Lucia", "Marco", "Nina",
    "Oskar", "Priya", "Ravi", "Sofia", "Takeshi", "Ursula",
]

LAST_NAMES = [
    "Ashworth", "Beaumont", "Cavendish", "Dalton", "Ellsworth", "Fairchild",
    "Grayson", "Hartwell", "Ives", "Jennings", "Kensington", "Lancaster",
    "Montague", "Northcott", "Pemberton", "Quincy", "Rothschild", "Sterling",
    "Thornton", "Underhill", "Vanderbilt", "Whitmore", "Chen", "Park",
    "Nakamura", "Petrov", "González", "Müller", "De Rossi", "Svensson",
    "Singh", "O'Brien", "Dupont", "Kim", "Tanaka", "Johansson",
    "Martinelli", "Westbrook", "Blackwood", "Crawford", "Huntington",
    "Waverly", "Carmichael", "Prescott", "Harrington", "Calloway",
]


def _load_archetypes(path: Path | None = None) -> list[dict]:
    if path is None:
        path = Path(__file__).parent.parent / "data" / "guest_archetypes.json"
    if not path.exists():
        return _default_archetypes()
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("archetypes", [])


def _default_archetypes() -> list[dict]:
    """Fallback archetypes if JSON file not found."""
    return [
        {
            "id": "collector",
            "name": "The Collector",
            "description": "Deeply knowledgeable wine enthusiast seeking rare and allocated bottles",
            "wine_knowledge": [0.8, 1.0],
            "patience": [0.5, 0.8],
            "generosity": [0.6, 0.9],
            "price_ceiling": [500, 5000],
            "price_floor": [100, 300],
            "adventure_level": [0.3, 0.7],
            "preferred_regions": ["Burgundy", "Bordeaux", "Piedmont", "Champagne"],
            "conversation_hints": [
                "mentions recent auction purchases",
                "asks about your allocation list",
                "name-drops specific vineyards",
                "compares vintages knowledgeably"
            ],
            "frequency": 0.08
        },
        {
            "id": "business",
            "name": "The Business Dinner",
            "description": "Hosting clients or colleagues, wants to impress without showing off",
            "wine_knowledge": [0.3, 0.6],
            "patience": [0.3, 0.6],
            "generosity": [0.7, 1.0],
            "price_ceiling": [200, 1000],
            "price_floor": [80, 200],
            "adventure_level": [0.1, 0.4],
            "preferred_regions": ["Bordeaux", "Napa Valley", "Champagne"],
            "conversation_hints": [
                "wants something 'impressive'",
                "asks what you'd recommend for a special occasion",
                "glances at the check discreetly",
                "defers to you as the expert"
            ],
            "frequency": 0.20
        },
        {
            "id": "couple",
            "name": "The Couple",
            "description": "Celebrating a special occasion, wants romance and guided experience",
            "wine_knowledge": [0.1, 0.5],
            "patience": [0.6, 0.9],
            "generosity": [0.5, 0.8],
            "price_ceiling": [80, 300],
            "price_floor": [30, 60],
            "adventure_level": [0.3, 0.7],
            "preferred_regions": [],
            "conversation_hints": [
                "mentions anniversary or birthday",
                "asks for 'something special'",
                "wants to know the story behind the wine",
                "interested in pairing suggestions"
            ],
            "celebrations": ["anniversary", "birthday", "engagement", "promotion"],
            "frequency": 0.25
        },
        {
            "id": "snob",
            "name": "The Wine Snob",
            "description": "Tests your knowledge aggressively, dismissive but rewards competence",
            "wine_knowledge": [0.6, 0.9],
            "patience": [0.2, 0.5],
            "generosity": [0.3, 0.7],
            "price_ceiling": [200, 800],
            "price_floor": [100, 200],
            "adventure_level": [0.2, 0.5],
            "preferred_regions": ["Burgundy", "Bordeaux", "Champagne", "Piedmont"],
            "conversation_hints": [
                "corrects your pronunciation",
                "asks trick questions about vintages",
                "mentions their own cellar",
                "dismisses your first suggestion"
            ],
            "frequency": 0.08
        },
        {
            "id": "adventurer",
            "name": "The Adventurer",
            "description": "Loves discovering unusual wines, values uniqueness over prestige",
            "wine_knowledge": [0.4, 0.8],
            "patience": [0.7, 1.0],
            "generosity": [0.5, 0.8],
            "price_ceiling": [60, 250],
            "price_floor": [20, 40],
            "adventure_level": [0.8, 1.0],
            "preferred_regions": ["Greece", "Georgia", "Lebanon", "Alto Adige", "Jura"],
            "conversation_hints": [
                "asks about natural wines",
                "wants something they've never tried",
                "interested in indigenous grape varieties",
                "asks about the winemaker's philosophy"
            ],
            "frequency": 0.12
        },
        {
            "id": "budget",
            "name": "The Value Seeker",
            "description": "Appreciates great wine but watches the spend carefully",
            "wine_knowledge": [0.2, 0.6],
            "patience": [0.5, 0.8],
            "generosity": [0.4, 0.6],
            "price_ceiling": [40, 100],
            "price_floor": [0, 20],
            "adventure_level": [0.3, 0.6],
            "preferred_regions": [],
            "conversation_hints": [
                "asks about by-the-glass options",
                "looks at prices before descriptions",
                "appreciates when you suggest value picks",
                "orders the second-least-expensive option"
            ],
            "frequency": 0.15
        },
        {
            "id": "newcomer",
            "name": "The Newcomer",
            "description": "Intimidated by the wine list, needs gentle guidance without jargon",
            "wine_knowledge": [0.0, 0.2],
            "patience": [0.6, 0.9],
            "generosity": [0.5, 0.8],
            "price_ceiling": [40, 120],
            "price_floor": [0, 20],
            "adventure_level": [0.2, 0.5],
            "preferred_regions": [],
            "conversation_hints": [
                "admits they don't know much about wine",
                "asks what's 'good'",
                "says they usually drink beer or cocktails",
                "worried about choosing wrong"
            ],
            "frequency": 0.10
        },
        {
            "id": "critic",
            "name": "The Critic",
            "description": "Restaurant critic dining anonymously — highest stakes service",
            "wine_knowledge": [0.7, 1.0],
            "patience": [0.3, 0.6],
            "generosity": [0.5, 0.7],
            "price_ceiling": [150, 500],
            "price_floor": [50, 100],
            "adventure_level": [0.5, 0.8],
            "preferred_regions": [],
            "conversation_hints": [
                "takes notes discreetly",
                "asks unusually detailed questions about the wine program",
                "orders a breadth of wines across the list",
                "seems to be evaluating everything"
            ],
            "is_critic": true,
            "frequency": 0.02
        }
    ]


def generate_guest(
    archetype: dict | None = None,
    archetypes: list[dict] | None = None,
) -> Guest:
    """Generate a random guest.

    Args:
        archetype: Specific archetype dict to use. If None, randomly selected.
        archetypes: Pool of archetypes. If None, loaded from file.
    """
    if archetypes is None:
        archetypes = _default_archetypes()

    if archetype is None:
        weights = [a.get("frequency", 0.1) for a in archetypes]
        archetype = random.choices(archetypes, weights=weights)[0]

    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)

    def rand_range(key, default=(0.5, 0.5)):
        val = archetype.get(key, default)
        if isinstance(val, list) and len(val) == 2:
            return random.uniform(val[0], val[1])
        return val

    knowledge = rand_range("wine_knowledge")
    patience = rand_range("patience")
    generosity = rand_range("generosity")
    price_ceil = rand_range("price_ceiling", [60, 200])
    price_floor = rand_range("price_floor", [0, 30])
    adventure = rand_range("adventure_level")

    party_size = random.choices([1, 2, 3, 4, 5, 6, 8], weights=[5, 35, 15, 25, 10, 7, 3])[0]
    if archetype["id"] == "couple":
        party_size = 2
    elif archetype["id"] == "business":
        party_size = random.choice([2, 4, 4, 6, 6, 8])

    hints = archetype.get("conversation_hints", [])
    selected_hints = random.sample(hints, min(2, len(hints)))

    # Dietary restrictions (small chance)
    dietary = ""
    if random.random() < 0.12:
        dietary = random.choice(["vegetarian", "pescatarian", "vegan", "gluten-free"])

    celebration = ""
    if archetype["id"] == "couple" and random.random() < 0.7:
        celebrations = archetype.get("celebrations", ["anniversary", "birthday"])
        celebration = random.choice(celebrations)

    # Preferred colors based on knowledge and adventure
    if random.random() < 0.7:
        colors = ["Red", "White"]
    else:
        colors = random.sample(["Red", "White", "Rosé", "Sparkling"], random.randint(1, 3))

    # Preferred grapes (more knowledgeable = more specific)
    preferred_grapes = []
    if knowledge > 0.5:
        common_grapes = [
            "Cabernet Sauvignon", "Pinot Noir", "Chardonnay", "Merlot",
            "Syrah", "Sauvignon Blanc", "Riesling", "Nebbiolo",
            "Tempranillo", "Sangiovese", "Grenache", "Viognier",
        ]
        n = random.randint(1, 3)
        preferred_grapes = random.sample(common_grapes, n)

    preferences = GuestPreferences(
        preferred_colors=colors,
        preferred_grapes=preferred_grapes,
        preferred_regions=archetype.get("preferred_regions", []),
        disliked_grapes=[],
        sweetness_preference=random.uniform(1.0, 2.5),
        body_preference=random.uniform(2.0, 4.5),
        adventure_level=adventure,
        price_ceiling=price_ceil,
        price_floor=price_floor,
    )

    return Guest(
        id=str(uuid.uuid4())[:8],
        archetype=archetype["id"],
        name=f"{first} {last}",
        party_size=party_size,
        wine_knowledge=knowledge,
        patience=patience,
        generosity=generosity,
        preferences=preferences,
        is_critic=archetype.get("is_critic", False),
        is_vip=archetype["id"] in ("collector", "critic"),
        has_dietary_restriction=dietary,
        celebration=celebration,
        conversation_hints=selected_hints,
    )


def generate_service_guests(
    num_tables: int,
    career_stage: str = "assistant_sommelier",
) -> list[Guest]:
    """Generate a set of guests for a service night."""
    archetypes = _default_archetypes()
    guests = []

    # Number of occupied tables scales with career stage
    occupancy_rates = {
        "assistant_sommelier": 0.6,
        "sommelier": 0.75,
        "head_sommelier": 0.85,
        "beverage_director": 0.90,
    }
    rate = occupancy_rates.get(career_stage, 0.7)
    num_occupied = max(1, int(num_tables * rate))

    for _ in range(num_occupied):
        guest = generate_guest(archetypes=archetypes)
        guests.append(guest)

    return guests
