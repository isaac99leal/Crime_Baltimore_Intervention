"""Random event generation for game variety."""

from __future__ import annotations
import json
import random
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class GameEvent:
    """A random event that can occur during gameplay."""
    id: str
    title: str
    description: str
    category: str               # "cellar", "service", "business", "career", "wine_world"
    severity: str               # "positive", "neutral", "negative", "critical"
    effects: dict = field(default_factory=dict)
    choices: list[dict] = field(default_factory=list)
    min_career_stage: str = "assistant_sommelier"
    probability: float = 0.1    # Base probability per week


# Default events built into the game
DEFAULT_EVENTS = [
    # Cellar events
    {
        "id": "ac_failure",
        "title": "Cellar Temperature Spike",
        "description": "The cellar cooling system has malfunctioned overnight. Temperature rose to 78°F for several hours before being detected.",
        "category": "cellar",
        "severity": "negative",
        "effects": {"spoilage_risk": 0.15, "budget_cost": 500},
        "choices": [
            {"text": "Emergency repair — fix immediately ($500)", "effect": {"budget": -500, "spoilage_risk": 0.05}},
            {"text": "Use backup fans and ice — cheaper but riskier ($100)", "effect": {"budget": -100, "spoilage_risk": 0.20}},
        ],
        "probability": 0.03,
    },
    {
        "id": "broken_bottles",
        "title": "Breakage in the Cellar",
        "description": "A shelf collapsed in the cellar. Several bottles are damaged.",
        "category": "cellar",
        "severity": "negative",
        "effects": {"bottles_lost": 6},
        "choices": [
            {"text": "Assess the damage and salvage what you can", "effect": {"bottles_lost": 3}},
            {"text": "Reinforce all shelving to prevent future incidents ($300)", "effect": {"bottles_lost": 6, "budget": -300, "prevent_future": True}},
        ],
        "probability": 0.02,
    },
    {
        "id": "perfect_storage",
        "title": "Optimal Cellar Conditions",
        "description": "Your cellar has maintained perfect temperature and humidity for the past month. Wines are developing beautifully.",
        "category": "cellar",
        "severity": "positive",
        "effects": {"aging_bonus": 0.1},
        "probability": 0.05,
    },
    # Service events
    {
        "id": "celebrity_visit",
        "title": "Celebrity Guest",
        "description": "A well-known celebrity has arrived without reservation. The maître d' is seating them at your best table.",
        "category": "service",
        "severity": "neutral",
        "effects": {"reputation_bonus": 50, "pressure": "high"},
        "choices": [
            {"text": "Personally handle the table — high risk, high reward", "effect": {"reputation_bonus": 100, "stress": 0.3}},
            {"text": "Assign your best server and supervise from a distance", "effect": {"reputation_bonus": 30, "stress": 0.1}},
        ],
        "probability": 0.04,
    },
    {
        "id": "difficult_guest",
        "title": "Impossible Guest",
        "description": "A guest is sending back every wine, claiming each one is flawed. The wines appear to be perfectly sound.",
        "category": "service",
        "severity": "negative",
        "effects": {"satisfaction_penalty": -0.2},
        "choices": [
            {"text": "Patiently work through their concerns, offer alternatives", "effect": {"satisfaction": 0.1, "time_cost": 20}},
            {"text": "Offer to comp a glass and start fresh", "effect": {"budget": -30, "satisfaction": 0.3}},
            {"text": "Gently explain the wines are in good condition", "effect": {"satisfaction": -0.1, "reputation": -5}},
        ],
        "probability": 0.06,
    },
    {
        "id": "corked_bottle",
        "title": "Corked Bottle",
        "description": "A guest flags a wine as potentially corked. You need to assess the situation.",
        "category": "service",
        "severity": "negative",
        "effects": {},
        "choices": [
            {"text": "Smell the wine yourself and make a call", "effect": {"skill_check": "tasting_accuracy"}},
            {"text": "Replace it immediately without question", "effect": {"budget": -40, "satisfaction": 0.2}},
            {"text": "Offer to let the wine open up for a few minutes", "effect": {"time_cost": 10, "skill_check": "wine_knowledge"}},
        ],
        "probability": 0.08,
    },
    # Business events
    {
        "id": "rare_allocation",
        "title": "Rare Wine Allocation Offered",
        "description": "A top distributor is offering you allocation of an extremely rare, highly-rated wine. Only 3 cases available.",
        "category": "business",
        "severity": "positive",
        "effects": {"opportunity": True},
        "choices": [
            {"text": "Buy all 3 cases — invest in prestige", "effect": {"budget": -3600, "prestige": 100, "cellar_add": True}},
            {"text": "Buy 1 case — cautious investment", "effect": {"budget": -1200, "prestige": 40, "cellar_add": True}},
            {"text": "Pass — save the budget for proven sellers", "effect": {"budget": 0, "prestige": -10}},
        ],
        "min_career_stage": "sommelier",
        "probability": 0.05,
    },
    {
        "id": "vendor_deal",
        "title": "Vendor Closeout Deal",
        "description": "A distributor is closing out a vintage and offering 40% off a solid wine you carry.",
        "category": "business",
        "severity": "positive",
        "effects": {"discount": 0.40},
        "probability": 0.08,
    },
    {
        "id": "price_increase",
        "title": "Supplier Price Increase",
        "description": "Your main wine supplier has announced a 15% price increase across their portfolio, effective next month.",
        "category": "business",
        "severity": "negative",
        "effects": {"cost_increase": 0.15},
        "choices": [
            {"text": "Stock up now before prices rise", "effect": {"budget": -2000, "savings": True}},
            {"text": "Accept the increase and adjust wine list prices", "effect": {"list_price_increase": 0.10}},
            {"text": "Negotiate — leverage your volume for a smaller increase", "effect": {"skill_check": "business_acumen", "cost_increase": 0.08}},
        ],
        "probability": 0.04,
    },
    # Wine world events
    {
        "id": "vintage_of_century",
        "title": "Vintage of the Century Declared",
        "description": "Critics are declaring the latest vintage from a major region as one of the greatest ever. Prices will skyrocket.",
        "category": "wine_world",
        "severity": "positive",
        "effects": {"vintage_hype": True},
        "probability": 0.02,
    },
    {
        "id": "frost_damage",
        "title": "Spring Frost in Major Region",
        "description": "Late spring frosts have devastated vineyards in a major wine region. Production will be down 40-60% this vintage.",
        "category": "wine_world",
        "severity": "negative",
        "effects": {"supply_decrease": 0.50, "price_increase_region": 0.30},
        "probability": 0.03,
    },
    {
        "id": "wine_trend",
        "title": "Wine Trend Alert",
        "description": "Food media is buzzing about a previously overlooked wine region. Guest requests for these wines are increasing.",
        "category": "wine_world",
        "severity": "neutral",
        "effects": {"trend_region": True, "demand_increase": 0.20},
        "probability": 0.06,
    },
    # Career events
    {
        "id": "wine_competition",
        "title": "Sommelier Competition Invitation",
        "description": "You've been invited to participate in a regional sommelier competition. It could boost your reputation significantly.",
        "category": "career",
        "severity": "positive",
        "effects": {"competition": True},
        "choices": [
            {"text": "Accept and prepare intensively", "effect": {"skill_check": "tasting_accuracy", "reputation_potential": 200}},
            {"text": "Decline — too much on your plate right now", "effect": {"reputation": -10}},
        ],
        "min_career_stage": "sommelier",
        "probability": 0.03,
    },
    {
        "id": "media_feature",
        "title": "Magazine Feature",
        "description": "A food & wine magazine wants to feature your restaurant's wine program in an upcoming issue.",
        "category": "career",
        "severity": "positive",
        "effects": {"reputation_bonus": 100, "traffic_increase": 0.15},
        "probability": 0.02,
    },
    {
        "id": "staff_quits",
        "title": "Staff Member Quits",
        "description": "One of your trained servers has given notice. You'll need to train a replacement.",
        "category": "career",
        "severity": "negative",
        "effects": {"staff_loss": 1},
        "min_career_stage": "head_sommelier",
        "probability": 0.05,
    },
    {
        "id": "wine_dinner_request",
        "title": "Wine Dinner Request",
        "description": "A regular guest wants to host a private wine dinner for 12 people. They want a 5-course pairing menu.",
        "category": "service",
        "severity": "positive",
        "effects": {"revenue_opportunity": True, "reputation_potential": 80},
        "choices": [
            {"text": "Accept — design a showcase menu highlighting your best wines", "effect": {"revenue": 3000, "reputation": 80, "time_cost": 40}},
            {"text": "Accept — play it safe with crowd-pleasing classics", "effect": {"revenue": 2000, "reputation": 30, "time_cost": 20}},
            {"text": "Decline — you're not ready for this yet", "effect": {"reputation": -20}},
        ],
        "min_career_stage": "sommelier",
        "probability": 0.04,
    },
]

CAREER_ORDER = [
    "assistant_sommelier", "sommelier", "head_sommelier", "beverage_director"
]


def generate_weekly_events(
    career_stage: str = "assistant_sommelier",
    game_week: int = 1,
) -> list[GameEvent]:
    """Generate random events for a game week.

    Returns a list of events that triggered this week.
    """
    stage_idx = CAREER_ORDER.index(career_stage) if career_stage in CAREER_ORDER else 0
    triggered = []

    for event_data in DEFAULT_EVENTS:
        # Check career stage requirement
        min_stage = event_data.get("min_career_stage", "assistant_sommelier")
        min_idx = CAREER_ORDER.index(min_stage) if min_stage in CAREER_ORDER else 0
        if stage_idx < min_idx:
            continue

        # Roll for probability
        prob = event_data.get("probability", 0.1)
        # Slightly increase event frequency as game progresses
        prob *= 1.0 + (game_week * 0.005)
        prob = min(prob, 0.5)

        if random.random() < prob:
            event = GameEvent(
                id=event_data["id"],
                title=event_data["title"],
                description=event_data["description"],
                category=event_data["category"],
                severity=event_data["severity"],
                effects=event_data.get("effects", {}),
                choices=event_data.get("choices", []),
                min_career_stage=event_data.get("min_career_stage", "assistant_sommelier"),
                probability=prob,
            )
            triggered.append(event)

    return triggered
