"""Feedback-aware autonomous-repair metrics for WorkPlan Phase 3."""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def phase3_summary(traces: pd.DataFrame, repair_events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    curriculum_rows = _curriculum_metrics(traces, repair_events)
    summary_rows: list[dict[str, float | int | str]] = []
    for (generation, condition), group in curriculum_rows.groupby(["generation", "condition"], sort=True):
        event_group = repair_events[(repair_events["generation"] == generation) & (repair_events["condition"] == condition)]
        trace_group = traces[(traces["generation"] == generation) & (traces["condition"] == condition)]
        proposals = int(event_group["candidates_evaluated"].sum())
        beneficial = int(event_group["beneficial_candidates"].sum())
        promoted = int(event_group["candidates_promoted"].sum())
        beneficial_promoted = int(event_group["beneficial_promoted"].sum())
        harmful = int(event_group["harmful_candidates"].sum())
        harmful_promoted = int(event_group["harmful_promoted"].sum())
        recurrence_errors = int(event_group["recurrence_errors"].sum())
        recurrence_exposures = int(event_group["recurrence_exposures"].sum())
        rollbacks = int(event_group["rollback_challenges"].sum())
        rollback_correct = int(event_group["rollback_correct"].sum())
        unsafe_count = int(trace_group["unsafe"].sum())
        safe_count = int((~trace_group["unsafe"]).sum())
        summary_rows.append(
            {
                "generation": int(generation),
                "condition": str(condition),
                "canonical_decisions": int(len(trace_group)),
                "time_to_detection": float(group["time_to_detection"].mean()),
                "time_to_containment": float(group["time_to_containment"].mean()),
                "time_to_certified_repair": float(group["time_to_certified_repair"].mean()),
                "median_recurrence": float(group["recurrence_errors"].median()),
                "recurrence_rate": _ratio(recurrence_errors, recurrence_exposures),
                "escalation_contraction": float(group["escalation_contraction"].mean()),
                "certification_precision": _ratio(beneficial_promoted, promoted),
                "certification_recall": _ratio(beneficial_promoted, beneficial),
                "beneficial_proposal_yield": _ratio(beneficial, proposals),
                "harmful_proposal_rate": _ratio(harmful, proposals),
                "harmful_promotion_rate": _ratio(harmful_promoted, promoted),
                "rollback_correctness": _ratio(rollback_correct, rollbacks),
                "perception_gain": float(group["perception_gain"].mean()),
                "scope_leakage": float(group["scope_leakage"].mean()),
                "active_library_complexity": float(event_group["active_library_size"].max()),
                "total_library_complexity": float(event_group["total_library_size"].max()),
                "rejected_candidates": int(event_group["rejected_candidates"].sum()),
                "uar": _ratio(int(trace_group["uar_error"].sum()), unsafe_count),
                "frr": _ratio(int(trace_group["frr_error"].sum()), safe_count),
                "escalation_rate": _ratio(int(trace_group["escalated"].sum()), len(trace_group)),
                "query_rate": _ratio(int(trace_group["query_used"].sum()), len(trace_group)),
                "trace_completeness": float(trace_group["trace_lineage_sha256"].notna().mean()),
            }
        )
    return pd.DataFrame(summary_rows), curriculum_rows


def _curriculum_metrics(traces: pd.DataFrame, repair_events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for event in repair_events.to_dict(orient="records"):
        group = traces[
            (traces["generation"] == event["generation"])
            & (traces["condition"] == event["condition"])
            & (traces["curriculum_id"] == event["curriculum_id"])
        ]
        pre = group[group["curriculum_step"] < int(event["promotion_step"])]
        post = group[(group["curriculum_step"] >= int(event["promotion_step"])) & (group["stage"] == "recurrence")]
        rows.append(
            {
                "generation": int(event["generation"]),
                "condition": str(event["condition"]),
                "curriculum_id": str(event["curriculum_id"]),
                "operation": str(event["operation"]),
                "time_to_detection": float(int(event["detection_step"]) - int(event["first_trigger_eligible_step"])),
                "time_to_containment": float(int(event["containment_step"]) - int(event["detection_step"])),
                "time_to_certified_repair": float(int(event["promotion_step"]) - int(event["detection_step"])),
                "recurrence_errors": int(event["recurrence_errors"]),
                "recurrence_exposures": int(event["recurrence_exposures"]),
                "recurrence_rate": _ratio(int(event["recurrence_errors"]), int(event["recurrence_exposures"])),
                "escalation_contraction": _ratio(int(pre["escalated"].sum()), len(pre)) - _ratio(int(post["escalated"].sum()), len(post)),
                "perception_gain": float(event["perception_gain"]),
                "scope_leakage": float(event["scope_leakage"]),
                "uar": _ratio(int(group["uar_error"].sum()), int(group["unsafe"].sum())),
                "frr": _ratio(int(group["frr_error"].sum()), int((~group["unsafe"]).sum())),
            }
        )
    return pd.DataFrame(rows)


def rejected_candidate_inventory(records: Iterable[dict]) -> pd.DataFrame:
    rows = list(records)
    return pd.DataFrame(rows).sort_values(["generation", "condition", "curriculum_id", "candidate_id"]).reset_index(drop=True) if rows else pd.DataFrame()


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0
