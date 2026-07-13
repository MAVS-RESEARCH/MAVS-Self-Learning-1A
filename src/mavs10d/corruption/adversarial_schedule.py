"""Budgeted adversarial-response schedule without participant hidden-state access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AdversarialScheduleState:
    step: int
    remaining_budget: float
    intensity: float
    target: str


class BudgetedAdversarialSchedule:
    def __init__(self, budget: float, maximum_step_intensity: float = 1.0) -> None:
        if budget < 0 or not 0 < maximum_step_intensity <= 1:
            raise ValueError("Invalid adversarial schedule budget.")
        self._initial_budget = float(budget)
        self._maximum = float(maximum_step_intensity)

    def state(self, step: int, public_signals: Mapping[str, float], spent: float) -> AdversarialScheduleState:
        if step < 0 or spent < 0:
            raise ValueError("step and spent must be non-negative.")
        remaining = max(0.0, self._initial_budget - spent)
        uncertainty = max(0.0, min(1.0, float(public_signals.get("uncertainty", 0.0))))
        disagreement = max(0.0, min(1.0, float(public_signals.get("disagreement", 0.0))))
        intensity = min(self._maximum, remaining, 0.5 * uncertainty + 0.5 * disagreement)
        target = "evidence" if uncertainty >= disagreement else "specialists"
        return AdversarialScheduleState(step, remaining, intensity, target)
