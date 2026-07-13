from __future__ import annotations

from mavs10d.baselines.common import governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


class AlwaysAcceptBaseline:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id

    def reset(self, seed: int) -> None:
        self._seed = int(seed)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase6.sanity.always_accept.decide
        console_log("phase6.sanity.always_accept.decide", method_id=self.method_id, t=obs.t)
        return governance_decision(
            baseline_name="always_accept",
            obs=obs,
            candidate=candidate,
            decision="accept",
            risk_score=0.0,
            severity=0.0,
            threshold=1.0,
            rationale="sanity baseline that accepts every candidate",
            triggered_checks=[],
            details={"sanity_baseline": "accept_everything"},
        )

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        return None


class AlwaysRejectBaseline:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id

    def reset(self, seed: int) -> None:
        self._seed = int(seed)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase6.sanity.always_reject.decide
        console_log("phase6.sanity.always_reject.decide", method_id=self.method_id, t=obs.t)
        return governance_decision(
            baseline_name="always_reject",
            obs=obs,
            candidate=candidate,
            decision="reject",
            risk_score=1.0,
            severity=1.0,
            threshold=0.0,
            rationale="sanity baseline that rejects every candidate",
            triggered_checks=["sanity_reject_everything"],
            details={"sanity_baseline": "reject_everything"},
        )

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        return None
