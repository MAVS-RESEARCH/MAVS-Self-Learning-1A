from __future__ import annotations

import copy
import random

import pytest


FAMILIES = (
    "immediately_separable", "one_query_separable", "multi_step_separable",
    "masked_safe_evidence", "harmful_vs_benign_correlation", "scope_neighbor",
    "conflicting_diagnostics", "new_composition", "genuinely_new_semantic_need",
    "irreducible_pair", "adversarial_query_trap", "budget_limited_case",
)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("index", [0, 1])
def test_locked_family_behavior(runtime, case_factory, family: str, index: int) -> None:
    case, truth = case_factory(family, index)
    result = runtime.resolve(case, 20000)
    assert result.trace["terminal_action"] == truth["expected_terminal"]
    assert result.trace["round_count"] == truth["expected_rounds"] if family not in {"budget_limited_case"} else result.trace["round_count"] == 0
    if family == "immediately_separable":
        assert not result.trace["resolver_entered"]
    if family == "multi_step_separable":
        assert all("IRRELEVANT" not in item["selected_action_id"] for item in result.rounds)
    if family == "scope_neighbor":
        assert all("LEAK" not in item["selected_action_id"] for item in result.rounds)
    if family == "conflicting_diagnostics":
        assert result.queries_and_probes[0]["action_type"] == "PROBE"
        assert all(not item["additive_severity_used"] for item in result.rounds)
    if family == "new_composition":
        assert len(result.programs[0]["influential_basis"]) == 2
        assert result.programs[0]["interaction_certificates"]
    if family == "genuinely_new_semantic_need":
        assert [item["action_type"] for item in result.queries_and_probes] == ["PROBE", "QUERY"]
    if family == "irreducible_pair":
        assert result.escalation["reason"] == "irreducible_ambiguity"
    if family == "adversarial_query_trap":
        assert "POISON" not in result.queries_and_probes[0]["action_id"]
    if family == "budget_limited_case":
        assert result.escalation["reason"] == "budget_exhaustion"
        assert result.escalation["untried_actions"]


def test_query_probe_round_and_external_escalation_are_distinct(runtime, case_factory) -> None:
    query_case, _ = case_factory("one_query_separable", 0)
    query_result = runtime.resolve(query_case, 20)
    assert query_result.trace["query_count"] == 1
    assert query_result.trace["round_count"] == 1
    assert query_result.trace["external_escalation_count"] == 0
    irreducible, _ = case_factory("irreducible_pair", 0)
    escalation_result = runtime.resolve(irreducible, 20)
    assert escalation_result.trace["query_count"] == 0
    assert escalation_result.trace["round_count"] == 0
    assert escalation_result.trace["external_escalation_count"] == 1


def test_active_basis_does_not_scale_with_library(runtime, case_factory) -> None:
    case, _ = case_factory("new_composition", 0)
    results = [runtime.resolve(case, size) for size in (20, 200, 2000, 20000)]
    assert {max(len(program["influential_basis"]) for program in item.programs) for item in results} == {2}
    assert len({item.trace["terminal_action"] for item in results}) == 1
    views = [item.rounds[0]["library_search"] for item in results]
    assert [item["total_library_size"] for item in views] == [20, 200, 2000, 20000]
    assert {item["conditionally_indexed_count"] for item in views} == {1}
    assert all(not item["global_cumulative_activation"] for item in views)


@pytest.mark.parametrize("family", ["one_query_separable", "multi_step_separable", "scope_neighbor", "adversarial_query_trap"])
def test_action_order_metamorphism_preserves_behavior(runtime, case_factory, family: str) -> None:
    case, _ = case_factory(family, 1)
    permuted = copy.deepcopy(case)
    random.Random(750001).shuffle(permuted["actions"])
    original = runtime.resolve(case, 200)
    transformed = runtime.resolve(permuted, 200)
    assert transformed.trace["terminal_action"] == original.trace["terminal_action"]
    assert [item["selected_action_id"] for item in transformed.rounds] == [item["selected_action_id"] for item in original.rounds]
    assert [item["realized_contraction"] for item in transformed.queries_and_probes] == [item["realized_contraction"] for item in original.queries_and_probes]
