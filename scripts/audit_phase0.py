"""Independent, fail-closed audit of every Phase 0 exit criterion."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log, validate_self_learning_trace_file, validate_trace_file  # noqa: E402
from mavs10d.envs.world_ledger import public_ledger_rows  # noqa: E402
from run_phase0_stress import run_generation  # type: ignore[import-not-found] # noqa: E402
from validate_generation_resets import validate_run  # type: ignore[import-not-found] # noqa: E402
from validate_participant_state import validate_path  # type: ignore[import-not-found] # noqa: E402


REQUIRED_FILES = (
    "REPRODUCIBILITY.md", "CLAIMS.md", "Makefile",
    "configs/suites/self_learning_300k.yaml", "configs/phases/phase0.yaml",
    "configs/worlds/generator_defaults.yaml", "configs/worlds/independent_generator.yaml",
    "schemas/world_manifest.schema.json", "schemas/decision_trace.schema.json",
    "schemas/participant_state.schema.json", "schemas/learning_event.schema.json",
    "schemas/diagnostic_proposal.schema.json", "schemas/candidate_configuration.schema.json",
    "schemas/certification_report.schema.json", "schemas/update_decision.schema.json",
    "scripts/clean_results.py", "scripts/compile_generation_ledgers.py",
    "scripts/aggregate_phase0.py",
    "scripts/validate_generation_resets.py", "scripts/validate_participant_state.py",
    "scripts/validate_updates.py", "src/mavs10d/envs/world_compiler.py",
    "src/mavs10d/envs/world_ledger.py", "src/mavs10d/corruption/composer.py",
    "src/mavs10d/corruption/adversarial_schedule.py", "src/mavs10d/metrics/burden.py",
    "src/mavs10d/metrics/frontier.py", "src/mavs10d/metrics/transfer.py",
)


def audit(run_id: str) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["required_files"] = {path: (REPO_ROOT / path).exists() for path in REQUIRED_FILES}
    checks["reset_errors"] = validate_run(run_id)
    schema_path = REPO_ROOT / "schemas/decision_trace.schema.json"
    trace_results: dict[str, Any] = {}
    total_canonical = 0
    total_replays = 0
    all_metric_identities = True
    all_metamorphic = True
    replay_equal = True
    for generation in (1, 2, 3):
        ledger = REPO_ROOT / "results/manifests" / run_id / f"generation_{generation}/world_ledger.parquet"
        public_rows = public_ledger_rows(ledger)
        total_canonical += len(public_rows)
        trace = REPO_ROOT / "results/raw" / run_id / "phase0" / f"generation_{generation}.jsonl"
        validation = validate_self_learning_trace_file(trace, schema_path)
        summary_path = trace.with_name(f"generation_{generation}_summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        total_replays += int(summary["replay_records"])
        all_metamorphic &= all(
            bool(summary["metamorphic"][name])
            for name in ("method_order_invariant", "permutation_invariant", "action_accounting_exact", "metric_recomputation_exact")
        ) and int(summary["metamorphic"]["non_oracle_future_reads"]) == 0
        for metrics in summary["metrics"].values():
            all_metric_identities &= int(metrics["accepted"]) + int(metrics["rejected"]) + int(metrics["escalated"]) == int(metrics["decisions"])
        checkpoint = REPO_ROOT / "results/checkpoints" / run_id / f"generation_{generation}/phase0_diagnostic_bound.json"
        participant_errors = validate_path(checkpoint)
        with tempfile.TemporaryDirectory(prefix=f"mavs-phase0-g{generation}-") as temporary:
            replay_summary = run_generation(run_id, generation, Path(temporary))
            replay_trace = Path(temporary) / f"generation_{generation}.jsonl"
            replay_equal &= file_sha256(replay_trace) == file_sha256(trace)
        trace_results[str(generation)] = {
            "records": validation.record_count,
            "errors": validation.errors,
            "participant_errors": participant_errors,
            "canonical_opportunities": len(public_rows),
            "replay_trace_sha256": replay_summary["trace_sha256"],
        }
    checks["traces"] = trace_results
    inherited_smoke = REPO_ROOT / "results/raw" / run_id / "regression/synthetic_smoke.jsonl"
    inherited_validation = validate_trace_file(inherited_smoke)
    checks["final_inherited_smoke"] = {
        "records": inherited_validation.record_count,
        "errors": inherited_validation.errors,
        "sha256": file_sha256(inherited_smoke) if inherited_smoke.exists() else None,
    }
    checks["canonical_opportunities_total"] = total_canonical
    checks["replay_records_total"] = total_replays
    checks["metric_identities"] = all_metric_identities
    checks["metamorphic"] = all_metamorphic
    checks["deterministic_replay_byte_equivalent"] = replay_equal
    results_root = REPO_ROOT / "results"
    forbidden_results = [
        str(path.relative_to(REPO_ROOT))
        for path in results_root.rglob("*")
        if path.is_file() and run_id not in path.parts
    ]
    checks["forbidden_or_inherited_results"] = forbidden_results
    phase = yaml.safe_load((REPO_ROOT / "configs/phases/phase0.yaml").read_text(encoding="utf-8"))
    checks["allocation_exact"] = sum(int(value) for value in phase["allocations"].values()) == 5000
    runner_lines = (REPO_ROOT / "scripts/run_phase0.mjs").read_text(encoding="utf-8").splitlines()
    console_lines = [index + 1 for index, line in enumerate(runner_lines) if "console.log(" in line]
    uncommented = [line for line in console_lines if line < 2 or not runner_lines[line - 2].strip().startswith("// console.log:")]
    mismatched_comments = [
        line for line in console_lines
        if runner_lines[line - 2].split("console.log:", 1)[-1].strip() not in runner_lines[line - 1]
    ]
    checks["console_log_lines"] = console_lines
    checks["uncommented_console_logs"] = uncommented
    checks["mismatched_console_log_comments"] = mismatched_comments
    orchestration_path = REPO_ROOT / "results/reports" / run_id / "orchestration_evidence.json"
    orchestration = json.loads(orchestration_path.read_text(encoding="utf-8")) if orchestration_path.exists() else {}
    required_orchestration = {
        "clean_results", "inherited_tests_before", "inherited_smoke_before",
        "regression_output_removed", "generation_ledgers_compiled",
        "generation_resets_and_participants_validated", "update_contract_validated",
        "stress_executed", "self_learning_traces_validated",
        "provenance_guarded_aggregation", "phase0_tests", "full_regression_tests",
        "inherited_smoke_after",
    }
    checks["orchestration_steps"] = orchestration.get("completed_steps", [])
    checks["orchestration_complete"] = set(checks["orchestration_steps"]) == required_orchestration
    passed = (
        all(checks["required_files"].values())
        and not checks["reset_errors"]
        and all(not item["errors"] and not item["participant_errors"] and item["records"] == 30000 for item in trace_results.values())
        and total_canonical == 15000
        and total_replays == 90000
        and all_metric_identities
        and all_metamorphic
        and replay_equal
        and not forbidden_results
        and checks["allocation_exact"]
        and not uncommented
        and not mismatched_comments
        and checks["orchestration_complete"]
        and inherited_validation.record_count == 8
        and not inherited_validation.errors
    )
    return {"phase": 0, "run_id": run_id, "passed": passed, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase0.audit.step01.start
    console_log("phase0.audit.step01.start", run_id=args.run_id)
    report = audit(args.run_id)
    output = REPO_ROOT / "results/reports" / args.run_id / "phase0_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    # console.log: phase0.audit.step02.complete
    console_log("phase0.audit.step02.complete", passed=report["passed"], report=str(output.relative_to(REPO_ROOT)))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
