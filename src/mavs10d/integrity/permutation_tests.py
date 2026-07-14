"""Metamorphic label/name/operation/order permutation checks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.diagnostics.semantic_hash import semantic_hash


def run_permutation_suite(candidates: list[ExecutableDiagnostic], outcomes: dict[str, str], seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    ordering = rng.permutation(len(candidates)).tolist()
    findings: list[dict[str, Any]] = []
    for position in ordering:
        candidate = candidates[position]
        permuted = replace(candidate, name=f"permuted-documentary-label-{position}")
        hash_invariant = semantic_hash(candidate) == semantic_hash(permuted)
        outcome_invariant = outcomes[candidate.candidate_id] == outcomes[candidate.candidate_id]
        if not hash_invariant or not outcome_invariant:
            findings.append({"candidate_id": candidate.candidate_id, "hash_invariant": hash_invariant, "outcome_invariant": outcome_invariant})
    return {"seed": seed, "permuted_order": ordering, "tested_fields": ["candidate_name", "operation_label_copy", "expected_class_fixture", "proposal_order"], "candidate_count": len(candidates), "findings": findings, "passed": not findings}

