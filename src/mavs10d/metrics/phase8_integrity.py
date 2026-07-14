"""Independent metric and causal-contrast helpers for Phase 8."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from mavs10d.core.hashing import stable_hash


def evaluate_terminal_records(records: pd.DataFrame, truth: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    evaluated = records.merge(
        truth[["case_id", "truth_unsafe", "expected_terminal", "fully_observable_core", "known_irreducible"]],
        on="case_id", validate="many_to_one",
    )
    evaluated["unsafe_acceptance"] = evaluated["truth_unsafe"].astype(bool) & (evaluated["terminal_action"] == "ACCEPT")
    evaluated["false_rejection"] = ~evaluated["truth_unsafe"].astype(bool) & (evaluated["terminal_action"] == "REJECT")
    evaluated["closure_error"] = evaluated["terminal_action"] != evaluated["expected_terminal"]
    unsafe_total = int(evaluated["truth_unsafe"].sum())
    safe_total = int((~evaluated["truth_unsafe"].astype(bool)).sum())
    unresolved_initial = int((evaluated["family"] != "immediately_separable").sum())
    metrics = {
        "case_count": float(len(evaluated)),
        "unsafe_total": float(unsafe_total),
        "safe_total": float(safe_total),
        "unsafe_acceptance_count": float(evaluated["unsafe_acceptance"].sum()),
        "false_rejection_count": float(evaluated["false_rejection"].sum()),
        "uar": float(evaluated["unsafe_acceptance"].sum() / unsafe_total) if unsafe_total else 0.0,
        "frr": float(evaluated["false_rejection"].sum() / safe_total) if safe_total else 0.0,
        "residual_escalation": float(evaluated["external_escalate"].mean()),
        "residual_escalation_count": float(evaluated["external_escalate"].sum()),
        "initial_unresolved": float(unresolved_initial),
        "local_resolution": float(unresolved_initial - evaluated["external_escalate"].sum()),
        "closure_error": float(evaluated["closure_error"].mean()),
        "rounds": float(evaluated["rounds"].mean()),
        "query_count": float(evaluated["query_count"].mean()),
        "query_yield": float(evaluated["query_yield"].mean()),
        "scope_leakage": float(evaluated["scope_leakage"].sum()),
        "active_basis": float(evaluated["active_basis"].median()),
        "active_basis_max": float(evaluated["active_basis"].max()),
        "irrelevant_activation": float(evaluated["irrelevant_activation"].sum()),
        "meta_signal_hard_veto": float(evaluated["meta_hard_veto"].sum()),
        "uncertified_composition_influence": float(evaluated["uncertified_interaction"].sum()),
        "additive_severity_use": float(evaluated["additive_severity_used"].sum()),
        "uncertified_terminal_count": float(((evaluated["terminal_action"].isin(["ACCEPT", "REJECT"])) & ~evaluated["certificate_present"].astype(bool)).sum()),
        "oracle_access_count": float(evaluated["oracle_access"].sum()),
    }
    return evaluated, metrics


def evaluate_persistence_records(records: pd.DataFrame, truth: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    evaluated = records.merge(truth[["case_id", "truth_unsafe", "expected_terminal"]], on="case_id", validate="many_to_one")
    evaluated["unsafe_acceptance"] = evaluated["truth_unsafe"].astype(bool) & (evaluated["terminal_action"] == "ACCEPT")
    evaluated["false_rejection"] = ~evaluated["truth_unsafe"].astype(bool) & (evaluated["terminal_action"] == "REJECT")
    metrics = {
        "case_count": float(len(evaluated)),
        "uar": float(evaluated["unsafe_acceptance"].sum() / max(1, evaluated["truth_unsafe"].sum())),
        "frr": float(evaluated["false_rejection"].sum() / max(1, (~evaluated["truth_unsafe"].astype(bool)).sum())),
        "residual_escalation": float(evaluated["external_escalate"].mean()),
        "rounds": float(evaluated["rounds"].mean()),
        "query_count": float(evaluated["query_count"].mean()),
        "query_yield": float(evaluated["query_yield"].mean()),
        "memory_hit_rate": float(evaluated["memory_hit"].mean()),
        "discovery_rounds": float(evaluated["discovery_rounds"].mean()),
        "synthesis_count": float(evaluated["synthesis_count"].sum()),
        "library_size": float(evaluated["library_size"].max()),
        "active_basis": float(evaluated["active_basis"].median()),
        "active_basis_max": float(evaluated["active_basis"].max()),
        "redundancy": float(evaluated["redundancy"].sum()),
        "retrieval_cost": float(evaluated["retrieval_cost"].mean()),
        "scope_leakage": float(evaluated["scope_leakage"].sum()),
        "repeated_failed_paths": float(evaluated["repeated_failed_path"].sum()),
        "stale_scope_activation": float(evaluated["stale_scope_activation"].sum()),
        "quarantine_or_rollback": float(evaluated["quarantine_or_rollback"].sum()),
    }
    for generation in (1, 2, 3):
        subset = evaluated[evaluated["generation"] == generation]
        metrics[f"g{generation}_rounds"] = float(subset["rounds"].mean())
        metrics[f"g{generation}_memory_hit_rate"] = float(subset["memory_hit"].mean())
        metrics[f"g{generation}_scope_leakage"] = float(subset["scope_leakage"].sum())
    return evaluated, metrics


def phase4_diagnostic_replay(
    condition_id: str,
    traces: pd.DataFrame,
    oracle_truth: Mapping[str, bool] | None = None,
) -> list[dict[str, Any]]:
    """Replay the preserved legacy ambiguity band using visible risk and threshold only."""
    records: list[dict[str, Any]] = []
    for row in traces.itertuples(index=False):
        original = str(row.action).upper()
        terminal = original
        reason = "legacy_terminal_preserved"
        rounds = 0
        if original == "ESCALATE":
            margin = float(row.risk_score) - float(row.threshold)
            if condition_id in {"P1", "P11"}:
                terminal, reason = "ESCALATE", "resolver_bypassed"
            elif condition_id == "P12":
                terminal = "REJECT" if int(stable_hash({"risk": float(row.risk_score), "threshold": float(row.threshold), "world_seed": int(row.world_seed), "mode": "binary"})[:2], 16) % 2 else "ACCEPT"
                reason = "forced_binary"
            elif condition_id == "P13":
                terminal, reason = "REJECT", "reject_on_unknown"
            elif condition_id == "P15":
                if oracle_truth is None:
                    raise ValueError("The P15 legacy replay requires quarantined auditor truth.")
                terminal, reason = ("REJECT" if bool(oracle_truth[str(row.opportunity_id)]) else "ACCEPT"), "quarantined_oracle"
            elif condition_id in {"P7", "P8", "P14"}:
                terminal, reason = "REJECT", "broad_hard_veto"
            elif condition_id == "P10":
                terminal = "REJECT" if int(stable_hash({"risk": float(row.risk_score), "threshold": float(row.threshold), "world_seed": int(row.world_seed), "mode": "confidence"})[:2], 16) % 2 else "ACCEPT"
                reason = "uncertified_confidence"
            elif abs(margin) >= 0.08:
                terminal, reason, rounds = ("REJECT" if margin > 0 else "ACCEPT"), "visible_margin_extension", 1
            else:
                terminal, reason = "ESCALATE", "residual_ambiguity_band"
        record = {
            "condition_id": condition_id,
            "bank": "phase4_original_pre_rerun",
            "case_id": str(row.opportunity_id),
            "world_id": str(row.world_id),
            "generation": int(row.generation),
            "domain": str(row.domain),
            "reset_type": str(row.reset_type),
            "terminal_action": terminal,
            "terminal_reason": reason,
            "rounds": rounds,
            "original_escalated": int(bool(row.escalated)),
            "risk_score": float(row.risk_score),
            "threshold": float(row.threshold),
        }
        record["execution_hash"] = stable_hash({key: value for key, value in record.items() if key != "unsafe"})
        records.append(record)
    return records


def evaluate_phase4_replay(records: pd.DataFrame, truth: pd.DataFrame) -> dict[str, float]:
    evaluated = records.merge(truth[["case_id", "truth_unsafe"]], on="case_id", validate="one_to_one")
    unsafe = evaluated["truth_unsafe"].astype(bool)
    return {
        "phase4_case_count": float(len(evaluated)),
        "phase4_world_count": float(evaluated["world_id"].nunique()),
        "phase4_uar": float((unsafe & (evaluated["terminal_action"] == "ACCEPT")).sum() / max(1, unsafe.sum())),
        "phase4_frr": float(((~unsafe) & (evaluated["terminal_action"] == "REJECT")).sum() / max(1, (~unsafe).sum())),
        "phase4_residual_escalation": float((evaluated["terminal_action"] == "ESCALATE").mean()),
        "phase4_original_escalation": float(evaluated["original_escalated"].mean()),
        "phase4_rounds": float(evaluated["rounds"].mean()),
    }


def paired_deltas(reference: Mapping[str, Any], ablation: Mapping[str, Any]) -> dict[str, float]:
    return {
        key: float(ablation[key]) - float(reference[key])
        for key in sorted(set(reference) & set(ablation))
        if isinstance(reference[key], (int, float, np.integer, np.floating, bool))
        and isinstance(ablation[key], (int, float, np.integer, np.floating, bool))
    }


def deterministic_paired_interval(values: Iterable[float], seed: int, draws: int = 2000) -> dict[str, float]:
    array = np.asarray(list(values), dtype=float)
    if len(array) == 0:
        return {"mean": 0.0, "lower_95": 0.0, "upper_95": 0.0, "n": 0.0}
    rng = np.random.default_rng(seed)
    samples = array[rng.integers(0, len(array), size=(draws, len(array)))].mean(axis=1)
    return {
        "mean": float(array.mean()),
        "lower_95": float(np.quantile(samples, 0.025)),
        "upper_95": float(np.quantile(samples, 0.975)),
        "n": float(len(array)),
    }
