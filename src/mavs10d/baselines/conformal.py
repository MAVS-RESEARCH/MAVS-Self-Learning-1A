from __future__ import annotations

from collections import deque

import numpy as np

from mavs10d.baselines.common import candidate_risk, clamp, governance_decision, load_yaml_config
from mavs10d.core.config import MethodConfig
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


class ConformalAbstentionBaseline:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        params = self._load_params(config.params)
        self.alpha = float(params.get("alpha", 0.10))
        self.calibration_scores = [float(score) for score in params.get("calibration_scores", [0.20, 0.35, 0.50, 0.65, 0.80])]
        self.threshold = self._quantile(self.calibration_scores, 1.0 - self.alpha)
        self.initial_threshold = self.threshold
        self.escalate_band = float(params.get("escalate_band", 0.05))

    def reset(self, seed: int) -> None:
        self._seed = int(seed)
        self.threshold = self.initial_threshold

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase3.conformal_static.decide.start
        console_log(
            "phase3.conformal_static.decide.start",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
            threshold=self.threshold,
        )
        score = self.nonconformity(obs, candidate)
        if score > self.threshold:
            decision = "reject"
            triggered = ["conformal_reject"]
            escalation_reason = None
        elif score > max(0.0, self.threshold - self.escalate_band):
            decision = "escalate"
            triggered = ["conformal_abstain_band"]
            escalation_reason = "nonconformity inside escalation band"
        else:
            decision = "accept"
            triggered = []
            escalation_reason = None
        # console.log: phase3.conformal_static.decide.complete
        console_log(
            "phase3.conformal_static.decide.complete",
            method_id=self.method_id,
            t=obs.t,
            decision=decision,
            nonconformity_score=score,
        )
        return governance_decision(
            baseline_name="conformal_static",
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=score,
            severity=score,
            threshold=self.threshold,
            rationale="static conformal abstention threshold",
            triggered_checks=triggered,
            details={
                "alpha": self.alpha,
                "calibration_size": len(self.calibration_scores),
                "nonconformity_score": score,
                "static_threshold": self.threshold,
                "refuses_update": True,
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

    def nonconformity(self, obs: Observation, candidate: CandidateAction) -> float:
        return candidate_risk(candidate)

    def _load_params(self, params: dict) -> dict:
        if "conformal_path" in params:
            data = load_yaml_config(params["conformal_path"])
            loaded = dict(data.get("conformal", {}))
        else:
            loaded = dict(params)
        if "calibration_scores_path" in loaded:
            calibration_data = load_yaml_config(loaded["calibration_scores_path"])
            loaded["calibration_scores"] = list(calibration_data["calibration_scores"])
        return loaded

    def _quantile(self, values: list[float], quantile: float) -> float:
        return clamp(float(np.quantile(values, quantile)))


class AdaptiveConformalBaseline(ConformalAbstentionBaseline):
    def __init__(self, config: MethodConfig):
        super().__init__(config)
        params = self._load_params(config.params)
        self.window = int(params.get("window", 25))
        self.scores = deque(self.calibration_scores, maxlen=self.window)
        self.update_count = 0
        self.previous_threshold = self.threshold

    def reset(self, seed: int) -> None:
        super().reset(seed)
        self.scores = deque(self.calibration_scores, maxlen=self.window)
        self.update_count = 0
        self.previous_threshold = self.threshold

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        old_threshold = self.threshold
        self.threshold = self._quantile(list(self.scores), 1.0 - self.alpha)
        self.previous_threshold = old_threshold
        # console.log: phase3.conformal_adaptive.decide.start
        console_log(
            "phase3.conformal_adaptive.decide.start",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
            threshold=self.threshold,
            update_count=self.update_count,
        )
        score = self.nonconformity(obs, candidate)
        if score > self.threshold:
            decision = "reject"
            triggered = ["adaptive_conformal_reject"]
            escalation_reason = None
        elif score > max(0.0, self.threshold - self.escalate_band):
            decision = "escalate"
            triggered = ["adaptive_conformal_abstain_band"]
            escalation_reason = "nonconformity inside adaptive escalation band"
        else:
            decision = "accept"
            triggered = []
            escalation_reason = None
        # console.log: phase3.conformal_adaptive.decide.complete
        console_log(
            "phase3.conformal_adaptive.decide.complete",
            method_id=self.method_id,
            t=obs.t,
            decision=decision,
            nonconformity_score=score,
            threshold=self.threshold,
        )
        return governance_decision(
            baseline_name="conformal_adaptive",
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=score,
            severity=score,
            threshold=self.threshold,
            rationale="adaptive conformal abstention threshold",
            triggered_checks=triggered,
            details={
                "alpha": self.alpha,
                "window": self.window,
                "window_size": len(self.scores),
                "nonconformity_score": score,
                "threshold": self.threshold,
                "update_count": self.update_count,
                "threshold_delta": self.threshold - old_threshold,
                "distribution_shift_level": float(
                    obs.risk_context.get("corruption_level", 0.0) or 0.0
                ),
                "threshold_lag_signal": bool(
                    float(obs.risk_context.get("corruption_level", 0.0) or 0.0) > 0.30
                    and score > self.threshold
                ),
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
        score = self.nonconformity(obs, candidate)
        self.scores.append(score)
        self.update_count += 1
        old_threshold = self.threshold
        self.threshold = self._quantile(list(self.scores), 1.0 - self.alpha)
        # console.log: phase3.conformal_adaptive.update
        console_log(
            "phase3.conformal_adaptive.update",
            method_id=self.method_id,
            t=obs.t,
            nonconformity_score=score,
            old_threshold=old_threshold,
            new_threshold=self.threshold,
            update_count=self.update_count,
        )
