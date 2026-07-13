"""Inspect Phase 3 memory chains, state persistence, libraries, ontologies, and rollback graphs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def inspect(run_id: str) -> dict[str, object]:
    errors: list[str] = []
    checkpoints: dict[str, object] = {}
    root = REPO_ROOT / "results/checkpoints" / run_id / "phase3"
    for generation in (1, 2, 3):
        for condition in ("cumulative", "fresh"):
            directory = root / f"generation_{generation}" / condition
            manifest = json.loads((directory / "checkpoint_manifest.json").read_text(encoding="utf-8"))
            key = f"generation_{generation}_{condition}"
            file_errors = [name for name, expected in manifest["files"].items() if file_sha256(directory / name) != expected]
            library = json.loads((directory / "configuration_library.json").read_text(encoding="utf-8"))
            records = library["records"]
            approved = [item for item in records if item["status"] == "approved"]
            non_base_approved = [item for item in approved if item["candidate_id"] is not None]
            invalid_approved = [item["config_id"] for item in non_base_approved if not item["certificate_hash"] or not item["rollback_target"] or item["eta"]["approval_status"] != "approved"]
            if file_errors:
                errors.append(f"{key}:file_hash:{file_errors}")
            if not manifest["memory_chain_valid"]:
                errors.append(f"{key}:memory_chain")
            if not all(manifest["forbidden_state_audit"].values()):
                errors.append(f"{key}:forbidden_state")
            if manifest["active_library_size"] > 32:
                errors.append(f"{key}:library_budget")
            if invalid_approved:
                errors.append(f"{key}:invalid_approved:{invalid_approved}")
            checkpoints[key] = {
                "memory_records": manifest["memory_records"],
                "memory_head_hash": manifest["memory_head_hash"],
                "retained_counterexamples": manifest["retained_counterexamples"],
                "failure_capsules": manifest["failure_capsules"],
                "uncertainty_entries": manifest["uncertainty_entries"],
                "active_library_size": manifest["active_library_size"],
                "total_library_size": manifest["total_library_size"],
                "library_hash": manifest["library_hash"],
                "ontology_hash": manifest["ontology_hash"],
                "file_errors": file_errors,
                "invalid_approved": invalid_approved,
            }
    report = {"schema_version": "1.0.0", "run_id": run_id, "passed": not errors, "errors": errors, "checkpoints": checkpoints}
    output = REPO_ROOT / "results/reports" / run_id / "phase3_library_inspection.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase3.library.step01.start
    console_log("phase3.library.step01.start", run_id=args.run_id)
    report = inspect(args.run_id)
    # console.log: phase3.library.step02.complete
    console_log("phase3.library.step02.complete", passed=report["passed"], errors=report["errors"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
