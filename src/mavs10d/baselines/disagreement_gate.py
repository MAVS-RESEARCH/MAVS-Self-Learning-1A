from __future__ import annotations

from mavs10d.baselines.common import clamp, disagreement_metrics, governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


class DisagreementGateBaseline:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.reject_threshold = float(config.params.get("reject_threshold", 0.55))
        self.escalate_threshold = float(config.params.get("escalate_threshold", 0.30))
        self.weights = dict(config.params.get("weights", {"spread": 0.5, "variance": 0.25, "entropy": 0.25}))

    def reset(self, seed: int) -> None:
        self._seed = int(seed)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase3.disagreement_gate.decide.start
        console_log(
            "phase3.disagreement_gate.decide.start",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
        )
        metrics = disagreement_metrics(candidate)
        score = clamp(
            metrics["spread"] * float(self.weights.get("spread", 0.5))
            + metrics["variance"] * float(self.weights.get("variance", 0.25))
            + metrics["entropy"] * float(self.weights.get("entropy", 0.25))
        )
        if score >= self.reject_threshold:
            decision = "reject"
            threshold = self.reject_threshold
            triggered = ["disagreement_reject_gate"]
            escalation_reason = None
        elif score >= self.escalate_threshold:
            decision = "escalate"
            threshold = self.escalate_threshold
            triggered = ["disagreement_escalation_gate"]
            escalation_reason = "specialist disagreement above escalation threshold"
        else:
            decision = "accept"
            threshold = self.escalate_threshold
            triggered = []
            escalation_reason = None
        # console.log: phase3.disagreement_gate.decide.complete
        console_log(
            "phase3.disagreement_gate.decide.complete",
            method_id=self.method_id,
            t=obs.t,
            decision=decision,
            disagreement_score=score,
        )
        return governance_decision(
            baseline_name="disagreement_gate",
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=score,
            severity=score,
            threshold=threshold,
            rationale="specialist disagreement and uncertainty gate",
            triggered_checks=triggered,
            details={
                "disagreement_metrics": metrics,
                "disagreement_score": score,
                "weights": self.weights,
                "escalation_reason": escalation_reason,
            },
        )

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        return None

