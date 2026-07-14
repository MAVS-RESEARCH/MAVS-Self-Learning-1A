from __future__ import annotations

import copy
from pathlib import Path

import pytest

from mavs10d.certification.local import issue_local_certificate
from mavs10d.certification.persistent import certify_persistent_handoff
from mavs10d.core.runtime import assert_runtime_blindness
from mavs10d.learning.consolidation import consolidate_knowledge, select_consolidation_operation


def test_local_certificate_has_every_obligation(runtime, case_factory) -> None:
    case, _ = case_factory("one_query_separable", 0)
    result = runtime.resolve(case, 20)
    assert set(result.certificate["obligations"]) == {
        "hypothesis_separation", "witness_sufficiency", "executable_scope", "evidence_integrity",
        "counterfactual_stability", "interaction_safety", "authority", "risk_justification",
        "kernel_preservation", "replay",
    }
    assert result.certificate["all_passed"]


def test_provisional_hypotheses_cannot_supply_terminal_authority(runtime, case_factory) -> None:
    case, _ = case_factory("genuinely_new_semantic_need", 0)
    assert {item["authority"] for item in case["hypotheses"]} == {"L0"}
    result = runtime.resolve(case, 20)
    assert result.queries_and_probes[0]["action_type"] == "PROBE"
    assert result.certificate["authority"] == "L2"


def test_kernel_mutation_prevents_local_terminal_authority(case_factory) -> None:
    from mavs10d.resolution.hypotheses import build_hypotheses, surviving_hypotheses

    case, _ = case_factory("one_query_separable", 0)
    evidence = dict(case["visible_evidence"])
    evidence.update(case["actions"][0]["evidence_response"])
    survivors = surviving_hypotheses(build_hypotheses(case["hypotheses"]), evidence)
    certificate = issue_local_certificate(
        case["case_id"], "ACCEPT", survivors, evidence, [], ["terminal_witness"], "L2",
        {"hard_veto": False, "mitigation": True, "monotonicity": True, "traceability": True, "rollback": True},
        "0" * 64,
    )
    assert not certificate["obligations"]["kernel_preservation"]
    assert not certificate["all_passed"]


@pytest.mark.parametrize("field", ["expected_outcome", "oracle_label", "unsafe", "hidden_world", "target_decision"])
def test_runtime_hidden_field_taint_is_rejected(case_factory, field: str) -> None:
    case, _ = case_factory("one_query_separable", 0)
    tainted = copy.deepcopy(case)
    tainted[field] = "sentinel"
    with pytest.raises(ValueError, match="Forbidden runtime field"):
        assert_runtime_blindness(tainted)


def test_persistent_handoff_is_blind_and_behavior_gated() -> None:
    blind = {"anonymous_semantic_id": "semantic", "expression_ast": {}, "parameters": {}}
    gates = {"anonymous_semantic_id": "semantic", "gates": {"gate": {"passed": True}}}
    passed = certify_persistent_handoff(blind, gates, {"replay_count": 2, "protected_regression": 0.0, "scope_leakage": 0.0})
    assert passed["passed"]
    failed = certify_persistent_handoff(blind, gates, {"replay_count": 1, "protected_regression": 0.0, "scope_leakage": 0.0})
    assert not failed["passed"]
    with pytest.raises(ValueError, match="forbidden outcome"):
        certify_persistent_handoff(blind, gates, {"replay_count": 2, "protected_regression": 0.0, "scope_leakage": 0.0, "oracle_label": 1})


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        ({"conditional_redundancy": 0.96}, "merge"),
        ({"neighbor_leakage": True}, "narrow"),
        ({"mechanism_conflation": True}, "split"),
        ({"dominated": True}, "retire"),
        ({"scope_leakage": 0.1}, "quarantine"),
        ({"unsafe_interaction": True}, "prohibit"),
    ],
)
def test_all_consolidation_operations(evidence: dict[str, object], expected: str) -> None:
    assert select_consolidation_operation(evidence) == expected


def test_active_eligibility_requires_blind_certification() -> None:
    record = consolidate_knowledge(
        "knowledge", ["case-a", "case-b"],
        {"conditional_perception_gain": 1.0, "outperforms_parent": True, "positive_scope": ["s"], "anti_scope": ["a"]},
        {"passed": False, "anonymous_semantic_id": "x", "gate_count": 15}, 0, 4,
    )
    assert not record["active_eligible"]


def test_runtime_process_does_not_import_auditor_truth() -> None:
    source = (Path(__file__).resolve().parents[2] / "scripts" / "run_phase7_runtime.py").read_text(encoding="utf-8")
    assert "auditor_truth" not in source
    assert "truth_unsafe" not in source
    assert "expected_terminal" not in source
