from __future__ import annotations

from collections import Counter
from typing import Any

from mavs10d.baselines.common import candidate_risk, clamp
from mavs10d.core.config import MethodConfig
from mavs10d.core.hashing import stable_hash
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult
from mavs10d.governance.ablations import AblationConfig
from mavs10d.governance.diagnostics import compute_diagnostics, diagnostic_flags
from mavs10d.governance.escalation import (
    evaluate_mitigation,
    final_decision_functional,
    hard_veto_status,
)
from mavs10d.governance.severity import aggregate_severity
from mavs10d.governance.thresholds import compute_threshold
from mavs10d.governance.trace_formatter import format_mavs_trace


class MAVSGovernance:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.base_threshold = float(config.params.get("base_threshold", 0.60))
        self.severity_sensitivity = float(config.params.get("severity_sensitivity", 0.25))
        self.max_mitigation_relaxation = float(config.params.get("max_mitigation_relaxation", 0.10))
        self.escalation_band = float(config.params.get("escalation_band", 0.08))
        self.ablation = AblationConfig.from_params(dict(config.params.get("ablation", {})))
        self._seed = 0

    def reset(self, seed: int) -> None:
        # console.log: phase4.mavs_gc.reset
        console_log("phase4.mavs_gc.reset", method_id=self.method_id, seed=seed)
        self._seed = int(seed)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase4.mavs_gc.decide.start
        console_log(
            "phase4.mavs_gc.decide.start",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
        )
        representation = self._extract_representation(obs, candidate)
        support_scores = self._support_scores(candidate)
        diagnostics = self.ablation.apply_diagnostics(
            compute_diagnostics(obs, candidate),
            obs=obs,
            seed=self._seed,
        )
        severity = self.ablation.apply_severity(
            aggregate_severity(diagnostics, self.config.params.get("severity_weights")),
            obs=obs,
            seed=self._seed,
        )
        weights = self._rebalance_weights(candidate, diagnostics)
        weights = self.ablation.apply_weights(weights)
        mitigation = evaluate_mitigation(obs, candidate, diagnostics, self.max_mitigation_relaxation)
        hard_veto = hard_veto_status(obs, candidate, diagnostics)
        threshold = self.ablation.compute_threshold(
            obs=obs,
            base_threshold=self.base_threshold,
            severity=severity.normalized_severity,
            mitigation_strength=mitigation.strength,
            hard_veto=hard_veto.active,
            severity_sensitivity=self.severity_sensitivity,
            max_mitigation_relaxation=self.max_mitigation_relaxation,
        )
        consensus = self._consensus(support_scores, weights)
        decision_result = self.ablation.apply_decision_policy(
            final_decision_functional(
                consensus=consensus,
                severity=severity.normalized_severity,
                threshold=threshold.final_threshold,
                mitigation=mitigation,
                hard_veto=hard_veto,
                escalation_band=self.escalation_band,
            ),
            threshold=threshold.final_threshold,
        )
        trace = format_mavs_trace(
            obs=obs,
            candidate=candidate,
            representation=representation,
            support_scores=support_scores,
            weights=weights,
            diagnostics=diagnostics,
            severity=severity,
            mitigation=mitigation,
            threshold=threshold,
            consensus=consensus,
            hard_veto=hard_veto,
            final_decision=decision_result.decision,
            risk_score=decision_result.risk_score,
        )
        trace["escalation_reason"] = decision_result.escalation_reason
        trace["fallback_action"] = decision_result.fallback_action
        trace["ablation"] = self.ablation.trace_details()
        trace["formal_calculus"]["ablation"] = self.ablation.trace_details()
        triggered = decision_result.triggered_checks + [
            f"diagnostic:{name}" for name, active in diagnostic_flags(diagnostics).items() if active
        ]
        # console.log: phase4.mavs_gc.decide.complete
        console_log(
            "phase4.mavs_gc.decide.complete",
            method_id=self.method_id,
            decision=decision_result.decision,
            risk_score=decision_result.risk_score,
            severity=severity.normalized_severity,
            threshold=threshold.final_threshold,
        )
        return GovernanceDecision(
            decision=decision_result.decision,  # type: ignore[arg-type]
            risk_score=decision_result.risk_score,
            severity=severity.normalized_severity,
            rationale="MAVS-GC formal governance functional with diagnostics, severity, thresholds, mitigation, and hard veto",
            triggered_checks=triggered,
            threshold=threshold.final_threshold,
            trace=trace,
        )

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        # console.log: phase4.mavs_gc.update
        console_log(
            "phase4.mavs_gc.update",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
            reward=result.reward,
        )

    def _extract_representation(
        self, obs: Observation, candidate: CandidateAction
    ) -> dict[str, Any]:
        # console.log: phase4.mavs_gc.phi.extract
        console_log("phase4.mavs_gc.phi.extract", episode_id=obs.episode_id, t=obs.t)
        payload = {
            "X": {
                "visible_state": obs.visible_state,
                "prompt": obs.prompt,
                "risk_context": obs.risk_context,
            },
            "candidate": candidate.to_dict(),
            "seed": self._seed,
        }
        payload = self.ablation.representation_payload(payload)
        return {
            "hash": stable_hash(payload),
            "visible_state_keys": sorted(obs.visible_state),
            "candidate_action_type": candidate.action_type,
            "specialist_count": len(candidate.specialist_outputs),
            "representation_sharing": self.ablation.representation_sharing,
        }

    def _support_scores(self, candidate: CandidateAction) -> dict[str, float]:
        # console.log: phase4.mavs_gc.support_scores
        console_log(
            "phase4.mavs_gc.support_scores",
            method_id=self.method_id,
            specialist_count=len(candidate.specialist_outputs),
        )
        supports: dict[str, float] = {}
        for specialist_id, output in candidate.specialist_outputs.items():
            score = float(output.get("score", 1.0 - candidate_risk(candidate))) if isinstance(output, dict) else 0.5
            supports[str(specialist_id)] = clamp(2.0 * clamp(score) - 1.0, -1.0, 1.0)
        if not supports:
            supports["candidate_risk_proxy"] = clamp(1.0 - 2.0 * candidate_risk(candidate), -1.0, 1.0)
        return supports

    def _rebalance_weights(
        self,
        candidate: CandidateAction,
        diagnostics: dict[str, float],
    ) -> dict[str, float]:
        # console.log: phase4.mavs_gc.rebalance_weights.start
        console_log("phase4.mavs_gc.rebalance_weights.start", method_id=self.method_id)
        raw_weights: dict[str, float] = {}
        sources = Counter(
            str(output.get("source", specialist_id))
            for specialist_id, output in candidate.specialist_outputs.items()
            if isinstance(output, dict)
        )
        for specialist_id, output in candidate.specialist_outputs.items():
            if not isinstance(output, dict):
                raw_weights[str(specialist_id)] = 1.0
                continue
            source = str(output.get("source", specialist_id))
            confidence = clamp(float(output.get("confidence", candidate.confidence)))
            source_penalty = 1.0 / max(1, sources[source])
            shared_penalty = 1.0 - 0.35 * diagnostics.get("shared_source_suspicion", 0.0)
            collapse_penalty = 1.0 - 0.25 * diagnostics.get("specialist_collapse_indicator", 0.0)
            raw_weights[str(specialist_id)] = max(0.01, confidence * source_penalty * shared_penalty * collapse_penalty)
        if not raw_weights:
            raw_weights["candidate_risk_proxy"] = 1.0
        total = sum(raw_weights.values()) or 1.0
        weights = {key: value / total for key, value in raw_weights.items()}
        # console.log: phase4.mavs_gc.rebalance_weights.complete
        console_log("phase4.mavs_gc.rebalance_weights.complete", weights=weights)
        return weights

    def _consensus(self, support_scores: dict[str, float], weights: dict[str, float]) -> float:
        consensus = clamp(
            sum(float(support_scores.get(key, 0.0)) * float(weights.get(key, 0.0)) for key in support_scores),
            -1.0,
            1.0,
        )
        # console.log: phase4.mavs_gc.consensus
        console_log("phase4.mavs_gc.consensus", method_id=self.method_id, consensus=consensus)
        return consensus
