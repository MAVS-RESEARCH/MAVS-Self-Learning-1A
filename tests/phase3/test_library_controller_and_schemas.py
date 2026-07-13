from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from mavs10d.core.contracts import active_configuration_from_dict
from mavs10d.envs.phase3_gauntlet import Phase3WorldCompiler
from mavs10d.governance.self_learning.config_library import CertifiedConfigurationLibrary
from mavs10d.governance.self_learning.controller import SelfLearningController
from mavs10d.governance.self_learning.failure_attribution import attribute_failure
from mavs10d.governance.self_learning.memory import FailureCapsule
from mavs10d.governance.self_learning.meta_diagnostics import MetaDiagnosticState
from mavs10d.governance.self_learning.proposal_engine import ProposalContext, ProposalEngine
from mavs10d.governance.self_learning.rollback import RollbackManager
from mavs10d.governance.self_learning.selector import GovernedSelector


def _base():
    return active_configuration_from_dict(yaml.safe_load(Path("configs/methods/phase0_approved_eta.yaml").read_text(encoding="utf-8")))


def _candidate():
    meta = MetaDiagnosticState(0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 1.0, 0.1, 0.1, 0.0)
    capsule = FailureCapsule("capsule", "R01", "family", "confirmed_terminal_error", ("trace",), {"generation": 1}, {"calibration_residual": 1.0}, "reject", "accept", 1.0, "released", 0.95, {}, {"thresholds": 1.0})
    return ProposalEngine().propose(capsule, meta, attribute_failure(meta), ProposalContext(1, "R01", "text_safety", _base().config_id, "a" * 64, "b" * 64))[0]


def test_selector_never_executes_proposed_configuration() -> None:
    library = CertifiedConfigurationLibrary(_base())
    record = library.register(_candidate())
    selected = GovernedSelector(library).select({"generation": 1, "curriculum_id": "R01", "domain": "text_safety", "target_context": True})
    assert selected.record.config_id == library.base_config_id
    assert record.status == "proposed"


def test_library_transition_and_rollback_rehearsal_are_reversible() -> None:
    library = CertifiedConfigurationLibrary(_base())
    record = library.register(_candidate())
    with pytest.raises(ValueError, match="Illegal"):
        library.promote(record.config_id)
    library.certify(record.config_id, "c" * 64)
    library.begin_shadow(record.config_id)
    library.promote(record.config_id)
    result = RollbackManager(library).rehearse(record.config_id, protected_replay_passed=True)
    assert result.passed
    assert library.record(record.config_id).status == "approved"


def test_rollback_rehearsal_fails_closed_when_protected_replay_fails() -> None:
    library = CertifiedConfigurationLibrary(_base())
    record = library.register(_candidate())
    library.certify(record.config_id, "c" * 64)
    library.begin_shadow(record.config_id)
    library.promote(record.config_id)
    result = RollbackManager(library).rehearse(record.config_id, protected_replay_passed=False)
    assert not result.passed
    assert result.fallback_verified and result.restored_after_rehearsal


def test_rejected_configuration_is_terminal_and_never_selectable() -> None:
    library = CertifiedConfigurationLibrary(_base())
    record = library.register(_candidate())
    library.reject(record.config_id)
    with pytest.raises(ValueError, match="Illegal"):
        library.certify(record.config_id, "c" * 64)
    selected = GovernedSelector(library).select(record.candidate.intended_scope)
    assert selected.record.config_id == library.base_config_id


def test_fast_loop_writes_prefeedback_trace_without_evaluator_state() -> None:
    compiled = Phase3WorldCompiler().compile_generation(1)
    pair = next((visible, hidden) for visible, hidden in zip(compiled.visible, compiled.hidden) if hidden.target_exposure and visible.feedback_reliability >= 0.75 and visible.feedback_release_step is not None)
    visible, hidden = pair
    controller = SelfLearningController(condition="fresh", generation=1, base_configuration=_base())
    decision = controller.fast_loop(visible.to_dict(), contained=False)
    record = controller.memory.records[0]
    assert record.event_type == "decision"
    assert not {"unsafe", "correct_action", "hidden_repair_mechanism", "expected_operation"} & set(record.payload)
    completion = controller.complete_released_feedback(decision, visible.to_dict(), released_unsafe_label=hidden.unsafe, feedback_provenance="released", feedback_reliability=visible.feedback_reliability)
    assert completion.outcome_record_hash == controller.memory.records[1].record_hash
    assert controller.memory.validate_chain()


def test_unreliable_feedback_cannot_enter_slow_loop() -> None:
    visible = Phase3WorldCompiler().compile_generation(1).visible[0]
    controller = SelfLearningController(condition="fresh", generation=1, base_configuration=_base())
    decision = controller.fast_loop(visible.to_dict(), contained=False)
    with pytest.raises(ValueError, match="quarantined"):
        controller.complete_released_feedback(decision, visible.to_dict(), released_unsafe_label=True, feedback_provenance="unreliable", feedback_reliability=0.7)


def test_all_phase3_schemas_are_valid_draft_2020_12() -> None:
    schemas = sorted(Path("schemas").glob("phase3*.schema.json"))
    assert len(schemas) >= 13
    for path in schemas:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
