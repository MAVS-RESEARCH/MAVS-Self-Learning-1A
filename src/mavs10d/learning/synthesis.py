"""Phase 6 executable candidate synthesis and frozen audit-bank construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from mavs10d.diagnostics.ast import collect_feature_references
from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.learning.operation_constraints import OPERATIONS, compliant_payload
from mavs10d.learning.parameter_fit import fit_parameters
from mavs10d.learning.structure_search import comparison, search_structures


BANK_NAMES = (
    "trigger", "retained", "holdout", "positive_scope_boundary", "anti_scope",
    "nuisance_counterfactual", "causal_counterfactual", "adversarial", "disjoint_analogue",
)


@dataclass(frozen=True)
class SynthesizedCandidate:
    candidate: ExecutableDiagnostic
    expected_lifecycle: str
    structure_trace: list[dict[str, Any]]
    parameter_trace: list[dict[str, Any]]


def build_bank(seed: int, cases_per_bank: int = 64) -> pd.DataFrame:
    """Create separated deterministic banks without a final-claim blind split."""
    rows: list[dict[str, Any]] = []
    for bank_index, bank in enumerate(BANK_NAMES):
        rng = np.random.default_rng(seed + bank_index * 1009)
        latent = np.linspace(0.02, 0.98, cases_per_bank)
        rng.shuffle(latent)
        if bank == "anti_scope":
            context = np.full(cases_per_bank, 0.05)
        elif bank == "positive_scope_boundary":
            context = np.linspace(0.14, 0.36, cases_per_bank)
        else:
            context = np.clip(0.35 + 0.60 * rng.random(cases_per_bank), 0.0, 1.0)
        unsafe = latent >= 0.5
        noise = lambda scale: np.clip(latent + rng.normal(0.0, scale, cases_per_bank), 0.0, 1.0)
        features = {
            "risk_score": noise(0.035),
            "safe_witness": np.clip(1.0 - latent + rng.normal(0.0, 0.025, cases_per_bank), 0.0, 1.0),
            "danger_witness": noise(0.025),
            "provenance_strength": np.clip(0.15 + 0.80 * rng.random(cases_per_bank), 0.0, 1.0),
            "independence_score": noise(0.045),
            "evidence_available": np.where(rng.random(cases_per_bank) > 0.04, 1.0, 0.0),
            "masking_score": noise(0.055),
            "policy_conflict": noise(0.040),
            "temporal_persistence": noise(0.050),
            "calibration_residual": noise(0.045),
            "context_match": context,
            "query_signal": noise(0.030),
            "nuisance_marker": rng.random(cases_per_bank),
        }
        if bank == "adversarial":
            features["nuisance_marker"] = unsafe.astype(float)
        if bank == "nuisance_counterfactual":
            features["nuisance_marker"] = 1.0 - features["nuisance_marker"]
        if bank == "causal_counterfactual":
            for key in ("risk_score", "danger_witness", "independence_score", "masking_score", "policy_conflict", "temporal_persistence", "calibration_residual", "query_signal"):
                features[key] = np.clip(1.0 - features[key], 0.0, 1.0)
            unsafe = ~unsafe
        for index in range(cases_per_bank):
            row = {"case_id": f"{bank}-{index:04d}", "bank": bank, "unsafe": bool(unsafe[index])}
            row.update({key: float(value[index]) for key, value in features.items()})
            rows.append(row)
    return pd.DataFrame(rows)


def synthesize_candidates(development: pd.DataFrame, synthesis_seed: int, development_seed: int) -> list[SynthesizedCandidate]:
    """Synthesize two valid, one integrity-control, and one certification-control candidate per operation."""
    synthesized: list[SynthesizedCandidate] = []
    for operation_index, operation in enumerate(OPERATIONS):
        accepted: list[SynthesizedCandidate] = []
        for variant_index, variant in enumerate(("A", "B")):
            candidate_id = f"P6-{operation.upper().replace('_', '-')}-{variant}"
            initial = _initial_parameters(operation_index, variant_index)
            selected_ast, structure_trace = search_structures(candidate_id, operation, variant_index, initial, development, synthesis_seed + operation_index * 100 + variant_index * 10)
            fitted, parameter_trace = fit_parameters(candidate_id, selected_ast, initial, development, development_seed + operation_index * 100 + variant_index * 10)
            candidate = _candidate(candidate_id, f"documentary-{operation}-{variant.lower()}", operation, selected_ast, fitted, variant_index)
            accepted_item = SynthesizedCandidate(candidate, "promoted", structure_trace, parameter_trace)
            accepted.append(accepted_item)
            synthesized.append(accepted_item)

        source = accepted[0]
        integrity_id = f"P6-{operation.upper().replace('_', '-')}-I"
        integrity_candidate = _candidate(
            integrity_id,
            f"renamed-{operation}-control",
            operation,
            source.candidate.expression_ast,
            source.candidate.parameters,
            0,
            integrity_control="name_only_semantic_duplicate",
        )
        integrity_candidate = ExecutableDiagnostic(
            **{**integrity_candidate.__dict__, "positive_scope_ast": source.candidate.positive_scope_ast, "anti_scope_ast": source.candidate.anti_scope_ast,
               "evidence_contract": source.candidate.evidence_contract, "influence_contract": source.candidate.influence_contract,
               "counterfactual_contract": source.candidate.counterfactual_contract}
        )
        synthesized.append(SynthesizedCandidate(integrity_candidate, "integrity_rejected", _retarget_trace(source.structure_trace, integrity_id), _retarget_trace(source.parameter_trace, integrity_id)))

        control_id = f"P6-{operation.upper().replace('_', '-')}-C"
        control_initial = _initial_parameters(operation_index, 2)
        control_ast, control_structures = search_structures(control_id, operation, 1, control_initial, development, synthesis_seed + operation_index * 100 + 80)
        control_parameters, control_trials = fit_parameters(control_id, control_ast, control_initial, development, development_seed + operation_index * 100 + 80)
        control_candidate = _candidate(control_id, f"blind-scope-control-{operation}", operation, control_ast, control_parameters, 2, certification_control="anti_scope_leak")
        synthesized.append(SynthesizedCandidate(control_candidate, "certification_rejected", control_structures, control_trials))
    return synthesized


def _candidate(candidate_id: str, name: str, operation: str, expression_ast: dict[str, Any], parameters: dict[str, float], variant_index: int, integrity_control: str | None = None, certification_control: str | None = None) -> ExecutableDiagnostic:
    positive_scope = {"op": "constant", "value": True} if certification_control else comparison("context_match", "scope_lower")
    anti_scope = {"op": "constant", "value": False} if certification_control else comparison("context_match", "anti_scope_upper", "lte")
    parameters = {**parameters, "scope_lower": float(parameters.get("scope_lower", 0.25)), "anti_scope_upper": float(parameters.get("anti_scope_upper", 0.10))}
    references = set(collect_feature_references(expression_ast)) | set(collect_feature_references(positive_scope)) | set(collect_feature_references(anti_scope))
    parents = [f"phase3-parent-{operation}"]
    if operation == "merge":
        parents.append("phase3-parent-merge-secondary")
    payload = compliant_payload(operation)
    if operation == "retire":
        payload["runtime_influence_before"] = 1.0
        payload["runtime_influence_after"] = 0.0
    candidate = ExecutableDiagnostic(
        candidate_id=candidate_id,
        name=name,
        expression_ast=expression_ast,
        parameters=parameters,
        positive_scope_ast=positive_scope,
        anti_scope_ast=anti_scope,
        evidence_contract={"sources": sorted(references), "provenance": "audited_visible_evidence_registry", "availability": "declared_per_case", "freshness_seconds": 60.0, "minimum_trust": 0.60, "failure_behavior": "deactivate"},
        influence_contract={"channel": "terminal", "minimum": 0.0, "maximum": 1.0, "terminal_authority": True},
        counterfactual_contract={"nuisance_interventions": ["nuisance_marker_permutation"], "causal_interventions": ["protected_signal_inversion"], "nuisance_tolerance": 1e-9, "minimum_causal_delta": 0.20},
        lineage={"parents": parents, "operation": operation, "triggering_contrast": f"protected-{operation}-contrast", "synthesis_evidence": ["synthesis", "development"], "structure_trace": "structure_search.parquet", "parameter_trace": "parameter_search.parquet", "rollback_target": parents[0]},
        operation_payload=payload,
        integrity_control=integrity_control,
        certification_control=certification_control,
    )
    candidate.validate()
    return candidate


def _initial_parameters(operation_index: int, variant_index: int) -> dict[str, float]:
    return {
        "threshold": 0.30 + 0.05 * ((operation_index + variant_index) % 7),
        "weight": 0.80 + 0.10 * (variant_index % 3),
        "availability_floor": 0.50,
        "interaction": 0.50,
        "persistence_floor": 0.50,
        "masking_floor": 0.50,
        "trust_floor": 0.50,
        "safe_ceiling": 0.50,
        "scope_lower": 0.25,
        "scope_upper": 0.75,
        "anti_scope_upper": 0.10,
    }


def _retarget_trace(traces: list[dict[str, Any]], candidate_id: str) -> list[dict[str, Any]]:
    return [{**trace, "candidate_id": candidate_id} for trace in traces]
