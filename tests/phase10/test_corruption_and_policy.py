from __future__ import annotations

import pytest

from mavs10d.audit_v04.integrity import CORRUPTION_CODES, detect_structural_corruption, lifecycle_reconciles, release_precondition_reason


@pytest.mark.parametrize("kind", sorted(CORRUPTION_CODES))
def test_every_deliberate_corruption_has_stable_reason(kind):
    assert detect_structural_corruption(kind, {"value": 1}, {"value": 2}) == CORRUPTION_CODES[kind]


def test_unchanged_artifact_has_no_corruption_reason():
    assert detect_structural_corruption("ast", {"node": 1}, {"node": 1}) is None


def test_candidate_lifecycle_reconciliation():
    assert lifecycle_reconciles({"proposed": 40, "integrity_rejected": 10, "certification_rejected": 10, "quarantined": 0, "promoted": 20})


@pytest.mark.parametrize("field,reason", [
    ("dirty_tree", "P10_DIRTY_TREE"), ("untracked_evidence", "P10_UNTRACKED_EVIDENCE"),
    ("missing_lfs", "P10_MISSING_LFS_OBJECT"), ("unsigned_manifest", "P10_UNSIGNED_MANIFEST"),
    ("unresolved_findings", "P10_UNRESOLVED_AUDIT_FINDINGS"), ("stale_pointer", "P10_STALE_RESULT_POINTER"),
    ("append_only_mutation", "P10_APPEND_ONLY_MUTATION"), ("provisional_claim", "P10_PROVISIONAL_CLAIM"),
])
def test_release_policy_fails_closed(field, reason):
    assert release_precondition_reason({field: True}) == reason


def test_release_policy_accepts_clean_state():
    assert release_precondition_reason({}) is None

