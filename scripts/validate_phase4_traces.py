"""Stream-validate complete Phase 4 action identities, provenance, and matched coverage."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


REQUIRED = {
    "point_id", "family", "mechanism", "condition", "config_hash", "opportunity_id", "world_id",
    "action", "unsafe", "unsafe_accepted", "false_rejected", "escalated", "accepted", "rejected",
    "normalized_compute", "ledger_sha256", "git_sha", "environment_hash", "registry_sha256", "trace_complete",
}


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    root = REPO_ROOT / "results/raw" / run_id / "phase4"
    manifest = json.loads((root / "tournament_manifest.json").read_text(encoding="utf-8"))
    expected_points = int(manifest["operating_point_count"])
    total = 0
    for artifact in manifest["artifacts"]:
        path = REPO_ROOT / artifact["trace"]
        parquet = pq.ParquetFile(path)
        if not REQUIRED <= set(parquet.schema_arrow.names):
            errors.append(f"schema:g{artifact['generation']}:{sorted(REQUIRED - set(parquet.schema_arrow.names))}")
            continue
        counts: Counter[str] = Counter()
        rows = 0
        for batch in parquet.iter_batches(batch_size=100000, columns=sorted(REQUIRED)):
            data = batch.to_pydict()
            count = batch.num_rows
            rows += count
            counts.update(data["point_id"])
            for index in range(count):
                action = data["action"][index]
                unsafe = bool(data["unsafe"][index])
                if action not in {"accept", "reject", "escalate"}:
                    errors.append(f"action:g{artifact['generation']}:{rows-count+index}")
                    break
                if bool(data["unsafe_accepted"][index]) != (unsafe and action == "accept"):
                    errors.append(f"uar_identity:g{artifact['generation']}:{rows-count+index}")
                    break
                if bool(data["false_rejected"][index]) != ((not unsafe) and action == "reject"):
                    errors.append(f"frr_identity:g{artifact['generation']}:{rows-count+index}")
                    break
                if sum((bool(data["accepted"][index]), bool(data["rejected"][index]), bool(data["escalated"][index]))) != 1:
                    errors.append(f"action_partition:g{artifact['generation']}:{rows-count+index}")
                    break
                if not bool(data["trace_complete"][index]):
                    errors.append(f"trace_incomplete:g{artifact['generation']}:{rows-count+index}")
                    break
            if errors:
                return errors
        if rows != 25000 * expected_points or any(value != 25000 for value in counts.values()) or len(counts) != expected_points:
            errors.append(f"coverage:g{artifact['generation']}:rows={rows}:points={len(counts)}")
        if file_sha256(path) != artifact["trace_sha256"]:
            errors.append(f"trace_hash:g{artifact['generation']}")
        total += rows
    if total != int(manifest["trace_rows"]):
        errors.append(f"total_trace_rows:{total}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase4.traces.step01.start
    console_log("phase4.traces.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase4.traces.step02.complete
    console_log("phase4.traces.step02.complete", errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
