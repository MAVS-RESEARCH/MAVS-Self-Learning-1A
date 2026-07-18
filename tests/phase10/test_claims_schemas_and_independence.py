from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from mavs10d.audit_v04.claims import derive_status, evaluate_cumulative_value
from mavs10d.audit_v04.common import REPO_ROOT


def test_claim_supported_only_when_all_required_gates_pass():
    assert derive_status(["a", "b"], {"a": True, "b": True}) == "supported"


def test_claim_downgrades_on_missing_gate():
    assert derive_status(["a", "b"], {"a": True}) == "unsupported"


def test_claim_partially_supported_on_mixed_scientific_gates():
    assert derive_status(["a", "b"], {"a": True, "b": False}) == "partially_supported"


def test_integrity_failure_falsifies_dependent_claim():
    assert derive_status(["a", "integrity"], {"a": True, "integrity": False}, integrity_gates=["integrity"]) == "falsified"


def test_forced_unsupported_cannot_be_elevated():
    assert derive_status(["a"], {"a": True}, forced_status="unsupported") == "unsupported"


def test_cumulative_value_is_derived_from_sealed_blind_rows():
    result = evaluate_cumulative_value()
    assert result["paired_rows_complete"]
    assert result["safety_noninferiority"]
    assert result["strict_burden_improvement"]
    assert result["scope_forgetting_growth_integrity"]
    assert result["status"] == "PASS"


@pytest.mark.parametrize("schema", ["audit_manifest", "claim_ledger", "release_manifest", "replay_comparison", "results_isolation_audit"])
def test_phase10_schema_is_valid_json(schema):
    payload = json.loads((REPO_ROOT / "schemas" / "v04" / f"{schema}.schema.json").read_text(encoding="utf-8"))
    assert payload["$schema"].endswith("2020-12/schema")


def test_audit_package_does_not_import_production_decision_modules():
    forbidden = ("mavs10d.certification", "mavs10d.learning", "mavs10d.revalidation", "mavs10d.metrics", "mavs10d.reports")
    hits = []
    for path in (REPO_ROOT / "src" / "mavs10d" / "audit_v04").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else ""
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            if any(module.startswith(prefix) for prefix in forbidden) or any(name.startswith(prefix) for name in names for prefix in forbidden):
                hits.append((path.name, node.lineno))
    assert hits == []


def test_replay_engine_is_independent_and_component_complete():
    source = (REPO_ROOT / "src" / "mavs10d" / "audit_v04" / "replay.py").read_text(encoding="utf-8")
    assert "phase9_replay_engine" in source
    assert "terminal_comparison_count" in source
    assert "query_probe_round_comparison_count" in source
    assert "program_scope_comparison_count" in source
    assert "certification_comparison_count" in source
    assert "mavs10d.revalidation" not in source
