from __future__ import annotations

from dataclasses import replace

import pytest

from mavs10d.envs.phase3_gauntlet import Phase3WorldCompiler, load_repair_curricula
from mavs10d.governance.self_learning.diagnostic_grammar import GrammarExpression, ProposalOperation
from mavs10d.governance.self_learning.failure_attribution import attribute_failure
from mavs10d.governance.self_learning.memory import FailureCapsule
from mavs10d.governance.self_learning.meta_diagnostics import MetaDiagnosticState
from mavs10d.governance.self_learning.meta_diagnostics import evaluate_meta_diagnostics, trigger_reasons
from mavs10d.governance.self_learning.proposal_engine import ProposalContext, ProposalEngine, SIGNAL_TO_OPERATION
from mavs10d.governance.self_learning.safety_kernel import ImmutableSafetyKernel
from mavs10d.governance.self_learning.validator import CandidateValidator


def _meta(primary: str) -> MetaDiagnosticState:
    values = {name: 0.1 for name in MetaDiagnosticState.__dataclass_fields__}
    values[primary] = 1.0
    if primary == "evidence_unavailable":
        values["evidence_masking"] = 1.0
    return MetaDiagnosticState(**values)


def _capsule(curriculum_id: str, primary: str) -> FailureCapsule:
    signature = {name: 0.1 for name in SIGNAL_TO_OPERATION}
    signature[primary] = 1.0
    signature.update({"domain": "text_safety", "generation": 1, "curriculum_id": curriculum_id, "target_context": True, "risk_proxy": 0.2})
    return FailureCapsule(
        capsule_id=f"capsule-{curriculum_id}", curriculum_id=curriculum_id, family_id=f"family-{primary}", trigger="confirmed_terminal_error", trace_ids=("trace",),
        context={"generation": 1}, observable_signature=signature, expected_action="reject", observed_action="accept", severity=1.0,
        feedback_provenance="released", feedback_reliability=0.95, minimal_contrasts={}, attribution={"diagnostics": 1.0},
    )


def test_unrestricted_grammar_primitive_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-approved"):
        GrammarExpression("generated_code", "x", ">=", 0.5, "increasing", 0.0, 1.0, {"x": 1.0})


def test_selector_uncertainty_is_boundary_sensitive_not_base_fallback_sensitive() -> None:
    fallback = evaluate_meta_diagnostics({}, nearest_support=1.0, selector_applicability=0.0, recurrence=0.0)
    boundary = evaluate_meta_diagnostics({}, nearest_support=1.0, selector_applicability=0.5, recurrence=0.0)
    assert fallback.selector_uncertainty == 0.0
    assert boundary.selector_uncertainty == 1.0


def test_all_slow_loop_trigger_classes_are_machine_detectable() -> None:
    state = MetaDiagnosticState(0.8, 0.1, 0.7, 0.1, 0.1, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1, 0.0)
    reasons = trigger_reasons(
        state,
        confirmed_error=True,
        recurring_escalations=5,
        significant_regression=True,
    )
    assert set(reasons) == {
        "confirmed_error",
        "recurring_escalation",
        "unexplained_novelty",
        "scope_leakage",
        "instability",
        "significant_regression",
    }


def test_proposal_engine_recovers_every_operation_from_visible_meta_signal() -> None:
    engine = ProposalEngine()
    for curriculum in load_repair_curricula():
        meta = _meta(curriculum.primary_meta_signal)
        attribution = attribute_failure(meta)
        proposals = engine.propose(
            _capsule(curriculum.curriculum_id, curriculum.primary_meta_signal), meta, attribution,
            ProposalContext(1, curriculum.curriculum_id, curriculum.domain, "phase0-approved-diagnostic-only", "a" * 64, "b" * 64),
        )
        matching = [item for item in proposals if item.operation.value == curriculum.operation]
        assert len(matching) == 1
        assert matching[0].allowed_influence["mitigation"] == 0.12
        assert all(item.to_dict()["exact_function"]["primitive"] != "generated_code" for item in proposals)


def test_correct_candidates_pass_all_gates_and_harmful_decoys_are_rejected() -> None:
    compiler = Phase3WorldCompiler()
    compiled = compiler.compile_generation(1)
    engine = ProposalEngine()
    validator = CandidateValidator(ImmutableSafetyKernel(), 64)
    for curriculum in load_repair_curricula():
        meta = _meta(curriculum.primary_meta_signal)
        proposals = engine.propose(
            _capsule(curriculum.curriculum_id, curriculum.primary_meta_signal), meta, attribute_failure(meta),
            ProposalContext(1, curriculum.curriculum_id, curriculum.domain, "phase0-approved-diagnostic-only", "a" * 64, "b" * 64),
        )
        cases = [item.to_dict() for item in compiled.certification_cases if item.curriculum_id == curriculum.curriculum_id]
        reports = [validator.certify(item, cases, evaluator_expected_operation=curriculum.operation, trace_complete=True, rollback_verified=True, retained_counterexamples_preserved=True, feedback_reliability=0.95) for item in proposals]
        passed = [item for item in reports if item.passed]
        rejected = [item for item in reports if not item.passed]
        assert len(passed) == len(rejected) == 1
        assert passed[0].truly_beneficial and not passed[0].harmful
        assert rejected[0].harmful


def test_kernel_rejects_mitigation_above_bound() -> None:
    curriculum = load_repair_curricula()[0]
    meta = _meta(curriculum.primary_meta_signal)
    candidate = ProposalEngine().propose(
        _capsule(curriculum.curriculum_id, curriculum.primary_meta_signal), meta, attribute_failure(meta),
        ProposalContext(1, curriculum.curriculum_id, curriculum.domain, "phase0-approved-diagnostic-only", "a" * 64, "b" * 64),
    )[0]
    harmful = replace(candidate, allowed_influence={**candidate.allowed_influence, "mitigation": 0.3})
    cases = [item.to_dict() for item in Phase3WorldCompiler().compile_generation(1).certification_cases if item.curriculum_id == curriculum.curriculum_id]
    report = CandidateValidator(ImmutableSafetyKernel(), 64).certify(harmful, cases, evaluator_expected_operation=curriculum.operation, trace_complete=True, rollback_verified=True, retained_counterexamples_preserved=True, feedback_reliability=0.95)
    assert not report.passed and report.harmful
    assert "kernel_failed:bounded_mitigation" in report.kernel["reason_codes"]
