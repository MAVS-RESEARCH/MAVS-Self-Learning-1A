"""Non-competitive trivial diagnostic bounds."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


Action = str


@dataclass
class TrivialBound:
    method_id: str
    fixed_action: Action | None
    seed: int = 0

    @property
    def competitive(self) -> bool:
        return False

    def decisions(self, count: int) -> tuple[Action, ...]:
        if count < 0:
            raise ValueError("count must be non-negative.")
        if self.fixed_action is not None:
            return (self.fixed_action,) * count
        rng = np.random.default_rng(self.seed)
        return tuple(str(value) for value in rng.choice(("accept", "reject", "escalate"), count))


def accept_all() -> TrivialBound:
    return TrivialBound("accept_all_diagnostic", "accept")


def reject_all() -> TrivialBound:
    return TrivialBound("reject_all_diagnostic", "reject")


def escalate_all() -> TrivialBound:
    return TrivialBound("escalate_all_diagnostic", "escalate")


def random_bound(seed: int) -> TrivialBound:
    return TrivialBound("random_diagnostic", None, seed)
