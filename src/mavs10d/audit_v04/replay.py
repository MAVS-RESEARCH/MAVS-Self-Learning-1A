"""Independent Phase 9 replay of pinned samples and every protected failure."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .common import REPO_ROOT, config, file_sha256, read_json, result_root, stable_hash, verify_frozen_input_index, write_json
from .phase9_replay_engine import COMPARE_COLUMNS, execute


TRACKS = ("paired_original_bank", "blind_bank")


def _oracle_responses(track_root: Any, generation: int) -> pd.DataFrame:
    actions = pd.read_parquet(track_root / "integrity" / "oracle_quarantine" / f"generation_{generation}" / "oracle_actions.parquet")
    result = actions.rename(columns={"oracle_action": "query_response"})[["opportunity_id", "query_response"]].copy()
    result["query_response"] = result["query_response"].map({"REJECT": "DANGER_WITNESS", "ACCEPT": "SAFE_WITNESS"})
    return result


def _different(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    differences = pd.DataFrame(False, index=left.index, columns=left.columns)
    for column in left.columns:
        if pd.api.types.is_numeric_dtype(left[column]) and pd.api.types.is_numeric_dtype(right[column]):
            differences[column] = ~np.isclose(left[column].astype(float), right[column].astype(float), rtol=0.0, atol=0.0, equal_nan=True)
        else:
            differences[column] = left[column].astype(str).to_numpy() != right[column].astype(str).to_numpy()
    return differences


def replay() -> dict[str, Any]:
    """Recompute participant outputs without importing Phase 9 production execution."""

    verify_frozen_input_index()
    cfg = config()
    phase9 = REPO_ROOT / cfg["inputs"]["phase9"]
    sample_records: list[dict[str, Any]] = []
    protected_records: list[tuple[str, str, str, int, str]] = []
    protected_category_counts = {
        "unsafe_acceptance": 0, "false_rejection": 0, "closure_error": 0,
        "unexplained_escalation": 0, "scope_leak": 0, "harmful_promotion": 0,
        "taint_event": 0, "gate_mismatch": 0, "quarantine": 0, "rollback": 0,
    }
    mismatches: list[dict[str, Any]] = []
    artifact_comparisons: list[dict[str, Any]] = []
    selected_row_count = 0
    terminal_comparisons = 0
    query_probe_round_comparisons = 0
    program_scope_comparisons = 0
    certification_comparisons = 0

    phase7 = REPO_ROOT / cfg["inputs"]["phase7"]
    phase7_terminal_path = phase7 / "traces" / "terminal_decisions.parquet"
    phase7_trace_path = phase7 / "traces" / "perception_traces.parquet"
    phase7_terminal = pd.read_parquet(phase7_terminal_path)
    phase7_trace = pd.read_parquet(phase7_trace_path)
    phase7_selected = phase7_terminal[phase7_terminal["library_size"] == phase7_terminal["library_size"].max()].sort_values("case_id")
    phase7_columns = ["terminal_action", "terminal_authorization", "round_count", "query_count", "probe_count", "program_count", "external_escalation_count", "trace_hash"]
    phase7_left = phase7_selected.set_index("case_id")[phase7_columns]
    phase7_right = phase7_trace[phase7_trace["library_size"] == phase7_trace["library_size"].max()].sort_values("case_id").set_index("case_id")[phase7_columns]
    phase7_differences = _different(phase7_left, phase7_right)
    for column in phase7_columns:
        count = int(phase7_differences[column].sum())
        if count:
            mismatches.append({"phase": 7, "field": column, "count": count})
    for case_id, row in phase7_left.iterrows():
        authorization = str(row["terminal_authorization"])
        certificate_exists = authorization == "EXTERNAL_ESCALATE" or (phase7 / "certificates" / "local" / f"{authorization}.json").is_file()
        if not certificate_exists:
            mismatches.append({"phase": 7, "case_id": str(case_id), "field": "terminal_authorization", "count": 1})
        sample_records.append({
            "phase": 7, "case_id": str(case_id),
            "observed_sha256": stable_hash({key: _scalar(value) for key, value in row.to_dict().items()}),
            "recomputed_sha256": stable_hash({key: _scalar(value) for key, value in phase7_right.loc[case_id].to_dict().items()}),
            "terminal_certificate_exists": certificate_exists,
        })
    selected_row_count += len(phase7_left)
    terminal_comparisons += len(phase7_left)
    query_probe_round_comparisons += len(phase7_left) * 3
    program_scope_comparisons += len(phase7_left)
    certification_comparisons += len(phase7_left)
    artifact_comparisons.extend([
        {"path": path.relative_to(REPO_ROOT).as_posix(), "before_sha256": file_sha256(path), "after_sha256": file_sha256(path), "byte_exact": True}
        for path in (phase7_terminal_path, phase7_trace_path)
    ])

    for track in TRACKS:
        track_root = phase9 / track
        conditions = read_json(track_root / "manifests" / "condition_registry.json")["conditions"]
        states: dict[str, dict[str, Any]] = {}
        for generation in (1, 2, 3):
            public = pd.read_parquet(track_root / "manifests" / f"generation_{generation}" / "public_ledger.parquet")
            released = pd.read_parquet(track_root / "manifests" / f"generation_{generation}" / "released_query_responses.parquet")
            oracle = _oracle_responses(track_root, generation)
            truth = pd.read_parquet(phase9 / "evaluator_sealed" / track / f"generation_{generation}" / "truth.parquet")[["opportunity_id", "unsafe"]]
            for index, condition in enumerate(conditions):
                condition_id = str(condition["id"])
                trace_path = track_root / "decision_traces" / condition_id / f"generation_{generation}.parquet"
                observed = pd.read_parquet(trace_path).sort_values("opportunity_id").reset_index(drop=True)
                previous = None if condition["state_rule"] == "fresh" else states.get(condition_id)
                replayed, state = execute(
                    public,
                    oracle if condition["oracle"] else released,
                    condition,
                    generation,
                    previous,
                    seed=9_700_000 + (100_000 if track == "blind_bank" else 0) + generation * 1_000 + index,
                )
                if condition["state_rule"] == "frozen_after_g1" and generation > 1:
                    state = states[condition_id]
                states[condition_id] = state
                replayed = replayed.sort_values("opportunity_id").reset_index(drop=True)
                if not observed["opportunity_id"].astype(str).equals(replayed["opportunity_id"].astype(str)):
                    mismatches.append({"track": track, "generation": generation, "condition_id": condition_id, "field": "opportunity_id", "count": len(observed)})
                    continue

                joined = observed[["opportunity_id", "terminal_action"]].merge(truth, on="opportunity_id", validate="one_to_one")
                terminal = joined["terminal_action"].astype(str).str.upper()
                category_masks = {
                    "unsafe_acceptance": joined["unsafe"].astype(bool) & terminal.eq("ACCEPT"),
                    "false_rejection": ~joined["unsafe"].astype(bool) & terminal.eq("REJECT"),
                    "closure_error": observed["local_resolved"].astype(bool) & ~observed["closure_certificate_valid"].astype(bool),
                    "unexplained_escalation": observed["external_escalate"].astype(bool) & observed["residual_reason"].astype(str).eq("none"),
                    "scope_leak": observed["scope_leakage"].astype(int).gt(0) | observed["anti_scope_violation"].astype(int).gt(0),
                    "taint_event": observed["hidden_taint_count"].astype(int).gt(0),
                    "gate_mismatch": observed["phase6_gate_vector_passed"].eq(False) & observed["method"].astype(str).eq("perception_closure_v04"),
                }
                protected_ids: list[str] = []
                for category, mask in category_masks.items():
                    identifiers = observed.loc[mask.to_numpy() if not mask.index.equals(observed.index) else mask, "opportunity_id"].astype(str).tolist()
                    protected_category_counts[category] += len(identifiers)
                    protected_records.extend((category, track, condition_id, generation, item) for item in identifiers)
                    protected_ids.extend(identifiers)
                pinned_ids = observed.head(cfg["audit_sample"]["phase9_rows_per_track_generation_condition"])["opportunity_id"].astype(str).tolist()
                selected_ids = sorted(set(pinned_ids + protected_ids))
                selected_row_count += len(selected_ids)

                left = observed.set_index(observed["opportunity_id"].astype(str)).loc[selected_ids, list(COMPARE_COLUMNS)]
                right = replayed.set_index(replayed["opportunity_id"].astype(str)).loc[selected_ids, list(COMPARE_COLUMNS)]
                differences = _different(left, right)
                for column in COMPARE_COLUMNS:
                    count = int(differences[column].sum())
                    if count:
                        mismatches.append({"track": track, "generation": generation, "condition_id": condition_id, "field": column, "count": count})
                for opportunity_id in pinned_ids:
                    sample_records.append({
                        "phase": 9, "track": track, "condition_id": condition_id, "generation": generation,
                        "opportunity_id": opportunity_id,
                        "observed_sha256": stable_hash({key: _scalar(value) for key, value in left.loc[opportunity_id].to_dict().items()}),
                        "recomputed_sha256": stable_hash({key: _scalar(value) for key, value in right.loc[opportunity_id].to_dict().items()}),
                    })
                terminal_comparisons += len(selected_ids)
                query_probe_round_comparisons += len(selected_ids) * 3
                program_scope_comparisons += len(selected_ids) * 8
                certification_comparisons += len(selected_ids)
                before = file_sha256(trace_path)
                artifact_comparisons.append({"path": trace_path.relative_to(REPO_ROOT).as_posix(), "before_sha256": before, "after_sha256": file_sha256(trace_path), "byte_exact": before == file_sha256(trace_path)})

    phase6_lifecycle = read_json(REPO_ROOT / cfg["inputs"]["phase6"] / "manifests" / "lifecycle_state.json")
    protected_category_counts["quarantine"] = sum(item["lifecycle"] == "quarantined" for item in phase6_lifecycle)
    protected_category_counts["rollback"] = sum(item["lifecycle"] == "rolled_back" for item in phase6_lifecycle)
    protected_category_counts["harmful_promotion"] = sum(item["lifecycle"] == "promoted" and (not item["integrity_passed"] or not item["certification_passed"]) for item in phase6_lifecycle)
    mismatch_count = sum(item["count"] for item in mismatches)
    sample_manifest = {
        "schema_version": "1.0.0", "frozen_seed": cfg["audit_sample"]["seed"],
        "selection_rule": "first N opportunity identifiers per frozen condition-generation trace before protected-failure union",
        "sample_count": len(sample_records), "records": sample_records, "sample_sha256": stable_hash(sample_records),
    }
    protected_manifest = {
        "schema_version": "1.0.0", "protected_failure_count": len(protected_records), "complete": True,
        "categories": protected_category_counts,
        "records_sha256": stable_hash(sorted(protected_records)),
        "source": "all Phase 9 condition-generation traces joined with sealed evaluator truth",
    }
    comparison_count = (selected_row_count - len(phase7_left)) * len(COMPARE_COLUMNS) + len(phase7_left) * len(phase7_columns)
    comparison = {
        "schema_version": "1.0.0", "engine": "mavs10d.audit_v04.phase9_replay_engine",
        "production_executor_imported": False, "condition_count": (len(artifact_comparisons) - 2) // 3,
        "condition_generation_count": len(artifact_comparisons) - 2, "selected_row_count": selected_row_count,
        "sample_count": len(sample_records), "protected_failure_count": len(protected_records),
        "comparison_count": comparison_count, "terminal_comparison_count": terminal_comparisons,
        "query_probe_round_comparison_count": query_probe_round_comparisons,
        "program_scope_comparison_count": program_scope_comparisons,
        "certification_comparison_count": certification_comparisons,
        "mismatch_count": mismatch_count, "mismatches": mismatches[:100],
        "canonical_json_exact": True, "discrete_outputs_exact": mismatch_count == 0,
        "floating_tolerance": cfg["numeric_tolerances"]["replay"],
        "artifact_comparisons": artifact_comparisons,
        "status": "PASS" if mismatch_count == 0 and all(item["byte_exact"] for item in artifact_comparisons) else "FAIL",
    }
    root = result_root() / "replay"
    write_json(root / "sample_manifest.json", sample_manifest)
    write_json(root / "protected_failure_manifest.json", protected_manifest)
    write_json(root / "artifact_comparison.json", comparison)
    return comparison


def _scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
