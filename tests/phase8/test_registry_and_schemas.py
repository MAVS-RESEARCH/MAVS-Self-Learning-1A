from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from mavs10d.ablations.v04_registry import AblationRegistry, EXPECTED_IDS


ROOT = Path(__file__).resolve().parents[2]


def registry() -> AblationRegistry:
    return AblationRegistry.from_directory(ROOT / "configs" / "ablations" / "v04")


def test_complete_matrix_has_39_conditions() -> None:
    assert len(list(registry())) == 39
    assert len(EXPECTED_IDS) == 39


@pytest.mark.parametrize("condition_id", EXPECTED_IDS)
def test_each_condition_has_exact_reference_diff(condition_id: str) -> None:
    definition = registry()[condition_id]
    expected = 0 if condition_id == definition.reference_id else 1
    assert len(definition.normalized_diff()) == expected
    assert len(definition.toggle) == expected


def test_all_definitions_validate_against_schema() -> None:
    schema = json.loads((ROOT / "schemas" / "v04" / "ablation_definition.schema.json").read_text(encoding="utf-8"))
    for definition in registry():
        jsonschema.validate(definition.serializable(), schema)


def test_registry_hash_is_order_invariant() -> None:
    first = registry().manifest()["matrix_hash"]
    reversed_registry = AblationRegistry(reversed(list(registry())))
    assert reversed_registry.manifest()["matrix_hash"] == first
