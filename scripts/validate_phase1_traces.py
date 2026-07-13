"""Validate Phase 1 Parquet traces, allocations, matching, and feedback causality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.baselines.phase1_registry import expected_method_conditions  # noqa: E402
from mavs10d.core.hashing import stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    run_manifest = json.loads((REPO_ROOT / "results/manifests" / run_id / "phase1/run_manifest.json").read_text(encoding="utf-8"))
    for generation in (1, 2, 3):
        path = REPO_ROOT / "results/raw" / run_id / "phase1" / f"generation_{generation}.parquet"
        table = pq.read_table(path)
        frame = table.to_pandas()
        expected_methods = expected_method_conditions(generation)
        expected_records = len(expected_methods) * 15000
        if len(frame) != expected_records:
            errors.append(f"generation {generation}: expected {expected_records} records, observed {len(frame)}")
        observed_methods = set(zip(frame["method_name"], frame["condition"]))
        if observed_methods != set(expected_methods):
            errors.append(f"generation {generation}: method-condition matrix mismatch")
        opportunity_hashes = set()
        for _, group in frame.groupby(["method_name", "condition"]):
            if len(group) != 15000:
                errors.append(f"generation {generation}: a method did not receive 15,000 opportunities")
            opportunity_hashes.add(stable_hash(group["opportunity_id"].tolist()))
        if len(opportunity_hashes) != 1:
            errors.append(f"generation {generation}: matched opportunity identity failed")
        if set(frame["implementation_git_sha"]) != {run_manifest["implementation_git_sha"]}:
            errors.append(f"generation {generation}: implementation SHA mismatch")
        if bool((frame["feedback_observed_by_step"] & frame["feedback_release_step"].isna()).any()):
            errors.append(f"generation {generation}: censored feedback treated as observed")
        observed = frame[frame["feedback_observed_by_step"]]
        if bool((observed["feedback_release_step"] > observed["step"]).any()):
            errors.append(f"generation {generation}: future feedback read")
        identities = (
            frame["uar_error"].eq(frame["unsafe"] & frame["decision"].eq("accept")).all()
            and frame["frr_error"].eq(~frame["unsafe"] & frame["decision"].eq("reject")).all()
            and frame["escalated"].eq(frame["decision"].eq("escalate")).all()
        )
        if not identities:
            errors.append(f"generation {generation}: metric identity mismatch")
        resource_columns = ("calibration_examples", "calls", "tokens", "latency_ms", "wall_time_ms", "memory_bytes", "update_operations", "configuration_switches")
        if any(column not in frame.columns for column in resource_columns):
            errors.append(f"generation {generation}: resource accounting column missing")
        elif bool((frame[list(resource_columns)] < 0).any().any()):
            errors.append(f"generation {generation}: negative resource accounting value")
        for _, group in frame.groupby(["method_name", "condition", "world_id"], sort=False):
            if not group.sort_values("step")["calls"].is_monotonic_increasing:
                errors.append(f"generation {generation}: call accounting is not monotonic")
                break
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase1.validate_traces.step01.start
    console_log("phase1.validate_traces.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase1.validate_traces.step02.complete
    console_log("phase1.validate_traces.step02.complete", errors=errors, error_count=len(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
