from __future__ import annotations

import pytest

from mavs10d.certification.blind_api import assert_blind_payload, make_blind_request
from mavs10d.core.hashing import stable_hash
from mavs10d.integrity.hidden_field_audit import audit_payloads
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


def test_control_allocation_is_nonvacuous() -> None:
    candidates = synthesize_candidates(build_bank(620001, 8), 610001, 620001)
    counts = {name: sum(item.expected_lifecycle == name for item in candidates) for name in ("promoted", "integrity_rejected", "certification_rejected")}
    assert counts == {"promoted": 20, "integrity_rejected": 10, "certification_rejected": 10}

