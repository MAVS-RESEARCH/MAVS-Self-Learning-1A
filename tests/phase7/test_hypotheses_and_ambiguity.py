from __future__ import annotations

import pytest

from mavs10d.resolution.ambiguity import ambiguity_contraction, make_ambiguity_state
from mavs10d.resolution.hypotheses import build_hypotheses, surviving_hypotheses


def test_finite_hypotheses_require_safe_and_unsafe(case_factory) -> None:
    case, _ = case_factory("one_query_separable", 0)
    built = build_hypotheses(case["hypotheses"])
    assert {item.decision_class for item in built} == {"safe", "unsafe"}
    with pytest.raises(ValueError, match="safe- and unsafe-compatible"):
        build_hypotheses(case["hypotheses"][:1])


def test_evidence_update_contracts_ambiguity(case_factory) -> None:
    case, _ = case_factory("one_query_separable", 0)
    built = build_hypotheses(case["hypotheses"])
    before_survivors = surviving_hypotheses(built, case["visible_evidence"])
    before = make_ambiguity_state(case["case_id"], 0, case["ambiguity_type"], case["visible_evidence"], before_survivors, "0" * 64)
    evidence = dict(case["visible_evidence"])
    evidence.update(case["actions"][0]["evidence_response"])
    after_survivors = surviving_hypotheses(built, evidence)
    after = make_ambiguity_state(case["case_id"], 1, case["ambiguity_type"], evidence, after_survivors, before.state_hash)
    assert not before.decision_homogeneous
    assert after.decision_homogeneous
    assert after.terminal_action == "ACCEPT"
    assert ambiguity_contraction(before, after) == 0.5
    assert after.parent_hash == before.state_hash


def test_hypothesis_update_cannot_eliminate_every_registered_explanation(case_factory) -> None:
    case, _ = case_factory("one_query_separable", 0)
    built = build_hypotheses(case["hypotheses"])
    impossible = {"terminal_witness": {"available": True, "value": "unregistered"}}
    with pytest.raises(RuntimeError, match="every registered"):
        surviving_hypotheses(built, impossible)
