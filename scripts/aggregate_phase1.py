"""Aggregate Phase 1 metrics and Pareto operating points from frozen traces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.metrics.phase1 import nondominated_frontier, phase1_method_summary  # noqa: E402


def aggregate(run_id: str) -> dict[str, object]:
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase1"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    stress = json.loads((REPO_ROOT / "results/raw" / run_id / "phase1/stress_summary.json").read_text(encoding="utf-8"))
    frames = []
    for record in stress["generation_records"]:
        path = REPO_ROOT / record["trace_path"]
        if file_sha256(path) != record["trace_sha256"]:
            raise ValueError("Phase 1 trace hash mismatch.")
        frame = pd.read_parquet(path)
        if set(frame["implementation_git_sha"]) != {run_manifest["implementation_git_sha"]}:
            raise ValueError("Phase 1 implementation provenance mismatch.")
        frames.append(frame)
    traces = pd.concat(frames, ignore_index=True)
    summary, worlds = phase1_method_summary(traces)
    frontier = nondominated_frontier(summary)
    output = REPO_ROOT / "results/processed" / run_id
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "phase1_summary.parquet"
    worlds_path = output / "phase1_world_metrics.parquet"
    frontier_path = output / "phase1_frontier.parquet"
    summary.to_parquet(summary_path, index=False, compression="zstd")
    worlds.to_parquet(worlds_path, index=False, compression="zstd")
    frontier.to_parquet(frontier_path, index=False, compression="zstd")
    report = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "implementation_git_sha": run_manifest["implementation_git_sha"],
        "canonical_opportunities": 45000,
        "trace_records": len(traces),
        "summary_rows": len(summary),
        "world_metric_rows": len(worlds),
        "frontier_rows": len(frontier),
        "artifacts": {path.name: file_sha256(path) for path in (summary_path, worlds_path, frontier_path)},
        "claim_boundary": "dynamic_baseline_characterization_no_self_learning_superiority",
    }
    report_path = output / "phase1_aggregation.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    blind_rows = summary[summary["method_name"].isin(["ctta_entropy", "ctta_pseudo_label"])].to_dict(orient="records")
    blind_report = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "checkpoint_sha256": run_manifest["ctta_checkpoint_sha256"],
        "training_domains": ["synthetic_control", "retrieval_qa", "medical_triage_proxy"],
        "blind_domains": ["text_safety", "tool_use", "cyber_triage", "financial_approval_proxy", "multi_agent_operations"],
        "post_blind_retuning": False,
        "metrics": blind_rows,
    }
    blind_path = REPO_ROOT / "results/reports" / run_id / "ctta_blind_evaluation.json"
    blind_path.parent.mkdir(parents=True, exist_ok=True)
    blind_path.write_text(json.dumps(blind_report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    report["ctta_blind_evaluation_sha256"] = file_sha256(blind_path)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase1.aggregate.step01.start
    console_log("phase1.aggregate.step01.start", run_id=args.run_id)
    report = aggregate(args.run_id)
    # console.log: phase1.aggregate.step02.complete
    console_log("phase1.aggregate.step02.complete", **report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
