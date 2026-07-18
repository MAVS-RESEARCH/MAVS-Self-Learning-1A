from __future__ import annotations

import json

from mavs10d.revalidation.conditions import condition_registry


def test_track_a_has_full_legacy_and_phase8_matrix() -> None:
    registry = condition_registry("paired_original_bank")
    assert len(registry) == 103
    assert len([item for item in registry if item.id.startswith("legacy_registry_A")]) == 50
    assert len([item for item in registry if item.id.startswith(("I", "P", "L"))]) == 39
    assert len({item.id for item in registry}) == len(registry)


def test_track_b_has_all_claim_critical_controls() -> None:
    registry = condition_registry("blind_bank")
    identifiers = {item.id for item in registry}
    assert len(registry) == 35
    assert {"v04_cumulative", "v04_fresh", "v04_frozen_after_g1", "legacy_A0", "A1_frozen", "A2_threshold_only", "A3_selector_only", "fixed_full_mavs", "ds_cf_lineage", "raw_memory", "matched_memory", "reduced_learning", "random_proposal", "oracle_closure"} <= identifiers
    assert len([item for item in registry if item.id.startswith(("I", "P", "L"))]) == 21


def test_legacy_registry_serializes_every_exact_change() -> None:
    registry = [item for item in condition_registry("paired_original_bank") if item.id.startswith("legacy_registry_A")]
    assert json.loads(registry[0].configuration_json) == {}
    assert json.loads(registry[17].configuration_json) == {"unknown_policy": "reject"}
    assert json.loads(registry[49].configuration_json) == {"memory_budget": "matched_baseline"}

