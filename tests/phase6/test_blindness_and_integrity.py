from __future__ import annotations

import pytest
from dataclasses import replace
import json
from pathlib import Path

from mavs10d.certification.blind_api import assert_blind_payload, make_blind_request
from mavs10d.core.hashing import stable_hash
from mavs10d.diagnostics.behavioral_fingerprint import fingerprint_frame
from mavs10d.integrity.hidden_field_audit import audit_payloads
from mavs10d.integrity.template_collapse import classify_pathology
from mavs10d.learning.synthesis import build_bank, synthesize_candidates


def test_blind_request_is_allowlisted_and_has_no_quality_labels() -> None:
    bank = build_bank(620001, 8)
    candidate = synthesize_candidates(bank, 610001, 620001)[0].candidate
    request = make_blind_request(candidate, {"trigger": stable_hash("bank")}, stable_hash("incumbent"))
    assert_blind_payload(request)
    serialized = str(request)
    assert candidate.candidate_id not in serialized
    assert candidate.name not in serialized
    assert candidate.lineage["operation"] not in serialized


def test_hidden_field_and_evaluator_sentinel_fail_closed() -> None:
    with pytest.raises(ValueError): assert_blind_payload({"hidden_world": "value"})
    with pytest.raises(ValueError): assert_blind_payload({"feature": "PHASE6_EVALUATOR_ONLY_SENTINEL_7F3B2D"})
    report = audit_payloads({"bad": {"oracle_label": 1}}, "PHASE6_EVALUATOR_ONLY_SENTINEL_7F3B2D")
    assert not report["passed"]
    fixture = json.loads((Path(__file__).parent / "fixtures" / "hidden_taint.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        assert_blind_payload(fixture)


def test_control_allocation_is_nonvacuous() -> None:
    candidates = synthesize_candidates(build_bank(620001, 8), 610001, 620001)
    counts = {name: sum(item.expected_lifecycle == name for item in candidates) for name in ("promoted", "integrity_rejected", "certification_rejected")}
    assert counts == {"promoted": 20, "integrity_rejected": 10, "certification_rejected": 10}


def test_all_adversarial_rejection_classes_receive_independent_reason_codes() -> None:
    bank = build_bank(630001, 16)
    base = synthesize_candidates(build_bank(620001, 16), 610001, 620001)[0].candidate
    base_frame = fingerprint_frame(base, bank)
    constant = replace(base, candidate_id="P6-FIXTURE-CONSTANT", expression_ast={"op": "constant", "value": 1.0})
    assert classify_pathology(constant, fingerprint_frame(constant, bank)) == "constant_output"
    no_op = replace(base, candidate_id="P6-FIXTURE-NOOP", positive_scope_ast={"op": "constant", "value": False})
    assert classify_pathology(no_op, fingerprint_frame(no_op, bank)) == "behaviorally_null_no_op"
    renamed_parent = replace(base, candidate_id="P6-FIXTURE-PARENT", name="renamed-parent-copy")
    assert classify_pathology(renamed_parent, fingerprint_frame(renamed_parent, bank), parent=base, parent_fingerprint=base_frame) == "parent_identical"
    renamed_sibling = replace(base, candidate_id="P6-FIXTURE-SIBLING", name="renamed-sibling-copy")
    assert classify_pathology(renamed_sibling, fingerprint_frame(renamed_sibling, bank), sibling=base, sibling_fingerprint=base_frame) == "sibling_identical"
    equivalent = replace(base, candidate_id="P6-FIXTURE-EQUIVALENT", expression_ast={"op": "and", "children": [base.expression_ast, {"op": "constant", "value": True}]})
    equivalent_frame = fingerprint_frame(equivalent, bank)
    assert classify_pathology(equivalent, equivalent_frame, parent=base, parent_fingerprint=base_frame) == "behavioral_equivalent_without_predeclared_gain"
    assert classify_pathology(equivalent, equivalent_frame, parent=base, parent_fingerprint=base_frame, certified_improvement={"dimension": "cost", "before": 2.0, "after": 1.0}) == "behavioral_equivalent_with_certified_improvement"
    overfit_frame = base_frame.copy()
    truth = bank[["case_id", "unsafe"]]
    truth_by_case = truth.set_index("case_id")["unsafe"]
    for index, row in overfit_frame.iterrows():
        unsafe = bool(truth_by_case[row["case_id"]])
        predicted = unsafe if row["bank"] == "trigger" else (not unsafe if row["bank"] in {"holdout", "disjoint_analogue"} else unsafe)
        overfit_frame.at[index, "discrete_output"] = int(predicted)
        overfit_frame.at[index, "raw_output"] = float(predicted)
        overfit_frame.at[index, "active"] = True
        overfit_frame.at[index, "terminal_influence"] = float(predicted)
    assert classify_pathology(base, overfit_frame, truth=truth) == "trigger_only_overfit"
