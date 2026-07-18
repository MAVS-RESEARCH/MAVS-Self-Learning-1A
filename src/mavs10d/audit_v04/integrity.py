"""Stable corruption reason codes used by audit and deliberate-corruption tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import canonical_bytes, file_sha256, stable_hash


CORRUPTION_CODES = {
    "ast": "P10_CORRUPT_AST",
    "parameter": "P10_CORRUPT_PARAMETER",
    "scope": "P10_CORRUPT_SCOPE",
    "evidence_dependency": "P10_CORRUPT_EVIDENCE_DEPENDENCY",
    "gate": "P10_CORRUPT_GATE",
    "trace": "P10_CORRUPT_TRACE",
    "seed": "P10_CORRUPT_SEED",
    "result_path": "P10_CORRUPT_RESULT_PATH",
    "signature": "P10_CORRUPT_SIGNATURE",
}


def detect_structural_corruption(kind: str, original: Any, challenged: Any) -> str | None:
    if kind not in CORRUPTION_CODES:
        raise ValueError(f"P10_UNKNOWN_CORRUPTION_KIND: {kind}")
    return CORRUPTION_CODES[kind] if canonical_bytes(original) != canonical_bytes(challenged) else None


def verify_artifact(path: Path, expected_size: int, expected_sha256: str) -> str | None:
    if not path.is_file():
        return "P10_MISSING_ARTIFACT"
    if path.stat().st_size != expected_size:
        return "P10_ARTIFACT_SIZE_MISMATCH"
    if file_sha256(path) != expected_sha256:
        return "P10_ARTIFACT_HASH_MISMATCH"
    return None


def lifecycle_reconciles(counts: dict[str, int]) -> bool:
    return counts["proposed"] == counts.get("integrity_rejected", 0) + counts.get("certification_rejected", 0) + counts.get("quarantined", 0) + counts.get("promoted", 0)


def release_precondition_reason(state: dict[str, Any]) -> str | None:
    checks = (
        ("dirty_tree", "P10_DIRTY_TREE"), ("untracked_evidence", "P10_UNTRACKED_EVIDENCE"),
        ("missing_lfs", "P10_MISSING_LFS_OBJECT"), ("unsigned_manifest", "P10_UNSIGNED_MANIFEST"),
        ("unresolved_findings", "P10_UNRESOLVED_AUDIT_FINDINGS"), ("stale_pointer", "P10_STALE_RESULT_POINTER"),
        ("append_only_mutation", "P10_APPEND_ONLY_MUTATION"), ("provisional_claim", "P10_PROVISIONAL_CLAIM"),
    )
    for key, reason in checks:
        if state.get(key, False):
            return reason
    return None

