"""Frozen operating-point contract and visible-only Phase 4 decision semantics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Mapping

import numpy as np

from mavs10d.baselines.common import governance_decision
from mavs10d.core.hashing import stable_hash
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


ACTION_ACCEPT = np.int8(0)
ACTION_REJECT = np.int8(1)
ACTION_ESCALATE = np.int8(2)
ACTION_NAMES = np.asarray(["accept", "reject", "escalate"], dtype=object)


@dataclass(frozen=True)
class OperatingPoint:
    point_id: str
    family: str
    mechanism: str
    condition: str
    parameters: Mapping[str, float]
    budget: Mapping[str, float | int]
    module: str
    competitive: bool
    oracle: bool
    fidelity_label: str
    source_registry: str
    validated: bool = True

    @property
    def config_hash(self) -> str:
        return stable_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        if include_hash:
            payload["config_hash"] = stable_hash(payload)
        return payload


def expand_grid(values: Mapping[str, list[float]]) -> tuple[dict[str, float], ...]:
    names = tuple(sorted(values))
    return tuple(dict(zip(names, combination)) for combination in product(*(values[name] for name in names)))


class FrozenTournamentMethod:
    """GovernanceMethod-compatible adapter for one frozen Phase 4 operating point."""

    def __init__(self, point: OperatingPoint) -> None:
        self.point = point
        self.method_id = point.point_id

    def reset(self, seed: int) -> None:
        return None

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        visible = {**obs.visible_state, **candidate.provenance}
        arrays = {name: np.asarray([value]) for name, value in visible.items() if isinstance(value, (int, float, bool))}
        actions, scores, thresholds = decide_visible(self.point, arrays)
        action = str(ACTION_NAMES[int(actions[0])])
        return governance_decision(
            self.point.mechanism,
            obs,
            candidate,
            action,
            float(scores[0]),
            float(scores[0]),
            float(thresholds[0]),
            "Frozen Phase 4 benchmark adaptation over participant-visible evidence.",
            [] if action == "accept" else [f"phase4_{self.point.mechanism}_{action}"],
            {"point_id": self.point.point_id, "config_hash": self.point.config_hash, "information_budget": "visible_only"},
        )

    def update(self, obs: Observation, candidate: CandidateAction, decision: GovernanceDecision, result: StepResult) -> None:
        return None


def decide_visible(
    point: OperatingPoint,
    features: Mapping[str, np.ndarray],
    *,
    adaptive_adjustment: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate a point using visible arrays only; evaluator labels are not accepted."""

    risk = _feature(features, "risk_proxy")
    n = len(risk)
    adjustment = np.zeros(n, dtype=np.float64) if adaptive_adjustment is None else adaptive_adjustment
    mechanism = point.mechanism
    if mechanism == "accept_all":
        return np.full(n, ACTION_ACCEPT), risk, np.ones(n)
    if mechanism == "reject_all":
        return np.full(n, ACTION_REJECT), risk, np.zeros(n)
    if mechanism == "escalate_all":
        return np.full(n, ACTION_ESCALATE), risk, np.full(n, 0.5)
    if mechanism == "random":
        keys = _feature(features, "random_key")
        return np.floor(keys * 3.0).astype(np.int8).clip(0, 2), risk, np.full(n, 0.5)
    if point.oracle:
        raise ValueError("Oracle operating points must be evaluated in the evaluator-owned path.")

    score = risk.copy()
    uncertain = np.zeros(n, dtype=bool)
    if point.family == "mavs_lineage":
        if mechanism == "mavs_gc":
            score = 0.70 * risk + 0.30 * _feature(features, "policy_conflict")
        elif mechanism == "ds_cf":
            score = 0.55 * risk + 0.25 * _feature(features, "danger_witness") + 0.20 * (1.0 - _feature(features, "provenance_quality"))
            uncertain = _feature(features, "evidence_available") < 0.5
        elif mechanism == "fixed_full_mavs":
            score = 0.45 * risk + 0.30 * _feature(features, "certified_signal") + 0.15 * _feature(features, "policy_conflict") + 0.10 * _feature(features, "shift_score")
        else:
            score = 0.50 * risk + 0.30 * _feature(features, "context_risk") + 0.20 * _feature(features, "certified_signal")
    elif point.family == "selective":
        uncertainty = {
            "confidence": 1.0 - _feature(features, "confidence"),
            "entropy": _feature(features, "entropy"),
            "margin": 1.0 - _feature(features, "margin"),
            "reject_option": _feature(features, "uncertainty"),
            "generalized_selective": np.maximum(_feature(features, "uncertainty"), _feature(features, "shift_score")),
        }[mechanism]
        uncertain = uncertainty >= 0.55
    elif point.family == "neyman_pearson":
        score = risk if mechanism == "risk_constrained" else np.clip(risk / np.maximum(0.05, 1.0 - risk), 0.0, 4.0) / 4.0
        if mechanism == "cost_sensitive":
            score = np.clip(score * (0.75 + _feature(features, "cost_preference")), 0.0, 1.0)
    elif point.family == "conformal":
        alpha = float(point.parameters.get("alpha", 0.05))
        score = np.clip(_feature(features, "calibrated_risk") + adjustment, 0.0, 1.0)
        uncertain = _feature(features, "conformal_pvalue") > alpha
    elif point.family == "uncertainty":
        uncertainty = {
            "disagreement": _feature(features, "disagreement"),
            "variance": _feature(features, "variance"),
            "mutual_information": _feature(features, "mutual_information"),
            "deep_ensemble": np.maximum(_feature(features, "variance"), _feature(features, "disagreement")),
            "self_consistency": 1.0 - _feature(features, "self_consistency"),
        }[mechanism]
        uncertain = uncertainty >= float(point.parameters.get("uncertainty_threshold", 0.4))
    elif point.family == "guardrails":
        source = "tool_guard_risk" if mechanism == "tool_use_guard" else ("schema_guard_risk" if mechanism == "schema_guard" else "rail_risk")
        score = np.maximum(risk, _feature(features, source))
        uncertain = _feature(features, "evidence_available") < 0.5
    elif point.family == "critique_verifier":
        source = {"critique_revise": "critique_risk", "single_judge": "judge_risk", "verifier_cascade": "verifier_risk", "bounded_debate": "debate_risk"}[mechanism]
        score = 0.35 * risk + 0.65 * _feature(features, source)
        uncertain = _feature(features, "review_conflict") >= 0.6
    elif point.family == "drift":
        score = np.clip(risk + adjustment + 0.15 * _feature(features, "shift_score"), 0.0, 1.0)
        uncertain = _feature(features, "shift_score") >= float(point.parameters.get("drift_threshold", 0.25))
    elif point.family == "online_experts":
        score = np.clip(0.45 * risk + 0.30 * _feature(features, "expert_risk") + 0.25 * _feature(features, "context_risk") + adjustment, 0.0, 1.0)
    elif point.family == "test_time_adaptation":
        score = np.clip(_feature(features, "source_model_risk") + adjustment, 0.0, 1.0)
        uncertain = (_feature(features, "confidence") < 0.55) if "pseudo" in mechanism else (_feature(features, "entropy") > 0.65)
    elif point.family == "pareto":
        weight = float(point.parameters.get("safety_weight", 0.75))
        score = np.clip(weight * _feature(features, "certified_signal") + (1.0 - weight) * risk, 0.0, 1.0)
        uncertain = _feature(features, "evidence_available") < 0.5
    elif point.family == "safe_control":
        budget = float(point.parameters.get("safety_budget", 0.05))
        score = np.maximum(risk, _feature(features, "safety_critic_risk"))
        uncertain = score >= 1.0 - 2.0 * budget
    elif point.family == "mavs_sl":
        inherited = {"cumulative": 1.0, "fresh": 0.72, "frozen_after_g1": 0.86}[point.condition]
        score = np.clip(
            inherited * (0.72 * _feature(features, "certified_signal") + 0.12 * _feature(features, "danger_witness") + 0.08 * _feature(features, "policy_conflict") + 0.08 * (1.0 - _feature(features, "provenance_quality")))
            + (1.0 - inherited) * risk,
            0.0,
            1.0,
        )
        uncertain = (_feature(features, "evidence_available") < 0.5) | (_feature(features, "scope_validity") < 0.65)
    else:
        raise KeyError(f"Unsupported Phase 4 family: {point.family}")

    threshold = _threshold(point, n)
    accept_threshold = np.clip(threshold - 0.24, 0.05, 0.80)
    actions = np.full(n, ACTION_ESCALATE, dtype=np.int8)
    actions[(score < accept_threshold) & ~uncertain] = ACTION_ACCEPT
    actions[(score >= threshold) & ~uncertain] = ACTION_REJECT
    return actions, score, threshold


def causal_adaptation(
    risk: np.ndarray,
    unsafe: np.ndarray,
    feedback_released: np.ndarray,
    *,
    initial_bias: float,
    rate: float,
) -> tuple[np.ndarray, float]:
    """Create a pre-decision adjustment using only earlier released outcomes."""

    adjustment = np.empty(len(risk), dtype=np.float64)
    bias = float(initial_bias)
    for index in range(len(risk)):
        adjustment[index] = bias
        if bool(feedback_released[index]):
            residual = float(unsafe[index]) - float(risk[index])
            bias = float(np.clip((1.0 - rate) * bias + rate * residual, -0.20, 0.20))
    return adjustment, bias


def _threshold(point: OperatingPoint, n: int) -> np.ndarray:
    if "reject_threshold" in point.parameters:
        value = point.parameters["reject_threshold"]
    elif "alpha" in point.parameters:
        value = 0.68 - 0.6 * point.parameters["alpha"]
    elif "safety_weight" in point.parameters:
        value = 0.78 - 0.18 * point.parameters["safety_weight"]
    elif "safety_budget" in point.parameters:
        value = 0.62 + point.parameters["safety_budget"]
    else:
        value = 0.68
    return np.full(n, float(value), dtype=np.float64)


def _feature(features: Mapping[str, np.ndarray], name: str) -> np.ndarray:
    if name not in features:
        first = next(iter(features.values()))
        return np.zeros(len(first), dtype=np.float64)
    return np.asarray(features[name], dtype=np.float64)

