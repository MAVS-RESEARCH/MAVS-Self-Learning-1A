from __future__ import annotations

import pytest

from mavs10d.baselines.phase1_registry import ADAPTIVE_METHODS, FIXED_METHODS, build_phase1_method, expected_method_conditions
from mavs10d.core.types import CandidateAction, Observation, StepResult


DEFAULT = {"reject_threshold": 0.60, "escalate_threshold": 0.45, "calibration_scores": [0.2, 0.3, 0.4, 0.5], "calibration_size": 4}


def _inputs():
    observation = Observation("world", 4, {"entropy": 0.7, "margin": 0.2, "evidence_quality": 0.8, "specialist_disagreement": 0.1}, None, {"domain": "text_safety", "cost_preference": "balanced", "schedule_family": "burst"}, None)
    candidate = CandidateAction("candidate", "visible", 0.7, {"s": {"score": 0.4}}, {"risk_proxy": 0.6, "model_risk": 0.55})
    return observation, candidate


@pytest.mark.parametrize("method_name", FIXED_METHODS + ADAPTIVE_METHODS)
def test_every_phase1_baseline_satisfies_common_governance_method(method_name: str) -> None:
    method = build_phase1_method(method_name, "cumulative" if method_name in ADAPTIVE_METHODS else "fixed", DEFAULT)
    observation, candidate = _inputs()
    method.reset(1)
    decision = method.decide(observation, candidate)
    assert decision.decision in {"accept", "reject", "escalate"}
    assert 0.0 <= decision.risk_score <= 1.0
    assert decision.trace["diagnostic_values"]["baseline_details"]["approved_configuration"] is True
    assert "unsafe" not in candidate.provenance
    result = StepResult(observation, 0.0, False, False, False, {"released_feedback": []})
    method.update(observation, candidate, decision, result)


def test_future_feedback_fails_closed() -> None:
    method = build_phase1_method("online_conformal", "fresh", DEFAULT)
    observation, candidate = _inputs()
    decision = method.decide(observation, candidate)
    result = StepResult(observation, 0.0, False, False, False, {"released_feedback": [{"release_step": 5, "risk_score": 0.4, "observed_label": True}]})
    with pytest.raises(RuntimeError, match="before its release"):
        method.update(observation, candidate, decision, result)


def test_cumulative_and_fresh_matrix_is_complete_in_later_generations() -> None:
    for generation in (2, 3):
        matrix = set(expected_method_conditions(generation))
        for method in ADAPTIVE_METHODS:
            assert {(method, "cumulative"), (method, "fresh")} <= matrix
        assert all((method, "fixed") in matrix for method in FIXED_METHODS)


def test_adaptive_state_load_rejects_cross_mechanism_state() -> None:
    source = build_phase1_method("online_experts", "cumulative", DEFAULT)
    target = build_phase1_method("adwin", "cumulative", DEFAULT)
    with pytest.raises(ValueError, match="type mismatch"):
        target.load_state_dict(source.state_dict())
