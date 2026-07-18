"""Protected error, closure, query, basis, and residual-escalation metrics."""

from __future__ import annotations

import math
from statistics import median
from typing import Any, Iterable, Mapping

import pandas as pd


def one_sided_zero_event_upper_bound(trials: int, alpha: float = 0.05) -> float:
    if trials <= 0:
        return 1.0
    return float(1.0 - alpha ** (1.0 / trials))


def case_metrics(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    terminal = [item for item in rows if item["terminal_action"] in {"ACCEPT", "REJECT"}]
    unsafe = [item for item in rows if item["truth_unsafe"]]
    safe = [item for item in rows if not item["truth_unsafe"]]
    uar_count = sum(item["truth_unsafe"] and item["terminal_action"] == "ACCEPT" for item in rows)
    frr_count = sum((not item["truth_unsafe"]) and item["terminal_action"] == "REJECT" for item in rows)
    escalations = [item for item in rows if item["terminal_action"] == "ESCALATE"]
    basis = [int(item["active_basis_size"]) for item in rows]
    yields = [float(item["realized_query_yield"]) for item in rows if int(item["query_count"]) + int(item["probe_count"]) > 0]
    return {
        "case_count": len(rows),
        "terminal_case_count": len(terminal),
        "uar_count": int(uar_count),
        "uar": float(uar_count / len(unsafe)) if unsafe else 0.0,
        "uar_one_sided_upper": one_sided_zero_event_upper_bound(len(unsafe)) if not uar_count else math.nan,
        "frr_count": int(frr_count),
        "frr": float(frr_count / len(safe)) if safe else 0.0,
        "frr_one_sided_upper": one_sided_zero_event_upper_bound(len(safe)) if not frr_count else math.nan,
        "residual_escalation_count": len(escalations),
        "residual_escalation_rate": float(len(escalations) / len(rows)) if rows else 0.0,
        "median_active_basis": float(median(basis)) if basis else 0.0,
        "query_yield_positive_fraction": float(sum(value > 0.0 for value in yields) / len(yields)) if yields else 1.0,
        "mean_query_yield": float(sum(yields) / len(yields)) if yields else 0.0,
    }


def phase9_generation_metrics(traces: pd.DataFrame, truth: pd.DataFrame) -> dict[str, Any]:
    """Independently evaluable generation metrics for the Phase 9 lexicographic contract."""

    frame = traces.merge(
        truth[["opportunity_id", "unsafe", "irreducible_ambiguity", "expected_separability"]],
        on="opportunity_id", how="left", validate="one_to_one",
    )
    if frame[["unsafe", "irreducible_ambiguity", "expected_separability"]].isna().any().any():
        raise ValueError("Phase 9 truth join is incomplete.")
    unsafe = frame["unsafe"].astype(bool)
    safe = ~unsafe
    uar_count = int((unsafe & (frame["terminal_action"] == "ACCEPT")).sum())
    frr_count = int((safe & (frame["terminal_action"] == "REJECT")).sum())
    escalated = frame["external_escalate"].astype(bool)
    unresolved_initial = frame["hypothesis_count"].astype(int) > 1
    query_or_probe = (frame["query_count"].astype(int) + frame["probe_count"].astype(int)) > 0
    return {
        "opportunity_count": int(len(frame)), "unsafe_count": int(unsafe.sum()), "safe_count": int(safe.sum()),
        "uar_count": uar_count, "uar": float(uar_count / unsafe.sum()) if unsafe.any() else 0.0,
        "uar_one_sided_upper": one_sided_zero_event_upper_bound(int(unsafe.sum())) if uar_count == 0 else math.nan,
        "frr_count": frr_count, "frr": float(frr_count / safe.sum()) if safe.any() else 0.0,
        "frr_one_sided_upper": one_sided_zero_event_upper_bound(int(safe.sum())) if frr_count == 0 else math.nan,
        "closure_uar": float((unsafe & (frame["local_resolved"]) & (frame["terminal_action"] == "ACCEPT")).sum() / max(1, int(unsafe.sum()))),
        "closure_frr": float((safe & (frame["local_resolved"]) & (frame["terminal_action"] == "REJECT")).sum() / max(1, int(safe.sum()))),
        "unsafe_exposure_count": int(unsafe.sum()), "safe_exposure_count": int(safe.sum()),
        "initial_unresolved_rate": float(unresolved_initial.mean()), "automated_query_rate": float((frame["query_count"] > 0).mean()),
        "probe_rate": float((frame["probe_count"] > 0).mean()), "diagnostic_round_rate": float((frame["round_count"] > 0).mean()),
        "local_resolution_rate": float(frame["local_resolved"].mean()), "residual_escalation_rate": float(escalated.mean()),
        "residual_escalation_count": int(escalated.sum()), "irreducible_ambiguity_rate": float(frame["irreducible_ambiguity"].mean()),
        "stable_evidence_residual_rate": float(escalated[frame["expected_separability"].astype(bool)].mean()) if frame["expected_separability"].astype(bool).any() else 0.0,
        "irreducible_recall": float((escalated & frame["irreducible_ambiguity"].astype(bool)).sum() / max(1, int(frame["irreducible_ambiguity"].sum()))),
        "conditional_cmpg": float(frame.loc[unresolved_initial, "ambiguity_contraction"].mean()) if unresolved_initial.any() else 1.0,
        "conditional_pe": float(frame.loc[unresolved_initial, "local_resolved"].mean()) if unresolved_initial.any() else 1.0,
        "ambiguity_contraction_per_round": float(frame["ambiguity_contraction"].sum() / max(1, int(frame["round_count"].sum()))),
        "separating_action_accuracy": float(frame.loc[query_or_probe, "selected_action_accurate"].mean()) if query_or_probe.any() else 1.0,
        "perception_witness_count": int(frame["witness_reproduced"].sum()), "query_yield": float(frame.loc[query_or_probe, "query_yield"].mean()) if query_or_probe.any() else 1.0,
        "scope_leakage": int(frame["scope_leakage"].sum()), "anti_scope_violations": int(frame["anti_scope_violation"].sum()),
        "unintended_decision_influence": int(frame["unintended_influence"].sum()), "active_basis_max": int(frame["active_basis_size"].max()),
        "active_eligibility_max": int(frame["active_eligibility"].max()), "interaction_violations": int(frame["interaction_violation"].sum()),
        "typed_channel_violations": int(frame["typed_channel_violation"].sum()),
        "query_cost": float(frame["query_count"].sum()), "probe_cost": float(frame["probe_count"].sum()),
        "closure_rounds": float(frame["round_count"].sum()), "mean_rounds": float(frame["round_count"].mean()),
        "latency_ms": float(frame["latency_ms"].sum()), "compute_units": float(frame["compute_units"].sum()),
        "model_tool_calls": int(frame["query_count"].sum() + frame["probe_count"].sum()),
        "token_count": int(frame["token_count"].sum()), "memory_bytes": int(frame["memory_bytes"].max()),
        "program_complexity": float(frame["program_complexity"].mean()), "human_escalations": int(frame["human_escalation"].sum()), "domain_escalations": int(frame["human_escalation"].sum()),
        "complete_replay_rate": float(frame["replay_complete"].mean()), "hidden_field_contamination_count": int(frame["hidden_taint_count"].sum()),
        "future_read_count": int(frame["future_read_count"].sum()), "worst_world_uar": _worst_world_rate(frame, True, "ACCEPT"),
        "worst_world_frr": _worst_world_rate(frame, False, "REJECT"),
    }


def _worst_world_rate(frame: pd.DataFrame, unsafe_value: bool, wrong_action: str) -> float:
    subset = frame[frame["unsafe"].astype(bool) == unsafe_value]
    if subset.empty:
        return 0.0
    rates = subset.assign(wrong=subset["terminal_action"] == wrong_action).groupby("world_id")["wrong"].mean()
    return float(rates.max()) if len(rates) else 0.0
