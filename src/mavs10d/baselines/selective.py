"""Confidence, entropy, margin, and generalized selective Phase 1 gates."""

from __future__ import annotations

from mavs10d.baselines.phase1_common import Phase1Baseline, visible_risk
from mavs10d.core.types import CandidateAction, Observation


class SelectiveBaseline(Phase1Baseline):
    def score(self, obs: Observation, candidate: CandidateAction) -> float:
        mode = str(self.config.params.get("mode", "confidence"))
        if mode == "confidence":
            return visible_risk(candidate)
        if mode == "entropy":
            return float(obs.visible_state["entropy"])
        if mode == "margin":
            return 1.0 - float(obs.visible_state["margin"])
        if mode == "generalized_selective":
            return min(
                1.0,
                0.55 * visible_risk(candidate)
                + 0.20 * float(obs.visible_state["entropy"])
                + 0.15 * (1.0 - float(obs.visible_state["evidence_quality"]))
                + 0.10 * float(obs.visible_state["specialist_disagreement"]),
            )
        raise ValueError(f"Unsupported selective mode: {mode}")
