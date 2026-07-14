from __future__ import annotations

import pytest

from mavs10d.memory.negative_knowledge import NegativeKnowledge
from mavs10d.resolution.perception_search import rank_actions
from mavs10d.resolution.query_planner import BudgetLedger, execute_action


def test_search_rejects_scope_provenance_redundancy_and_negative_knowledge(case_factory) -> None:
    case, _ = case_factory("scope_neighbor", 0)
    valid = dict(case["actions"][1])
    duplicate = dict(valid, action_id="duplicate", semantic_id=valid["semantic_id"])
    poisoned = dict(valid, action_id="poisoned", semantic_id="poison", behavioral_id="poison", provenance_valid=False)
    blocked = dict(valid, action_id="blocked", semantic_id="blocked", behavioral_id="blocked")
    negative = NegativeKnowledge(low_yield_queries={"blocked"})
    result = rank_actions([case["actions"][0], valid, duplicate, poisoned, blocked], case["visible_evidence"], negative)
    reasons = {item.action_id: item.reason for item in result.findings}
    assert result.selected["action_id"] == valid["action_id"]
    assert reasons[case["actions"][0]["action_id"]] == "executable_anti_scope"
    assert reasons["duplicate"] == "semantic_duplicate"
    assert reasons["poisoned"] == "invalid_provenance"
    assert reasons["blocked"] == "negative_knowledge_low_yield"


def test_runtime_created_candidate_requires_phase6_integrity(case_factory) -> None:
    case, _ = case_factory("one_query_separable", 0)
    candidate = dict(case["actions"][0], runtime_created=True, phase6_integrity_passed=False)
    result = rank_actions([candidate], case["visible_evidence"], NegativeKnowledge())
    assert result.selected is None
    assert result.findings[0].reason == "phase6_integrity_not_passed"


def test_small_protected_regression_cannot_trade_for_larger_contraction(case_factory) -> None:
    case, _ = case_factory("one_query_separable", 0)
    safe = dict(case["actions"][0])
    regressing = dict(safe, action_id="regressing", semantic_id="regressing", behavioral_id="regressing", protected_regression=0.000001, expected_contraction=1.0)
    result = rank_actions([regressing, safe], case["visible_evidence"], NegativeKnowledge())
    assert result.selected["action_id"] == safe["action_id"]
    assert {item.action_id: item.reason for item in result.findings}["regressing"] == "protected_regression"


def test_budget_is_exact_and_fail_closed(case_factory) -> None:
    case, _ = case_factory("budget_limited_case", 0)
    ledger = BudgetLedger(max_cost=2.0, max_latency_ms=1000.0, max_calls=1, max_privacy_units=1.0)
    assert not ledger.permits(case["actions"][0])
    with pytest.raises(RuntimeError, match="bounded budget"):
        execute_action(case["actions"][0], case["visible_evidence"], ledger)
    assert ledger.spent_calls == 0
