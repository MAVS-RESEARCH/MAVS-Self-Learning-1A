from __future__ import annotations

from copy import deepcopy

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


def test_every_operation_rejects_a_metadata_only_or_missing_semantic_delta() -> None:
    candidates = synthesize_candidates(build_bank(620001, 16), 610001, 620001)
    by_operation = {item.candidate.lineage["operation"]: item.candidate.to_dict() for item in candidates if item.expected_lifecycle == "promoted"}
    mutations = {
        "recalibrate": lambda payload, candidate: payload.update(parent_expression_ast={"op": "constant", "value": True}),
        "split": lambda payload, candidate: payload.update(children=[{"expression_ast": candidate["expression_ast"]}, {"expression_ast": candidate["expression_ast"]}]),
        "merge": lambda payload, candidate: payload.update(redundancy_after=payload["redundancy_before"]),
        "add": lambda payload, candidate: payload.update(new_dependencies=[]),
        "scope_narrow": lambda payload, candidate: payload.update(parent_positive_scope_ast=candidate["positive_scope_ast"], parent_anti_scope_ast=candidate["anti_scope_ast"], deactivated_neighbor_case_ids=[]),
        "scope_expand": lambda payload, candidate: payload.update(passed_suites=["boundary"]),
        "evidence_recovery": lambda payload, candidate: payload["acquisition_record"].update(status="metadata_only"),
        "policy_interaction": lambda payload, candidate: payload.update(after_relationship=payload["before_relationship"]),
        "configuration_specialization": lambda payload, candidate: payload.update(mapping_after=payload["mapping_before"]),
        "retire": lambda payload, candidate: payload.update(runtime_eligibility_after=True),
    }
    for operation, candidate in by_operation.items():
        mutated = deepcopy(candidate)
        mutations[operation](mutated["operation_payload"], mutated)
        assert not check_operation(mutated)["passed"], operation
