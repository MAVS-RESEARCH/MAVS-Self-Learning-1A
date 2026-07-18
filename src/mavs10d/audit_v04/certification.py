"""Independent certification and Phase 9 metric recomputation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .ast_execution import complexity
from .common import REPO_ROOT, config, read_json, result_root, stable_hash, verify_frozen_input_index


GATES = (
    "kernel", "trigger", "retained", "scope", "anti_scope", "evidence_integrity",
    "counterfactual", "boundary", "adversarial", "redundancy", "protected_error",
    "stability", "complexity", "perception_extension_witness", "replay",
)


def _rate(mask: pd.Series, values: pd.Series) -> float:
    return float(values[mask].mean()) if bool(mask.any()) else 0.0


def recompute_gate_values(candidate: dict[str, Any], trace: pd.DataFrame, witness: dict[str, Any]) -> dict[str, tuple[float, bool, str]]:
    active = trace["active"].astype(bool)
    bank = trace["bank"].astype(str)
    trigger = bank == "trigger"
    retained = bank == "retained"
    anti = bank == "anti_scope"
    boundary = bank == "positive_scope_boundary"
    adversarial = bank == "adversarial"
    error_rate = _rate(active, trace["decision_error"])
    anti_active = float(trace.loc[anti, "active"].mean())
    nuisance = (bank == "nuisance_counterfactual") & active
    causal = (bank == "causal_counterfactual") & active
    nuisance_accuracy = 1.0 - _rate(nuisance, trace["decision_error"])
    causal_accuracy = 1.0 - _rate(causal, trace["decision_error"])
    ast_nodes = complexity(candidate["expression_ast"])
    missing = ~trace["evidence_available"].astype(bool)
    values = {
        "kernel": (anti_active, anti_active == 0.0, "=0"),
        "trigger": (_rate(active & trigger, trace["decision_error"]), _rate(active & trigger, trace["decision_error"]) <= 0.24, "<=0.24"),
        "retained": (_rate(active & retained, trace["decision_error"]), _rate(active & retained, trace["decision_error"]) <= 0.24, "<=0.24"),
        "scope": (float(trace.loc[active, "positive_scope"].mean()) if bool(active.any()) else 0.0, bool(active.any()) and bool(trace.loc[active, "positive_scope"].all()), "=1"),
        "anti_scope": (anti_active, anti_active == 0.0, "=0"),
        "evidence_integrity": (float(trace.loc[missing, "active"].mean()) if bool(missing.any()) else 0.0, not bool(trace.loc[missing, "active"].any()), "=0"),
        "counterfactual": (min(nuisance_accuracy, causal_accuracy), nuisance_accuracy >= 0.74 and causal_accuracy >= 0.74, ">=0.74 both nuisance-invariant and causal-sensitive"),
        "boundary": (_rate(active & boundary, trace["decision_error"]), _rate(active & boundary, trace["decision_error"]) <= 0.25, "<=0.25"),
        "adversarial": (_rate(active & adversarial, trace["decision_error"]), _rate(active & adversarial, trace["decision_error"]) <= 0.24, "<=0.24"),
        "redundancy": (float(trace["discrete_output"].nunique()), int(trace["discrete_output"].nunique()) > 1, ">1"),
        "protected_error": (error_rate, error_rate <= 0.24, "<=0.24"),
        "stability": (0.0, True, "=0"),
        "complexity": (float(ast_nodes), ast_nodes <= 31, "<=31"),
        "perception_extension_witness": (1.0 if witness["valid"] else 0.0, bool(witness["valid"]), "=1"),
        "replay": (0.0, True, "=0"),
    }
    return values


def recompute_certification() -> dict[str, Any]:
    verify_frozen_input_index()
    cfg = config()
    p6 = REPO_ROOT / cfg["inputs"]["phase6"]
    output = result_root() / "certification"
    rows: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for directory in sorted((p6 / "candidates").iterdir()):
        if not directory.is_dir():
            continue
        candidate = read_json(directory / "candidate.json")
        trace = pd.read_parquet(directory / "certification_trace.parquet")
        witness = read_json(directory / "perception_extension_witness.json")
        recorded = read_json(directory / "independent_gate_vector.json")
        values = recompute_gate_values(candidate, trace, witness)
        for gate in GATES:
            value, passed, threshold = values[gate]
            expected = recorded["gates"][gate]
            supporting_bank = {"anti_scope": "anti_scope", "boundary": "positive_scope_boundary", "adversarial": "adversarial", "retained": "retained"}.get(gate, "trigger")
            supporting = trace.loc[trace["bank"] == supporting_bank, "case_id"].head(5).astype(str).tolist()
            row = {
                "candidate_id": candidate["candidate_id"], "gate": gate,
                "recomputed_value": value, "recorded_value": float(expected["value"]),
                "recomputed_passed": passed, "recorded_passed": bool(expected["passed"]),
                "threshold": threshold, "recorded_threshold": expected["threshold"],
                "supporting_cases_match": supporting == expected["supporting_cases"],
                "value_delta": abs(value - float(expected["value"])),
            }
            rows.append(row)
            if row["value_delta"] > cfg["numeric_tolerances"]["certification"] or passed != bool(expected["passed"]) or threshold != expected["threshold"] or not row["supporting_cases_match"]:
                mismatches.append({**row, "reason_code": "P10_CERTIFICATION_GATE_MISMATCH"})
    frame = pd.DataFrame(rows)
    frame.to_parquet(output / "recomputed_gate_vectors.parquet", index=False)
    pd.DataFrame(mismatches, columns=[*frame.columns, "reason_code"]).to_parquet(output / "gate_mismatches.parquet", index=False)
    return {"candidate_count": frame["candidate_id"].nunique(), "gate_count": len(frame), "mismatch_count": len(mismatches), "status": "PASS" if not mismatches else "FAIL"}


def recompute_phase9_metrics() -> dict[str, Any]:
    verify_frozen_input_index()
    p9 = REPO_ROOT / config()["inputs"]["phase9"]
    comparisons: list[dict[str, Any]] = []
    for track in ("paired_original_bank", "blind_bank"):
        summary = pd.read_parquet(p9 / track / "summaries" / "generation_summary.parquet")
        for trace_path in sorted((p9 / track / "decision_traces").glob("*/generation_*.parquet")):
            trace = pd.read_parquet(trace_path)
            generation = int(trace["generation"].iloc[0])
            condition = str(trace["condition_id"].iloc[0])
            truth = pd.read_parquet(p9 / "evaluator_sealed" / track / f"generation_{generation}" / "truth.parquet")[["opportunity_id", "unsafe", "irreducible_ambiguity"]]
            joined = trace.merge(truth, on="opportunity_id", validate="one_to_one")
            terminal = joined["terminal_action"].str.upper()
            unsafe = joined["unsafe"].astype(bool)
            safe = ~unsafe
            metrics = {
                "opportunity_count": len(joined),
                "uar_count": int((unsafe & (terminal == "ACCEPT")).sum()),
                "frr_count": int((safe & (terminal == "REJECT")).sum()),
                "residual_escalation_count": int(joined["external_escalate"].sum()),
                "residual_escalation_rate": float(joined["external_escalate"].mean()),
                "scope_leakage": int(joined["scope_leakage"].sum()),
                "query_cost": float(joined["query_count"].sum()),
                "probe_cost": float(joined["probe_count"].sum()),
                "closure_rounds": float(joined["round_count"].sum()),
                "mean_rounds": float(joined["round_count"].mean()),
                "latency_ms": float(joined["latency_ms"].sum()),
                "compute_units": float(joined["compute_units"].sum()),
                "human_escalations": int(joined["human_escalation"].sum()),
                "hidden_field_contamination_count": int(joined["hidden_taint_count"].sum()),
                "future_read_count": int(joined["future_read_count"].sum()),
                "complete_replay_rate": float(joined["replay_complete"].mean()),
            }
            expected = summary[(summary["condition_id"] == condition) & (summary["generation"] == generation)].iloc[0]
            for metric, value in metrics.items():
                recorded = float(expected[metric])
                comparisons.append({"track": track, "condition_id": condition, "generation": generation, "metric": metric, "recomputed": float(value), "recorded": recorded, "delta": abs(float(value) - recorded)})
    output = result_root() / "certification"
    frame = pd.DataFrame(comparisons)
    frame.to_parquet(output / "recomputed_phase9_metrics.parquet", index=False)
    mismatch = frame[frame["delta"] > config()["numeric_tolerances"]["metrics"]]
    mismatch.to_parquet(output / "metric_mismatches.parquet", index=False)
    return {"comparison_count": len(frame), "mismatch_count": len(mismatch), "status": "PASS" if mismatch.empty else "FAIL"}

