from __future__ import annotations

from mavs10d.certification.gates import certification_trace, evaluate_gates, perception_extension_witness
from mavs10d.learning.synthesis import build_bank, synthesize_candidates


def test_behavior_only_certification_separates_valid_and_scope_leak_controls() -> None:
    development = build_bank(620001, 32)
    certification = build_bank(630001, 32)
    candidates = synthesize_candidates(development, 610001, 620001)
    valid = next(item.candidate for item in candidates if item.expected_lifecycle == "promoted")
    control = next(item.candidate for item in candidates if item.expected_lifecycle == "certification_rejected")
    valid_trace = certification_trace(valid, certification)
    valid_witness = perception_extension_witness(valid, valid_trace)
    assert evaluate_gates(valid, valid_trace, valid_witness, 630001)["all_passed"]
    control_trace = certification_trace(control, certification)
    control_witness = perception_extension_witness(control, control_trace)
    vector = evaluate_gates(control, control_trace, control_witness, 630001)
    assert not vector["all_passed"]
    assert not vector["gates"]["anti_scope"]["passed"]
