from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from mavs10d.core.contracts import (
    ACTIVE_CONFIGURATION_SEMANTICS,
    ContractError,
    LearningEvent,
    active_configuration_from_dict,
)
from scripts.validate_updates import validate_record


def test_all_json_schemas_are_draft_2020_12_valid() -> None:
    paths = sorted(Path("schemas").glob("*.schema.json"))
    assert len(paths) >= 9
    for path in paths:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_active_configuration_has_exact_eta_tuple_and_architecture_scope() -> None:
    payload = yaml.safe_load(Path("configs/methods/phase0_approved_eta.yaml").read_text(encoding="utf-8"))
    configuration = active_configuration_from_dict(payload)
    configuration.validate(require_approved=True)
    assert tuple(component.symbol for component in configuration.components()) == tuple(ACTIVE_CONFIGURATION_SEMANTICS)
    assert configuration.omega_scope_policy["learning_enabled"] is False
    assert len(configuration.config_hash) == 64


def test_unapproved_configuration_cannot_enter_fast_loop() -> None:
    payload = yaml.safe_load(Path("configs/methods/phase0_approved_eta.yaml").read_text(encoding="utf-8"))
    payload["approval_status"] = "proposed"
    configuration = active_configuration_from_dict(payload)
    with pytest.raises(ContractError, match="approved"):
        configuration.validate(require_approved=True)


@pytest.mark.parametrize("reliability", [-0.01, 1.01])
def test_learning_event_rejects_invalid_feedback_reliability(reliability: float) -> None:
    with pytest.raises(ContractError):
        LearningEvent("event", "trigger", ("trace",), "mechanism", (), True, "released_label", reliability)


def test_phase0_budget_is_exact_and_noncompetitive() -> None:
    phase = yaml.safe_load(Path("configs/phases/phase0.yaml").read_text(encoding="utf-8"))
    assert phase["allocations"] == {
        "inherited_static": 1000,
        "generated_world": 2000,
        "trace_metric_metamorphic": 2000,
    }
    assert sum(phase["allocations"].values()) == 5000
    assert phase["competitive_methods"] == []


def test_quarantine_update_fixture_passes_schema_and_hash_validation() -> None:
    payload = json.loads(Path("tests/fixtures/phase0_quarantine_update.json").read_text(encoding="utf-8"))
    assert validate_record(payload) == []


def test_update_hash_tampering_is_rejected() -> None:
    payload = json.loads(Path("tests/fixtures/phase0_quarantine_update.json").read_text(encoding="utf-8"))
    payload["action"] = "promote"
    assert any("hash mismatch" in error for error in validate_record(payload))
