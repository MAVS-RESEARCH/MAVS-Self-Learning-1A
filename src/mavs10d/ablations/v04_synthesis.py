"""Executable synthesis-integrity controls for the Version 0.4 ablation matrix."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from mavs10d.diagnostics.ast import collect_feature_references, template_signature
from mavs10d.diagnostics.behavioral_fingerprint import behavioral_hash, fingerprint_frame
from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.diagnostics.semantic_hash import semantic_hash
from mavs10d.integrity.hidden_field_audit import find_taint
from mavs10d.learning.operation_constraints import OPERATIONS, check_operation
from mavs10d.learning.structure_search import comparison, structure_space


def _variant_candidates(
    condition_id: str,
    candidates: list[ExecutableDiagnostic],
    seed: int,
) -> list[ExecutableDiagnostic]:
    base = candidates[0]
    if condition_id in {"I1", "I10"}:
        return [replace(base, candidate_id=f"{condition_id}-FIXED-{index:03d}", name=f"renamed-feature-{index:03d}") for index in range(len(candidates))]
    if condition_id == "I3":
        originals = candidates[: len(candidates) // 2]
        equivalents = []
        for index, candidate in enumerate(originals):
            expression = {"op": "not", "children": [{"op": "not", "children": [candidate.expression_ast]}]}
            equivalents.append(replace(candidate, candidate_id=f"I3-BEH-{index:03d}", name=f"behavior-equivalent-{index:03d}", expression_ast=expression))
        return originals + equivalents
    if condition_id == "I4":
        variants = []
        for candidate in candidates:
            parameters = {key: (1.0 if key == "weight" else 0.5) for key in candidate.parameters}
            variants.append(replace(candidate, parameters=parameters))
        return variants
    if condition_id == "I5":
        variants = []
        for index, candidate in enumerate(candidates):
            current = str(candidate.lineage["operation"])
            wrong = OPERATIONS[(OPERATIONS.index(current) + 1) % len(OPERATIONS)]
            variants.append(replace(candidate, lineage={**candidate.lineage, "operation": wrong}, candidate_id=f"I5-META-{index:03d}"))
        return variants
    if condition_id == "I9":
        variants = []
        for index, candidate in enumerate(candidates):
            expression = comparison("nuisance_marker", "threshold")
            evidence = {**candidate.evidence_contract, "sources": sorted(set(candidate.evidence_contract["sources"]) | {"nuisance_marker"})}
            variants.append(replace(candidate, candidate_id=f"I9-CONFOUND-{index:03d}", expression_ast=expression, evidence_contract=evidence))
        return variants
    if condition_id == "I11":
        rng = np.random.default_rng(seed)
        variants = []
        for index, candidate in enumerate(candidates):
            operation = str(candidate.lineage["operation"])
            space = structure_space(operation, index % 2)
            expression = space[int(rng.integers(1, len(space)))]
            evidence = {
                **candidate.evidence_contract,
                "sources": sorted(
                    set(candidate.evidence_contract["sources"])
                    | set(collect_feature_references(expression))
                ),
            }
            variants.append(replace(candidate, candidate_id=f"I11-RANDOM-{index:03d}", expression_ast=expression, evidence_contract=evidence))
        return variants
    return candidates


def evaluate_synthesis_condition(
    condition_id: str,
    candidates: Iterable[ExecutableDiagnostic],
    bank: pd.DataFrame,
    lifecycle_by_id: Mapping[str, str],
    gate_by_id: Mapping[str, Mapping[str, Any]],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Evaluate executable identity, behavior, operation semantics, and promotion pressure."""
    originals = list(candidates)
    variants = _variant_candidates(condition_id, originals, seed)
    records: list[dict[str, Any]] = []
    semantic_seen: set[str] = set()
    behavioral_seen: set[str] = set()
    for index, candidate in enumerate(variants):
        candidate.validate()
        fingerprint = fingerprint_frame(candidate, bank)
        semantic = semantic_hash(candidate)
        behavioral = behavioral_hash(fingerprint)
        semantic_duplicate = semantic in semantic_seen
        behavioral_duplicate = behavioral in behavioral_seen
        semantic_seen.add(semantic)
        behavioral_seen.add(behavioral)
        anti_scope = fingerprint[fingerprint["bank"] == "anti_scope"]
        retained = fingerprint[fingerprint["bank"].isin(["retained", "holdout", "disjoint_analogue"])]
        truth = bank[["case_id", "unsafe"]]
        evaluated = fingerprint.merge(truth, on="case_id", validate="one_to_one")
        active = evaluated["active"].astype(bool)
        output = evaluated["discrete_output"].astype(bool)
        unsafe = evaluated["unsafe"].astype(bool)
        protected_error = float(((active & (output != unsafe))).mean())
        try:
            operation_passed = bool(check_operation(candidate.to_dict())["passed"])
        except (KeyError, TypeError, ValueError):
            operation_passed = False
        original_id = originals[index].candidate_id if index < len(originals) else ""
        original_promoted = lifecycle_by_id.get(original_id) == "promoted"
        witness_passed = bool(gate_by_id.get(original_id, {}).get("gates", {}).get("perception_extension_witness", {}).get("passed", original_promoted))
        integrity_eligible = original_promoted
        certification_eligible = original_promoted
        rejection_reason = None
        if condition_id in {"I1", "I10"}:
            integrity_eligible = False if condition_id == "I1" else True
            certification_eligible = integrity_eligible
            rejection_reason = "template_collapse" if condition_id == "I1" else None
        elif condition_id == "I2":
            certification_eligible = not behavioral_duplicate
            integrity_eligible = certification_eligible
            rejection_reason = "behavioral_duplicate" if behavioral_duplicate else None
        elif condition_id == "I3":
            integrity_eligible = True
            certification_eligible = True
        elif condition_id == "I4":
            integrity_eligible = original_promoted
            certification_eligible = original_promoted
        elif condition_id == "I5":
            integrity_eligible = True
            certification_eligible = True
        elif condition_id == "I8":
            witness_passed = False if index >= len(variants) // 2 else witness_passed
            integrity_eligible = True
            certification_eligible = True
        elif condition_id == "I9":
            integrity_eligible = True
            certification_eligible = True
        elif condition_id == "I11":
            integrity_eligible = not behavioral_duplicate and bool(fingerprint["active"].any())
            certification_eligible = integrity_eligible and operation_passed and protected_error <= 0.35
        record = {
            "condition_id": condition_id,
            "bank": "phase6_frozen_synthesis_banks",
            "candidate_id": candidate.candidate_id,
            "operation": str(candidate.lineage["operation"]),
            "semantic_hash": semantic,
            "behavioral_hash": behavioral,
            "template_signature": template_signature(candidate.expression_ast),
            "semantic_duplicate": int(semantic_duplicate),
            "behavioral_duplicate": int(behavioral_duplicate),
            "operation_compliant": int(operation_passed),
            "witness_passed": int(witness_passed),
            "integrity_eligible": int(integrity_eligible),
            "certification_eligible": int(certification_eligible),
            "active_fraction": float(fingerprint["active"].mean()),
            "anti_scope_leakage": float(anti_scope["active"].mean()) if len(anti_scope) else 0.0,
            "retained_activity": float(retained["active"].mean()) if len(retained) else 0.0,
            "protected_error": protected_error,
            "parameter_distance_from_half": float(np.mean([abs(float(value) - 0.5) for value in candidate.parameters.values()])),
            "rejection_reason": rejection_reason or "",
        }
        records.append(record)
    frame = pd.DataFrame(records)
    taint_count = 0
    firewall_detected = False
    if condition_id == "I6":
        attack = {"operation": "split", "expected_class": "beneficial"}
        taint_count = len(find_taint(attack, "phase8_evaluator_only_sentinel"))
        firewall_detected = taint_count > 0
    if condition_id == "I7":
        attack = {"hidden_world": {"oracle_label": "unsafe"}, "sentinel": "phase8_evaluator_only_sentinel"}
        taint_count = len(find_taint(attack, "phase8_evaluator_only_sentinel"))
        firewall_detected = taint_count > 0
    summary = {
        "candidate_count": len(frame),
        "semantic_class_count": int(frame["semantic_hash"].nunique()),
        "behavioral_class_count": int(frame["behavioral_hash"].nunique()),
        "template_count": int(frame["template_signature"].nunique()),
        "semantic_duplicate_count": int(frame["semantic_duplicate"].sum()),
        "behavioral_equivalent_count": int(frame["behavioral_duplicate"].sum()),
        "certification_pressure": int(frame["certification_eligible"].sum()),
        "active_eligibility": int(frame["integrity_eligible"].sum()),
        "operation_noncompliance": int((frame["operation_compliant"] == 0).sum()),
        "missing_witness_promotions": int(((frame["witness_passed"] == 0) & (frame["certification_eligible"] == 1)).sum()),
        "witness_success": float(frame["witness_passed"].mean()),
        "scope_leakage": float(frame["anti_scope_leakage"].mean()),
        "protected_error": float(frame["protected_error"].mean()),
        "parameter_diversity": float(frame["parameter_distance_from_half"].mean()),
        "taint_count": taint_count,
        "firewall_detected": firewall_detected,
        "publication_allowed": bool(condition_id == "I10" or frame["template_signature"].nunique() >= 5),
        "valid_yield": float(frame["certification_eligible"].mean()),
        "witnessed_yield": float(((frame["certification_eligible"] == 1) & (frame["witness_passed"] == 1)).mean()),
        "harmful_noop_rate": float(((frame["active_fraction"] == 0.0) | (frame["protected_error"] > 0.35)).mean()),
    }
    if condition_id == "I2":
        summary["certification_pressure"] = int(frame["certification_eligible"].sum() + frame["semantic_duplicate"].sum())
    return records, summary
