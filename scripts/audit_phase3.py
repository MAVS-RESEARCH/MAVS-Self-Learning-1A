"""Independent fail-closed WorkPlan Phase 3 compliance and deterministic-replay audit."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.governance.self_learning.meta_diagnostics import MetaDiagnosticState, trigger_reasons  # noqa: E402
from run_phase3_stress import run_phase3  # type: ignore[import-not-found] # noqa: E402
from validate_phase3_separation import validate as validate_separation  # type: ignore[import-not-found] # noqa: E402
from validate_phase3_traces import validate as validate_traces  # type: ignore[import-not-found] # noqa: E402
from validate_phase3_updates import validate as validate_updates  # type: ignore[import-not-found] # noqa: E402
from inspect_phase3_library import inspect as inspect_library  # type: ignore[import-not-found] # noqa: E402


SELF_LEARNING_MODULES = (
    "controller.py", "memory.py", "ontology.py", "meta_diagnostics.py", "failure_attribution.py", "diagnostic_grammar.py",
    "proposal_engine.py", "validator.py", "safety_kernel.py", "config_library.py", "selector.py", "consolidation.py", "rollback.py",
)
REQUIRED_FILES = tuple(f"src/mavs10d/governance/self_learning/{name}" for name in SELF_LEARNING_MODULES) + (
    "configs/phases/phase3.yaml", "src/mavs10d/envs/phase3_gauntlet.py", "src/mavs10d/metrics/phase3.py",
    "scripts/compile_phase3_ledgers.py", "scripts/validate_phase3_separation.py", "scripts/run_phase3_stress.py",
    "scripts/make_phase3_cards.py", "scripts/validate_phase3_updates.py", "scripts/inspect_phase3_library.py",
    "scripts/validate_phase3_traces.py", "scripts/aggregate_phase3.py", "scripts/run_phase3.mjs",
)
PHASE3_SCRIPT_FILES = (
    "scripts/run_phase3.mjs", "scripts/compile_phase3_ledgers.py", "scripts/validate_phase3_separation.py", "scripts/run_phase3_stress.py",
    "scripts/make_phase3_cards.py", "scripts/validate_phase3_updates.py", "scripts/inspect_phase3_library.py",
    "scripts/validate_phase3_traces.py", "scripts/aggregate_phase3.py", "scripts/audit_phase3.py",
)


def audit(run_id: str) -> dict[str, object]:
    checks: dict[str, object] = {}
    checks["required_files"] = {path: (REPO_ROOT / path).exists() for path in REQUIRED_FILES}
    curricula = sorted((REPO_ROOT / "configs/repair_curricula").glob("*.yaml"))
    schemas = sorted((REPO_ROOT / "schemas").glob("phase3*.schema.json"))
    checks["curriculum_files"] = [str(path.relative_to(REPO_ROOT)) for path in curricula]
    checks["schema_files"] = [str(path.relative_to(REPO_ROOT)) for path in schemas]
    checks["separation_errors"] = validate_separation(run_id)
    checks["trace_errors"] = validate_traces(run_id, require_cards=True)
    checks["update_errors"] = validate_updates(run_id)
    library_report = inspect_library(run_id)
    checks["library_inspection"] = {"passed": library_report["passed"], "errors": library_report["errors"]}
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase3"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    generation_checks = {}
    for generation in (1, 2, 3):
        body = json.loads((manifest_root / f"generation_{generation}/generation_manifest.json").read_text(encoding="utf-8"))["body"]
        generation_checks[str(generation)] = {
            "canonical_opportunities": body["opportunity_count"],
            "worlds": body["world_count"],
            "curricula": body["curricula_count"],
            "operations": sorted(body["operations"]),
            "stage_counts": body["stage_counts"],
            "participant_final_access": body["participant_final_access"],
            "ledger_hash": body["ledger_sha256"],
        }
    checks["generations"] = generation_checks
    summary = pd.read_parquet(REPO_ROOT / "results/processed" / run_id / "phase3_summary.parquet")
    required_metrics = set(yaml.safe_load((REPO_ROOT / "configs/phases/phase3.yaml").read_text(encoding="utf-8"))["required_metrics"])
    checks["metrics"] = {
        "rows": len(summary),
        "complete": required_metrics <= set(summary.columns) and not bool(summary[list(required_metrics)].isna().any().any()),
        "harmful_promotion_rate_max": float(summary["harmful_promotion_rate"].max()),
        "median_recurrence_max": float(summary["median_recurrence"].max()),
        "rollback_correctness_min": float(summary["rollback_correctness"].min()),
        "trace_completeness_min": float(summary["trace_completeness"].min()),
        "rejected_candidates": int(summary["rejected_candidates"].sum()),
    }
    card_manifest = json.loads((REPO_ROOT / "results/reports" / run_id / "phase3_cards/card_manifest.json").read_text(encoding="utf-8"))
    terminal_errors = sum(
        int(pd.read_parquet(path)["terminal_error"].sum())
        for path in sorted((REPO_ROOT / "results/raw" / run_id / "phase3").glob("generation_*_*.parquet"))
    )
    checks["cards"] = {
        "terminal_errors": terminal_errors,
        "terminal_error_cards": card_manifest["artifacts"]["terminal_errors"]["records"],
        "unique_terminal_lineages": card_manifest["terminal_error_lineages"],
        "promotions": card_manifest["artifacts"]["promotions"]["records"],
        "rollbacks": card_manifest["artifacts"]["rollbacks"]["records"],
        "rejected_candidates": card_manifest["artifacts"]["rejected_candidates"]["records"],
        "genealogies": card_manifest["artifacts"]["genealogies"]["records"],
    }
    participant_sources = tuple(REPO_ROOT / "src/mavs10d/governance/self_learning" / name for name in ("controller.py", "meta_diagnostics.py", "failure_attribution.py", "proposal_engine.py", "selector.py"))
    forbidden = ("hidden_outcomes", "certification_cases.json", "hidden_repair_mechanism", "expected_operation", "catastrophic_if_accepted", "feedback_poisoned")
    checks["participant_hidden_access"] = {token: [str(path.relative_to(REPO_ROOT)) for path in participant_sources if token in path.read_text(encoding="utf-8")] for token in forbidden}
    checks["grammar"] = {
        "unrestricted_generated_code_absent": "exec(" not in (REPO_ROOT / "src/mavs10d/governance/self_learning/diagnostic_grammar.py").read_text(encoding="utf-8"),
        "operation_count": len({yaml.safe_load(path.read_text(encoding="utf-8"))["operation"] for path in curricula}),
    }
    repair_events = json.loads((REPO_ROOT / "results/raw" / run_id / "phase3/repair_events.json").read_text(encoding="utf-8"))["records"]
    observed_triggers = {reason for event in repair_events for reason in event["trigger_reasons"]}
    synthetic_triggers = set(
        trigger_reasons(
            MetaDiagnosticState(0.8, 0.1, 0.7, 0.1, 0.1, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1, 0.0),
            confirmed_error=True,
            recurring_escalations=5,
            significant_regression=True,
        )
    )
    checks["slow_loop_triggers"] = {
        "observed": sorted(observed_triggers),
        "machine_detectable": sorted(synthetic_triggers),
        "required": sorted({"confirmed_error", "recurring_escalation", "unexplained_novelty", "scope_leakage", "instability", "significant_regression"}),
    }
    with tempfile.TemporaryDirectory(prefix="mavs-phase3-replay-") as temporary:
        replay = run_phase3(run_id, Path(temporary))
        authoritative = json.loads((REPO_ROOT / "results/raw" / run_id / "phase3/stress_summary.json").read_text(encoding="utf-8"))
        checks["deterministic_replay"] = {
            "trace_hashes_match": [item["trace_sha256"] for item in replay["trace_files"]] == [item["trace_sha256"] for item in authoritative["trace_files"]],
            "repair_events_match": replay["repair_events_sha256"] == authoritative["repair_events_sha256"],
            "learning_artifacts_match": replay["learning_artifacts_sha256"] == authoritative["learning_artifacts_sha256"],
        }
    console_records, console_errors = _console_registry()
    checks["console_registry"] = {"records": console_records, "errors": console_errors}
    orchestration = json.loads((REPO_ROOT / "results/reports" / run_id / "orchestration_evidence.json").read_text(encoding="utf-8"))
    required_steps = {
        "clean_phase3_run", "inherited_tests_before", "phase3_ledgers_compiled", "separation_validated", "stress_executed",
        "traces_validated_without_cards", "cards_created", "updates_validated", "library_inspected", "traces_and_cards_validated",
        "metrics_aggregated", "phase3_tests", "full_regression", "inherited_smoke_after",
    }
    checks["orchestration_complete"] = set(orchestration["completed_steps"]) == required_steps
    smoke = REPO_ROOT / "results/raw" / run_id / "regression/synthetic_smoke.jsonl"
    checks["final_inherited_smoke_records"] = sum(1 for line in smoke.read_text(encoding="utf-8").splitlines() if line)
    checks["claim_boundary"] = run_manifest["claim_boundary"] == "controlled_mechanism_recovery_only" and run_manifest["model_training"] == "none" and run_manifest["post_holdout_retuning"] is False
    passed = (
        all(checks["required_files"].values()) and len(curricula) == 10 and len(schemas) >= 13
        and not checks["separation_errors"] and not checks["trace_errors"] and not checks["update_errors"] and checks["library_inspection"]["passed"]
        and all(item["canonical_opportunities"] == 20000 and item["worlds"] == 200 and item["curricula"] == 10 and len(item["operations"]) == 10 and item["participant_final_access"] is False for item in generation_checks.values())
        and checks["metrics"]["rows"] == 6 and checks["metrics"]["complete"] and checks["metrics"]["harmful_promotion_rate_max"] == 0.0
        and checks["metrics"]["median_recurrence_max"] == 0.0 and checks["metrics"]["rollback_correctness_min"] == 1.0 and checks["metrics"]["trace_completeness_min"] == 1.0
        and checks["cards"]["terminal_errors"] == checks["cards"]["terminal_error_cards"] == checks["cards"]["unique_terminal_lineages"]
        and checks["cards"]["promotions"] == checks["cards"]["rollbacks"] == 60 and checks["cards"]["rejected_candidates"] == 60 and checks["cards"]["genealogies"] == 6
        and all(not paths for paths in checks["participant_hidden_access"].values()) and checks["grammar"]["unrestricted_generated_code_absent"] and checks["grammar"]["operation_count"] == 10
        and set(checks["slow_loop_triggers"]["required"]) == set(checks["slow_loop_triggers"]["machine_detectable"])
        and {"confirmed_error", "recurring_escalation", "unexplained_novelty", "scope_leakage", "instability"} <= set(checks["slow_loop_triggers"]["observed"])
        and all(checks["deterministic_replay"].values()) and not console_errors and checks["orchestration_complete"]
        and checks["final_inherited_smoke_records"] == 8 and checks["claim_boundary"]
    )
    return {"schema_version": "1.0.0", "phase": 3, "run_id": run_id, "passed": passed, "checks": checks}


def _console_registry() -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in PHASE3_SCRIPT_FILES:
        path = REPO_ROOT / relative
        lines = path.read_text(encoding="utf-8").splitlines()
        expected_prefix = "// console.log:" if path.suffix == ".mjs" else "# console.log:"
        for index, line in enumerate(lines):
            stripped = line.strip()
            is_checkpoint = (
                stripped.startswith("console.log(")
                if path.suffix == ".mjs"
                else stripped.startswith("console_log(")
            )
            if not is_checkpoint:
                continue
            comment = lines[index - 1].strip() if index else ""
            event = comment.split("console.log:", 1)[-1].strip() if comment.startswith(expected_prefix) else ""
            matched = bool(event and event in line)
            record = {"file": relative, "comment_line": index, "statement_line": index + 1, "comment": comment, "event": event, "matched": matched}
            records.append(record)
            if not matched:
                errors.append(f"{relative}:{index + 1}")
    return records, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase3.audit.step01.start
    console_log("phase3.audit.step01.start", run_id=args.run_id)
    report = audit(args.run_id)
    output = REPO_ROOT / "results/reports" / args.run_id / "phase3_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    # console.log: phase3.audit.step02.complete
    console_log("phase3.audit.step02.complete", passed=report["passed"], output=str(output.relative_to(REPO_ROOT)))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
