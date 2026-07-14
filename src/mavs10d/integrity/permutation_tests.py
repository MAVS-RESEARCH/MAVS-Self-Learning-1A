"""Metamorphic label/name/operation/order permutation checks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from mavs10d.diagnostics.behavioral_fingerprint import behaviorally_equivalent, fingerprint_frame
from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.diagnostics.semantic_hash import semantic_hash


def run_permutation_suite(candidates: list[ExecutableDiagnostic], outcomes: dict[str, str], bank: pd.DataFrame, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    ordering = rng.permutation(len(candidates)).tolist()
    operations = [candidate.lineage["operation"] for candidate in candidates]
    permuted_operations = [operations[index] for index in rng.permutation(len(operations))]
    expected_labels = ["beneficial" if index % 2 == 0 else "harmful" for index in range(len(candidates))]
    permuted_labels = [expected_labels[index] for index in rng.permutation(len(expected_labels))]
    semantic_outcomes = {semantic_hash(candidate): outcomes[candidate.candidate_id] for candidate in candidates}
    findings: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for permutation_position, position in enumerate(ordering):
        candidate = candidates[position]
        lineage = {**candidate.lineage, "operation": permuted_operations[permutation_position]}
        permuted = replace(candidate, name=f"permuted-documentary-label-{position}", lineage=lineage)
        hash_invariant = semantic_hash(candidate) == semantic_hash(permuted)
        outcome_invariant = semantic_outcomes.get(semantic_hash(permuted)) == outcomes[candidate.candidate_id]
        behavior_invariant = behaviorally_equivalent(fingerprint_frame(candidate, bank), fingerprint_frame(permuted, bank))
        record = {"candidate_id": candidate.candidate_id, "permuted_name": permuted.name, "permuted_operation": permuted_operations[permutation_position], "permuted_expected_class": permuted_labels[permutation_position], "permuted_position": permutation_position, "hash_invariant": hash_invariant, "behavior_invariant": behavior_invariant, "outcome_invariant": outcome_invariant}
        records.append(record)
        if not hash_invariant or not behavior_invariant or not outcome_invariant:
            findings.append(record)
    return {"seed": seed, "permuted_order": ordering, "tested_fields": ["candidate_name", "operation_label", "expected_class", "proposal_order"], "candidate_count": len(candidates), "records": records, "findings": findings, "passed": not findings}
