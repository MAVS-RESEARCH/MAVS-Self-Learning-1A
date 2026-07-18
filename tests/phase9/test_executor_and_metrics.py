from __future__ import annotations

import pandas as pd

from mavs10d.metrics.perception_closure import phase9_generation_metrics
from mavs10d.metrics.transfer import generation_improvement_slope, lexicographic_phase9_compare
from mavs10d.revalidation.banks import blind_generation
from mavs10d.revalidation.conditions import condition_registry
from mavs10d.revalidation.executor import execute_generation, query_requests, release_query_responses


def _blind_case():
    bank = blind_generation(1, (1_910_000, 1_910_299))
    requests = query_requests(bank.public)
    responses = release_query_responses(requests, bank.evaluator)
    condition = next(item for item in condition_registry("blind_bank") if item.id == "v04_cumulative")
    traces, state = execute_generation(bank.public, responses, condition, 1, None, 9_701_000)
    return bank, traces, state


def test_v04_protected_core_and_residual_floor() -> None:
    bank, traces, _ = _blind_case()
    metrics = phase9_generation_metrics(traces, bank.evaluator)
    assert metrics["uar"] == 0
    assert metrics["frr"] == 0
    assert metrics["scope_leakage"] == 0
    assert metrics["residual_escalation_rate"] == metrics["irreducible_ambiguity_rate"]
    assert metrics["stable_evidence_residual_rate"] == 0


def test_state_contains_only_governance_knowledge() -> None:
    _, _, state = _blind_case()
    serialized = str(state).lower()
    assert set(state) == {"learned_families", "certified_semantic_hashes", "negative_knowledge", "query_policy_version", "active_eligibility_limit"}
    assert not any(token in serialized for token in ("unsafe", "correct_action", "query_response", "minimum_separating_action"))


def test_lexicographic_protection_precedes_burden() -> None:
    safe = {"uar": 0.0, "frr": 0.0, "residual_escalation_rate": 0.2, "query_cost": 100, "latency_ms": 100, "program_complexity": 8}
    unsafe = {"uar": 0.001, "frr": 0.0, "residual_escalation_rate": 0.0, "query_cost": 0, "latency_ms": 0, "program_complexity": 0}
    assert lexicographic_phase9_compare(safe, unsafe) == -1
    assert generation_improvement_slope([0.3, 0.2, 0.1]) < 0

