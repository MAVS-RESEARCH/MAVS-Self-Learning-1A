"""Aggregate Phase 2 corruption and partial-observability metrics."""

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
from mavs10d.metrics.phase2 import phase2_summary  # noqa: E402


def aggregate(run_id: str) -> dict[str, object]:
    manifest = json.loads((REPO_ROOT / "results/manifests" / run_id / "phase2/run_manifest.json").read_text(encoding="utf-8"))
    stress = json.loads((REPO_ROOT / "results/raw" / run_id / "phase2/stress_summary.json").read_text(encoding="utf-8"))
    frames = []
    for item in stress["generation_records"]:
        path = REPO_ROOT / item["trace_path"]
        if file_sha256(path) != item["trace_sha256"]:
            raise ValueError("Phase 2 trace hash mismatch")
        frame = pd.read_parquet(path)
        if set(frame["implementation_git_sha"]) != {manifest["implementation_git_sha"]}:
            raise ValueError("Phase 2 implementation provenance mismatch")
        frames.append(frame)
    traces = pd.concat(frames, ignore_index=True)
    summary, worlds = phase2_summary(traces)
    output = REPO_ROOT / "results/processed" / run_id
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "phase2_summary.parquet"
    world_path = output / "phase2_world_metrics.parquet"
    summary.to_parquet(summary_path, index=False, compression="zstd")
    worlds.to_parquet(world_path, index=False, compression="zstd")
    report = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "implementation_git_sha": manifest["implementation_git_sha"],
        "canonical_opportunities": 60000,
        "trace_records": len(traces),
        "summary_rows": len(summary),
        "world_metric_rows": len(worlds),
        "artifacts": {summary_path.name: file_sha256(summary_path), world_path.name: file_sha256(world_path)},
        "claim_boundary": manifest["claim_boundary"],
    }
    (output / "phase2_aggregation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase2.aggregate.step01.start
    console_log("phase2.aggregate.step01.start", run_id=args.run_id)
    report = aggregate(args.run_id)
    # console.log: phase2.aggregate.step02.complete
    console_log("phase2.aggregate.step02.complete", **report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
