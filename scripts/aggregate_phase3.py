"""Aggregate Phase 3 repair, safety, burden, and library metrics."""

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
from mavs10d.metrics.phase3 import phase3_summary, rejected_candidate_inventory  # noqa: E402


def aggregate(run_id: str) -> dict[str, object]:
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase3"
    traces = pd.concat([pd.read_parquet(path) for path in sorted(raw_root.glob("generation_*_*.parquet"))], ignore_index=True)
    repair_events = pd.DataFrame(json.loads((raw_root / "repair_events.json").read_text(encoding="utf-8"))["records"])
    artifacts = json.loads((raw_root / "learning_artifacts.json").read_text(encoding="utf-8"))
    summary, curricula = phase3_summary(traces, repair_events)
    rejected = rejected_candidate_inventory(artifacts["rejected_candidates"])
    output = REPO_ROOT / "results/processed" / run_id
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "phase3_summary.parquet"
    curricula_path = output / "phase3_curriculum_metrics.parquet"
    rejected_path = output / "phase3_rejected_candidates.parquet"
    summary.to_parquet(summary_path, index=False)
    curricula.to_parquet(curricula_path, index=False)
    rejected.to_parquet(rejected_path, index=False)
    report = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "canonical_opportunities": 60000,
        "condition_decisions": len(traces),
        "summary_rows": len(summary),
        "curriculum_rows": len(curricula),
        "rejected_candidates": len(rejected),
        "artifacts": {
            summary_path.name: file_sha256(summary_path),
            curricula_path.name: file_sha256(curricula_path),
            rejected_path.name: file_sha256(rejected_path),
        },
        "claim_boundary": "controlled_mechanism_recovery_only",
    }
    (output / "phase3_aggregation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase3.aggregate.step01.start
    console_log("phase3.aggregate.step01.start", run_id=args.run_id)
    report = aggregate(args.run_id)
    # console.log: phase3.aggregate.step02.complete
    console_log("phase3.aggregate.step02.complete", **report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
