from __future__ import annotations

from mavs10d.learning.operation_constraints import OPERATIONS, check_operation
from mavs10d.learning.synthesis import build_bank, synthesize_candidates


def test_structure_and_parameter_trials_are_executed_with_provenance() -> None:
    bank = build_bank(620001, 16)
    candidates = synthesize_candidates(bank, 610001, 620001)
    for item in candidates:
        assert len(item.structure_trace) >= 2
        assert sum(trace["selected"] for trace in item.structure_trace) == 1
        assert len(item.parameter_trace) >= 8
        assert sum(trace["selected"] for trace in item.parameter_trace) == 1
        tried = {tuple(sorted(trace["parameters"].items())) for trace in item.parameter_trace}
        assert len(tried) > 1


def test_all_operation_semantics_are_machine_checked() -> None:
    bank = build_bank(620001, 16)
    candidates = synthesize_candidates(bank, 610001, 620001)
    accepted = [item.candidate for item in candidates if item.expected_lifecycle == "promoted"]
    assert {candidate.lineage["operation"] for candidate in accepted} == set(OPERATIONS)
    assert all(check_operation(candidate.to_dict())["passed"] for candidate in accepted)

