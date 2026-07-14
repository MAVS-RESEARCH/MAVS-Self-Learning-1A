from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from mavs10d.ablations.v04_runtime import RuntimeAblationAdapter


@pytest.fixture(scope="module")
def adapter() -> RuntimeAblationAdapter:
    path = Path(__file__).resolve().parents[2] / "configs" / "perception_closure_v04" / "runtime.yaml"
    return RuntimeAblationAdapter(yaml.safe_load(path.read_text(encoding="utf-8")))


def case_for(cases, family: str):
    return next(item for item in cases if item["family"] == family)


def truth_for(truth, case_id: str):
    return truth[truth["case_id"] == case_id].iloc[0].to_dict()


@pytest.mark.parametrize("condition_id", [f"P{index}" for index in range(16)])
def test_all_runtime_controls_execute(condition_id, adapter, phase7_cases, phase7_truth) -> None:
    case = case_for(phase7_cases, "new_composition" if condition_id in {"P9"} else "harmful_vs_benign_correlation" if condition_id in {"P7", "P14"} else "irreducible_pair" if condition_id in {"P12", "P13"} else "one_query_separable")
    result = adapter.run(condition_id, case, 20000, truth_for(phase7_truth, case["case_id"]))
    assert result["condition_id"] == condition_id
    assert result["terminal_action"] in {"ACCEPT", "REJECT", "ESCALATE"}
    assert len(result["execution_hash"]) == 64


def test_p0_resolves_one_query_case_with_certificate(adapter, phase7_cases, phase7_truth) -> None:
    case = case_for(phase7_cases, "one_query_separable")
    result = adapter.run("P0", case, 20000, truth_for(phase7_truth, case["case_id"]))
    assert result["certificate_present"]
    assert result["external_escalate"] == 0
    assert result["query_count"] == 1


def test_p1_bypasses_resolver(adapter, phase7_cases, phase7_truth) -> None:
    case = case_for(phase7_cases, "one_query_separable")
    result = adapter.run("P1", case, 20000, truth_for(phase7_truth, case["case_id"]))
    assert result["terminal_action"] == "ESCALATE"
    assert result["rounds"] == 0


def test_nonsemantic_case_id_does_not_change_binary_control(adapter, phase7_cases, phase7_truth) -> None:
    case = case_for(phase7_cases, "irreducible_pair")
    renamed = copy.deepcopy(case)
    renamed["case_id"] = "NONSEMANTIC-RENAMED-CASE"
    original = adapter.run("P12", case, 20000, truth_for(phase7_truth, case["case_id"]))
    permuted = adapter.run("P12", renamed, 20000, truth_for(phase7_truth, case["case_id"]))
    assert original["terminal_action"] == permuted["terminal_action"]


def test_scope_and_interaction_attacks_are_instrumented(adapter, phase7_cases, phase7_truth) -> None:
    scope = case_for(phase7_cases, "scope_neighbor")
    composition = case_for(phase7_cases, "new_composition")
    scope_result = adapter.run("P5", scope, 20000, truth_for(phase7_truth, scope["case_id"]))
    interaction_result = adapter.run("P9", composition, 20000, truth_for(phase7_truth, composition["case_id"]))
    assert scope_result["scope_leakage"] == 1
    assert interaction_result["uncertified_interaction"] == 1
