from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from mavs10d.core.hashing import stable_hash
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, mavs_trace_template


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def candidate_risk(candidate: CandidateAction) -> float:
    if "risk_proxy" in candidate.provenance:
        return clamp(float(candidate.provenance["risk_proxy"]))
    if "hidden_risk_proxy" in candidate.provenance:
        return clamp(float(candidate.provenance["hidden_risk_proxy"]))
    return clamp(1.0 - float(candidate.confidence))


def specialist_scores(candidate: CandidateAction) -> list[float]:
    scores: list[float] = []
    for output in candidate.specialist_outputs.values():
        if isinstance(output, dict) and "score" in output:
            scores.append(clamp(float(output["score"])))
    return scores


def disagreement_metrics(candidate: CandidateAction) -> dict[str, float]:
    scores = specialist_scores(candidate)
    if not scores:
        return {"variance": 0.0, "spread": 0.0, "entropy": 0.0}
    mean = sum(scores) / len(scores)
    variance = sum((score - mean) ** 2 for score in scores) / len(scores)
    spread = max(scores) - min(scores)
    accept_fraction = sum(score >= 0.5 for score in scores) / len(scores)
    entropy = _binary_entropy(accept_fraction)
    return {
        "variance": clamp(variance),
        "spread": clamp(spread),
        "entropy": clamp(entropy),
    }


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at {path}")
    return data


def make_baseline_trace(
    baseline_name: str,
    obs: Observation,
    candidate: CandidateAction,
    risk_score: float,
    severity: float,
    threshold: float,
    triggered_checks: list[str],
    details: dict[str, Any],
) -> dict[str, Any]:
    scores = specialist_scores(candidate)
    disagreement = disagreement_metrics(candidate)
    trace = mavs_trace_template()
    trace.update(
        {
            "specialist_id": list(candidate.specialist_outputs),
            "representation_hash": stable_hash(
                {
                    "baseline": baseline_name,
                    "episode_id": obs.episode_id,
                    "t": obs.t,
                    "candidate": candidate.to_dict(),
                }
            ),
            "support_score": clamp(1.0 - risk_score),
            "confidence": candidate.confidence,
            "source": baseline_name,
            "corruption_exposure": obs.corruption_hint,
            "diagnostic_values": {
                "baseline_details": details,
                "candidate_risk": candidate_risk(candidate),
            },
            "disagreement": disagreement["spread"],
            "consistency": clamp(1.0 - disagreement["spread"]),
            "missing_evidence": 1.0
            if candidate.provenance.get("evidence_visible") is False
            else 0.0,
            "policy_conflict": severity,
            "corruption_signal": float(
                obs.risk_context.get("corruption_level", 0.0) or 0.0
            ),
            "raw_severity": severity,
            "normalized_severity": clamp(severity),
            "severity_contribution_breakdown": details,
            "base_threshold": threshold,
            "threshold_delta": float(details.get("threshold_delta", 0.0) or 0.0),
            "final_threshold": threshold,
            "escalation_reason": details.get("escalation_reason"),
            "fallback_action": details.get("fallback_action"),
        }
    )
    if scores:
        trace["diagnostic_values"]["specialist_scores"] = scores
    return trace


def governance_decision(
    baseline_name: str,
    obs: Observation,
    candidate: CandidateAction,
    decision: str,
    risk_score: float,
    severity: float,
    threshold: float,
    rationale: str,
    triggered_checks: list[str],
    details: dict[str, Any],
) -> GovernanceDecision:
    trace = make_baseline_trace(
        baseline_name=baseline_name,
        obs=obs,
        candidate=candidate,
        risk_score=risk_score,
        severity=severity,
        threshold=threshold,
        triggered_checks=triggered_checks,
        details=details,
    )
    return GovernanceDecision(
        decision=decision,  # type: ignore[arg-type]
        risk_score=clamp(risk_score),
        severity=clamp(severity),
        rationale=rationale,
        triggered_checks=triggered_checks,
        threshold=threshold,
        trace=trace,
    )


def _binary_entropy(p: float) -> float:
    p = clamp(p)
    if p in {0.0, 1.0}:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))

