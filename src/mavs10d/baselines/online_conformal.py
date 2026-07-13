"""Split, CRC, adaptive, and online conformal benchmark adaptations."""

from __future__ import annotations

import numpy as np

from mavs10d.baselines.phase1_common import Phase1Baseline, visible_risk
from mavs10d.core.types import CandidateAction, Observation


class OnlineConformalBaseline(Phase1Baseline):
    adaptive = True

    def __init__(self, config):
        super().__init__(config)
        self.mode = str(config.params.get("mode", "online"))
        self.adaptive = self.mode not in {"split", "crc"}
        self.alpha = float(config.params.get("alpha", 0.05))
        calibration = [float(value) for value in config.params.get("calibration_scores", [0.15, 0.25, 0.35, 0.45, 0.55])]
        self.calibration_scores = tuple(calibration)
        self.calibration_size = len(calibration)
        self._recompute_threshold()

    def reset(self, seed: int) -> None:
        super().reset(seed)
        self._recompute_threshold()

    def score(self, obs: Observation, candidate: CandidateAction) -> float:
        return visible_risk(candidate)

    def on_released_feedback(self, event):
        if self.mode in {"split", "crc"}:
            return
        residual = abs(float(event["risk_score"]) - float(bool(event["observed_label"])))
        self.resources.update_operations += 1
        values = [abs(float(item["risk_score"]) - float(bool(item["observed_label"]))) for item in self.feedback_history]
        if values:
            old = self.reject_threshold
            quantile = float(np.quantile(values, 1.0 - self.alpha))
            rate = 0.25 if self.mode == "adaptive" else 0.50
            self.reject_threshold = min(0.95, max(0.30, (1.0 - rate) * old + rate * quantile))
            self.escalate_threshold = max(0.15, self.reject_threshold - 0.15)
            if abs(old - self.reject_threshold) > 1e-12:
                self.resources.configuration_switches += 1

    def _recompute_threshold(self) -> None:
        threshold = float(np.quantile(self.calibration_scores, 1.0 - self.alpha))
        if self.mode == "crc":
            threshold = min(threshold, float(self.config.params.get("risk_limit", 0.50)))
        self.reject_threshold = max(0.30, min(0.95, threshold))
        self.escalate_threshold = max(0.15, self.reject_threshold - 0.15)
