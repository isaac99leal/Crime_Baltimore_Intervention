"""Distributor/grower relationship and allocation mechanics."""

from __future__ import annotations

from dataclasses import dataclass
import random

from .domain import AllocationOffer, BeverageProgram, RelationshipAccount


@dataclass(frozen=True)
class AllocationDecision:
    success: bool
    probability: float
    bottles_awarded: int
    explanation: str


class RelationshipManager:
    def __init__(self, program: BeverageProgram):
        self.program = program

    def record_purchase(self, supplier_id: str, amount: float) -> None:
        account = self._account(supplier_id)
        account.spend_ytd += max(0.0, amount)
        account.trust += min(2.5, max(0.0, amount) / 5_000)
        account.last_contact_day = self.program.day
        account.clamp()

    def record_contact(self, supplier_id: str, quality: float, time_blocks: int = 1) -> bool:
        if not self.program.spend_time(time_blocks):
            return False
        account = self._account(supplier_id)
        q = max(0.0, min(1.0, quality))
        account.trust += 1.0 + q * 3.0
        account.access += q * 1.5
        account.last_contact_day = self.program.day
        account.clamp()
        return True

    def support_portfolio(self, supplier_id: str, spend: float) -> None:
        account = self._account(supplier_id)
        account.support_score += min(8.0, max(0.0, spend) / 500)
        account.spend_ytd += max(0.0, spend)
        account.trust += min(3.0, max(0.0, spend) / 2_000)
        account.clamp()

    def allocation_probability(self, offer: AllocationOffer) -> float:
        account = self._account(offer.supplier_id)
        spend_score = min(1.0, account.spend_ytd / max(1.0, offer.required_support_spend or 20_000.0))
        relationship = (
            account.trust * 0.35
            + account.access * 0.25
            + account.reliability * 0.15
            + account.support_score * 0.15
            + self.program.reputation * 0.10
        ) / 100.0
        scarcity_penalty = max(0.05, 1.0 - (offer.scarcity * 0.75))
        lateness_penalty = max(0.65, 1.0 - account.late_payments * 0.08)
        probability = (0.12 + relationship * 0.62 + spend_score * 0.20) * scarcity_penalty * lateness_penalty
        return max(0.02, min(0.98, probability))

    def resolve_allocation(self, offer: AllocationOffer, seed: int | None = None) -> AllocationDecision:
        probability = self.allocation_probability(offer)
        rng = random.Random(seed)
        success = rng.random() < probability
        if not success:
            return AllocationDecision(False, probability, 0, "Allocation missed: relationship, support spend, or access was not strong enough.")

        account = self._account(offer.supplier_id)
        access_factor = 0.45 + (account.access / 100.0) * 0.55
        awarded = max(1, min(offer.offered_bottles, round(offer.offered_bottles * access_factor)))
        return AllocationDecision(True, probability, awarded, "Allocation secured. Stronger access can increase the awarded share next cycle.")

    def _account(self, supplier_id: str) -> RelationshipAccount:
        try:
            return self.program.relationships[supplier_id]
        except KeyError as exc:
            raise KeyError(f"unknown supplier_id: {supplier_id}") from exc
