from __future__ import annotations

import random

from mavs10d.baselines.common import candidate_risk, clamp, governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.seeds import derive_seed
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


class SelfConsistencyBaseline:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.k = int(config.params.get("k", 7))
        self.min_margin = float(config.params.get("min_margin", 0.25))
        self.accept_threshold = float(config.params.get("accept_threshold", 0.50))
        self.perturbation = float(config.params.get("perturbation", 0.12))
        self._seed = 0

    def reset(self, seed: int) -> None:
        self._seed = int(seed)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase3.self_consistency.decide.start
        console_log(
            "phase3.self_consistency.decide.start",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
            k=self.k,
        )
        rng = random.Random(derive_seed(self._seed, f"{self.method_id}:{obs.episode_id}", obs.t))
        base_risk = candidate_risk(candidate)
        votes: list[str] = []
        sampled_risks: list[float] = []
        for _ in range(self.k):
            sampled_risk = clamp(base_risk + rng.uniform(-self.perturbation, self.perturbation))
            sampled_risks.append(sampled_risk)
            votes.append("accept" if sampled_risk < self.accept_threshold else "reject")
        accept_votes = votes.count("accept")
        reject_votes = votes.count("reject")
        margin = abs(accept_votes - reject_votes) / self.k
        if margin < self.min_margin:
            decision = "escalate"
            triggered = ["self_consistency_low_margin"]
            escalation_reason = "vote margin below minimum"
        else:
            decision = "accept" if accept_votes > reject_votes else "reject"
            triggered = ["self_consistency_majority_reject"] if decision == "reject" else []
            escalation_reason = None
        risk = clamp(reject_votes / self.k)
        # console.log: phase3.self_consistency.decide.complete
        console_log(
            "phase3.self_consistency.decide.complete",
            method_id=self.method_id,
            t=obs.t,
            decision=decision,
            accept_votes=accept_votes,
            reject_votes=reject_votes,
            margin=margin,
        )
        return governance_decision(
            baseline_name="self_consistency",
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=risk,
            severity=risk,
            threshold=self.accept_threshold,
            rationale="deterministic seed-controlled multi-sample voting",
            triggered_checks=triggered,
            details={
                "k": self.k,
                "votes": votes,
                "sampled_risks": sampled_risks,
                "accept_votes": accept_votes,
                "reject_votes": reject_votes,
                "margin": margin,
                "min_margin": self.min_margin,
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

