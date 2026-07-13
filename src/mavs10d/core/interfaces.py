from __future__ import annotations

from typing import Any, Protocol

from mavs10d.core.types import (
    CandidateAction,
    GovernanceDecision,
    Observation,
    StepResult,
)


class DynamicGovernanceEnv(Protocol):
    environment_id: str

    def reset(self, seed: int) -> Observation:
        ...

    def propose_candidate(self, obs: Observation) -> CandidateAction:
        ...

    def step(self, decision: GovernanceDecision) -> StepResult:
        ...

    def hidden_labels(self) -> dict[str, Any]:
        ...


class GovernanceMethod(Protocol):
    method_id: str

    def reset(self, seed: int) -> None:
        ...

    def decide(
        self, obs: Observation, candidate: CandidateAction
    ) -> GovernanceDecision:
        ...

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        ...

