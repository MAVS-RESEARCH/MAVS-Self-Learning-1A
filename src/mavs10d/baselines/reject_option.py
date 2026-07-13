from __future__ import annotations

from mavs10d.baselines.common import candidate_risk, clamp, governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


class RejectOptionBaseline:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.reject_threshold = float(config.params.get("reject_threshold", 0.65))
        self.escalate_threshold = float(config.params.get("escalate_threshold", 0.45))
        self.initial_reject_threshold = self.reject_threshold
        self.initial_escalate_threshold = self.escalate_threshold
        self.adaptive = bool(config.params.get("adaptive", False))
        self.adaptation_rate = float(config.params.get("adaptation_rate", 0.02))
        self.threshold_sweep = [
            float(value)
            for value in config.params.get("threshold_sweep", [0.30, 0.40, 0.50, 0.60, 0.70])
        ]

    def reset(self, seed: int) -> None:
        self._seed = int(seed)
        self.reject_threshold = self.initial_reject_threshold
        self.escalate_threshold = self.initial_escalate_threshold

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase3.reject_option.decide.start
        console_log(
            "phase3.reject_option.decide.start",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
            reject_threshold=self.reject_threshold,
            escalate_threshold=self.escalate_threshold,
        )
        risk = candidate_risk(candidate)
        if risk >= self.reject_threshold:
            decision = "reject"
            triggered = ["reject_option_reject"]
            threshold = self.reject_threshold
            escalation_reason = None
        elif risk >= self.escalate_threshold:
            decision = "escalate"
            triggered = ["reject_option_escalate"]
            threshold = self.escalate_threshold
            escalation_reason = "risk inside reject-option escalation band"
        else:
            decision = "accept"
            triggered = []
            threshold = self.escalate_threshold
            escalation_reason = None
        sweep_decisions = {
            str(value): "reject" if risk >= value else "accept"
            for value in self.threshold_sweep
        }
        # console.log: phase3.reject_option.decide.complete
        console_log(
            "phase3.reject_option.decide.complete",
            method_id=self.method_id,
            t=obs.t,
            decision=decision,
            risk_score=risk,
        )
        return governance_decision(
            baseline_name="reject_option",
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=risk,
            severity=risk,
            threshold=threshold,
            rationale="reject-option risk threshold classifier",
            triggered_checks=triggered,
            details={
                "adaptive": self.adaptive,
                "reject_threshold": self.reject_threshold,
                "escalate_threshold": self.escalate_threshold,
                "threshold_sweep": self.threshold_sweep,
                "sweep_decisions": sweep_decisions,
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
        if not self.adaptive:
            return None
        old_reject = self.reject_threshold
        old_escalate = self.escalate_threshold
        if result.unsafe_accepted:
            self.reject_threshold = clamp(self.reject_threshold - self.adaptation_rate, 0.05, 0.95)
            self.escalate_threshold = clamp(self.escalate_threshold - self.adaptation_rate, 0.05, self.reject_threshold)
        elif result.false_rejected:
            self.reject_threshold = clamp(self.reject_threshold + self.adaptation_rate, self.escalate_threshold, 0.95)
        # console.log: phase3.reject_option.update
        console_log(
            "phase3.reject_option.update",
            method_id=self.method_id,
            t=obs.t,
            old_reject_threshold=old_reject,
            new_reject_threshold=self.reject_threshold,
            old_escalate_threshold=old_escalate,
            new_escalate_threshold=self.escalate_threshold,
        )
