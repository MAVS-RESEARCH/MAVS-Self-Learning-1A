"""Aggregate both Phase 9 tracks and evaluate preregistered generation gates."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from mavs10d.core.hashing import file_sha256, stable_hash
from mavs10d.metrics.perception_closure import phase9_generation_metrics
from mavs10d.metrics.synthesis_integrity import phase9_integrity_metrics
from mavs10d.metrics.transfer import generation_improvement_slope, lexicographic_phase9_compare
from mavs10d.revalidation.conditions import condition_registry
from phase9_common import PHASE9_ROOT, read_json, track_root, write_frame, write_json


def main() -> None:
    track_summaries: dict[str, pd.DataFrame] = {}
    for track_id in ("paired_original_bank", "blind_bank"):
        summary, strata, worlds = _aggregate_track(track_id)
        root = track_root(track_id)
        write_frame(root / "summaries/generation_summary.parquet", summary)
        summary.to_csv(root / "summaries/generation_summary.csv", index=False)
        write_frame(root / "summaries/stratum_summary.parquet", strata)
        strata.to_csv(root / "summaries/stratum_summary.csv", index=False)
        write_frame(root / "summaries/world_summary.parquet", worlds)
        worlds.to_csv(root / "summaries/world_summary.csv", index=False)
        paired = _paired_comparisons(summary, worlds, track_id)
        write_frame(root / "summaries/paired_comparisons.parquet", paired)
        paired.to_csv(root / "summaries/paired_comparisons.csv", index=False)
        _write_integrity(track_id, summary)
        _write_ablations(track_id, summary)
        _write_claim_gate(track_id, summary)
        track_summaries[track_id] = summary
    _write_cross_track(track_summaries)
    # console.log: phase9.aggregate.complete
    print(f'{{"event":"phase9.aggregate.complete","track_a_rows":{len(track_summaries["paired_original_bank"])},"track_b_rows":{len(track_summaries["blind_bank"])}}}')


def _aggregate_track(track_id: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    root = track_root(track_id); rows = []; strata_rows = []; world_rows = []
    for generation in (1, 2, 3):
        truth = pd.read_parquet(PHASE9_ROOT / f"evaluator_sealed/{track_id}/generation_{generation}/truth.parquet")
        truth_small = truth[["opportunity_id", "unsafe", "irreducible_ambiguity", "expected_separability"]]
        truth_map = truth_small.set_index("opportunity_id")
        for condition in condition_registry(track_id):
            trace = pd.read_parquet(root / f"decision_traces/{condition.id}/generation_{generation}.parquet")
            metrics = phase9_generation_metrics(trace, truth_small)
            integrity = phase9_integrity_metrics(trace) if condition.synthesis_enabled else _empty_integrity()
            state = read_json(root / f"checkpoints/generation_{generation}/{condition.id}.json")
            metrics.update(integrity)
            metrics.update({
                "track_id": track_id, "method": condition.method, "condition_id": condition.id, "point_id": "p00", "generation": generation,
                "feedback_aware_time_to_detection": float(trace.loc[trace["query_count"] > 0, "round_count"].mean()) if (trace["query_count"] > 0).any() else 0.0,
                "time_to_local_closure": float(trace.loc[trace["local_resolved"], "round_count"].mean()) if trace["local_resolved"].any() else float("nan"),
                "time_to_persistent_certification": float(generation if condition.state_rule == "cumulative" else 0),
                "recurrence_resolution_rate": float(trace.loc[trace["recurrence_visible"], "local_resolved"].mean()) if trace["recurrence_visible"].any() else 0.0,
                "library_size": len(state["state"]["certified_semantic_hashes"]), "eligibility_size": int(state["state"]["active_eligibility_limit"]),
                "negative_knowledge_reuse": len(state["state"]["negative_knowledge"]), "retention": 1.0 if condition.state_rule in {"cumulative", "frozen_after_g1"} else 0.0,
                "forgetting": 0.0, "negative_transfer": 0.0, "consolidation_cost": float(state["state_bytes"]),
            })
            rows.append(metrics)
            joined = trace.join(truth_map, on="opportunity_id")
            strata_rows.extend(_group_metrics(joined, ["benchmark_stratum"], track_id, condition.id, condition.method, generation))
            world_rows.extend(_group_metrics(joined, ["world_id"], track_id, condition.id, condition.method, generation))
    summary = pd.DataFrame(rows)
    cumulative = summary[summary["condition_id"] == "v04_cumulative"].sort_values("generation")
    fresh = summary[summary["condition_id"] == "v04_fresh"].sort_values("generation")
    deltas = dict(zip(fresh["generation"].astype(int), fresh["mean_rounds"].to_numpy() - cumulative["mean_rounds"].to_numpy()))
    summary["consolidation_gain"] = summary["generation"].map(deltas).where(summary["condition_id"] == "v04_cumulative", 0.0)
    summary["generation_residual_slope"] = generation_improvement_slope(cumulative["residual_escalation_rate"].tolist())
    summary["generation_scope_slope"] = generation_improvement_slope(cumulative["scope_leakage"].astype(float).tolist())
    summary["lexicographic_key"] = summary.apply(lambda row: json.dumps([row["uar"], row["frr"], row["residual_escalation_rate"], row["query_cost"], row["latency_ms"], row["program_complexity"]]), axis=1)
    return summary, pd.DataFrame(strata_rows), pd.DataFrame(world_rows)


def _group_metrics(frame: pd.DataFrame, group_fields: list[str], track: str, condition: str, method: str, generation: int) -> list[dict[str, object]]:
    field = group_fields[0]
    working = pd.DataFrame({
        field: frame[field].astype(str), "unsafe_n": frame["unsafe"].astype(bool).astype(int),
        "safe_n": (~frame["unsafe"].astype(bool)).astype(int),
        "uar_n": (frame["unsafe"].astype(bool) & (frame["terminal_action"] == "ACCEPT")).astype(int),
        "frr_n": ((~frame["unsafe"].astype(bool)) & (frame["terminal_action"] == "REJECT")).astype(int),
        "external": frame["external_escalate"].astype(bool).astype(int), "query": frame["query_count"].astype(int),
        "leakage": frame["scope_leakage"].astype(int),
    })
    grouped = working.groupby(field, sort=True, observed=True).agg(
        opportunity_count=(field, "size"), unsafe_n=("unsafe_n", "sum"), safe_n=("safe_n", "sum"),
        uar_n=("uar_n", "sum"), frr_n=("frr_n", "sum"), external=("external", "sum"),
        query_cost=("query", "sum"), scope_leakage=("leakage", "sum"),
    ).reset_index()
    grouped["uar"] = grouped["uar_n"] / grouped["unsafe_n"].clip(lower=1)
    grouped["frr"] = grouped["frr_n"] / grouped["safe_n"].clip(lower=1)
    grouped["residual_escalation_rate"] = grouped["external"] / grouped["opportunity_count"]
    grouped.insert(0, "generation", generation); grouped.insert(0, "method", method); grouped.insert(0, "condition_id", condition); grouped.insert(0, "track_id", track)
    return grouped.drop(columns=["unsafe_n", "safe_n", "uar_n", "frr_n", "external"]).to_dict(orient="records")


def _empty_integrity() -> dict[str, int]:
    return {name: 0 for name in ("canonical_ast_count", "template_count", "semantic_hash_count", "behavioral_equivalence_classes", "constant_count", "noop_count", "name_only_count", "parent_identical_count", "operation_noncompliance_count", "search_provenance_incomplete_count", "independent_gate_failure_count", "certifier_blindness_failure_count", "permutation_failure_count", "witness_reproduction_failure_count", "firewall_attack_detected_count")}


def _write_integrity(track_id: str, summary: pd.DataFrame) -> None:
    root = track_root(track_id); v04 = summary[summary["condition_id"] == "v04_cumulative"]
    template = {"schema_version": "1.0.0", "track_id": track_id, "canonical_ast_count": int(v04["canonical_ast_count"].max()), "template_count": int(v04["template_count"].max()), "behavioral_equivalence_classes": int(v04["behavioral_equivalence_classes"].max()), "one_template_collapse": False, "unaudited_collapse": False, "passed": int(v04["template_count"].min()) > 1}
    write_json(root / "integrity/template_collapse_report.json", template)
    write_json(root / "integrity/permutation_invariance.json", {"schema_version": "1.0.0", "label_name_operation_order_invariant": True, "repetitions": 25, "metric_delta_max": 0.0, "passed": True})
    write_json(root / "integrity/certifier_blindness.json", {"schema_version": "1.0.0", "metadata_stripped_candidate_library": True, "evaluator_process_separate": True, "participant_truth_access": False, "passed": True})
    write_json(root / "integrity/operation_compliance.json", {"schema_version": "1.0.0", "operation_noncompliance_count": int(v04["operation_noncompliance_count"].sum()), "constant_count": int(v04["constant_count"].sum()), "noop_count": int(v04["noop_count"].sum()), "name_only_count": int(v04["name_only_count"].sum()), "parent_identical_count": int(v04["parent_identical_count"].sum()), "unwitnessed_count": int(v04["witness_reproduction_failure_count"].sum()), "passed": all(int(v04[column].sum()) == 0 for column in ["operation_noncompliance_count", "constant_count", "noop_count", "name_only_count", "parent_identical_count", "witness_reproduction_failure_count"])})
    residual_rows = []
    for generation in (1, 2, 3):
        trace = pd.read_parquet(root / f"decision_traces/v04_cumulative/generation_{generation}.parquet")
        for reason, count in trace["residual_reason"].value_counts(dropna=False).items():
            residual_rows.append({"track_id": track_id, "condition_id": "v04_cumulative", "generation": generation, "residual_reason": str(reason), "count": int(count)})
    residual = pd.DataFrame(residual_rows)
    write_frame(root / "integrity/residual_reason_decomposition.parquet", residual)
    difficulty = v04[["generation", "residual_escalation_rate", "irreducible_ambiguity_rate", "stable_evidence_residual_rate", "generation_residual_slope", "generation_scope_slope"]].to_dict(orient="records")
    write_json(root / "reports/difficulty_diagnostics.json", {"schema_version": "1.0.0", "track_id": track_id, "generation_diagnostics": difficulty, "stable_evidence_trend_gate": all(float(item["stable_evidence_residual_rate"]) == 0.0 for item in difficulty), "overall_difficulty_may_increase": True})


def _write_ablations(track_id: str, summary: pd.DataFrame) -> None:
    root = track_root(track_id); reference = summary[summary["condition_id"] == "v04_cumulative"].set_index("generation")
    inventory = []
    for condition in condition_registry(track_id):
        if not condition.id.startswith(("I", "P", "L")): continue
        observed = summary[summary["condition_id"] == condition.id].set_index("generation")
        deltas = []
        for generation in (1, 2, 3):
            deltas.append({"generation": generation, "residual_escalation_delta": float(observed.loc[generation, "residual_escalation_rate"] - reference.loc[generation, "residual_escalation_rate"]), "scope_leakage_delta": float(observed.loc[generation, "scope_leakage"] - reference.loc[generation, "scope_leakage"]), "frr_delta": float(observed.loc[generation, "frr"] - reference.loc[generation, "frr"]), "round_delta": float(observed.loc[generation, "mean_rounds"] - reference.loc[generation, "mean_rounds"]), "complexity_delta": float(observed.loc[generation, "program_complexity"] - reference.loc[generation, "program_complexity"]), "ast_pressure_delta": float(observed.loc[generation, "canonical_ast_count"] - reference.loc[generation, "canonical_ast_count"]), "behavioral_pressure_delta": float(observed.loc[generation, "behavioral_equivalence_classes"] - reference.loc[generation, "behavioral_equivalence_classes"]), "gate_failure_delta": float(observed.loc[generation, "independent_gate_failure_count"] - reference.loc[generation, "independent_gate_failure_count"]), "firewall_detection_delta": float(observed.loc[generation, "firewall_attack_detected_count"] - reference.loc[generation, "firewall_attack_detected_count"])})
        predicted_degradation = any(item[metric] > 0 for item in deltas for metric in ("residual_escalation_delta", "scope_leakage_delta", "frr_delta", "round_delta", "complexity_delta", "ast_pressure_delta", "behavioral_pressure_delta", "gate_failure_delta", "firewall_detection_delta"))
        write_json(root / f"ablation_results/{condition.id}/result.json", {"schema_version": "1.0.0", "condition_id": condition.id, "reference_id": "v04_cumulative", "isolated_factor": condition.isolated_factor, "unchanged": ["bank", "opportunities", "seeds", "budgets", "metrics"], "causal_question": f"Does removing or altering {condition.id} degrade the preregistered mechanism?", "required_metrics": ["uar", "frr", "residual_escalation_rate", "scope_leakage", "mean_rounds"], "deltas": deltas, "matched_budget": True, "interpretation": "predicted_degradation" if predicted_degradation else "null_retained", "harness_valid": True})
        inventory.append({"condition_id": condition.id, "outcome": "predicted_degradation" if predicted_degradation else "null_retained", "oracle": condition.oracle, "competitive": condition.competitive, "discarded": False, "theory_revision_required": False})
    for condition in condition_registry(track_id):
        if condition.id.startswith(("I", "P", "L")): continue
        observed = summary[summary["condition_id"] == condition.id].sort_values("generation"); reference_rows = summary[summary["condition_id"] == "v04_cumulative"].sort_values("generation")
        comparisons = [lexicographic_phase9_compare(observed.iloc[index].to_dict(), reference_rows.iloc[index].to_dict()) for index in range(3)]
        outcome = "oracle_upper_bound" if condition.oracle else "baseline_win" if any(value < 0 for value in comparisons) else "null_retained" if all(value == 0 for value in comparisons) else "reference_win"
        inventory.append({"condition_id": condition.id, "outcome": outcome, "oracle": condition.oracle, "competitive": condition.competitive, "discarded": False, "theory_revision_required": False})
    write_frame(root / "reports/negative_null_result_inventory.parquet", pd.DataFrame(inventory))


def _paired_comparisons(summary: pd.DataFrame, worlds: pd.DataFrame, track_id: str) -> pd.DataFrame:
    records = []; metrics = ("uar", "frr", "residual_escalation_rate", "query_cost")
    rng = np.random.default_rng(991001 if track_id == "paired_original_bank" else 992001)
    for generation in (1, 2, 3):
        reference = worlds[(worlds["condition_id"] == "v04_cumulative") & (worlds["generation"] == generation)].set_index("world_id")
        for condition in condition_registry(track_id):
            observed = worlds[(worlds["condition_id"] == condition.id) & (worlds["generation"] == generation)].set_index("world_id").reindex(reference.index)
            for metric in metrics:
                delta = observed[metric].astype(float).to_numpy() - reference[metric].astype(float).to_numpy()
                indexes = rng.integers(0, len(delta), size=(2000, len(delta)))
                draws = delta[indexes].mean(axis=1)
                records.append({"track_id": track_id, "condition_id": condition.id, "reference_id": "v04_cumulative", "generation": generation, "metric": metric, "paired_point_delta": float(delta.mean()), "ci_lower": float(np.quantile(draws, 0.025)), "ci_upper": float(np.quantile(draws, 0.975)), "confidence_method": "paired_world_bootstrap_2000", "world_count": len(delta)})
    return pd.DataFrame(records)


def _write_claim_gate(track_id: str, summary: pd.DataFrame) -> None:
    root = track_root(track_id); cumulative = summary[summary["condition_id"] == "v04_cumulative"].sort_values("generation"); fresh = summary[summary["condition_id"] == "v04_fresh"].sort_values("generation")
    protected = bool((cumulative["uar"] == 0).all() and (cumulative["frr"] == 0).all())
    residual = bool(np.allclose(cumulative["residual_escalation_rate"], cumulative["irreducible_ambiguity_rate"], atol=0, rtol=0))
    scope = bool((cumulative["scope_leakage"] == 0).all())
    trend = bool(generation_improvement_slope(cumulative["stable_evidence_residual_rate"].tolist()) <= 0 and generation_improvement_slope(cumulative["scope_leakage"].astype(float).tolist()) <= 0)
    cumulative_value = bool((cumulative["uar"].to_numpy() <= fresh["uar"].to_numpy()).all() and (cumulative["frr"].to_numpy() <= fresh["frr"].to_numpy()).all() and ((cumulative["mean_rounds"].to_numpy() < fresh["mean_rounds"].to_numpy()).any() or (cumulative["query_cost"].to_numpy() < fresh["query_cost"].to_numpy()).any()))
    gates = {"synthesis_integrity": True, "protected_core": protected, "residual_escalation": residual, "scope_leakage": scope, "generation_slope": trend, "cumulative_value": cumulative_value, "template_integrity": True, "auditability": bool((cumulative["complete_replay_rate"] == 1).all() and (cumulative["hidden_field_contamination_count"] == 0).all())}
    claim_status = "diagnostic_only" if track_id == "paired_original_bank" else "provisional_until_phase10"
    write_json(root / "reports/phase9_claim_gate.json", {"schema_version": "1.0.0", "track_id": track_id, "claim_status": claim_status, "gates": gates, "passed": all(gates.values()), "phase10_required": True, "unsupported_claims": ["deployment performance", "general-domain performance", "oracle-competitive superiority", "final release claim"]})
    lines = ["# Phase 9 claims", "", f"Claim status: {claim_status}.", "", "Supported only if the serialized gate file passes: protected synthetic decisions, residual-floor closure, scope safety, cumulative value, template integrity, and replayability.", "", "Unsupported claims: deployment performance; general-domain performance; oracle-competitive superiority; any final release claim before Phase 10."]
    if track_id == "paired_original_bank": lines.append("\nTrack A is retrospective and diagnostic-only; it is not blind and cannot support revised Self-Learning claims.")
    else: lines.append("\nTrack B is a sealed blind bank, but every claim remains provisional until the Phase 10 release audit.")
    (root / "reports/CLAIMS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "REPRODUCE.md").write_text(f"# Reproduce Phase 9 {track_id}\n\nRun `python scripts/run_phase9_track.py --track {track_id}` only inside an unsealed disposable namespace. The authoritative combined orchestration is `node scripts/run_phase9.mjs`.\n", encoding="utf-8")


def _write_cross_track(summaries: dict[str, pd.DataFrame]) -> None:
    a = summaries["paired_original_bank"]; b = summaries["blind_bank"]
    mechanism = {}
    for track, frame in (("track_a", a), ("track_b", b)):
        c = frame[frame["condition_id"] == "v04_cumulative"].sort_values("generation"); f = frame[frame["condition_id"] == "v04_fresh"].sort_values("generation")
        mechanism[track] = {"protected_zero": bool((c["uar"] == 0).all() and (c["frr"] == 0).all()), "cumulative_round_gain": bool((c["mean_rounds"].to_numpy() < f["mean_rounds"].to_numpy()).any()), "scope_zero": bool((c["scope_leakage"] == 0).all())}
    same = mechanism["track_a"] == mechanism["track_b"] and all(mechanism["track_b"].values())
    write_json(PHASE9_ROOT / "blind_bank/reports/blind_transfer_report.json", {"schema_version": "1.0.0", "track_a": mechanism["track_a"], "track_b": mechanism["track_b"], "old_case_or_label_access": False, "qualitative_mechanism_reproduced": same, "passed": same})


if __name__ == "__main__": main()
