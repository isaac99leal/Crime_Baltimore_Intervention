"""Player character model."""

from __future__ import annotations
from dataclasses import dataclass, field
from somm_simulator.config import CAREER_STAGES


@dataclass
class PlayerSkills:
    """Skills that improve through gameplay."""
    tasting_accuracy: float = 0.3    # 0-1, affects blind tasting success
    service_grace: float = 0.3       # 0-1, affects guest satisfaction
    wine_knowledge: float = 0.1      # 0-1, affects pairing quality
    business_acumen: float = 0.1     # 0-1, affects purchasing deals
    leadership: float = 0.0          # 0-1, affects staff training
    salesmanship: float = 0.2        # 0-1, affects upselling

    def improve(self, skill: str, amount: float):
        current = getattr(self, skill, 0.0)
        setattr(self, skill, min(1.0, current + amount))

    def to_dict(self) -> dict:
        return {
            "tasting_accuracy": self.tasting_accuracy,
            "service_grace": self.service_grace,
            "wine_knowledge": self.wine_knowledge,
            "business_acumen": self.business_acumen,
            "leadership": self.leadership,
            "salesmanship": self.salesmanship,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerSkills:
        return cls(**data)


@dataclass
class Player:
    """The player character."""
    name: str = "Sommelier"
    career_stage: str = "assistant_sommelier"
    reputation: int = 0
    total_tips: float = 0.0
    services_completed: int = 0
    wines_tasted: int = 0
    correct_blind_tastings: int = 0
    total_blind_tastings: int = 0
    skills: PlayerSkills = field(default_factory=PlayerSkills)
    # Regions the player has studied / wines they've learned
    known_regions: list[str] = field(default_factory=list)
    known_grapes: list[str] = field(default_factory=list)

    @property
    def stage_info(self) -> dict:
        return CAREER_STAGES.get(self.career_stage, CAREER_STAGES["assistant_sommelier"])

    @property
    def title(self) -> str:
        return self.stage_info["title"]

    @property
    def can_promote(self) -> bool:
        stages = list(CAREER_STAGES.keys())
        current_idx = stages.index(self.career_stage)
        if current_idx >= len(stages) - 1:
            return False
        next_stage = stages[current_idx + 1]
        return self.reputation >= CAREER_STAGES[next_stage]["reputation_needed"]

    def promote(self) -> bool:
        """Attempt promotion. Returns True if successful."""
        if not self.can_promote:
            return False
        stages = list(CAREER_STAGES.keys())
        current_idx = stages.index(self.career_stage)
        self.career_stage = stages[current_idx + 1]
        return True

    @property
    def blind_tasting_accuracy(self) -> float:
        if self.total_blind_tastings == 0:
            return 0.0
        return self.correct_blind_tastings / self.total_blind_tastings

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "career_stage": self.career_stage,
            "reputation": self.reputation,
            "total_tips": self.total_tips,
            "services_completed": self.services_completed,
            "wines_tasted": self.wines_tasted,
            "correct_blind_tastings": self.correct_blind_tastings,
            "total_blind_tastings": self.total_blind_tastings,
            "skills": self.skills.to_dict(),
            "known_regions": self.known_regions,
            "known_grapes": self.known_grapes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Player:
        data["skills"] = PlayerSkills.from_dict(data["skills"])
        return cls(**data)
