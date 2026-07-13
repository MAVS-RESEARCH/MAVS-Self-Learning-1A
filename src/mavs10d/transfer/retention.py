"""Retention non-inferiority, catastrophic interference, and forgetting gates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionResult:
    prior_objective: float
    retained_objective: float
    prior_uar: float
    retained_uar: float
    catastrophic_interference: int
    objective_margin: float
    uar_margin: float

    @property
    def objective_noninferior(self) -> bool:
        return self.retained_objective >= self.prior_objective - self.objective_margin

    @property
    def safety_noninferior(self) -> bool:
        return self.retained_uar <= self.prior_uar + self.uar_margin

    @property
    def passed(self) -> bool:
        return self.objective_noninferior and self.safety_noninferior and self.catastrophic_interference == 0

    @property
    def forgetting(self) -> float:
        return max(0.0, self.prior_objective - self.retained_objective)
