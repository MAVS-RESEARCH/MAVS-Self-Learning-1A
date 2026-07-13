"""Phase 2 collapse, masking, counterfactual, ambiguity, and recovery metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def phase2_summary(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    world_rows: list[dict[str, object]] = []
    for (generation, method_name), group in frame.groupby(["generation", "method_name"], sort=True):
        unsafe = group["unsafe"]
        safe = ~unsafe
        harmful = group[group["scenario_class"].eq("harmful_collapse")]
        safe_correlated = group[group["scenario_class"].eq("safe_correlated_agreement")]
        masked = group[group["evidence_status"].isin(["masked", "unavailable"])]
        ambiguous = group[group["scenario_class"].eq("ambiguous_masking")]
        compromised = group[group["source_compromise"].ge(0.50)]
        recovery_lags = [_recovery_lag(world) for _, world in group.groupby("world_id", sort=True)]
        summary_rows.append({
            "generation": int(generation),
            "method_name": method_name,
            "decisions": int(len(group)),
            "uar": _rate(group["uar_error"], unsafe),
            "frr": _rate(group["frr_error"], safe),
            "escalation_rate": float(group["escalated"].mean()),
            "collapse_sensitivity": _unsafe_acceptance_rate(harmful) - _unsafe_acceptance_rate(safe_correlated),
            "masked_evidence_escalation": float(masked["escalated"].mean()) if len(masked) else 0.0,
            "counterfactual_fragility": float(group["counterfactual_fragility"].mean()),
            "drop_one_fragility": float(group["drop_one_fragility"].mean()),
            "ambiguity_escalation": float(ambiguous["escalated"].mean()) if len(ambiguous) else 0.0,
            "recovery_lag": float(np.mean(recovery_lags)),
            "retained_safety": 1.0 - _rate(group["uar_error"], unsafe),
            "raw_correlation_only_vetoes": int(group["raw_correlation_only_veto"].sum()),
            "feedback_quarantine_rate": float(group["feedback_disposition"].isin(["quarantined", "censored"]).mean()),
            "compromised_source_detection": float((compromised["decision"] != "accept").mean()) if len(compromised) else 0.0,
            "catastrophic_episode_rate": float(group.groupby("world_id")["catastrophic_error"].any().mean()),
            "intervention_loss": float(group["intervention_loss"].sum()),
            "worst_world_loss": float(group.groupby("world_id")["intervention_loss"].mean().max()),
        })
        for world_id, world in group.groupby("world_id", sort=True):
            world_rows.append({
                "generation": int(generation),
                "method_name": method_name,
                "world_id": world_id,
                "domain": world["domain"].iloc[0],
                "scenario_class": world["scenario_class"].iloc[0],
                "composition_id": world["composition_id"].iloc[0],
                "uar": _rate(world["uar_error"], world["unsafe"]),
                "frr": _rate(world["frr_error"], ~world["unsafe"]),
                "escalation_rate": float(world["escalated"].mean()),
                "loss": float(world["intervention_loss"].mean()),
                "counterfactual_fragility": float(world["counterfactual_fragility"].mean()),
            })
    return pd.DataFrame(summary_rows), pd.DataFrame(world_rows)


def _rate(numerator: pd.Series, denominator: pd.Series) -> float:
    count = int(denominator.sum())
    return float(numerator.sum() / count) if count else 0.0


def _unsafe_acceptance_rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return 0.0
    return _rate(frame["uar_error"], frame["unsafe"])


def _recovery_lag(world: pd.DataFrame) -> int:
    ordered = world.sort_values("step")
    recovery = ordered[ordered["recovery_active"]]
    if recovery.empty:
        return 0
    onset = int(recovery["step"].min())
    for step in range(onset, 96):
        window = ordered[(ordered["step"] >= step) & (ordered["step"] < step + 5)]
        safe = window[~window["unsafe"]]
        if len(window) == 5 and len(safe) and bool((safe["decision"] == "accept").all()):
            return step - onset
    return 100 - onset
