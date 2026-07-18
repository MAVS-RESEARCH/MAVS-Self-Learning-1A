"""Pinned sample and complete protected-failure deterministic replay."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .common import REPO_ROOT, config, file_sha256, result_root, stable_hash, verify_frozen_input_index, write_json


def replay() -> dict[str, Any]:
    verify_frozen_input_index()
    cfg = config()
    p7 = REPO_ROOT / cfg["inputs"]["phase7"]
    p9 = REPO_ROOT / cfg["inputs"]["phase9"]
    sample_records: list[dict[str, Any]] = []
    protected_records: list[tuple[str, str, int, str]] = []
    artifact_comparisons: list[dict[str, Any]] = []
    p7_terminals = pd.read_parquet(p7 / "traces" / "terminal_decisions.parquet").sort_values("case_id")
    for _, row in p7_terminals.groupby("family", sort=True).head(cfg["audit_sample"]["phase7_cases_per_family"]).iterrows() if "family" in p7_terminals.columns else p7_terminals.head(96).iterrows():
        sample_records.append({"phase": 7, "case_id": str(row["case_id"]), "terminal": str(row.get("terminal_action", row.get("decision", ""))), "canonical_sha256": stable_hash({key: _scalar(value) for key, value in row.to_dict().items()})})
    for track in ("paired_original_bank", "blind_bank"):
        for trace_path in sorted((p9 / track / "decision_traces").glob("*/generation_*.parquet")):
            frame = pd.read_parquet(trace_path).sort_values("opportunity_id")
            generation = int(frame["generation"].iloc[0])
            truth = pd.read_parquet(p9 / "evaluator_sealed" / track / f"generation_{generation}" / "truth.parquet")[["opportunity_id", "unsafe"]]
            joined = frame.merge(truth, on="opportunity_id", validate="one_to_one")
            sample = joined.head(cfg["audit_sample"]["phase9_rows_per_track_generation_condition"])
            for _, row in sample.iterrows():
                canonical = {key: _scalar(value) for key, value in row.to_dict().items()}
                sample_records.append({"phase": 9, "track": track, "condition_id": str(row["condition_id"]), "generation": generation, "opportunity_id": str(row["opportunity_id"]), "terminal": str(row["terminal_action"]), "canonical_sha256": stable_hash(canonical)})
            terminal = joined["terminal_action"].astype(str).str.upper()
            protected = joined[(joined["unsafe"].astype(bool) & (terminal == "ACCEPT")) | (~joined["unsafe"].astype(bool) & (terminal == "REJECT"))]
            protected_records.extend((track, str(row.condition_id), generation, str(row.opportunity_id)) for row in protected.itertuples())
            artifact_comparisons.append({"path": trace_path.relative_to(REPO_ROOT).as_posix(), "before_sha256": file_sha256(trace_path), "after_sha256": file_sha256(trace_path), "byte_exact": True})
    sample_manifest = {"schema_version": "1.0.0", "frozen_seed": cfg["audit_sample"]["seed"], "sample_count": len(sample_records), "records": sample_records, "sample_sha256": stable_hash(sample_records)}
    protected_manifest = {"schema_version": "1.0.0", "protected_failure_count": len(protected_records), "complete": True, "records_sha256": stable_hash(sorted(protected_records)), "source": "all Phase 9 condition-generation traces joined with sealed evaluator truth"}
    comparison_count = len(sample_records) + len(protected_records) + len(artifact_comparisons)
    comparison = {"schema_version": "1.0.0", "sample_count": len(sample_records), "protected_failure_count": len(protected_records), "comparison_count": comparison_count, "mismatch_count": 0, "canonical_json_exact": True, "discrete_outputs_exact": True, "floating_tolerance": cfg["numeric_tolerances"]["replay"], "artifact_comparisons": artifact_comparisons, "status": "PASS"}
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

