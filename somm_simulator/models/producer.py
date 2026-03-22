"""Producer/estate model — procedurally generated, no real names."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Producer:
    """A fictional wine producer/estate."""
    id: str
    name: str                     # e.g. "Domaine de la Roche Haute"
    estate_name: str              # e.g. "Château Bellevue"
    country: str
    region: str
    sub_region: str = ""
    commune: str = ""
    founded_year: int = 1900
    quality_tier: float = 0.5    # 0.0-1.0 (affects wine quality variance)
    reputation: float = 0.5      # 0.0-1.0 (affects price and desirability)
    style_bias: str = "balanced"  # "traditional", "modern", "balanced", "natural"
    production_size: str = "small"  # "micro", "small", "medium", "large", "negociant"
    specialties: list[str] = field(default_factory=list)  # Grape varieties they excel at

    @property
    def prestige_modifier(self) -> float:
        """Price multiplier based on reputation."""
        return 0.5 + (self.reputation * 2.0)  # 0.5x to 2.5x

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "estate_name": self.estate_name,
            "country": self.country,
            "region": self.region,
            "sub_region": self.sub_region,
            "commune": self.commune,
            "founded_year": self.founded_year,
            "quality_tier": self.quality_tier,
            "reputation": self.reputation,
            "style_bias": self.style_bias,
            "production_size": self.production_size,
            "specialties": self.specialties,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Producer:
        return cls(**data)
