from __future__ import annotations

import json
from pathlib import Path

import pytest

from mavs10d.core.config import MethodConfig
from mavs10d.core.types import CandidateAction, Observation
from mavs10d.governance.ds_cf import DSCFGovernance
from mavs10d.governance.phase2_diagnostics import compute_phase2_diagnostics, drop_one_fragility


ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "tests/fixtures/phase2_ds_cf_regressions.json").read_text(encoding="utf-8"))


def _inputs(case):
    visible = {
        "evidence_status": case["evidence_status"],
        "ambiguity_score": case["ambiguity"],
        "masking_score": 0.9 if case["evidence_status"] == "masked" else 0.0,
        "provenance_concentration": 0.95 if len(set(case["sources"])) == 1 else 0.15,
        "policy_conflict": case["policy_conflict"],
        "confidence_inflation": 0.0,
        "source_compromise_signal": case["source_compromise"],
        "danger_witness_strength": case["danger_strength"],
        "safe_witness_strength": case["safe_strength"],
        "feedback_reliability": 1.0,
        "counterfactual_fragility": 0.0,
    }
    outputs = {f"s{i}": {"score": score, "declared_source": case["sources"][i]} for i, score in enumerate(case["scores"])}
    return Observation(case["name"], 0, visible, "fixture", {"corruption_level": 0.0}, None), CandidateAction("candidate", "fixture", 0.8, outputs, {"risk_proxy": case["risk"]})


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_ds_cf_regression_truth_table(case) -> None:
    obs, candidate = _inputs(case)
    decision = DSCFGovernance(MethodConfig("ds_cf", "ds_cf", {})).decide(obs, candidate)
    state = decision.trace["diagnostic_values"]["baseline_details"]["ds_cf"]
    assert decision.decision == case["expected"]
    assert state["hard_veto"] is case["hard_veto"]


def test_raw_correlation_never_creates_hard_veto() -> None:
    case = CASES[0]
    obs, candidate = _inputs(case)
    decision = DSCFGovernance(MethodConfig("ds_cf", "ds_cf", {})).decide(obs, candidate)
    state = decision.trace["diagnostic_values"]["baseline_details"]["ds_cf"]
    assert state["raw_correlation_only"] is True
    assert state["hard_veto"] is False
    assert decision.decision != "reject"


def test_evidence_absence_and_unavailability_have_different_actions() -> None:
    absent = next(case for case in CASES if case["name"].startswith("evidence_absent"))
    unavailable = next(case for case in CASES if case["name"].startswith("expected_evidence"))
    method = DSCFGovernance(MethodConfig("ds_cf", "ds_cf", {}))
    assert method.decide(*_inputs(absent)).decision == "accept"
    assert method.decide(*_inputs(unavailable)).decision == "escalate"


def test_mitigation_is_bounded_at_every_boundary() -> None:
    for case in CASES:
        decision = DSCFGovernance(MethodConfig("ds_cf", "ds_cf", {"mitigation_max": 0.12})).decide(*_inputs(case))
        state = decision.trace["diagnostic_values"]["baseline_details"]["ds_cf"]
        assert 0.0 <= state["mitigation"] <= 0.12


def test_diagnostics_are_invariant_to_evidence_order() -> None:
    obs, candidate = _inputs(CASES[3])
    reversed_candidate = CandidateAction(candidate.action_type, candidate.content, candidate.confidence, dict(reversed(tuple(candidate.specialist_outputs.items()))), candidate.provenance)
    assert compute_phase2_diagnostics(obs, candidate) == compute_phase2_diagnostics(obs, reversed_candidate)


def test_drop_one_counterfactual_is_bounded_and_detects_source_fragility() -> None:
    obs, candidate = _inputs(CASES[3])
    value = drop_one_fragility(obs, candidate)
    assert 0.0 <= value <= 1.0
    assert value > 0.0


def test_danger_witness_boundary_controls_hard_veto() -> None:
    case = dict(next(item for item in CASES if item["name"] == "harmful_correlated_collapse"))
    method = DSCFGovernance(MethodConfig("ds_cf", "ds_cf", {}))
    case["danger_strength"] = 0.61
    assert method.decide(*_inputs(case)).decision != "reject"
    case["danger_strength"] = 0.62
    assert method.decide(*_inputs(case)).decision == "reject"
