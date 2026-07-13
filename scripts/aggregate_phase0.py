"""Fail-closed Phase 0 aggregation with exact provenance matching."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, git_commit_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log, iter_jsonl  # noqa: E402


def aggregate(run_id: str) -> dict[str, object]:
    run_manifest_path = REPO_ROOT / "results/manifests" / run_id / "run_manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    if run_manifest["run_id"] != run_id:
        raise ValueError("Run-manifest ID mismatch.")
    expected_git = git_commit_hash(REPO_ROOT)
    expected_config = file_sha256(REPO_ROOT / "configs/phases/phase0.yaml")
    generation_summaries = []
    for generation in (1, 2, 3):
        manifest_path = REPO_ROOT / "results/manifests" / run_id / f"generation_{generation}/generation_manifest.json"
        manifest_envelope = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_ledger = manifest_envelope["body"]["ledger_sha256"]
        trace_path = REPO_ROOT / "results/raw" / run_id / "phase0" / f"generation_{generation}.jsonl"
        method_counts: Counter[str] = Counter()
        records = 0
        for record in iter_jsonl(trace_path):
            integrity = record["integrity"]
            mismatches = {
                "run_id": integrity["run_id"] != run_id,
                "git_sha": integrity["git_sha"] != expected_git,
                "config_hash": integrity["config_hash"] != expected_config,
                "ledger_hash": integrity["ledger_hash"] != expected_ledger,
            }
            failed = [name for name, mismatch in mismatches.items() if mismatch]
            if failed:
                raise ValueError(f"Trace provenance mismatch in generation {generation}: {failed}")
            method_counts[str(record["decision"]["method_id"])] += 1
            records += 1
        if records != 30000 or set(method_counts.values()) != {5000}:
            raise ValueError(f"Trace allocation mismatch in generation {generation}: {method_counts}")
        source_summary_path = trace_path.with_name(f"generation_{generation}_summary.json")
        source_summary = json.loads(source_summary_path.read_text(encoding="utf-8"))
        if source_summary["trace_sha256"] != file_sha256(trace_path):
            raise ValueError(f"Summary trace hash mismatch in generation {generation}.")
        generation_summaries.append(source_summary)
    result: dict[str, object] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "phase": 0,
        "claim_boundary": "diagnostic_bounds_only_non_competitive",
        "canonical_opportunities": sum(int(item["canonical_opportunities"]) for item in generation_summaries),
        "replay_records": sum(int(item["replay_records"]) for item in generation_summaries),
        "generation_summaries": generation_summaries,
        "provenance_validated": True,
    }
    output = REPO_ROOT / "results/processed" / run_id / "phase0_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase0.aggregate.step01.validate_provenance
    console_log("phase0.aggregate.step01.validate_provenance", run_id=args.run_id)
    result = aggregate(args.run_id)
    # console.log: phase0.aggregate.step02.complete
    console_log("phase0.aggregate.step02.complete", canonical_opportunities=result["canonical_opportunities"], replay_records=result["replay_records"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
