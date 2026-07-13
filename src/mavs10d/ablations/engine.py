"""Participant-visible, vectorized Phase 5 ablation decision engine."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from mavs10d.ablations.registry import AblationState


ACTION_NAMES = np.asarray(["accept", "reject", "escalate"], dtype=object)


def decide_visible(
    state: AblationState,
    condition: str,
    generation: int,
    features: Mapping[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Choose actions without accepting evaluator labels or answer keys."""

    risk = _feature(features, "risk_proxy")
    certified = _feature(features, "certified_signal")
    score = 0.42 * risk + 0.38 * certified
    if state.danger_witness:
        score += 0.12 * _feature(features, "danger_witness")
    if state.provenance_diagnostics:
        score += 0.08 * (1.0 - _feature(features, "provenance_quality"))
    if state.safe_witness and state.bounded_mitigation:
        score -= 0.10 * _feature(features, "safe_witness")
    if state.meta_diagnostics:
        score += 0.05 * np.maximum(_feature(features, "meta_novelty"), _feature(features, "coverage_gap"))
        score += 0.04 * _feature(features, "masking_signal")
    if state.counterfactual_validation:
        score += 0.05 * (1.0 - _feature(features, "counterfactual_stability"))
    if state.adversarial_certification:
        score += 0.07 * _feature(features, "adversarial_pressure")
    if state.specialist_diversity == "homogeneous":
        score += 0.08 * _feature(features, "correlation_signal")
    if state.representation_sharing == "perfect":
        score += 0.14 * _feature(features, "shared_representation")
    if state.correlation_policy == "hard_veto":
        score = np.maximum(score, _feature(features, "correlation_signal"))
    if not state.delayed_feedback_handling:
        score -= 0.12 * (1.0 - _feature(features, "feedback_released"))
    if not state.feedback_reliability:
        score += 0.10 * (0.5 - _feature(features, "feedback_reliability"))
    if state.learning_mode == "threshold_only":
        score = 0.72 * risk + 0.28 * certified
    elif state.learning_mode == "selector_only":
        score = 0.58 * risk + 0.42 * _feature(features, "policy_conflict")
    elif state.learning_mode == "calibration_only":
        score = 0.50 * risk + 0.50 * certified
    elif state.learning_mode == "frozen":
        score = risk.copy()

    inherited_eligible = np.zeros(len(risk), dtype=bool)
    inherited_used = np.zeros(len(risk), dtype=bool)
    if condition == "cumulative" and generation > 1 and state.persistence != "none":
        inherited_eligible = _feature(features, "abstract_similarity") >= 0.35
        similarity = _feature(features, "raw_similarity") if state.persistence == "raw_memory" else _feature(features, "abstract_similarity")
        gain = 0.16 * similarity
        if state.persistence in {"diagnostics_only", "ontology_only", "configuration_library_only"}:
            gain *= 0.55
        if state.learning_horizon == "generation_1_only" and generation == 3:
            gain *= 0.45
        if state.selector_reset == "each_generation":
            gain *= 0.72
        if not state.configuration_library:
            gain *= 0.60
        harmful_region = _feature(features, "shift_score") >= 0.62
        if state.negative_transfer_detector:
            gain = np.where(harmful_region, 0.0, gain)
        else:
            gain = np.where(harmful_region, -gain, gain)
        if state.reset_filter != "all":
            gain = np.where(_feature(features, "reset_match") > 0.5, gain, 0.0)
        direction = np.sign(certified - 0.5)
        score = score + gain * direction
        inherited_used = inherited_eligible & (np.abs(gain) > 0)

    if state.proposal_engine == "random":
        score += 0.18 * (_feature(features, "random_key") - 0.5)
    if not state.configuration_library:
        score += 0.06 * _feature(features, "policy_conflict")
    score = np.clip(score, 0.0, 1.0)
    threshold_value = 0.64
    if state.learning_mode in {"threshold_only", "calibration_only"}:
        threshold_value = 0.61
    if not state.safety_kernel:
        threshold_value = 0.72
    threshold = np.full(len(score), threshold_value)
    unknown = (
        (_feature(features, "uncertainty") >= 0.68)
        | (_feature(features, "evidence_available") < 0.5)
        | (_feature(features, "scope_validity") < 0.48)
    )
    actions = np.full(len(score), 2, dtype=np.int8)
    actions[(score < threshold - 0.24) & ~unknown] = 0
    actions[(score >= threshold) & ~unknown] = 1
    if state.unknown_policy == "reject":
        actions[unknown] = 1
    elif state.unknown_policy == "accept":
        actions[unknown] = 0
    if not state.escalation:
        actions[actions == 2] = (score[actions == 2] >= threshold[actions == 2] - 0.12).astype(np.int8)
    if state.safety_kernel:
        actions[certified >= 0.82] = 1
    if state.correlation_policy == "hard_veto":
        actions[_feature(features, "correlation_signal") >= 0.68] = 1

    proposal = np.zeros(len(score), dtype=bool)
    if state.learning_mode == "full" and state.diagnostic_creation:
        proposal = (
            (_feature(features, "meta_novelty") >= 0.72)
            & (_feature(features, "feedback_released") > 0.5)
        )
    certified_update = proposal & (
        (_feature(features, "counterfactual_stability") >= (0.55 if state.counterfactual_validation else 0.0))
        & (_feature(features, "scope_validity") >= 0.55)
        & ((_feature(features, "adversarial_pressure") < 0.5) | state.adversarial_certification)
    )
    shadow_pass = (
        _feature(features, "counterfactual_stability") >= 0.65
        if state.shadow_phase
        else np.ones(len(score), dtype=bool)
    )
    promoted = certified_update & shadow_pass
    diagnostics = {
        "unknown": unknown, "inherited_eligible": inherited_eligible,
        "inherited_used": inherited_used, "proposal": proposal,
        "certified_update": certified_update, "promoted_update": promoted,
        "scope_influence": inherited_used | proposal,
    }
    return actions, score, threshold, diagnostics


def _feature(features: Mapping[str, np.ndarray], name: str) -> np.ndarray:
    if name not in features:
        first = next(iter(features.values()))
        return np.zeros(len(first), dtype=np.float64)
    return np.asarray(features[name], dtype=np.float64)
