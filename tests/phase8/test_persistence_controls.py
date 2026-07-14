from __future__ import annotations

import pytest

from mavs10d.ablations.v04_persistence import simulate_persistence


@pytest.fixture(scope="module")
def baseline(phase7_cases):
    return {
        case["case_id"]: {
            "terminal_action": case["fast_loop"]["outcome"] if case["fast_loop"]["outcome"] != "UNRESOLVED" else ("ESCALATE" if case["family"] in {"irreducible_pair", "budget_limited_case"} else "ACCEPT"),
            "rounds": 0 if case["family"] in {"immediately_separable", "irreducible_pair", "budget_limited_case"} else 1,
            "query_count": int(case["family"] not in {"immediately_separable", "new_composition", "irreducible_pair", "budget_limited_case"}),
        }
        for case in phase7_cases
    }


@pytest.mark.parametrize("condition_id", [f"L{index}" for index in range(11)])
def test_all_persistence_controls_execute(condition_id, phase7_cases, baseline) -> None:
    records, knowledge = simulate_persistence(condition_id, phase7_cases, baseline)
    assert records
    assert knowledge
    assert {item["generation"] for item in records} == {1, 2, 3}
    assert all(len(item["execution_hash"]) == 64 for item in records)


def test_cumulative_beats_fresh_on_round_burden(phase7_cases, baseline) -> None:
    cumulative, _ = simulate_persistence("L0", phase7_cases, baseline)
    fresh, _ = simulate_persistence("L1", phase7_cases, baseline)
    assert sum(item["rounds"] for item in cumulative) < sum(item["rounds"] for item in fresh)


def test_no_consolidation_and_unlimited_eligibility_create_pressure(phase7_cases, baseline) -> None:
    reference, _ = simulate_persistence("L0", phase7_cases, baseline)
    no_consolidation, _ = simulate_persistence("L3", phase7_cases, baseline)
    unlimited, _ = simulate_persistence("L9", phase7_cases, baseline)
    assert max(item["library_size"] for item in no_consolidation) > max(item["library_size"] for item in reference)
    assert max(item["active_basis"] for item in unlimited) > max(item["active_basis"] for item in reference)


def test_no_recertification_activates_stale_scope(phase7_cases, baseline) -> None:
    records, _ = simulate_persistence("L10", phase7_cases, baseline)
    assert sum(item["stale_scope_activation"] for item in records) > 0
    assert sum(item["scope_leakage"] for item in records) > 0
